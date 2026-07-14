"""Classe de base des collecteurs : normalisation -> upsert -> déduplication.

Chaque collecteur produit des dictionnaires "événement normalisé" :

    {
        "external_id": str | None,   # généré par hash si absent
        "title": str,
        "description": str | None,
        "event_type": str | None,
        "date_start": date,          # requis
        "date_end": date | None,
        "time_start": time | None,
        "time_end": time | None,
        "is_permanent": bool,
        "price_info": str | None,
        "image_url": str | None,
        "event_url": str | None,
        "audience": str | None,
        "raw_data": dict | None,
        "museum": {                  # optionnel : rattachement au musée
            "name": str, "address": str, "city": str, "postal_code": str,
            "latitude": float, "longitude": float, "website_url": str,
            "openagenda_uid": str,
        },
    }
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models import Event, Museum
from app.services.deduplicator import deduplicate_events
from app.utils import normalizer

logger = logging.getLogger(__name__)

# Champs recopiés tels quels lors de l'upsert
_EVENT_FIELDS = (
    "title",
    "description",
    "event_type",
    "date_start",
    "date_end",
    "time_start",
    "time_end",
    "is_permanent",
    "price_info",
    "image_url",
    "event_url",
    "audience",
    "raw_data",
)


class BaseCollector(ABC):
    """Un collecteur = une source de données (API ou scraping)."""

    source: str = "unknown"

    @abstractmethod
    async def collect(self) -> list[dict[str, Any]]:
        """Récupère et normalise les événements de la source."""

    async def run(self) -> dict[str, int]:
        """Point d'entrée : collecte puis sauvegarde dans sa propre session."""
        events = await self.collect()
        async with async_session_maker() as session:
            stats = await self.save(session, events)
            await session.commit()
        logger.info("[%s] %s", self.source, stats)
        return stats

    async def save(self, session: AsyncSession, events: list[dict[str, Any]]) -> dict[str, int]:
        created = updated = skipped = 0
        saved: list[Event] = []
        museum_cache: dict[str, Museum] = {}

        for data in events:
            if not data.get("title") or not data.get("date_start"):
                skipped += 1
                continue

            museum = None
            if data.get("museum"):
                museum = await self._get_or_create_museum(session, data["museum"], museum_cache)
            elif data.get("museum_id"):
                museum = await session.get(Museum, data["museum_id"])

            external_id = data.get("external_id") or normalizer.stable_external_id(
                data["title"], data["date_start"], museum.name if museum else None
            )

            existing = (
                await session.execute(
                    select(Event).where(
                        Event.source == self.source, Event.external_id == external_id
                    )
                )
            ).scalar_one_or_none()

            if existing is None:
                event = Event(source=self.source, external_id=external_id)
                session.add(event)
                created += 1
            else:
                event = existing
                updated += 1

            for field in _EVENT_FIELDS:
                if field in data:
                    setattr(event, field, data[field])
            event.title = normalizer.truncate(event.title, 500) or event.title
            # Garde-fou toutes sources : une URL non chargeable (objet, nom de
            # fichier nu, > 500 car.) vaut mieux absente que cassée à l'affichage
            event.image_url = normalizer.clean_url(event.image_url)
            event.event_url = normalizer.clean_url(event.event_url)
            if museum is not None:
                event.museum = museum
            saved.append(event)

        await session.flush()
        duplicates = await deduplicate_events(session, saved)
        return {"created": created, "updated": updated, "skipped": skipped, "duplicates": duplicates}

    async def _get_or_create_museum(
        self,
        session: AsyncSession,
        data: dict[str, Any],
        cache: dict[str, Museum],
    ) -> Museum | None:
        name = (data.get("name") or "").strip()
        if not name:
            return None
        slug = normalizer.slugify(name)
        if slug in cache:
            return cache[slug]

        museum = (
            await session.execute(select(Museum).where(Museum.slug == slug))
        ).scalar_one_or_none()
        if museum is None:
            museum = Museum(name=name, slug=slug)
            session.add(museum)

        # Complète les champs manquants sans écraser le référentiel existant
        for field in (
            "address",
            "city",
            "postal_code",
            "latitude",
            "longitude",
            "website_url",
            "openagenda_uid",
            "logo_url",
        ):
            if data.get(field) and getattr(museum, field, None) in (None, ""):
                setattr(museum, field, data[field])
        if not museum.department:
            museum.department = normalizer.department_from_postal_code(museum.postal_code)

        await session.flush()
        cache[slug] = museum
        return museum
