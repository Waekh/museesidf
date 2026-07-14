from datetime import date

import pytest

from app.collectors.scraper import (
    SCRAPE_TARGETS,
    MuseumScraperCollector,
    clean_html,
    extract_og_image,
    parse_claude_json,
)

LOUVRE = SCRAPE_TARGETS[0]


def test_parse_claude_json_plain():
    text = '[{"titre": "Expo", "date_debut": "2026-09-01"}]'
    assert parse_claude_json(text) == [{"titre": "Expo", "date_debut": "2026-09-01"}]


def test_parse_claude_json_with_markdown_fences():
    text = '```json\n[{"titre": "Expo", "date_debut": "2026-09-01"}]\n```'
    assert parse_claude_json(text)[0]["titre"] == "Expo"


def test_parse_claude_json_invalid_returns_empty():
    assert parse_claude_json("désolé, aucun événement") == []
    assert parse_claude_json("[pas du json") == []


def test_clean_html_strips_scripts_and_styles():
    html = (
        "<html><head><script>alert(1)</script><style>.a{}</style></head>"
        "<body><main><article>Exposition Delacroix</article></main></body></html>"
    )
    cleaned = clean_html(html)
    assert "Exposition Delacroix" in cleaned
    assert "alert(1)" not in cleaned
    assert ".a{}" not in cleaned


def test_normalize_builds_absolute_urls_and_stable_id():
    collector = MuseumScraperCollector(LOUVRE)
    raw = {
        "titre": "Nocturne du vendredi",
        "description": "Le musée ouvre en soirée.",
        "date_debut": "2026-09-04",
        "date_fin": None,
        "heure_debut": "18:00",
        "heure_fin": "21:45",
        "lieu": "Musée du Louvre",
        "type": "nocturne",
        "url": "/agenda/nocturne",
        "image_url": None,
        "prix": "Inclus dans le billet",
    }
    event = collector.normalize(raw)
    assert event is not None
    assert event["event_url"] == "https://www.louvre.fr/agenda/nocturne"
    assert event["event_type"] == "nocturne"
    assert event["date_start"] == date(2026, 9, 4)
    assert event["museum"]["name"] == "Musée du Louvre"
    # Le hash doit être stable entre deux collectes
    assert event["external_id"] == collector.normalize(raw)["external_id"]


def test_normalize_rejects_event_without_date():
    collector = MuseumScraperCollector(LOUVRE)
    assert collector.normalize({"titre": "Sans date", "date_debut": None}) is None


def test_extract_og_image_finds_property_meta():
    html = (
        '<html><head><meta property="og:image" content="https://x.fr/hero.jpg">'
        "</head><body></body></html>"
    )
    assert extract_og_image(html) == "https://x.fr/hero.jpg"


def test_extract_og_image_falls_back_to_twitter_card():
    html = '<html><head><meta name="twitter:image" content="https://x.fr/tw.jpg"></head></html>'
    assert extract_og_image(html) == "https://x.fr/tw.jpg"


def test_extract_og_image_prefers_og_over_twitter():
    html = (
        '<meta property="og:image" content="https://x.fr/og.jpg">'
        '<meta name="twitter:image" content="https://x.fr/tw.jpg">'
    )
    assert extract_og_image(html) == "https://x.fr/og.jpg"


def test_extract_og_image_absent_returns_none():
    assert extract_og_image("<html><head></head><body></body></html>") is None


async def test_collect_uses_page_og_image_when_event_has_none(monkeypatch):
    """L'image la plus mise en valeur de la page sert de repli pour les
    événements sans image propre (ex. Château de Versailles en JSON-LD)."""
    versailles = next(t for t in SCRAPE_TARGETS if t.slug == "versailles")
    collector = MuseumScraperCollector(versailles)

    html = """
    <html><head>
    <meta property="og:image" content="https://chateauversailles.fr/hero.jpg">
    <script type="application/ld+json">
    {"@type": "ExhibitionEvent", "name": "Grandes Eaux", "startDate": "2026-09-04"}
    </script>
    </head><body></body></html>
    """
    monkeypatch.setattr(collector, "fetch_html", lambda url: _async_return(html))

    events = await collector.collect()
    assert len(events) == 1
    assert events[0]["image_url"] == "https://chateauversailles.fr/hero.jpg"


async def test_collect_keeps_event_own_image_over_page_fallback(monkeypatch):
    versailles = next(t for t in SCRAPE_TARGETS if t.slug == "versailles")
    collector = MuseumScraperCollector(versailles)

    html = """
    <html><head>
    <meta property="og:image" content="https://chateauversailles.fr/hero.jpg">
    <script type="application/ld+json">
    {"@type": "ExhibitionEvent", "name": "Grandes Eaux", "startDate": "2026-09-04",
     "image": "https://chateauversailles.fr/specific.jpg"}
    </script>
    </head><body></body></html>
    """
    monkeypatch.setattr(collector, "fetch_html", lambda url: _async_return(html))

    events = await collector.collect()
    assert events[0]["image_url"] == "https://chateauversailles.fr/specific.jpg"


async def _async_return(value):
    return value
