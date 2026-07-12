from datetime import date, time

from sqlalchemy import select

from app.collectors.openagenda import OpenAgendaCollector
from app.models import Event, Museum

SAMPLE_RAW = {
    "uid": 123456,
    "slug": "monet-en-lumiere",
    "title": {"fr": "Monet en lumière", "en": "Monet in light"},
    "description": {"fr": "Une exposition exceptionnelle."},
    "longDescription": {"fr": "Une exposition exceptionnelle sur l'impressionnisme."},
    "dateRange": {"fr": "Du 1er au 30 septembre 2026"},
    "keywords": {"fr": ["exposition", "peinture"]},
    "conditions": {"fr": "12€, gratuit -18 ans"},
    "age": {"fr": "Tout public"},
    "firstTiming": {"begin": "2026-09-01T10:00:00+02:00", "end": "2026-09-01T18:00:00+02:00"},
    "lastTiming": {"begin": "2026-09-30T10:00:00+02:00", "end": "2026-09-30T18:00:00+02:00"},
    "image": {"base": {"url": "https://cdn.openagenda.com/img.jpg"}},
    "location": {
        "name": "Musée d'Orsay",
        "address": "1 rue de la Légion d'Honneur",
        "postalCode": "75007",
        "city": "Paris",
        "latitude": 48.86,
        "longitude": 2.32,
    },
    "originAgenda": {"uid": 999, "slug": "paris-musees"},
}


def test_normalize_maps_all_fields():
    event = OpenAgendaCollector.normalize(SAMPLE_RAW)
    assert event is not None
    assert event["external_id"] == "123456"
    assert event["title"] == "Monet en lumière"
    assert "impressionnisme" in event["description"]
    assert event["event_type"] == "exposition"
    assert event["date_start"] == date(2026, 9, 1)
    assert event["date_end"] == date(2026, 9, 30)
    assert event["time_start"] == time(10, 0)
    assert event["time_end"] == time(18, 0)
    assert event["price_info"] == "12€, gratuit -18 ans"
    assert event["image_url"] == "https://cdn.openagenda.com/img.jpg"
    assert event["event_url"] == "https://openagenda.com/paris-musees/events/monet-en-lumiere"
    assert event["audience"] == "tout public"
    assert event["museum"]["name"] == "Musée d'Orsay"
    assert event["museum"]["postal_code"] == "75007"


def test_normalize_rejects_incomplete_events():
    assert OpenAgendaCollector.normalize({"uid": 1}) is None
    assert OpenAgendaCollector.normalize({"title": {"fr": "Sans date"}}) is None


async def test_save_creates_event_and_museum(session):
    collector = OpenAgendaCollector()
    normalized = OpenAgendaCollector.normalize(SAMPLE_RAW)

    stats = await collector.save(session, [normalized])
    await session.commit()

    assert stats["created"] == 1
    event = (await session.execute(select(Event))).scalar_one()
    assert event.source == "openagenda"
    assert event.external_id == "123456"

    museum = (await session.execute(select(Museum))).scalar_one()
    assert museum.slug == "musee-d-orsay"
    assert museum.department == "Paris"  # déduit du code postal 75007
    assert event.museum_id == museum.id


async def test_save_upserts_on_source_external_id(session):
    collector = OpenAgendaCollector()
    normalized = OpenAgendaCollector.normalize(SAMPLE_RAW)

    await collector.save(session, [normalized])
    updated = dict(normalized, title="Monet en lumière — prolongation")
    stats = await collector.save(session, [updated])
    await session.commit()

    assert stats["created"] == 0
    assert stats["updated"] == 1
    events = (await session.execute(select(Event))).scalars().all()
    assert len(events) == 1
    assert events[0].title == "Monet en lumière — prolongation"
