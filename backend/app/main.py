import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import alerts, events, museums, stats

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Démarre le scheduler APScheduler dans le processus API.

    En production sur Render (plan gratuit), le worker séparé n'est pas
    dispo. On intègre donc le scheduler ici. En local avec docker-compose,
    on peut toujours utiliser le worker séparé (`python -m app.worker`) et
    désactiver celui-ci via la variable d'env DISABLE_EMBEDDED_SCHEDULER=1.
    """
    scheduler = None
    if not os.getenv("DISABLE_EMBEDDED_SCHEDULER"):
        import asyncio

        from app.services.scheduler import bootstrap_if_empty, create_scheduler

        scheduler = create_scheduler()
        scheduler.start()
        logger.info(
            "Scheduler intégré démarré — %d jobs planifiés",
            len(scheduler.get_jobs()),
        )
        # Amorçage en tâche de fond : ne bloque pas le health check Render
        asyncio.create_task(bootstrap_if_empty())
    yield
    if scheduler is not None:
        scheduler.shutdown()
        logger.info("Scheduler arrêté")


app = FastAPI(
    title="Musées d'Île-de-France — API",
    description="Agrégateur d'événements des musées franciliens "
    "(OpenAgenda, Open Data Paris, data.culture.gouv.fr, scraping assisté par IA).",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router)
app.include_router(museums.router)
app.include_router(stats.router)
app.include_router(alerts.router)


@app.get("/api/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/admin/collect", tags=["admin"])
async def trigger_collect(secret: str = "") -> dict[str, Any]:
    """Déclenche manuellement une collecte de données.

    Protégé par SECRET_KEY pour éviter les abus.
    Utilisation : POST /api/admin/collect?secret=<SECRET_KEY>
    """
    if secret != settings.secret_key:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Clé invalide")

    import asyncio

    from app.collectors.culture_gouv import sync_museums
    from app.collectors.openagenda import OpenAgendaCollector
    from app.collectors.paris_opendata import ParisOpenDataCollector

    # Lancer les collectes en parallèle (musées d'abord, puis événements)
    logger.info("Collecte manuelle déclenchée")
    try:
        museum_count = await sync_museums()
        results = await asyncio.gather(
            OpenAgendaCollector().run(),
            ParisOpenDataCollector().run(),
            return_exceptions=True
        )
        
        return {
            "status": "collection finished",
            "museums_synced": museum_count,
            "openagenda_result": results[0] if not isinstance(results[0], Exception) else str(results[0]),
            "paris_opendata_result": results[1] if not isinstance(results[1], Exception) else str(results[1]),
        }
    except Exception as e:
        logger.error(f"Error during collection: {e}")
        return {"status": "error", "error": str(e)}


@app.get("/api/admin/images-sample", tags=["admin"])
async def images_sample(secret: str = "") -> dict[str, Any]:
    """Diagnostic : état des images par source (couverture + exemples d'URLs).

    Permet de vérifier en production que les collecteurs stockent des URLs
    d'images chargeables. Utilisation :
    GET /api/admin/images-sample?secret=<SECRET_KEY>
    """
    if secret != settings.secret_key:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Clé invalide")

    from sqlalchemy import func, select

    from app.database import async_session_maker
    from app.models import Event

    async with async_session_maker() as session:
        rows = (
            await session.execute(
                select(
                    Event.source,
                    func.count(Event.id),
                    func.count(Event.image_url),
                ).group_by(Event.source)
            )
        ).all()

        samples: dict[str, list[str | None]] = {}
        for source, _, _ in rows:
            urls = (
                (
                    await session.execute(
                        select(Event.image_url)
                        .where(Event.source == source, Event.image_url.is_not(None))
                        .limit(3)
                    )
                )
                .scalars()
                .all()
            )
            samples[source] = list(urls)

    return {
        "by_source": [
            {"source": source, "events": total, "with_image": with_image}
            for source, total, with_image in rows
        ],
        "sample_urls": samples,
    }

