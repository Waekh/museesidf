from datetime import date

from sqlalchemy import select

from app.models import Event, Museum
from app.services.deduplicator import deduplicate_events, pick_keeper, titles_similar


def test_titles_similar_obvious_cases():
    assert titles_similar("Monet en lumière", "Monet en lumière")
    assert titles_similar("Monet en lumière", "Monet en Lumière !")
    assert not titles_similar("Monet en lumière", "Picasso et la céramique")


def test_titles_similar_edge_cases():
    # En dessous du seuil de 85 %
    assert not titles_similar("Exposition Rodin", "Exposition Renoir et ses amis")
    # Casse et espaces ignorés
    assert titles_similar("  NOCTURNE DU JEUDI ", "nocturne du jeudi")


async def _make_museum(session) -> Museum:
    museum = Museum(name="Musée d'Orsay", slug="musee-d-orsay")
    session.add(museum)
    await session.flush()
    return museum


async def test_duplicate_marked_and_most_complete_kept(session):
    museum = await _make_museum(session)
    short = Event(
        source="openagenda",
        external_id="a",
        title="Monet en lumière",
        description="Court.",
        date_start=date(2026, 9, 1),
        museum_id=museum.id,
    )
    long = Event(
        source="paris_opendata",
        external_id="b",
        title="Monet en Lumière",
        description="Une description bien plus complète de l'exposition Monet.",
        date_start=date(2026, 9, 1),
        museum_id=museum.id,
    )
    session.add_all([short, long])
    await session.flush()

    marked = await deduplicate_events(session, [long])
    await session.commit()

    assert marked == 1
    assert short.is_duplicate is True
    assert short.duplicate_of_id == long.id
    assert long.is_duplicate is False


async def test_different_dates_are_not_duplicates(session):
    museum = await _make_museum(session)
    a = Event(
        source="openagenda",
        external_id="a",
        title="Nocturne du jeudi",
        date_start=date(2026, 9, 3),
        museum_id=museum.id,
    )
    b = Event(
        source="paris_opendata",
        external_id="b",
        title="Nocturne du jeudi",
        date_start=date(2026, 9, 10),
        museum_id=museum.id,
    )
    session.add_all([a, b])
    await session.flush()

    marked = await deduplicate_events(session, [a, b])
    assert marked == 0
    assert not a.is_duplicate and not b.is_duplicate


async def test_same_source_not_deduplicated(session):
    museum = await _make_museum(session)
    a = Event(
        source="openagenda",
        external_id="a",
        title="Visite guidée",
        date_start=date(2026, 9, 3),
        museum_id=museum.id,
    )
    b = Event(
        source="openagenda",
        external_id="b",
        title="Visite guidée",
        date_start=date(2026, 9, 3),
        museum_id=museum.id,
    )
    session.add_all([a, b])
    await session.flush()

    marked = await deduplicate_events(session, [a, b])
    assert marked == 0


async def test_events_without_museum_are_ignored(session):
    a = Event(source="openagenda", external_id="a", title="X", date_start=date(2026, 9, 3))
    session.add(a)
    await session.flush()
    assert await deduplicate_events(session, [a]) == 0


def test_pick_keeper_prefers_longer_description():
    a = Event(source="s1", title="T", date_start=date(2026, 1, 1), description="long texte ici")
    b = Event(source="s2", title="T", date_start=date(2026, 1, 1), description="court")
    keeper, duplicate = pick_keeper(a, b)
    assert keeper is a and duplicate is b
