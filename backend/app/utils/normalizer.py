"""Normalisation des données hétérogènes des différentes sources.

Convention temporelle : les horodatages système (created_at...) sont stockés
en UTC ; les dates/heures d'événements sont stockées en heure locale
Europe/Paris (celle affichée par les musées), après conversion si la source
fournit un fuseau.
"""

import hashlib
import re
import unicodedata
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

PARIS_TZ = ZoneInfo("Europe/Paris")

# Codes postaux -> départements d'Île-de-France
IDF_DEPARTMENTS = {
    "75": "Paris",
    "77": "Seine-et-Marne",
    "78": "Yvelines",
    "91": "Essonne",
    "92": "Hauts-de-Seine",
    "93": "Seine-Saint-Denis",
    "94": "Val-de-Marne",
    "95": "Val-d'Oise",
}

# Boîte englobante approximative de l'Île-de-France (repli quand le code
# postal est absent) : lat_min, lat_max, lon_min, lon_max
IDF_BBOX = (48.10, 49.25, 1.40, 3.60)

EVENT_TYPES = [
    "exposition",
    "conférence",
    "atelier",
    "visite",
    "nocturne",
    "concert",
    "spectacle",
    "autre",
]

_TYPE_KEYWORDS: list[tuple[str, str]] = [
    ("nocturne", "nocturne"),
    ("exposition", "exposition"),
    ("expo", "exposition"),
    ("vernissage", "exposition"),
    ("conference", "conférence"),
    ("rencontre", "conférence"),
    ("table ronde", "conférence"),
    ("colloque", "conférence"),
    ("atelier", "atelier"),
    ("workshop", "atelier"),
    ("stage", "atelier"),
    ("visite", "visite"),
    ("parcours", "visite"),
    ("balade", "visite"),
    ("concert", "concert"),
    ("musique", "concert"),
    ("spectacle", "spectacle"),
    ("theatre", "spectacle"),
    ("danse", "spectacle"),
    ("projection", "spectacle"),
    ("cinema", "spectacle"),
]

_AUDIENCE_KEYWORDS: list[tuple[str, str]] = [
    ("enfant", "enfants"),
    ("jeune public", "enfants"),
    ("famille", "enfants"),
    ("scolaire", "scolaires"),
    ("adulte", "adultes"),
    ("tout public", "tout public"),
]


def strip_accents(value: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c)
    )


def slugify(value: str) -> str:
    value = strip_accents(value).lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def normalize_event_type(value: str | None) -> str:
    """Ramène une catégorie libre à un type canonique."""
    if not value:
        return "autre"
    cleaned = strip_accents(value).lower()
    if cleaned in (strip_accents(t) for t in EVENT_TYPES):
        for t in EVENT_TYPES:
            if strip_accents(t) == cleaned:
                return t
    for keyword, canonical in _TYPE_KEYWORDS:
        if keyword in cleaned:
            return canonical
    return "autre"


def normalize_audience(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = strip_accents(value).lower()
    for keyword, canonical in _AUDIENCE_KEYWORDS:
        if keyword in cleaned:
            return canonical
    return "tout public"


def parse_date(value: str | date | datetime | None) -> date | None:
    """Extrait une date depuis une chaîne ISO (avec ou sans heure/fuseau)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return _to_paris(value).date()
    if isinstance(value, date):
        return value
    value = value.strip()
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return _to_paris(dt).date()
    except ValueError:
        pass
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", value)
    if match:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return None


def parse_time(value: str | time | datetime | None) -> time | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _to_paris(value).time().replace(second=0, microsecond=0)
    if isinstance(value, time):
        return value
    value = value.strip()
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return _to_paris(dt).time().replace(second=0, microsecond=0)
    except ValueError:
        pass
    match = re.match(r"^(\d{1,2})[:h](\d{2})", value)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        if hour < 24 and minute < 60:
            return time(hour, minute)
    return None


def _to_paris(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(PARIS_TZ)


def department_from_postal_code(postal_code: str | None) -> str | None:
    if not postal_code:
        return None
    prefix = postal_code.strip()[:2]
    return IDF_DEPARTMENTS.get(prefix)


def _in_idf_bbox(lat: float | None, lon: float | None) -> bool:
    if lat is None or lon is None:
        return False
    lat_min, lat_max, lon_min, lon_max = IDF_BBOX
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def is_idf_location(
    postal_code: str | None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> bool | None:
    """Un lieu est-il en Île-de-France ?

    Retourne True (certainement IDF), False (certainement hors IDF) ou None
    (indéterminé — on ne dispose d'aucun signal exploitable). On distingue
    False de None pour ne rejeter que ce qui est *prouvé* hors IDF sans jeter
    les événements dont la localisation est inconnue.
    """
    if postal_code:
        code = str(postal_code).strip()[:2]
        if code.isdigit():
            return code in IDF_DEPARTMENTS
    if latitude is not None and longitude is not None:
        return _in_idf_bbox(latitude, longitude)
    return None


def stable_external_id(title: str, date_start: date | str | None, museum: str | None = None) -> str:
    """ID stable (hash) quand la source ne fournit pas d'identifiant natif."""
    parts = [
        slugify(title or ""),
        str(date_start or ""),
        slugify(museum or ""),
    ]
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()


def truncate(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value[:max_length] if len(value) > max_length else value


def clean_url(value, max_length: int = 500) -> str | None:
    """Ne garde que les URLs http(s) réellement chargeables.

    Les sources renvoient parfois un objet {url:...}/{filename:...} au lieu
    d'une chaîne, un nom de fichier sans domaine, ou une URL trop longue pour
    la colonne — autant de valeurs qui donnaient des <img> cassés (icône de
    repli affichée à la place de l'image).
    """
    if isinstance(value, dict):
        value = value.get("url") or value.get("src") or value.get("href")
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value.startswith(("http://", "https://")):
        return None
    if len(value) > max_length:  # ne rentre pas dans la colonne, inutilisable tronquée
        return None
    return value
