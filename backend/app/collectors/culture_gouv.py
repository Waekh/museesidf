"""Référentiel des Musées de France — data.culture.gouv.fr.

Ce collecteur ne produit pas d'événements : il alimente la table `museums`
avec les ~200 musées officiels d'Île-de-France (nom, adresse, GPS, site web),
utilisée ensuite comme base pour le scraping et l'affichage carte.

Robustesse : les noms de champs des jeux Opendatasoft varient (ex. le point
géo est tantôt `coordonnees`, tantôt `geo_point_2d`). On essaie donc plusieurs
noms candidats pour chaque champ, et on filtre l'Île-de-France via le code
postal (déterministe) plutôt que via la chaîne `region_administrative` (dont
la casse/les accents peuvent différer et casser un filtre exact).
"""

import logging
from typing import Any

import httpx
from sqlalchemy import select

from app.database import async_session_maker
from app.models import Museum
from app.utils import normalizer

logger = logging.getLogger(__name__)

BASE_URL = "https://data.culture.gouv.fr/api/explore/v2.1/catalog/datasets"
DATASET = "liste-et-localisation-des-musees-de-france"
PAGE_SIZE = 100
MAX_RECORDS = 5000  # garde-fou pagination

# Noms de champs candidats (le premier renseigné gagne)
# nom_officiel_du_musee = champ réel de l'API en ligne (vérifié) — prioritaire
NAME_FIELDS = ("nom_officiel_du_musee", "nom_officiel", "nom_du_musee", "nom")
ADDRESS_FIELDS = ("adresse", "adresse_complete", "adresse_1")
CITY_FIELDS = ("ville", "commune", "nom_de_la_commune", "commune_du_musee")
POSTAL_FIELDS = ("code_postal", "code_postal_de_la_commune", "code_postal_du_musee", "cp")
WEBSITE_FIELDS = ("url", "site_web", "url_du_site_web", "site_internet")
COORD_FIELDS = (
    "geo_point_2d",
    "coordonnees",
    "coordonnees_geographiques",
    "geolocalisation",
    "geo_point",
    "geolocalisation_ban",
)
REGION_FIELDS = ("region_administrative", "region", "nouvelle_region")
DEPT_FIELDS = ("departement", "departement_de_la_commune", "nom_du_departement", "dpt")

# Détection Île-de-France
IDF_DEPT_CODES = {"75", "77", "78", "91", "92", "93", "94", "95"}
IDF_DEPT_NAMES = {normalizer.strip_accents(n).lower() for n in normalizer.IDF_DEPARTMENTS.values()}
# Boîte englobante approximative de l'IDF (repli si ni CP ni région exploitables)
IDF_BBOX = (48.10, 49.25, 1.40, 3.60)  # lat_min, lat_max, lon_min, lon_max


def _first(raw: dict[str, Any], fields: tuple[str, ...]) -> Any:
    for field in fields:
        value = raw.get(field)
        if value not in (None, ""):
            return value
    return None


def _coords(raw: dict[str, Any]) -> tuple[float | None, float | None]:
    """Extrait (latitude, longitude) quelle que soit la forme du champ géo.

    Gère : {"lat":..,"lon":..}, {"lat":..,"lng":..}, [lat, lon] (convention
    Opendatasoft geo_point_2d), ou "lat,lon".
    """
    value = _first(raw, COORD_FIELDS)
    if value is None:
        return None, None
    if isinstance(value, dict):
        lat = value.get("lat") if value.get("lat") is not None else value.get("latitude")
        lon = value.get("lon")
        if lon is None:
            lon = value.get("lng") if value.get("lng") is not None else value.get("longitude")
        return _as_float(lat), _as_float(lon)
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        # geo_point_2d : [latitude, longitude]
        return _as_float(value[0]), _as_float(value[1])
    if isinstance(value, str) and "," in value:
        lat_str, lon_str = value.split(",", 1)
        return _as_float(lat_str), _as_float(lon_str)
    return None, None


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _in_idf_bbox(lat: float | None, lon: float | None) -> bool:
    if lat is None or lon is None:
        return False
    lat_min, lat_max, lon_min, lon_max = IDF_BBOX
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def _department_from_field(raw: dict[str, Any]) -> str | None:
    """Déduit un département IDF depuis un champ 'departement' (nom ou code)."""
    value = _first(raw, DEPT_FIELDS)
    if value is None:
        return None
    text = normalizer.strip_accents(str(value)).lower().strip()
    # Code à 2 chiffres présent dans la valeur (ex. "78", "Yvelines (78)")
    for code in IDF_DEPT_CODES:
        if code in text:
            return normalizer.IDF_DEPARTMENTS[code]
    # Nom de département
    for name in normalizer.IDF_DEPARTMENTS.values():
        if normalizer.strip_accents(name).lower() in text:
            return name
    return None


def _region_is_idf(raw: dict[str, Any]) -> bool:
    value = _first(raw, REGION_FIELDS)
    if value is None:
        return False
    text = normalizer.strip_accents(str(value)).lower()
    return "ile-de-france" in text or ("ile" in text and "france" in text)


def idf_department(
    raw: dict[str, Any], postal_code: str | None, lat: float | None, lon: float | None
) -> str | None:
    """Retourne le département IDF du musée, ou None s'il n'est pas en IDF.

    Multi-signaux, du plus fiable au moins fiable : code postal → champ
    département → région IDF → position dans la boîte englobante IDF. Cette
    redondance évite de tout jeter si un seul nom de champ diffère.
    """
    dept = normalizer.department_from_postal_code(postal_code)
    if dept:
        return dept
    dept = _department_from_field(raw)
    if dept:
        return dept
    if _region_is_idf(raw) or _in_idf_bbox(lat, lon):
        return ""  # IDF confirmée mais département précis inconnu
    return None


async def sync_museums() -> int:
    """Upsert des musées IDF depuis le référentiel du ministère de la Culture."""
    records: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=30) as client:
        offset = 0
        while offset < MAX_RECORDS:
            try:
                resp = await client.get(
                    f"{BASE_URL}/{DATASET}/records",
                    params={"limit": PAGE_SIZE, "offset": offset},
                )
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                logger.error("data.culture.gouv.fr : %s", exc)
                break
            results = resp.json().get("results", [])
            records.extend(results)
            if len(results) < PAGE_SIZE:
                break
            offset += PAGE_SIZE

    # Diagnostic : noms de champs réels du dataset (utile en cas de 0 musée)
    if records:
        logger.info(
            "Référentiel : champs disponibles du 1er enregistrement : %s",
            sorted(records[0].keys()),
        )

    count = await upsert_records(records)
    logger.info(
        "Référentiel musées : %d enregistrements récupérés, %d musées IDF synchronisés",
        len(records),
        count,
    )
    return count


async def upsert_records(records: list[dict[str, Any]]) -> int:
    """Filtre l'IDF (multi-signaux) et met à jour la table museums."""
    count = 0
    async with async_session_maker() as session:
        for raw in records:
            name = _first(raw, NAME_FIELDS)
            if not name:
                continue
            postal_code = _first(raw, POSTAL_FIELDS)
            postal_code = str(postal_code) if postal_code is not None else None
            lat, lon = _coords(raw)

            department = idf_department(raw, postal_code, lat, lon)
            if department is None:  # hors Île-de-France
                continue

            slug = normalizer.slugify(name)
            museum = (
                await session.execute(select(Museum).where(Museum.slug == slug))
            ).scalar_one_or_none()
            if museum is None:
                museum = Museum(name=name, slug=slug)
                session.add(museum)

            museum.address = _first(raw, ADDRESS_FIELDS) or museum.address
            museum.city = _first(raw, CITY_FIELDS) or museum.city
            museum.postal_code = postal_code or museum.postal_code
            if department:  # non vide
                museum.department = department
            if lat is not None:
                museum.latitude = lat
            if lon is not None:
                museum.longitude = lon
            museum.website_url = _first(raw, WEBSITE_FIELDS) or museum.website_url
            count += 1
        await session.commit()
    return count
