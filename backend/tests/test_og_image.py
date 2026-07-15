"""Miniature og:image de la page source (repli d'image)."""

from datetime import date

import httpx
import pytest

from app.utils.og_image import extract_og_image, fetch_og_image


def test_extract_og_image_property_and_link_fallback():
    assert (
        extract_og_image('<meta property="og:image" content="https://x.fr/a.jpg">')
        == "https://x.fr/a.jpg"
    )
    assert (
        extract_og_image('<link rel="image_src" href="https://x.fr/b.jpg">')
        == "https://x.fr/b.jpg"
    )
    assert extract_og_image("<html><head></head></html>") is None


async def test_fetch_og_image_reads_remote_meta(monkeypatch):
    html = '<html><head><meta property="og:image" content="https://cdn.x.fr/hero.jpg"></head></html>'

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html, headers={"content-type": "text/html"})

    transport = httpx.MockTransport(handler)
    _patch_async_client(monkeypatch, transport)

    url = await fetch_og_image("https://musee.fr/evenement", "TestBot/1.0")
    assert url == "https://cdn.x.fr/hero.jpg"


async def test_fetch_og_image_makes_relative_absolute(monkeypatch):
    html = '<meta property="og:image" content="/img/hero.jpg">'

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html, headers={"content-type": "text/html"})

    _patch_async_client(monkeypatch, httpx.MockTransport(handler))

    url = await fetch_og_image("https://musee.fr/agenda/expo", "TestBot/1.0")
    assert url == "https://musee.fr/img/hero.jpg"


async def test_fetch_og_image_handles_errors(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    _patch_async_client(monkeypatch, httpx.MockTransport(handler))

    assert await fetch_og_image("https://musee.fr/mort", "TestBot/1.0") is None
    # URL invalide : pas de requête
    assert await fetch_og_image("pas-une-url", "TestBot/1.0") is None


def _patch_async_client(monkeypatch, transport: httpx.MockTransport) -> None:
    """Injecte un transport mock dans httpx.AsyncClient utilisé par fetch_og_image."""
    original_init = httpx.AsyncClient.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)
