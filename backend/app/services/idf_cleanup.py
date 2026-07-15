"""Purge des données déjà stockées mais situées hors Île-de-France.

Le filtre à la sauvegarde (base.py) empêche les nouvelles entrées hors IDF,
mais les collectes précédentes ont pu créer des musées/événements nationaux
(agendas OpenAgenda non franciliens). Cette purge nettoie l'existant.
"""

import logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event, Museum
from app.utils import normalizer

logger = logging.getLogger(__name__)


async def purge_non_idf(session: AsyncSession) -> dict[str, int]:
    """Supprime les musées prouvés hors IDF et leurs événements."""
    museums = (await session.execute(select(Museum))).scalars().all()
    non_idf_ids = [
        m.id
        for m in museums
        if normalizer.is_idf_location(m.postal_code, m.latitude, m.longitude) is False
    ]
    if not non_idf_ids:
        return {"museums_removed": 0, "events_removed": 0}

    events_removed = (
        await session.execute(
            delete(Event).where(Event.museum_id.in_(non_idf_ids))
        )
    ).rowcount or 0
    museums_removed = (
        await session.execute(delete(Museum).where(Museum.id.in_(non_idf_ids)))
    ).rowcount or 0

    logger.info(
        "Purge hors-IDF : %d musées et %d événements supprimés",
        museums_removed,
        events_removed,
    )
    return {"museums_removed": museums_removed, "events_removed": events_removed}
