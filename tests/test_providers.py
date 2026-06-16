from app.affordability.models import Confidence, CostCategory, DataMode
from app.cities import get_supported_city
from app.food.basket import canonical_food_basket
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
            geo_name="Península",
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
    assert all(item.data_mode == DataMode.MANUAL_SEED for item in items)


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
        self.calls = 0

    def get(self, url: str, headers: dict, params: dict) -> FakeResponse:
        self.calls += 1
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
        geo_name="Península",
    ).fetch_city(city)[0]

    assert item.category == CostCategory.ELECTRICITY
    assert item.monthly_amount == 48.2
    assert item.confidence == Confidence.LOW
    assert item.data_mode == DataMode.MANUAL_SEED
    assert item.details["fallback_reason"] == "Missing ESIOS_API_TOKEN"


def test_seed_food_provider_uses_canonical_basket() -> None:
    city = get_supported_city("Valencia")
    assert city is not None
    basket = canonical_food_basket()

    item = SeedFoodBasketProvider().fetch_city(city)[0]

    assert item.category == CostCategory.FOOD
    assert item.monthly_amount == basket.seed_monthly_total_eur()
    assert item.details["basket_version"] == basket.version
    assert item.details["basket_items"] == len(basket.items)
    assert item.details["required_items"] == basket.required_item_count
    assert item.details["aggregation_method"] == "median_valid_supermarket_basket"


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
        geo_name="Península",
        client=client,
    ).fetch_city(city)[0]

    assert item.category == CostCategory.ELECTRICITY
    assert item.monthly_amount == 41
    assert item.confidence == Confidence.HIGH
    assert item.data_mode == DataMode.OFFICIAL_API
    assert item.details["raw_values"] == 2
    assert item.details["average_eur_per_kwh"] == 0.15
    assert client.last_request["headers"]["x-api-key"] == "token"


def test_esios_provider_reuses_one_cached_response_across_cities() -> None:
    madrid = get_supported_city("Madrid")
    valencia = get_supported_city("Valencia")
    assert madrid is not None
    assert valencia is not None
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
    provider = EsiosElectricityProvider(
        api_token="token",
        indicator_id=1001,
        monthly_kwh=180,
        fixed_monthly_eur=14,
        lookback_days=30,
        geo_name="Península",
        client=client,
    )

    madrid_item = provider.fetch_city(madrid)[0]
    valencia_item = provider.fetch_city(valencia)[0]

    assert madrid_item.monthly_amount == valencia_item.monthly_amount == 41
    assert client.calls == 1


def test_esios_provider_filters_to_peninsula_values() -> None:
    city = get_supported_city("Madrid")
    assert city is not None
    payload = {
        "indicator": {
            "magnitud": [{"name": "Precio €/MWh", "id": 23}],
            "values": [
                {
                    "value": 100,
                    "datetime": "2026-06-01T00:00:00+00:00",
                    "geo_name": "Península",
                },
                {
                    "value": 1000,
                    "datetime": "2026-06-01T00:00:00+00:00",
                    "geo_name": "Canarias",
                },
                {
                    "value": 200,
                    "datetime": "2026-06-02T00:00:00+00:00",
                    "geo_name": "Península",
                },
                {
                    "value": 2000,
                    "datetime": "2026-06-02T00:00:00+00:00",
                    "geo_name": "Canarias",
                },
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
        geo_name="Península",
        client=client,
    ).fetch_city(city)[0]

    assert item.details["geo_name"] == "Península"
    assert item.details["raw_values"] == 2
    assert item.details["average_raw_value"] == 150
    assert item.details["average_eur_per_kwh"] == 0.15
    assert item.monthly_amount == 41
