from app.affordability.models import Confidence, CostCategory
from app.cities import get_supported_city
from app.providers.esios import EsiosElectricityProvider
from app.providers.seed import (
    SeedFoodBasketProvider,
    SeedHousingProvider,
    SeedMunicipalTaxProvider,
    SeedTransportProvider,
    SeedUtilityProvider,
)


def test_seed_providers_cover_all_core_categories() -> None:
    city = get_supported_city("Madrid")
    assert city is not None

    items = []
    for provider in [
        SeedHousingProvider(),
        SeedFoodBasketProvider(),
        EsiosElectricityProvider(
            api_token=None,
            indicator_id=1001,
            monthly_kwh=180,
            fixed_monthly_eur=14,
            lookback_days=30,
        ),
        SeedUtilityProvider(),
        SeedMunicipalTaxProvider(),
        SeedTransportProvider(),
    ]:
        items.extend(provider.fetch_city(city))

    categories = {item.category for item in items}

    assert categories == {
        CostCategory.RENT,
        CostCategory.ELECTRICITY,
        CostCategory.GAS,
        CostCategory.WATER,
        CostCategory.TRASH_TAX,
        CostCategory.FOOD,
        CostCategory.PUBLIC_TRANSPORT,
    }
    assert all(item.source_name for item in items)
    assert all(item.source_url for item in items)


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class FakeClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.last_request = None

    def get(self, url: str, headers: dict, params: dict) -> FakeResponse:
        self.last_request = {"url": url, "headers": headers, "params": params}
        return FakeResponse(self.payload)


def test_esios_provider_uses_fallback_without_token() -> None:
    city = get_supported_city("Madrid")
    assert city is not None

    item = EsiosElectricityProvider(
        api_token=None,
        indicator_id=1001,
        monthly_kwh=180,
        fixed_monthly_eur=14,
        lookback_days=30,
    ).fetch_city(city)[0]

    assert item.category == CostCategory.ELECTRICITY
    assert item.monthly_amount == 48.2
    assert item.confidence == Confidence.LOW
    assert item.details["fallback_reason"] == "Missing ESIOS_API_TOKEN"


def test_esios_provider_calculates_from_indicator_values() -> None:
    city = get_supported_city("Madrid")
    assert city is not None
    payload = {
        "indicator": {
            "unit": "EUR/MWh",
            "values": [
                {"value": 100, "datetime": "2026-06-01T00:00:00+00:00"},
                {"value": 200, "datetime": "2026-06-02T00:00:00+00:00"},
            ],
        }
    }
    client = FakeClient(payload)

    item = EsiosElectricityProvider(
        api_token="token",
        indicator_id=1001,
        monthly_kwh=180,
        fixed_monthly_eur=14,
        lookback_days=30,
        client=client,
    ).fetch_city(city)[0]

    assert item.category == CostCategory.ELECTRICITY
    assert item.monthly_amount == 41
    assert item.confidence == Confidence.HIGH
    assert item.details["raw_values"] == 2
    assert item.details["average_eur_per_kwh"] == 0.15
    assert client.last_request["headers"]["x-api-key"] == "token"
