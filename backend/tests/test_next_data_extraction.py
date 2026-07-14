"""Extraction gratuite depuis le blob __NEXT_DATA__ (sites Next.js)."""

import json

from app.collectors.scraper import extract_events_from_next_data

# Structure typique : __NEXT_DATA__ contient les props de la page, avec une
# liste d'événements imbriquée quelque part dans pageProps.
NEXT_HTML = """
<html><body>
<script id="__NEXT_DATA__" type="application/json">
{
  "props": {
    "pageProps": {
      "agenda": {
        "events": [
          {
            "title": "Exposition Kimono",
            "description": "Une plongée dans le vêtement japonais.",
            "startDate": "2026-11-02T10:00:00+01:00",
            "endDate": "2027-03-15",
            "url": "/fr/expositions/kimono",
            "image": {"url": "https://cdn.quaibranly.fr/kimono.jpg"}
          },
          {
            "name": "Atelier calligraphie",
            "date": "2026-11-08",
            "slug": "atelier-calligraphie"
          },
          {
            "title": "Objet sans date",
            "description": "ne doit pas être extrait"
          }
        ]
      }
    }
  }
}
</script>
</body></html>
"""


def test_extracts_events_with_title_and_date():
    events = extract_events_from_next_data(NEXT_HTML)
    titles = {e["titre"] for e in events}
    assert titles == {"Exposition Kimono", "Atelier calligraphie"}


def test_maps_fields_and_nested_image():
    events = extract_events_from_next_data(NEXT_HTML)
    kimono = next(e for e in events if e["titre"] == "Exposition Kimono")
    assert kimono["date_debut"] == "2026-11-02"
    assert kimono["date_fin"] == "2027-03-15"
    assert kimono["heure_debut"] == "2026-11-02T10:00:00+01:00"
    assert kimono["url"] == "/fr/expositions/kimono"
    assert kimono["image_url"] == "https://cdn.quaibranly.fr/kimono.jpg"


def test_deduplicates_identical_title_date():
    duplicated = {
        "props": {
            "a": {"title": "Nocturne", "startDate": "2026-11-02"},
            "b": {"title": "Nocturne", "startDate": "2026-11-02"},
        }
    }
    html = f'<script id="__NEXT_DATA__">{json.dumps(duplicated)}</script>'
    events = extract_events_from_next_data(html)
    assert len(events) == 1


def test_no_next_data_returns_empty():
    assert extract_events_from_next_data("<html><body>rien</body></html>") == []


def test_invalid_json_returns_empty():
    assert extract_events_from_next_data('<script id="__NEXT_DATA__">{{{ cassé</script>') == []
