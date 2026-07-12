"""Processus worker : démarre APScheduler et tourne indéfiniment.

Lancement : python -m app.worker
"""

import asyncio
import logging

from app.services.scheduler import create_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
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
