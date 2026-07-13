"""Référentiel des Musées de France — data.culture.gouv.fr.

Ce collecteur ne produit pas d'événements : il alimente la table `museums`
avec les ~200 musées officiels d'Île-de-France (nom, adresse, GPS, site web),
utilisée ensuite comme base pour le scraping et l'affichage carte.
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


async def sync_museums() -> int:
    """Upsert des musées IDF depuis le référentiel du ministère de la Culture."""
    records: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=30) as client:
        offset = 0
        while True:
            try:
                resp = await client.get(
                    f"{BASE_URL}/{DATASET}/records",
                    params={
                        "where": 'region_administrative = "Île-de-France"',
                        "limit": PAGE_SIZE,
                        "offset": offset,
                    },
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

    count = 0
    async with async_session_maker() as session:
        for raw in records:
            name = raw.get("nom_officiel_du_musee") or raw.get("nom_officiel") or raw.get("nom_du_musee")
            if not name:
                continue
            slug = normalizer.slugify(name)
            museum = (
                await session.execute(select(Museum).where(Museum.slug == slug))
            ).scalar_one_or_none()
            if museum is None:
                museum = Museum(name=name, slug=slug)
                session.add(museum)

            coords = raw.get("coordonnees") or {}
            postal_code = raw.get("code_postal")
            museum.address = raw.get("adresse") or museum.address
            museum.city = raw.get("ville") or raw.get("commune") or museum.city
            museum.postal_code = postal_code or museum.postal_code
            museum.department = (
                normalizer.department_from_postal_code(postal_code) or museum.department
            )
            museum.latitude = coords.get("lat") or museum.latitude
            museum.longitude = coords.get("lon") or museum.longitude
            museum.website_url = raw.get("url") or museum.website_url
            count += 1
        await session.commit()
    logger.info("Référentiel musées synchronisé : %d musées IDF", count)
    return count
