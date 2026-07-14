"""Tests du référentiel musées — robustesse à la variabilité des champs."""

import pytest
from sqlalchemy import select

from app.collectors import culture_gouv
from app.collectors.culture_gouv import _coords, _first, idf_department, upsert_records
from app.models import Museum


def test_first_returns_first_non_empty_candidate():
    raw = {"nom_du_musee": "", "nom_officiel": "Musée du Louvre"}
    assert _first(raw, culture_gouv.NAME_FIELDS) == "Musée du Louvre"
    assert _first({}, culture_gouv.NAME_FIELDS) is None


def test_coords_geo_point_2d_list_form():
    # Convention Opendatasoft : [latitude, longitude]
    assert _coords({"geo_point_2d": [48.8606, 2.3376]}) == (48.8606, 2.3376)


def test_coords_dict_forms():
    assert _coords({"coordonnees": {"lat": 48.86, "lon": 2.33}}) == (48.86, 2.33)
    assert _coords({"geolocalisation": {"latitude": 48.86, "longitude": 2.33}}) == (48.86, 2.33)


def test_coords_string_form_and_missing():
    assert _coords({"geo_point_2d": "48.86,2.33"}) == (48.86, 2.33)
    assert _coords({}) == (None, None)


def test_idf_department_from_postal_code():
    assert idf_department({}, "75001", None, None) == "Paris"
    assert idf_department({}, "78000", None, None) == "Yvelines"


def test_idf_department_from_department_field_when_no_postal():
    # Nom de département
    assert idf_department({"departement": "Seine-Saint-Denis"}, None, None, None) == "Seine-Saint-Denis"
    # Code de département inclus dans la valeur
    assert idf_department({"departement": "Yvelines (78)"}, None, None, None) == "Yvelines"


def test_idf_department_from_region_field():
    # Région IDF mais pas de département précis : chaîne vide (= IDF, dept inconnu)
    assert idf_department({"region_administrative": "Île-de-France"}, None, None, None) == ""
    assert idf_department({"region": "ILE-DE-FRANCE"}, None, None, None) == ""


def test_idf_department_from_bounding_box():
    # Coordonnées dans l'IDF, aucun autre indice
    assert idf_department({}, None, 48.86, 2.33) == ""


def test_idf_department_rejects_non_idf():
    # Lyon : hors IDF sur tous les signaux
    assert idf_department({"region": "Auvergne-Rhône-Alpes"}, "69002", 45.75, 4.85) is None
    assert idf_department({}, None, None, None) is None


@pytest.fixture
def patched_session_maker(session_maker, monkeypatch):
    monkeypatch.setattr(culture_gouv, "async_session_maker", session_maker)
    return session_maker


async def test_upsert_keeps_only_idf_and_sets_coordinates(patched_session_maker):
    records = [
        {
            "nom_officiel": "Musée du Louvre",
            "adresse": "Rue de Rivoli",
            "ville": "Paris",
            "code_postal": "75001",
            "geo_point_2d": [48.8606, 2.3376],
            "url": "https://www.louvre.fr",
        },
        {
            "nom_officiel": "MAC VAL",
            "code_postal": "94400",
            "geo_point_2d": [48.7873, 2.3931],
        },
        {
            # Hors IDF (Lyon) : doit être ignoré
            "nom_officiel": "Musée des Confluences",
            "code_postal": "69002",
            "geo_point_2d": [45.7333, 4.8180],
        },
    ]

    count = await upsert_records(records)
    assert count == 2

    async with patched_session_maker() as session:
        museums = (await session.execute(select(Museum).order_by(Museum.name))).scalars().all()
        names = [m.name for m in museums]
        assert names == ["MAC VAL", "Musée du Louvre"]

        louvre = museums[1]
        assert louvre.department == "Paris"
        assert louvre.latitude == 48.8606
        assert louvre.longitude == 2.3376
        assert louvre.website_url == "https://www.louvre.fr"

        macval = museums[0]
        assert macval.department == "Val-de-Marne"
        assert macval.latitude is not None  # présent sur la carte


async def test_upsert_is_idempotent(patched_session_maker):
    records = [{"nom_officiel": "Musée du Louvre", "code_postal": "75001"}]
    await upsert_records(records)
    await upsert_records(records)

    async with patched_session_maker() as session:
        museums = (await session.execute(select(Museum))).scalars().all()
        assert len(museums) == 1
