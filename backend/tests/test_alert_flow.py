from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.models import AlertSubscription
from app.services import mailer


@pytest.fixture(autouse=True)
def mock_mailer(monkeypatch):
    mock = AsyncMock(return_value=True)
    monkeypatch.setattr(mailer, "send_confirmation", mock)
    return mock


async def test_create_alert_sends_confirmation(client, session, mock_mailer):
    resp = await client.post(
        "/api/alerts",
        json={
            "email": "alice@example.com",
            "filters": {"departments": ["Paris"], "types": ["exposition"], "keywords": ["monet"]},
            "frequency": "daily",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "alice@example.com"
    assert data["frequency"] == "daily"
    assert data["is_active"] is True
    assert data["token"]
    assert data["filters"]["departments"] == ["Paris"]

    mock_mailer.assert_awaited_once()

    sub = (await session.execute(select(AlertSubscription))).scalar_one()
    assert sub.email == "alice@example.com"


async def test_create_alert_rejects_bad_frequency(client):
    resp = await client.post(
        "/api/alerts", json={"email": "a@b.com", "frequency": "hourly"}
    )
    assert resp.status_code == 422


async def test_create_alert_rejects_bad_email(client):
    resp = await client.post(
        "/api/alerts", json={"email": "pas-un-email", "frequency": "weekly"}
    )
    assert resp.status_code == 422


async def test_resubscribe_same_email_updates_instead_of_duplicating(client, session):
    await client.post("/api/alerts", json={"email": "bob@example.com", "frequency": "daily"})
    resp = await client.post(
        "/api/alerts",
        json={"email": "bob@example.com", "frequency": "weekly"},
    )
    assert resp.status_code == 201

    subs = (await session.execute(select(AlertSubscription))).scalars().all()
    assert len(subs) == 1
    assert subs[0].frequency == "weekly"


async def test_unsubscribe_by_token(client, session):
    created = (
        await client.post("/api/alerts", json={"email": "carol@example.com"})
    ).json()

    resp = await client.delete(f"/api/alerts/{created['token']}")
    assert resp.status_code == 204

    sub = (await session.execute(select(AlertSubscription))).scalar_one()
    assert sub.is_active is False


async def test_unsubscribe_link_from_email(client, session):
    created = (
        await client.post("/api/alerts", json={"email": "dave@example.com"})
    ).json()

    resp = await client.get(f"/api/alerts/unsubscribe/{created['token']}")
    assert resp.status_code == 200
    assert "Désinscription confirmée" in resp.text

    sub = (await session.execute(select(AlertSubscription))).scalar_one()
    assert sub.is_active is False


async def test_unsubscribe_unknown_token_404(client):
    resp = await client.delete("/api/alerts/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
