from datetime import date, timedelta

import pytest

from app.models import Event, Museum

TODAY = date.today()


@pytest.fixture
async def seed(session):
    orsay = Museum(name="Musée d'Orsay", slug="musee-d-orsay", department="Paris")
    mac_val = Museum(name="MAC VAL", slug="mac-val", department="Val-de-Marne")
    session.add_all([orsay, mac_val])
    await session.flush()

    events = [
        Event(
            source="openagenda",
            external_id="1",
            title="Monet en lumière",
            description="Exposition impressionnisme",
            event_type="exposition",
            date_start=TODAY + timedelta(days=5),
            date_end=TODAY + timedelta(days=60),
            museum_id=orsay.id,
            audience="tout public",
        ),
        Event(
            source="paris_opendata",
            external_id="2",
            title="Atelier gravure",
            event_type="atelier",
            date_start=TODAY + timedelta(days=10),
            museum_id=orsay.id,
            audience="enfants",
        ),
        Event(
            source="openagenda",
            external_id="3",
            title="Visite des collections",
            event_type="visite",
            date_start=TODAY + timedelta(days=100),
            museum_id=mac_val.id,
        ),
        Event(
            source="openagenda",
            external_id="4",
            title="Événement passé",
            event_type="exposition",
            date_start=TODAY - timedelta(days=30),
            date_end=TODAY - timedelta(days=10),
            museum_id=orsay.id,
        ),
        Event(
            source="paris_opendata",
            external_id="5",
            title="Doublon caché",
            event_type="exposition",
            date_start=TODAY + timedelta(days=5),
            museum_id=orsay.id,
            is_duplicate=True,
        ),
    ]
    session.add_all(events)
    await session.commit()
    return {"orsay": orsay, "mac_val": mac_val}


async def test_list_excludes_past_and_duplicates(client, seed):
    resp = await client.get("/api/events")
    assert resp.status_code == 200
    data = resp.json()
    titles = [e["title"] for e in data["events"]]
    assert data["total"] == 3
    assert "Événement passé" not in titles
    assert "Doublon caché" not in titles


async def test_filter_by_date_range(client, seed):
    resp = await client.get(
        "/api/events",
        params={
            "date_from": (TODAY + timedelta(days=8)).isoformat(),
            "date_to": (TODAY + timedelta(days=20)).isoformat(),
        },
    )
    data = resp.json()
    titles = [e["title"] for e in data["events"]]
    # L'expo en cours (jusqu'à J+60) et l'atelier (J+10) matchent ; la visite (J+100) non
    assert "Atelier gravure" in titles
    assert "Visite des collections" not in titles


async def test_filter_by_department(client, seed):
    resp = await client.get("/api/events", params={"department": "Val-de-Marne"})
    data = resp.json()
    assert data["total"] == 1
    assert data["events"][0]["title"] == "Visite des collections"


async def test_filter_by_event_type_list(client, seed):
    resp = await client.get("/api/events", params={"event_type": "atelier,visite"})
    data = resp.json()
    assert data["total"] == 2
    assert {e["event_type"] for e in data["events"]} == {"atelier", "visite"}


async def test_filter_by_keyword(client, seed):
    resp = await client.get("/api/events", params={"keyword": "impressionnisme"})
    data = resp.json()
    assert data["total"] == 1
    assert data["events"][0]["title"] == "Monet en lumière"


async def test_filter_by_audience(client, seed):
    resp = await client.get("/api/events", params={"audience": "enfants"})
    data = resp.json()
    assert data["total"] == 1
    assert data["events"][0]["title"] == "Atelier gravure"


async def test_filter_by_museum_id(client, seed):
    resp = await client.get("/api/events", params={"museum_id": seed["mac_val"].id})
    data = resp.json()
    assert data["total"] == 1


async def test_pagination(client, seed):
    resp = await client.get("/api/events", params={"page": 1, "page_size": 2})
    data = resp.json()
    assert data["total"] == 3
    assert len(data["events"]) == 2
    resp2 = await client.get("/api/events", params={"page": 2, "page_size": 2})
    assert len(resp2.json()["events"]) == 1


async def test_page_size_capped_at_100(client, seed):
    resp = await client.get("/api/events", params={"page_size": 500})
    assert resp.status_code == 422


async def test_event_detail_includes_museum(client, seed):
    listing = (await client.get("/api/events")).json()
    event_id = listing["events"][0]["id"]
    resp = await client.get(f"/api/events/{event_id}")
    assert resp.status_code == 200
    assert resp.json()["museum"]["name"]


async def test_event_detail_404(client, seed):
    resp = await client.get("/api/events/999999")
    assert resp.status_code == 404


async def test_stats_endpoint(client, seed):
    resp = await client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_museums"] == 2
    assert data["by_department"]["Paris"] >= 1
    assert "exposition" in data["by_event_type"]


async def test_museums_endpoint_counts_upcoming(client, seed):
    resp = await client.get("/api/museums")
    assert resp.status_code == 200
    museums = {m["name"]: m for m in resp.json()}
    assert museums["Musée d'Orsay"]["upcoming_events_count"] == 2
    assert museums["MAC VAL"]["upcoming_events_count"] == 1

    resp = await client.get("/api/museums", params={"department": "Paris"})
    assert [m["name"] for m in resp.json()] == ["Musée d'Orsay"]


async def test_museums_filtered_by_event_type_for_map(client, seed):
    # Un filtre d'événement ne retient que les musées ayant un événement matchant
    resp = await client.get("/api/museums", params={"event_type": "visite"})
    names = [m["name"] for m in resp.json()]
    assert names == ["MAC VAL"]  # seul MAC VAL a une visite

    resp = await client.get("/api/museums", params={"event_type": "atelier"})
    data = resp.json()
    assert [m["name"] for m in data] == ["Musée d'Orsay"]
    assert data[0]["upcoming_events_count"] == 1  # compteur limité au filtre


async def test_museums_filtered_by_audience_for_map(client, seed):
    resp = await client.get("/api/museums", params={"audience": "enfants"})
    assert [m["name"] for m in resp.json()] == ["Musée d'Orsay"]


async def test_museums_multi_department_csv(client, seed):
    resp = await client.get("/api/museums", params={"department": "Paris,Val-de-Marne"})
    assert {m["name"] for m in resp.json()} == {"Musée d'Orsay", "MAC VAL"}
