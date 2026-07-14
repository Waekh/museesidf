from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://user:password@db:5432/musees_idf"

    # APIs externes
    openagenda_api_key: str = ""
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"

    # Email (alertes)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "alertes@musees-idf.fr"

    # App
    frontend_url: str = "http://localhost:5173"
    api_url: str = "http://localhost:8000"
    secret_key: str = "change-me"

    # Scraping — CGU : User-Agent identifiable, délai entre requêtes, cache 24h
    scraper_user_agent: str = "MuseesIDF-Bot/1.0 (+https://github.com/waekh/museesidf)"
    scraper_delay_seconds: float = 2.0
    scraper_cache_dir: str = "/tmp/musees_idf_cache"
    scraper_cache_ttl_hours: int = 24
    # Mode gratuit : extraction déterministe uniquement (JSON-LD, __NEXT_DATA__).
    # Mettre à False (ou laisser ANTHROPIC_API_KEY vide) pour n'engager aucun
    # coût d'API IA. À True + clé présente, Claude sert de recours sur les
    # pages sans données structurées.
    scraper_use_ai: bool = True

    # Rétention RGPD : abonnements inactifs supprimés après 1 an
    alert_retention_days: int = 365


@lru_cache
def get_settings() -> Settings:
    return Settings()
