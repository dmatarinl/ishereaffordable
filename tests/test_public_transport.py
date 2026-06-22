import pytest

from app.affordability.models import Confidence, DataMode
from app.cities import SUPPORTED_CITIES, get_supported_city
from app.providers.public_transport import OfficialTransportFareProvider
from app.public_transport.fares import MODEL_VERSION, transport_fare_catalog


@pytest.mark.parametrize(
    ("city_name", "monthly_amount"),
    [
        ("Madrid", 32.70),
        ("Barcelona", 22.80),
        ("Valencia", 21.00),
        ("Sevilla", 21.20),
        ("Zaragoza", 22.00),
        ("Malaga", 23.97),
        ("Bilbao", 30.25),
        ("Alicante", 24.00),
    ],
)
def test_official_transport_fare_by_city(
    city_name: str,
    monthly_amount: float,
) -> None:
    city = get_supported_city(city_name)
    assert city is not None

    item = OfficialTransportFareProvider().fetch_city(city)[0]

    assert item.monthly_amount == monthly_amount
    assert item.data_mode == DataMode.OFFICIAL_PUBLICATION
    assert item.confidence == Confidence.MEDIUM
    assert item.valid_until is not None
    assert item.details["model_version"] == MODEL_VERSION
    assert item.details["product_name"]
    assert item.details["calculation_summary"]
    assert item.details["modes_included"]


def test_zaragoza_uses_explicit_monthly_journey_scenario() -> None:
    city = get_supported_city("Zaragoza")
    assert city is not None

    item = OfficialTransportFareProvider().fetch_city(city)[0]

    assert item.details["calculation_type"] == "monthly_journey_scenario"
    assert item.details["monthly_journeys"] == 40
    assert item.details["unit_fare_eur"] == 0.55
    assert item.monthly_amount == 40 * 0.55


def test_limited_passes_expose_excluded_modes() -> None:
    provider = OfficialTransportFareProvider()
    sevilla = get_supported_city("Sevilla")
    malaga = get_supported_city("Malaga")
    assert sevilla is not None
    assert malaga is not None

    sevilla_item = provider.fetch_city(sevilla)[0]
    malaga_item = provider.fetch_city(malaga)[0]

    assert "Metro Line 1" in sevilla_item.details["excluded_modes"]
    assert "Metro de Malaga" in malaga_item.details["excluded_modes"]


def test_transport_catalog_covers_supported_cities() -> None:
    catalog = transport_fare_catalog()

    assert {fare["city_key"] for fare in catalog} == {
        city.key for city in SUPPORTED_CITIES
    }
