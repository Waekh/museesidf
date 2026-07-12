"""Détection des doublons entre sources.

Deux événements sont considérés comme doublons si :
- similarité de Levenshtein sur le titre >= 85 %,
- même date_start,
- même museum_id (et sources différentes).

L'événement le plus complet (description la plus longue) est conservé ;
l'autre est marqué is_duplicate + duplicate_of_id.
"""

import logging
from collections.abc import Sequence

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 85.0


def titles_similar(a: str, b: str, threshold: float = SIMILARITY_THRESHOLD) -> bool:
    return fuzz.ratio(a.casefold().strip(), b.casefold().strip()) >= threshold


def pick_keeper(a: Event, b: Event) -> tuple[Event, Event]:
    """Retourne (conservé, doublon) : le plus complet gagne."""
    len_a = len(a.description or "")
    len_b = len(b.description or "")
    if len_a >= len_b:
        return a, b
    return b, a


async def deduplicate_events(session: AsyncSession, events: Sequence[Event]) -> int:
    """Compare chaque événement fraîchement sauvé aux événements existants
    du même musée / même date provenant d'autres sources."""
    marked = 0
    for event in events:
        if event.is_duplicate or event.museum_id is None:
            continue
        candidates = (
            (
                await session.execute(
                    select(Event).where(
                        Event.museum_id == event.museum_id,
                        Event.date_start == event.date_start,
                        Event.source != event.source,
                        Event.is_duplicate.is_(False),
                        Event.id != event.id,
                    )
                )
            )
            .scalars()
            .all()
        )
        for candidate in candidates:
            if not titles_similar(event.title, candidate.title):
                continue
            keeper, duplicate = pick_keeper(event, candidate)
            duplicate.is_duplicate = True
            duplicate.duplicate_of_id = keeper.id
            marked += 1
            logger.debug(
                "Doublon : '%s' (%s) -> conserve '%s' (%s)",
                duplicate.title,
                duplicate.source,
                keeper.title,
                keeper.source,
            )
            if duplicate is event:
                break
    await session.flush()
    return marked
