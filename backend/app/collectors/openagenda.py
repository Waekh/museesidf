"""Collecteur OpenAgenda (https://developers.openagenda.com/).

Interroge les agendas ciblés (Paris Musées, IDF...) via l'API v2 publique.
Rate limit : 100 req/min sur la clé publique — pagination `after` + délai.
"""

import asyncio
import logging
from datetime import date
from typing import Any

import httpx

from app.collectors.base import BaseCollector
from app.config import get_settings
from app.utils import normalizer

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openagenda.com/v2"

# UIDs des agendas suivis. Peut être complété via `discover_agenda_uids()`
# (GET /agendas?search=musée&region=11) une fois la clé API configurée.
DEFAULT_AGENDA_SLUGS = [
    "ile-de-france",
    "paris-musees",
]

PAGE_SIZE = 100
MAX_PAGES = 50  # garde-fou


class OpenAgendaCollector(BaseCollector):
    source = "openagenda"

    def __init__(self, agenda_uids: list[str] | None = None) -> None:
        self.settings = get_settings()
        self.agenda_uids = agenda_uids or []

    async def collect(self) -> list[dict[str, Any]]:
        if not self.settings.openagenda_api_key:
            logger.warning("OPENAGENDA_API_KEY absente : collecte OpenAgenda ignorée")
            return []

        async with httpx.AsyncClient(timeout=30) as client:
            uids = self.agenda_uids or await self.discover_agenda_uids(client)
            events: list[dict[str, Any]] = []
            for uid in uids:
                try:
                    events.extend(await self._collect_agenda(client, uid))
                except httpx.HTTPError as exc:
                    logger.error("OpenAgenda %s : %s", uid, exc)
        return events

    async def discover_agenda_uids(self, client: httpx.AsyncClient) -> list[str]:
        """Résout les slugs cibles + recherche 'musée' en région IDF (code 11)."""
        uids: list[str] = []
        for slug in DEFAULT_AGENDA_SLUGS:
            try:
                resp = await client.get(
                    f"{BASE_URL}/agendas",
                    params={"key": self.settings.openagenda_api_key, "search": slug, "size": 5},
                )
                resp.raise_for_status()
                for agenda in resp.json().get("agendas", []):
                    if agenda.get("slug") == slug:
                        uids.append(str(agenda["uid"]))
            except httpx.HTTPError as exc:
                logger.error("OpenAgenda discover %s : %s", slug, exc)
        try:
            resp = await client.get(
                f"{BASE_URL}/agendas",
                params={
                    "key": self.settings.openagenda_api_key,
                    "search": "musée",
                    "official": 1,
                    "size": 20,
                },
            )
            resp.raise_for_status()
            uids.extend(str(a["uid"]) for a in resp.json().get("agendas", []))
        except httpx.HTTPError as exc:
            logger.error("OpenAgenda discover musées : %s", exc)
        return list(dict.fromkeys(uids))

    async def _collect_agenda(self, client: httpx.AsyncClient, uid: str) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        after: list[Any] | None = None
        for _ in range(MAX_PAGES):
            params: dict[str, Any] = {
                "key": self.settings.openagenda_api_key,
                "size": PAGE_SIZE,
                "timings[gte]": date.today().isoformat(),
                "detailed": 1,
            }
            if after:
                params["after[]"] = after
            resp = await client.get(f"{BASE_URL}/agendas/{uid}/events", params=params)
            resp.raise_for_status()
            payload = resp.json()
            batch = payload.get("events", [])
            for raw in batch:
                if not isinstance(raw, dict):
                    continue
                try:
                    normalized = self.normalize(raw, uid)
                except Exception as exc:  # noqa: BLE001 — un événement mal formé ne doit pas tout arrêter
                    logger.warning("OpenAgenda : événement ignoré (%s)", exc)
                    continue
                if normalized:
                    events.append(normalized)
            after = payload.get("after")
            if not after or len(batch) < PAGE_SIZE:
                break
            await asyncio.sleep(0.7)  # ~100 req/min max
        return [e for e in events if e]

    @staticmethod
    def normalize(raw: dict[str, Any], agenda_uid: str | None = None) -> dict[str, Any] | None:
        """Mappe un événement OpenAgenda vers le format interne."""
        title = _lang(raw.get("title"))
        first = _obj(raw.get("firstTiming"))
        last = _obj(raw.get("lastTiming"))
        date_start = normalizer.parse_date(first.get("begin"))
        if not title or not date_start:
            return None

        location = _obj(raw.get("location"))
        image_url = _openagenda_image_url(_obj(raw.get("image")))

        origin = _obj(raw.get("originAgenda"))
        slug = raw.get("slug")
        event_url = f"https://openagenda.com/{origin.get('slug', agenda_uid)}/events/{slug}" if slug else None

        keywords = _lang(raw.get("keywords")) or []
        type_hint = " ".join(keywords) if isinstance(keywords, list) else str(keywords)

        return {
            "external_id": str(raw.get("uid")) if raw.get("uid") else None,
            "title": title,
            "description": _lang(raw.get("longDescription")) or _lang(raw.get("description")),
            "event_type": normalizer.normalize_event_type(f"{title} {type_hint}"),
            "date_start": date_start,
            "date_end": normalizer.parse_date(last.get("end") or first.get("end")),
            "time_start": normalizer.parse_time(first.get("begin")),
            "time_end": normalizer.parse_time(first.get("end")),
            "is_permanent": False,
            "price_info": _lang(raw.get("conditions")),
            "image_url": image_url,
            "event_url": event_url,
            "audience": normalizer.normalize_audience(_lang(raw.get("age")) if raw.get("age") else None),
            "raw_data": {"uid": raw.get("uid"), "originAgenda": origin.get("uid") or agenda_uid},
            "museum": {
                "name": location.get("name"),
                "address": location.get("address"),
                "postal_code": location.get("postalCode"),
                "city": location.get("city"),
                "latitude": location.get("latitude"),
                "longitude": location.get("longitude"),
                "website_url": location.get("website"),
                "openagenda_uid": str(origin.get("uid")) if origin.get("uid") else None,
            }
            if location.get("name")
            else None,
        }


def _lang(value: Any, lang: str = "fr") -> Any:
    """OpenAgenda renvoie des champs multilingues {'fr': ..., 'en': ...}."""
    if isinstance(value, dict):
        return value.get(lang) or next(iter(value.values()), None)
    return value


def _obj(value: Any) -> dict[str, Any]:
    """Garantit un dict : l'API renvoie parfois une chaîne/null là où on
    attend un objet, ce qui ferait planter un appel .get()."""
    return value if isinstance(value, dict) else {}


def _openagenda_image_url(image: dict[str, Any]) -> str | None:
    """Construit l'URL absolue de l'image d'un événement OpenAgenda.

    Bug corrigé : l'image OpenAgenda combine un préfixe CDN (`base.url`,
    souvent juste le domaine, ex. "https://cdn.openagenda.com/") avec un nom
    de fichier séparé (`filename`, au niveau de l'image ou d'une variante).
    Ni l'un ni l'autre pris isolément ne donne une URL chargeable — c'était
    la cause des images jamais affichées côté frontend (URL cassée que le
    navigateur ne pouvait pas résoudre).
    """
    if not image:
        return None

    direct = image.get("url")
    if isinstance(direct, str) and direct.startswith("http"):
        return direct

    base = _obj(image.get("base"))
    base_url = base.get("url") if isinstance(base.get("url"), str) else ""

    variants = image.get("variants") if isinstance(image.get("variants"), list) else []
    first_variant = variants[0] if variants and isinstance(variants[0], dict) else {}

    for candidate in (
        first_variant.get("url"),
        image.get("filename"),
        first_variant.get("filename"),
    ):
        if not isinstance(candidate, str) or not candidate:
            continue
        if candidate.startswith("http"):
            return candidate
        if base_url:
            return base_url.rstrip("/") + "/" + candidate.lstrip("/")

    return base_url if base_url.startswith("http") else None
