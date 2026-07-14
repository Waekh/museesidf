from datetime import date, time

from app.utils import normalizer


def test_normalize_event_type():
    assert normalizer.normalize_event_type("Exposition temporaire") == "exposition"
    assert normalizer.normalize_event_type("Conférence : les impressionnistes") == "conférence"
    assert normalizer.normalize_event_type("Atelier enfants") == "atelier"
    assert normalizer.normalize_event_type("Visite guidée") == "visite"
    assert normalizer.normalize_event_type("Nocturne du jeudi") == "nocturne"
    assert normalizer.normalize_event_type("Concert baroque") == "concert"
    assert normalizer.normalize_event_type("n'importe quoi") == "autre"
    assert normalizer.normalize_event_type(None) == "autre"


def test_parse_date_iso_variants():
    assert normalizer.parse_date("2026-09-15") == date(2026, 9, 15)
    assert normalizer.parse_date("2026-09-15T18:30:00+02:00") == date(2026, 9, 15)
    # Conversion UTC -> Europe/Paris : 23h UTC le 14 = 01h le 15 à Paris (été)
    assert normalizer.parse_date("2026-09-14T23:00:00Z") == date(2026, 9, 15)
    assert normalizer.parse_date(None) is None
    assert normalizer.parse_date("pas une date") is None


def test_parse_time():
    assert normalizer.parse_time("18:30") == time(18, 30)
    assert normalizer.parse_time("18h30") == time(18, 30)
    assert normalizer.parse_time("2026-09-15T18:30:00+02:00") == time(18, 30)
    assert normalizer.parse_time(None) is None
    assert normalizer.parse_time("99:99") is None


def test_department_from_postal_code():
    assert normalizer.department_from_postal_code("75001") == "Paris"
    assert normalizer.department_from_postal_code("92200") == "Hauts-de-Seine"
    assert normalizer.department_from_postal_code("93100") == "Seine-Saint-Denis"
    assert normalizer.department_from_postal_code("69000") is None
    assert normalizer.department_from_postal_code(None) is None


def test_stable_external_id_is_stable_and_discriminating():
    a = normalizer.stable_external_id("Monet en lumière", date(2026, 9, 1), "Musée d'Orsay")
    b = normalizer.stable_external_id("Monet en lumière", date(2026, 9, 1), "Musée d'Orsay")
    c = normalizer.stable_external_id("Monet en lumière", date(2026, 9, 2), "Musée d'Orsay")
    assert a == b
    assert a != c


def test_slugify():
    assert normalizer.slugify("Musée d'Orsay") == "musee-d-orsay"
    assert normalizer.slugify("Château de Versailles") == "chateau-de-versailles"


def test_normalize_audience():
    assert normalizer.normalize_audience("Jeune public") == "enfants"
    assert normalizer.normalize_audience("Scolaires") == "scolaires"
    assert normalizer.normalize_audience(None) is None


def test_clean_url_accepts_valid_http_urls():
    assert normalizer.clean_url("https://cdn.x.fr/img.jpg") == "https://cdn.x.fr/img.jpg"
    assert normalizer.clean_url("  http://x.fr/a.png  ") == "http://x.fr/a.png"


def test_clean_url_extracts_from_object_fields():
    # Champ image renvoyé en objet par certaines APIs Opendatasoft
    assert normalizer.clean_url({"url": "https://x.fr/img.jpg"}) == "https://x.fr/img.jpg"
    assert normalizer.clean_url({"filename": "img.jpg"}) is None  # pas d'URL chargeable


def test_clean_url_rejects_unloadable_values():
    assert normalizer.clean_url("abc123.jpg") is None  # nom de fichier nu
    assert normalizer.clean_url("") is None
    assert normalizer.clean_url(None) is None
    assert normalizer.clean_url(42) is None
    assert normalizer.clean_url("https://x.fr/" + "a" * 600) is None  # dépasse la colonne
