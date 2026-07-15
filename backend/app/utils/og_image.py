"""Récupération de la miniature de prévisualisation (og:image) d'une page.

Sert de repli d'image pour les événements sans visuel propre : on lit la
balise Open Graph / Twitter Card de la page source — exactement l'image
affichée quand on partage le lien.
"""

import logging

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_META_CANDIDATES = (
    {"property": "og:image"},
    {"property": "og:image:secure_url"},
    {"property": "og:image:url"},
    {"name": "twitter:image"},
    {"name": "twitter:image:src"},
)


def extract_og_image(html: str) -> str | None:
    """Extrait l'image la plus mise en valeur de la page (Open Graph /
    Twitter Card)."""
    soup = BeautifulSoup(html, "lxml")
    for attrs in _META_CANDIDATES:
        tag = soup.find("meta", attrs=attrs)
        content = tag.get("content") if tag else None
        if isinstance(content, str) and content.strip():
            return content.strip()
    # Repli : lien <link rel="image_src">
    link = soup.find("link", rel="image_src")
    href = link.get("href") if link else None
    if isinstance(href, str) and href.strip():
        return href.strip()
    return None


async def fetch_og_image(url: str, user_agent: str) -> str | None:
    """Télécharge une page et en extrait l'og:image (best-effort)."""
    if not url or not url.startswith(("http://", "https://")):
        return None
    try:
        async with httpx.AsyncClient(
            timeout=8,
            follow_redirects=True,
            headers={"User-Agent": user_agent},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "html" not in content_type:
                return None
            og = extract_og_image(resp.text)
    except (httpx.HTTPError, ValueError) as exc:
        logger.info("og:image indisponible pour %s : %s", url, exc)
        return None

    # L'og:image peut être relative -> la rendre absolue
    if og and not og.startswith(("http://", "https://")):
        from urllib.parse import urljoin

        og = urljoin(url, og)
    return og if og and og.startswith(("http://", "https://")) else None
