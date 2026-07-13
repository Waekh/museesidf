"""Scraper générique des sites officiels de musées + extraction par IA.

Respect des CGU :
- vérification de robots.txt avant chaque fetch,
- User-Agent identifiable (MuseesIDF-Bot/1.0),
- délai de 2 s entre requêtes,
- cache HTML 24 h pour limiter les fetchs ET les appels Claude.

L'extraction structurée est déléguée à l'API Claude (modèle configurable,
`claude-sonnet-4-6` par défaut) : on lui passe le HTML nettoyé, elle renvoie
un JSON d'événements.
"""

import asyncio
import hashlib
import json
import logging
import time as time_module
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from anthropic import AsyncAnthropic
from bs4 import BeautifulSoup

from app.collectors.base import BaseCollector
from app.config import get_settings
from app.utils import normalizer

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Tu es un extracteur de données structurées. Voici le HTML brut d'une page agenda de musée.
Extrais tous les événements présents et retourne UNIQUEMENT un JSON valide (sans markdown)
avec cette structure :
[{
  "titre": "...",
  "description": "...",
  "date_debut": "YYYY-MM-DD",
  "date_fin": "YYYY-MM-DD ou null",
  "heure_debut": "HH:MM ou null",
  "heure_fin": "HH:MM ou null",
  "lieu": "...",
  "type": "exposition|conférence|atelier|visite|nocturne|concert|autre",
  "url": "...",
  "image_url": "... ou null",
  "prix": "... ou null"
}]
Ne retourne rien d'autre que le JSON. Si aucun événement n'est trouvé, retourne []."""

# Taille max du HTML envoyé à Claude (maîtrise du coût)
MAX_HTML_CHARS = 150_000


@dataclass
class ScrapeTarget:
    slug: str
    museum_name: str
    url: str
    requires_js: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


SCRAPE_TARGETS: list[ScrapeTarget] = [
    ScrapeTarget("louvre", "Musée du Louvre", "https://www.louvre.fr/agenda"),
    ScrapeTarget("orsay", "Musée d'Orsay", "https://www.musee-orsay.fr/fr/agenda"),
    ScrapeTarget(
        "pompidou", "Centre Pompidou", "https://www.centrepompidou.fr/fr/programme", requires_js=True
    ),
    ScrapeTarget("versailles", "Château de Versailles", "https://www.chateauversailles.fr/agenda"),
    ScrapeTarget("grandpalais", "Grand Palais", "https://www.grandpalais.fr/fr/agenda"),
    ScrapeTarget("picasso", "Musée Picasso Paris", "https://www.museepicassoparis.fr/agenda"),
    ScrapeTarget(
        "quaibranly",
        "Musée du quai Branly - Jacques Chirac",
        "https://www.museedequai-branly.fr/fr/activites-et-calendrier",
    ),
    ScrapeTarget(
        "jacquemart",
        "Musée Jacquemart-André",
        "https://www.musee-jacquemart-andre.com/fr/expositions",
    ),
]


class MuseumScraperCollector(BaseCollector):
    """Collecteur pour un site de musée donné (source = scraping_<slug>)."""

    def __init__(self, target: ScrapeTarget) -> None:
        self.target = target
        self.source = f"scraping_{target.slug}"
        self.settings = get_settings()
        self._robots_cache: dict[str, RobotFileParser] = {}

    async def collect(self) -> list[dict[str, Any]]:
        html = await self.fetch_html(self.target.url)
        if not html:
            return []
        # 1. Données structurées JSON-LD si le site en publie (ex. Versailles) :
        #    extraction déterministe, aucun appel IA facturé.
        raw_events = extract_events_from_jsonld(html)
        if raw_events:
            logger.info(
                "[%s] %d événements extraits via JSON-LD (sans appel IA)",
                self.source,
                len(raw_events),
            )
        else:
            # 2. Sinon, extraction par Claude sur le HTML nettoyé.
            raw_events = await self.extract_events_with_claude(clean_html(html))
        return [
            event
            for raw in raw_events
            if (event := self.normalize(raw)) is not None
        ]

    # ------------------------------------------------------------------ fetch

    async def fetch_html(self, url: str) -> str | None:
        cached = self._read_cache(url)
        if cached is not None:
            logger.info("[%s] cache HTML utilisé pour %s", self.source, url)
            return cached

        if not await self._robots_allowed(url):
            logger.warning("[%s] robots.txt interdit %s", self.source, url)
            return None

        await asyncio.sleep(self.settings.scraper_delay_seconds)

        if self.target.requires_js:
            html = await self._fetch_with_playwright(url)
        else:
            html = await self._fetch_with_httpx(url)
        if html:
            self._write_cache(url, html)
        return html

    async def _fetch_with_httpx(self, url: str) -> str | None:
        try:
            async with httpx.AsyncClient(
                timeout=30,
                follow_redirects=True,
                headers={"User-Agent": self.settings.scraper_user_agent},
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.text
        except httpx.HTTPError as exc:
            logger.error("[%s] fetch %s : %s", self.source, url, exc)
            return None

    async def _fetch_with_playwright(self, url: str) -> str | None:
        """Pages rendues en JS (ex. Centre Pompidou). Nécessite un Chromium
        Playwright installé ; sinon la cible est ignorée proprement."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning("[%s] playwright non installé, cible ignorée", self.source)
            return None
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(user_agent=self.settings.scraper_user_agent)
                await page.goto(url, wait_until="networkidle", timeout=45_000)
                html = await page.content()
                await browser.close()
                return html
        except Exception as exc:  # noqa: BLE001 — playwright lève des types variés
            logger.error("[%s] playwright %s : %s", self.source, url, exc)
            return None

    async def _robots_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        parser = self._robots_cache.get(base)
        if parser is None:
            parser = RobotFileParser()
            try:
                async with httpx.AsyncClient(
                    timeout=10, headers={"User-Agent": self.settings.scraper_user_agent}
                ) as client:
                    resp = await client.get(f"{base}/robots.txt")
                if resp.status_code == 200:
                    parser.parse(resp.text.splitlines())
                else:
                    parser.parse([])  # pas de robots.txt -> autorisé
            except httpx.HTTPError:
                parser.parse([])
            self._robots_cache[base] = parser
        return parser.can_fetch(self.settings.scraper_user_agent, url)

    # ------------------------------------------------------------------ cache

    def _cache_path(self, url: str) -> Path:
        digest = hashlib.sha1(url.encode()).hexdigest()
        return Path(self.settings.scraper_cache_dir) / f"{digest}.html"

    def _read_cache(self, url: str) -> str | None:
        path = self._cache_path(url)
        if not path.exists():
            return None
        age_hours = (time_module.time() - path.stat().st_mtime) / 3600
        if age_hours > self.settings.scraper_cache_ttl_hours:
            return None
        return path.read_text(encoding="utf-8", errors="ignore")

    def _write_cache(self, url: str, html: str) -> None:
        path = self._cache_path(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")

    # ----------------------------------------------------------- extraction IA

    async def extract_events_with_claude(self, html: str) -> list[dict[str, Any]]:
        if not self.settings.anthropic_api_key:
            logger.warning("[%s] ANTHROPIC_API_KEY absente : extraction ignorée", self.source)
            return []

        client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        try:
            response = await client.messages.create(
                model=self.settings.claude_model,
                max_tokens=8192,
                system=EXTRACTION_PROMPT,
                messages=[{"role": "user", "content": html[:MAX_HTML_CHARS]}],
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("[%s] appel Claude : %s", self.source, exc)
            return []

        if response.stop_reason == "refusal":
            logger.warning("[%s] extraction refusée par le modèle", self.source)
            return []

        text = next((b.text for b in response.content if b.type == "text"), "")
        return parse_claude_json(text)

    # ------------------------------------------------------------- normalize

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any] | None:
        title = raw.get("titre")
        date_start = normalizer.parse_date(raw.get("date_debut"))
        if not title or not date_start:
            return None
        event_url = raw.get("url")
        if event_url and not event_url.startswith("http"):
            event_url = urljoin(self.target.url, event_url)
        image_url = raw.get("image_url")
        if image_url and not image_url.startswith("http"):
            image_url = urljoin(self.target.url, image_url)
        return {
            "external_id": normalizer.stable_external_id(title, date_start, self.target.museum_name),
            "title": title,
            "description": raw.get("description"),
            "event_type": normalizer.normalize_event_type(raw.get("type") or title),
            "date_start": date_start,
            "date_end": normalizer.parse_date(raw.get("date_fin")),
            "time_start": normalizer.parse_time(raw.get("heure_debut")),
            "time_end": normalizer.parse_time(raw.get("heure_fin")),
            "is_permanent": False,
            "price_info": raw.get("prix"),
            "image_url": image_url,
            "event_url": event_url or self.target.url,
            "audience": None,
            "raw_data": raw,
            "museum": {"name": self.target.museum_name, "website_url": _site_root(self.target.url)},
        }


# schema.org -> types canoniques internes
JSONLD_TYPE_MAP = {
    "ExhibitionEvent": "exposition",
    "VisualArtsEvent": "exposition",
    "MusicEvent": "concert",
    "TheaterEvent": "spectacle",
    "DanceEvent": "spectacle",
    "ScreeningEvent": "spectacle",
    "EducationEvent": "atelier",
}


def extract_events_from_jsonld(html: str) -> list[dict[str, Any]]:
    """Extrait les événements schema.org (`application/ld+json`) d'une page.

    Retourne des dictionnaires au même format que la sortie de Claude
    (titre/date_debut/...), pour que `normalize()` traite les deux chemins
    de façon identique.
    """
    soup = BeautifulSoup(html, "lxml")
    nodes: list[dict[str, Any]] = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue
        nodes.extend(_jsonld_event_nodes(data))
    events = [_jsonld_to_raw(node) for node in nodes]
    return [e for e in events if e.get("titre") and e.get("date_debut")]


def _jsonld_event_nodes(node: Any) -> list[dict[str, Any]]:
    """Parcourt récursivement listes et @graph à la recherche de *Event."""
    if isinstance(node, list):
        return [event for item in node for event in _jsonld_event_nodes(item)]
    if isinstance(node, dict):
        if "@graph" in node:
            return _jsonld_event_nodes(node["@graph"])
        node_type = node.get("@type")
        types = node_type if isinstance(node_type, list) else [node_type]
        if any(isinstance(t, str) and t.endswith("Event") for t in types):
            return [node]
    return []


def _jsonld_to_raw(node: dict[str, Any]) -> dict[str, Any]:
    start = str(node.get("startDate") or "")
    end = str(node.get("endDate") or "")

    image = node.get("image")
    if isinstance(image, list):
        image = image[0] if image else None
    if isinstance(image, dict):
        image = image.get("url")

    offers = node.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    price = offers.get("price") if isinstance(offers, dict) else None
    prix = None
    if price is not None:
        if str(price) in ("0", "0.0", "0.00"):
            prix = "Gratuit"
        else:
            prix = f"{price} {offers.get('priceCurrency') or '€'}".replace("EUR", "€").strip()

    location = node.get("location") or {}
    if isinstance(location, list):
        location = location[0] if location else {}

    node_type = node.get("@type")
    if isinstance(node_type, list):
        node_type = next((t for t in node_type if t in JSONLD_TYPE_MAP), node_type[0] if node_type else None)

    return {
        "titre": node.get("name"),
        "description": node.get("description"),
        "date_debut": start[:10] or None,
        "date_fin": end[:10] or None,
        # Une date sans composante horaire ne doit pas devenir "00:00"
        "heure_debut": start if "T" in start else None,
        "heure_fin": end if "T" in end else None,
        "lieu": location.get("name") if isinstance(location, dict) else None,
        # None -> normalize() retombera sur le titre pour déduire le type
        "type": JSONLD_TYPE_MAP.get(node_type) if isinstance(node_type, str) else None,
        "url": node.get("url"),
        "image_url": image,
        "prix": prix,
    }


def clean_html(html: str) -> str:
    """Allège le HTML avant envoi à Claude (scripts, styles, svg...)."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "svg", "noscript", "iframe", "link", "meta"]):
        tag.decompose()
    main = soup.find("main") or soup.body or soup
    return str(main)


def parse_claude_json(text: str) -> list[dict[str, Any]]:
    """Parse la réponse du modèle avec tolérance aux clôtures markdown."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0]
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        logger.error("Réponse Claude non parsable : %.200s", text)
        return []
    return [item for item in data if isinstance(item, dict)]


def _site_root(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


async def run_all_scrapers() -> dict[str, dict[str, int]]:
    """Exécute séquentiellement tous les scrapers (politesse envers les sites)."""
    results: dict[str, dict[str, int]] = {}
    for target in SCRAPE_TARGETS:
        collector = MuseumScraperCollector(target)
        try:
            results[collector.source] = await collector.run()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Scraper %s en échec : %s", collector.source, exc)
            results[collector.source] = {"error": 1}
    return results
