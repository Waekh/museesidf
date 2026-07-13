from app.collectors.scraper import extract_events_from_jsonld

PAGE_WITH_JSONLD = """
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "ExhibitionEvent",
      "name": "Le Grand Trianon retrouvé",
      "description": "Exposition-événement dans les appartements royaux.",
      "startDate": "2026-09-15T10:00:00+02:00",
      "endDate": "2027-01-10T18:30:00+01:00",
      "url": "https://www.chateauversailles.fr/agenda/grand-trianon",
      "image": {"@type": "ImageObject", "url": "https://cdn.versailles.fr/trianon.jpg"},
      "location": {"@type": "Place", "name": "Château de Versailles"},
      "offers": {"@type": "Offer", "price": "21", "priceCurrency": "EUR"}
    },
    {
      "@type": "MusicEvent",
      "name": "Les Grandes Eaux Musicales",
      "startDate": "2026-06-01",
      "endDate": "2026-10-31",
      "offers": {"@type": "Offer", "price": "0"}
    },
    {"@type": "Organization", "name": "Château de Versailles"}
  ]
}
</script>
<script type="application/ld+json">pas du json valide {{{</script>
</head><body></body></html>
"""


def test_extracts_events_from_graph():
    events = extract_events_from_jsonld(PAGE_WITH_JSONLD)
    assert len(events) == 2

    expo = events[0]
    assert expo["titre"] == "Le Grand Trianon retrouvé"
    assert expo["type"] == "exposition"  # ExhibitionEvent -> exposition
    assert expo["date_debut"] == "2026-09-15"
    assert expo["date_fin"] == "2027-01-10"
    assert expo["heure_debut"] == "2026-09-15T10:00:00+02:00"
    assert expo["lieu"] == "Château de Versailles"
    assert expo["image_url"] == "https://cdn.versailles.fr/trianon.jpg"
    assert expo["prix"] == "21 €"


def test_date_only_events_have_no_time():
    events = extract_events_from_jsonld(PAGE_WITH_JSONLD)
    concert = events[1]
    assert concert["type"] == "concert"  # MusicEvent -> concert
    assert concert["heure_debut"] is None  # pas de "00:00" fantôme
    assert concert["prix"] == "Gratuit"


def test_non_event_nodes_are_ignored():
    events = extract_events_from_jsonld(PAGE_WITH_JSONLD)
    assert all(e["titre"] != "Château de Versailles" for e in events)


def test_top_level_list_and_single_event():
    html = """
    <script type="application/ld+json">
    [{"@type": "Event", "name": "Nocturne", "startDate": "2026-09-04T18:00:00"}]
    </script>
    """
    events = extract_events_from_jsonld(html)
    assert len(events) == 1
    assert events[0]["titre"] == "Nocturne"
    assert events[0]["type"] is None  # "Event" générique -> déduit du titre ensuite


def test_page_without_jsonld_returns_empty():
    assert extract_events_from_jsonld("<html><body><p>Rien ici</p></body></html>") == []
