from datetime import date

from sqlalchemy import select

from app.collectors.paris_opendata import ParisOpenDataCollector
from app.models import Event, Museum

SAMPLE_RAW = {
    "id": "evt-42",
    "title": "Atelier gravure au Petit Palais",
    "lead_text": "Initiation à la gravure.",
    "body": "Un atelier pour découvrir la gravure sur cuivre.",
    "date_start": "2026-10-05T14:00:00+02:00",
    "date_end": "2026-10-05T17:00:00+02:00",
    "address_name": "Petit Palais",
    "address_street": "Avenue Winston Churchill",
    "address_zipcode": "75008",
    "address_city": "Paris",
    "lat_lon": {"lat": 48.866, "lon": 2.314},
    "url": "https://quefaire.paris.fr/evt-42",
    "cover_url": "https://cdn.paris.fr/img.jpg",
    "tags": ["musée", "atelier"],
    "category": "Atelier",
    "audience": "Enfants à partir de 8 ans",
    "price_type": "payant",
}


def test_normalize_maps_all_fields():
    event = ParisOpenDataCollector.normalize(SAMPLE_RAW)
    assert event is not None
    assert event["external_id"] == "evt-42"
    assert event["title"] == "Atelier gravure au Petit Palais"
    assert "Initiation" in event["description"]
    assert "cuivre" in event["description"]
    assert event["event_type"] == "atelier"
    assert event["date_start"] == date(2026, 10, 5)
    assert event["date_end"] == date(2026, 10, 5)
    assert event["audience"] == "enfants"
    assert event["event_url"] == "https://quefaire.paris.fr/evt-42"
    assert event["museum"]["name"] == "Petit Palais"
    assert event["museum"]["latitude"] == 48.866


def test_normalize_free_events():
    raw = dict(SAMPLE_RAW, price_type="gratuit")
    event = ParisOpenDataCollector.normalize(raw)
    assert event["price_info"] == "Gratuit"


def test_normalize_rejects_missing_title_or_date():
    assert ParisOpenDataCollector.normalize({"title": "Sans date"}) is None
    assert ParisOpenDataCollector.normalize({"date_start": "2026-01-01"}) is None


async def test_save_persists_event(session):
    collector = ParisOpenDataCollector()
    normalized = ParisOpenDataCollector.normalize(SAMPLE_RAW)

    stats = await collector.save(session, [normalized])
    await session.commit()

    assert stats["created"] == 1
    event = (await session.execute(select(Event))).scalar_one()
    assert event.source == "paris_opendata"
    museum = (await session.execute(select(Museum))).scalar_one()
    assert museum.name == "Petit Palais"
    assert museum.department == "Paris"
