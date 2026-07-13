import logging
import os
from contextlib import asynccontextmanager

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
        from app.services.scheduler import create_scheduler

        scheduler = create_scheduler()
        scheduler.start()
        logger.info(
            "Scheduler intégré démarré — %d jobs planifiés",
            len(scheduler.get_jobs()),
        )
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
