"""Tests de l'amorçage initial (bootstrap_if_empty)."""

from datetime import date
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.models import Event, Museum
from app.services import scheduler as sched


@pytest.fixture
def patched_session_maker(session_maker, monkeypatch):
    monkeypatch.setattr(sched, "async_session_maker", session_maker)
    return session_maker


async def test_bootstrap_runs_collectors_when_empty(patched_session_maker, monkeypatch):
    sync_mock = AsyncMock(return_value=5)
    run_mock = AsyncMock(return_value={"created": 3})
    monkeypatch.setattr(sched, "sync_museums", sync_mock)
    monkeypatch.setattr(sched.ParisOpenDataCollector, "run", run_mock)

    await sched.bootstrap_if_empty()

    sync_mock.assert_awaited_once()
    run_mock.assert_awaited_once()


async def test_bootstrap_skips_when_already_populated(patched_session_maker, monkeypatch):
    async with patched_session_maker() as session:
        session.add(Museum(name="Musée d'Orsay", slug="musee-d-orsay"))
        await session.commit()

    sync_mock = AsyncMock(return_value=0)
    monkeypatch.setattr(sched, "sync_museums", sync_mock)

    await sched.bootstrap_if_empty()

    sync_mock.assert_not_awaited()


async def test_bootstrap_swallows_collector_errors(patched_session_maker, monkeypatch):
    # Un échec réseau à l'amorçage ne doit jamais faire planter le démarrage
    monkeypatch.setattr(sched, "sync_museums", AsyncMock(side_effect=RuntimeError("réseau")))

    await sched.bootstrap_if_empty()  # ne lève pas
