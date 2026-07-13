"""Jobs planifiés : collectes quotidiennes, alertes email, nettoyage.

Tourne dans le container `worker` (voir app/worker.py).
"""

import logging
from datetime import date, datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import delete, func, or_, select, update

from app.collectors.culture_gouv import sync_museums
from app.collectors.openagenda import OpenAgendaCollector
from app.collectors.paris_opendata import ParisOpenDataCollector
from app.collectors.scraper import run_all_scrapers
from app.config import get_settings
from app.database import async_session_maker
from app.models import AlertSubscription, Event, Museum
from app.services import mailer

logger = logging.getLogger(__name__)


async def bootstrap_if_empty() -> None:
    """Première collecte si la table museums est vide (déploiement neuf).

    Amorce le référentiel des musées IDF (carte peuplée sur toute la région)
    et les événements « Que Faire à Paris ? », tous deux sans clé requise, pour
    que l'app ne soit pas vide en attendant le premier cron de 6h. Appelé au
    démarrage du worker et de l'API (lifespan).
    """
    async with async_session_maker() as session:
        count = (await session.execute(select(func.count(Museum.id)))).scalar_one()
    if count > 0:
        logger.info("Base déjà peuplée (%d musées) — pas d'amorçage", count)
        return
    logger.info("Base vide — amorçage du référentiel musées + Que Faire à Paris")
    try:
        await sync_museums()
        await ParisOpenDataCollector().run()
    except Exception as exc:  # noqa: BLE001 — l'amorçage ne doit jamais bloquer le démarrage
        logger.exception("Amorçage initial en échec : %s", exc)


async def collect_openagenda() -> None:
    await OpenAgendaCollector().run()


async def collect_paris_opendata() -> None:
    await ParisOpenDataCollector().run()


async def collect_scrapers() -> None:
    await run_all_scrapers()


async def sync_museum_registry() -> None:
    await sync_museums()


async def cleanup_old_events() -> None:
    """Supprime les événements terminés depuis plus de 30 jours, et les
    abonnements inactifs depuis plus d'un an (RGPD)."""
    cutoff = date.today() - timedelta(days=30)
    async with async_session_maker() as session:
        # Détache d'abord les références de doublons vers les événements purgés
        old_ids = select(Event.id).where(
            or_(
                Event.date_end < cutoff,
                (Event.date_end.is_(None)) & (Event.date_start < cutoff),
            )
        )
        await session.execute(
            update(Event)
            .where(Event.duplicate_of_id.in_(old_ids))
            .values(duplicate_of_id=None)
        )
        result = await session.execute(
            delete(Event).where(
                or_(
                    Event.date_end < cutoff,
                    (Event.date_end.is_(None)) & (Event.date_start < cutoff),
                )
            )
        )
        retention = datetime.now(timezone.utc) - timedelta(
            days=get_settings().alert_retention_days
        )
        await session.execute(
            delete(AlertSubscription).where(
                AlertSubscription.is_active.is_(False),
                AlertSubscription.created_at < retention,
            )
        )
        await session.commit()
    logger.info("Nettoyage : %d événements supprimés", result.rowcount)


def _matches_filters(event: Event, filters: dict) -> bool:
    departments = filters.get("departments") or []
    if departments and (not event.museum or event.museum.department not in departments):
        return False
    types = filters.get("types") or []
    if types and event.event_type not in types:
        return False
    keywords = filters.get("keywords") or []
    if keywords:
        haystack = f"{event.title} {event.description or ''}".casefold()
        if not any(k.casefold() in haystack for k in keywords):
            return False
    museum_ids = filters.get("museum_ids") or []
    if museum_ids and event.museum_id not in museum_ids:
        return False
    return True


async def send_alerts(frequency: str) -> None:
    """Envoie aux abonnés les événements ajoutés depuis le dernier cycle."""
    window = timedelta(days=1 if frequency == "daily" else 7)
    since = datetime.now(timezone.utc) - window
    async with async_session_maker() as session:
        subscriptions = (
            (
                await session.execute(
                    select(AlertSubscription).where(
                        AlertSubscription.is_active.is_(True),
                        AlertSubscription.frequency == frequency,
                    )
                )
            )
            .scalars()
            .all()
        )
        if not subscriptions:
            return

        from sqlalchemy.orm import selectinload

        new_events = (
            (
                await session.execute(
                    select(Event)
                    .options(selectinload(Event.museum))
                    .where(
                        Event.created_at >= since,
                        Event.is_duplicate.is_(False),
                        Event.date_start >= date.today(),
                    )
                    .order_by(Event.date_start)
                )
            )
            .scalars()
            .all()
        )
        if not new_events:
            return

        for subscription in subscriptions:
            matching = [
                e for e in new_events if _matches_filters(e, subscription.filters or {})
            ][:30]
            if not matching:
                continue
            sent = await mailer.send_event_alert(subscription, matching)
            if sent:
                subscription.last_sent_at = datetime.now(timezone.utc)
        await session.commit()


async def send_daily_alerts() -> None:
    await send_alerts("daily")


async def send_weekly_alerts() -> None:
    await send_alerts("weekly")


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Europe/Paris")

    # Collectes quotidiennes
    scheduler.add_job(collect_openagenda, "cron", hour=6, minute=0)
    scheduler.add_job(collect_paris_opendata, "cron", hour=6, minute=15)
    scheduler.add_job(collect_scrapers, "cron", hour=6, minute=30)

    # Référentiel musées : hebdomadaire (il bouge peu)
    scheduler.add_job(sync_museum_registry, "cron", day_of_week="sun", hour=5, minute=0)

    # Alertes email
    scheduler.add_job(send_daily_alerts, "cron", hour=8, minute=0)
    scheduler.add_job(send_weekly_alerts, "cron", day_of_week="mon", hour=8, minute=0)

    # Nettoyage des événements passés (> 30 jours)
    scheduler.add_job(cleanup_old_events, "cron", hour=2, minute=0)

    return scheduler
