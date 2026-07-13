"""Processus worker : démarre APScheduler et tourne indéfiniment.

Lancement : python -m app.worker

Au démarrage, si la base est vide, on amorce immédiatement le référentiel
des musées IDF (et les événements « Que Faire à Paris ? », sans clé requise)
pour que la carte ne soit pas vide en attendant le premier cron de 6h.
"""

import asyncio
import logging

from sqlalchemy import func, select

from app.collectors.culture_gouv import sync_museums
from app.collectors.paris_opendata import ParisOpenDataCollector
from app.database import async_session_maker
from app.models import Museum
from app.services.scheduler import create_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


async def bootstrap_if_empty() -> None:
    """Première collecte si la table museums est vide (déploiement neuf)."""
    async with async_session_maker() as session:
        count = (await session.execute(select(func.count(Museum.id)))).scalar_one()
    if count > 0:
        logger.info("Base déjà peuplée (%d musées) — pas d'amorçage", count)
        return
    logger.info("Base vide — amorçage du référentiel musées + Que Faire à Paris")
    try:
        await sync_museums()
        await ParisOpenDataCollector().run()
    except Exception as exc:  # noqa: BLE001 — l'amorçage ne doit jamais bloquer le worker
        logger.exception("Amorçage initial en échec : %s", exc)


async def main() -> None:
    await bootstrap_if_empty()
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Worker démarré — %d jobs planifiés", len(scheduler.get_jobs()))
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
