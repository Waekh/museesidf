"""Filtre Île-de-France : rejet à la sauvegarde + purge de l'existant."""

from datetime import date

import pytest
from sqlalchemy import select

from app.collectors.base import BaseCollector, is_non_idf
from app.models import Event, Museum
from app.services.idf_cleanup import purge_non_idf
from app.utils import normalizer


class _Collector(BaseCollector):
    source = "test"

    async def collect(self):
        return []


def test_is_idf_location_signals():
    assert normalizer.is_idf_location("75001") is True
    assert normalizer.is_idf_location("94400") is True
    assert normalizer.is_idf_location("69002") is False  # Lyon
    assert normalizer.is_idf_location(None, 48.86, 2.33) is True  # Paris (bbox)
    assert normalizer.is_idf_location(None, 45.75, 4.85) is False  # Lyon (bbox)
    assert normalizer.is_idf_location(None) is None  # indéterminé


def test_is_non_idf_only_true_when_proven_outside():
    assert is_non_idf({"postal_code": "69002"}) is True
    assert is_non_idf({"postal_code": "75001"}) is False
    assert is_non_idf({"latitude": 45.75, "longitude": 4.85}) is True
    assert is_non_idf({}) is False  # indéterminé -> conservé


def _event(museum: dict | None) -> dict:
    return {
        "external_id": (museum or {}).get("name", "x"),
        "title": "Événement",
        "date_start": date(2026, 9, 1),
        "museum": museum,
    }


async def test_save_rejects_non_idf_events(session):
    collector = _Collector()
    events = [
        _event({"name": "Musée du Louvre", "postal_code": "75001"}),      # IDF
        _event({"name": "Musée de Lyon", "postal_code": "69002"}),        # hors IDF
        _event({"name": "Musée sans CP"}),                                # indéterminé -> gardé
    ]
    stats = await collector.save(session, events)
    await session.commit()

    titles_sources = (await session.execute(select(Museum.name))).scalars().all()
    assert "Musée du Louvre" in titles_sources
    assert "Musée sans CP" in titles_sources
    assert "Musée de Lyon" not in titles_sources  # rejeté
    assert stats["skipped"] == 1


async def test_purge_removes_existing_non_idf(session):
    idf = Museum(name="Louvre", slug="louvre", postal_code="75001")
    lyon = Museum(name="Confluences", slug="confluences", postal_code="69002")
    session.add_all([idf, lyon])
    await session.flush()
    session.add_all(
        [
            Event(source="s", external_id="a", title="Expo IDF", date_start=date(2026, 9, 1), museum_id=idf.id),
            Event(source="s", external_id="b", title="Expo Lyon", date_start=date(2026, 9, 1), museum_id=lyon.id),
        ]
    )
    await session.commit()

    result = await purge_non_idf(session)
    await session.commit()

    assert result == {"museums_removed": 1, "events_removed": 1}
    remaining_museums = (await session.execute(select(Museum.name))).scalars().all()
    assert remaining_museums == ["Louvre"]
    remaining_events = (await session.execute(select(Event.title))).scalars().all()
    assert remaining_events == ["Expo IDF"]
