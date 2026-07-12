"""Collecteur "Que Faire à Paris ?" — Open Data Paris (Explore API v2.1).

Pas d'authentification requise. Filtre sur les événements liés aux musées.
"""

import logging
from datetime import date
from typing import Any

import httpx

from app.collectors.base import BaseCollector
from app.utils import normalizer

logger = logging.getLogger(__name__)

BASE_URL = "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets"
DATASET = "que-faire-a-paris-"
PAGE_SIZE = 100
MAX_RECORDS = 5000  # garde-fou pagination offset


class ParisOpenDataCollector(BaseCollector):
    source = "paris_opendata"

    async def collect(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        today = date.today().isoformat()
        where = (
            f'(category like "musée" OR tags like "musée" OR category like "expo" '
            f'OR tags like "exposition") AND date_start >= date\'{today}\''
        )
        async with httpx.AsyncClient(timeout=30) as client:
            offset = 0
            while offset < MAX_RECORDS:
                try:
                    resp = await client.get(
                        f"{BASE_URL}/{DATASET}/records",
                        params={
                            "where": where,
                            "order_by": "date_start ASC",
                            "limit": PAGE_SIZE,
                            "offset": offset,
                        },
                    )
                    resp.raise_for_status()
                except httpx.HTTPError as exc:
                    logger.error("Open Data Paris : %s", exc)
                    break
                results = resp.json().get("results", [])
                events.extend(filter(None, (self.normalize(r) for r in results)))
                if len(results) < PAGE_SIZE:
                    break
                offset += PAGE_SIZE
        return events

    @staticmethod
    def normalize(raw: dict[str, Any]) -> dict[str, Any] | None:
        title = raw.get("title")
        date_start = normalizer.parse_date(raw.get("date_start"))
        if not title or not date_start:
            return None

        lat_lon = raw.get("lat_lon") or {}
        tags = raw.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        type_hint = " ".join([str(raw.get("category") or ""), *map(str, tags), str(title)])

        description = raw.get("lead_text") or ""
        body = raw.get("body") or ""
        if body and body not in description:
            description = f"{description}\n\n{body}".strip()

        price = raw.get("price_type") or raw.get("price_detail")
        if isinstance(price, str) and price.lower() == "gratuit":
            price = "Gratuit"

        return {
            "external_id": str(raw.get("id")) if raw.get("id") else None,
            "title": title,
            "description": description or None,
            "event_type": normalizer.normalize_event_type(type_hint),
            "date_start": date_start,
            "date_end": normalizer.parse_date(raw.get("date_end")),
            "time_start": normalizer.parse_time(raw.get("date_start")),
            "time_end": normalizer.parse_time(raw.get("date_end")),
            "is_permanent": False,
            "price_info": price,
            "image_url": raw.get("cover_url") or raw.get("image"),
            "event_url": raw.get("url"),
            "audience": normalizer.normalize_audience(raw.get("audience")),
            "raw_data": {"id": raw.get("id"), "category": raw.get("category"), "tags": tags},
            "museum": {
                "name": raw.get("address_name"),
                "address": raw.get("address_street"),
                "postal_code": raw.get("address_zipcode"),
                "city": raw.get("address_city"),
                "latitude": lat_lon.get("lat"),
                "longitude": lat_lon.get("lon"),
            }
            if raw.get("address_name")
            else None,
        }
