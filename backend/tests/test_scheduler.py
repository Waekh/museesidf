from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.models import AlertSubscription, Event, Museum
from app.services import scheduler as sched


# ------------------------------------------------------------ _matches_filters


def _event(**kwargs) -> Event:
    defaults = dict(source="openagenda", title="Expo Monet", date_start=date(2026, 9, 1))
    defaults.update(kwargs)
    return Event(**defaults)


def test_matches_filters_empty_filters_match_everything():
    assert sched._matches_filters(_event(), {}) is True


def test_matches_filters_department():
    museum = Museum(name="Orsay", department="Paris")
    event = _event(museum=museum)
    assert sched._matches_filters(event, {"departments": ["Paris"]}) is True
    assert sched._matches_filters(event, {"departments": ["Yvelines"]}) is False
    # Événement sans musée : rejeté si un filtre département est demandé
    assert sched._matches_filters(_event(), {"departments": ["Paris"]}) is False


def test_matches_filters_types_and_keywords():
    event = _event(event_type="exposition", description="Autour de l'impressionnisme")
    assert sched._matches_filters(event, {"types": ["exposition", "atelier"]}) is True
    assert sched._matches_filters(event, {"types": ["visite"]}) is False
    assert sched._matches_filters(event, {"keywords": ["IMPRESSIONNISME"]}) is True
    assert sched._matches_filters(event, {"keywords": ["picasso"]}) is False


# ------------------------------------------------------- cleanup_old_events


@pytest.fixture
def patched_session_maker(session_maker, monkeypatch):
    monkeypatch.setattr(sched, "async_session_maker", session_maker)
    return session_maker


async def test_cleanup_removes_old_events_and_stale_subscriptions(patched_session_maker):
    today = date.today()
    async with patched_session_maker() as session:
        session.add_all(
            [
                Event(
                    source="s",
                    external_id="old",
                    title="Terminé depuis longtemps",
                    date_start=today - timedelta(days=90),
                    date_end=today - timedelta(days=60),
                ),
                Event(
                    source="s",
                    external_id="recent",
                    title="Terminé récemment",
                    date_start=today - timedelta(days=20),
                    date_end=today - timedelta(days=5),
                ),
                Event(
                    source="s",
                    external_id="future",
                    title="À venir",
                    date_start=today + timedelta(days=10),
                ),
                AlertSubscription(
                    email="vieux@example.com",
                    is_active=False,
                    created_at=datetime.now(timezone.utc) - timedelta(days=400),
                ),
                AlertSubscription(email="actif@example.com", is_active=True),
            ]
        )
        await session.commit()

    await sched.cleanup_old_events()

    async with patched_session_maker() as session:
        remaining = (await session.execute(select(Event.external_id))).scalars().all()
        assert sorted(remaining) == ["future", "recent"]
        emails = (await session.execute(select(AlertSubscription.email))).scalars().all()
        assert emails == ["actif@example.com"]


# ------------------------------------------------------------- send_alerts


async def test_send_alerts_only_matching_subscribers(patched_session_maker, monkeypatch):
    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr(sched.mailer, "send_event_alert", mock_send)

    async with patched_session_maker() as session:
        orsay = Museum(name="Orsay", slug="orsay", department="Paris")
        session.add(orsay)
        await session.flush()
        session.add_all(
            [
                Event(
                    source="openagenda",
                    external_id="1",
                    title="Expo Monet",
                    event_type="exposition",
                    date_start=date.today() + timedelta(days=5),
                    museum_id=orsay.id,
                ),
                AlertSubscription(
                    email="paris@example.com",
                    frequency="daily",
                    filters={"departments": ["Paris"]},
                ),
                AlertSubscription(
                    email="yvelines@example.com",
                    frequency="daily",
                    filters={"departments": ["Yvelines"]},
                ),
                AlertSubscription(
                    email="hebdo@example.com",
                    frequency="weekly",
                    filters={},
                ),
            ]
        )
        await session.commit()

    await sched.send_alerts("daily")

    # Seul l'abonné quotidien dont les filtres matchent est notifié
    assert mock_send.await_count == 1
    subscription, events = mock_send.await_args.args
    assert subscription.email == "paris@example.com"
    assert [e.title for e in events] == ["Expo Monet"]

    async with patched_session_maker() as session:
        notified = (
            await session.execute(
                select(AlertSubscription).where(
                    AlertSubscription.email == "paris@example.com"
                )
            )
        ).scalar_one()
        assert notified.last_sent_at is not None


async def test_send_alerts_no_new_events_sends_nothing(patched_session_maker, monkeypatch):
    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr(sched.mailer, "send_event_alert", mock_send)

    async with patched_session_maker() as session:
        session.add(AlertSubscription(email="a@example.com", frequency="daily", filters={}))
        await session.commit()

    await sched.send_alerts("daily")
    mock_send.assert_not_awaited()
