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
CITY_FIELDS = ("ville", "commune", "nom_de_la_commune")
POSTAL_FIELDS = ("code_postal", "code_postal_de_la_commune", "cp")
WEBSITE_FIELDS = ("url", "site_web", "url_du_site_web", "site_internet")
COORD_FIELDS = ("geo_point_2d", "coordonnees", "coordonnees_geographiques", "geolocalisation")


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

    count = await upsert_records(records)
    logger.info(
        "Référentiel musées : %d enregistrements récupérés, %d musées IDF synchronisés",
        len(records),
        count,
    )
    return count


async def upsert_records(records: list[dict[str, Any]]) -> int:
    """Filtre l'IDF (par code postal) et met à jour la table museums."""
    count = 0
    async with async_session_maker() as session:
        for raw in records:
            name = _first(raw, NAME_FIELDS)
            postal_code = _first(raw, POSTAL_FIELDS)
            postal_code = str(postal_code) if postal_code is not None else None
            department = normalizer.department_from_postal_code(postal_code)
            # Ne garder que les musées d'Île-de-France
            if not name or department is None:
                continue

            slug = normalizer.slugify(name)
            museum = (
                await session.execute(select(Museum).where(Museum.slug == slug))
            ).scalar_one_or_none()
            if museum is None:
                museum = Museum(name=name, slug=slug)
                session.add(museum)

            lat, lon = _coords(raw)
            museum.address = _first(raw, ADDRESS_FIELDS) or museum.address
            museum.city = _first(raw, CITY_FIELDS) or museum.city
            museum.postal_code = postal_code or museum.postal_code
            museum.department = department or museum.department
            if lat is not None:
                museum.latitude = lat
            if lon is not None:
                museum.longitude = lon
            museum.website_url = _first(raw, WEBSITE_FIELDS) or museum.website_url
            count += 1
        await session.commit()
    return count
