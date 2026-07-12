import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import alerts, events, museums, stats

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Musées d'Île-de-France — API",
    description="Agrégateur d'événements des musées franciliens "
    "(OpenAgenda, Open Data Paris, data.culture.gouv.fr, scraping assisté par IA).",
    version="1.0.0",
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
