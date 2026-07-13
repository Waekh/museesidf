"""Processus worker : démarre APScheduler et tourne indéfiniment.

Lancement : python -m app.worker

Au démarrage, si la base est vide, on amorce immédiatement le référentiel
des musées IDF (et les événements « Que Faire à Paris ? », sans clé requise)
pour que la carte ne soit pas vide en attendant le premier cron de 6h.
"""

import asyncio
import logging

from app.services.scheduler import bootstrap_if_empty, create_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


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
