from app.affordability.models import Confidence, CostCategory, DataMode
from app.cities import get_supported_city
from app.food.basket import canonical_food_basket
from app.gas.profiles import GasBillAssumptions
from app.providers.boe_gas import (
    BoeGasTurProvider,
    parse_gas_tur_document,
    parse_gas_tur_terms,
)
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
            lookback_days=30,
            default_profile="standard",
            geo_name="Península",
        ),
        BoeGasTurProvider(
            source_url=None,
            user_agent="test",
            enable_discovery=False,
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
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class FakeClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.last_request = None
        self.calls = 0

    def get(self, url: str, headers: dict, params: dict | None = None) -> FakeResponse:
        self.calls += 1
        self.last_request = {"url": url, "headers": headers, "params": params}
        return FakeResponse(self.payload)


class FakeTextResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        return None


class FakeTextClient:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls = 0
        self.last_request = None

    def get(self, url: str, headers: dict) -> FakeTextResponse:
        self.calls += 1
        self.last_request = {"url": url, "headers": headers}
        return FakeTextResponse(self.text)


def test_esios_provider_uses_fallback_without_token() -> None:
    city = get_supported_city("Madrid")
    assert city is not None

    item = EsiosElectricityProvider(
        api_token=None,
        indicator_id=1001,
        lookback_days=30,
        default_profile="standard",
        geo_name="Península",
    ).fetch_city(city)[0]

    assert item.category == CostCategory.ELECTRICITY
    assert item.monthly_amount == 53.91
    assert item.confidence == Confidence.LOW
    assert item.data_mode == DataMode.MANUAL_SEED
    assert item.details["fallback_reason"] == "Missing ESIOS_API_TOKEN"
    assert item.details["electricity_profile"] == "standard"


def test_boe_gas_provider_uses_fallback_without_source_url() -> None:
    city = get_supported_city("Madrid")
    assert city is not None

    item = BoeGasTurProvider(
        source_url=None,
        user_agent="test",
        enable_discovery=False,
    ).fetch_city(city)[0]

    assert item.category == CostCategory.GAS
    assert item.monthly_amount == 30.05
    assert item.confidence == Confidence.LOW
    assert item.data_mode == DataMode.MANUAL_SEED
    assert "Missing BOE_GAS_TUR_URL" in item.details["fallback_reason"]
    assert item.details["gas_profile"] == "standard"
    assert item.details["vat_rate"] == 0.21
    assert item.details["hydrocarbons_tax_eur"] == 0.58


def test_boe_gas_provider_parses_tur_terms() -> None:
    city = get_supported_city("Madrid")
    assert city is not None
    text = """
    Publicado en BOE núm. 76, de 31 de marzo de 2026.
    Tarifa Término fijo (€/cliente)/mes Término variable (c€/kWh)
    TUR.1 Consumo anual inferior o igual a 5.000 kWh 4,63 5,112345
    TUR.2 Consumo anual entre 5.001 y 15.000 kWh 8,02 4,987654
    """
    client = FakeTextClient(text)

    item = BoeGasTurProvider(
        source_url="https://www.boe.es/diario_boe/xml.php?id=BOE-A-test",
        user_agent="test-agent",
        client=client,
    ).fetch_city(city)[0]

    assert item.category == CostCategory.GAS
    assert item.monthly_amount == 21.77
    assert item.confidence == Confidence.MEDIUM
    assert item.data_mode == DataMode.OFFICIAL_API
    assert item.details["fixed_term_eur_month"] == 4.63
    assert item.details["variable_term_eur_per_kwh"] == 0.051123
    assert item.details["hydrocarbons_tax_eur"] == 0.58
    assert item.details["vat_eur"] == 3.78
    assert item.details["gas_terms"]["TUR.2"]["fixed_term_eur_month"] == 8.02
    assert item.valid_until is not None
    assert client.calls == 1
    assert client.last_request["headers"]["User-Agent"] == "test-agent"


def test_parse_gas_tur_terms_accepts_xml_payload() -> None:
    xml = """
    <documento>
      <texto>
        Publicado en BOE núm. 76, de 31 de marzo de 2026.
        Tarifa Término fijo €/cliente/mes Término variable c€/kWh
        TUR.1 4,63 5,112345
      </texto>
    </documento>
    """

    terms = parse_gas_tur_terms(xml, "TUR.1")

    assert terms.fixed_term_eur_month == 4.63
    assert terms.variable_term_eur_per_kwh == 0.05112345


def test_parse_gas_tur_document_accepts_xml_payload() -> None:
    xml = """
    <documento>
      <texto>
        Documento BOE-A-2026-1234.
        Publicado en BOE núm. 76, de 31 de marzo de 2026.
        Tarifa Término fijo €/cliente/mes Término variable c€/kWh
        TUR.1 4,63 5,112345
      </texto>
    </documento>
    """

    document = parse_gas_tur_document(
        xml,
        source_url="https://www.boe.es/diario_boe/xml.php?id=BOE-A-2026-1234",
    )

    assert document.document_id == "BOE-A-2026-1234"
    assert document.observed_at.year == 2026
    assert document.terms_by_rate["TUR.1"].fixed_term_eur_month == 4.63


def test_boe_gas_provider_normalizes_pdf_url() -> None:
    city = get_supported_city("Madrid")
    assert city is not None
    text = """
    Publicado en BOE núm. 78, de 30 de marzo de 2026.
    Tarifa Término fijo €/cliente/mes Término variable cent/kWh
    TUR.1 Consumo inferior o igual a 5.000 kWh/año. 3,93 3,822924
    TUR.2 Consumo superior a 5.000 kWh/año e inferior o igual a 15.000 kWh/año.
    8,11 3,613034
    """
    client = FakeTextClient(text)

    item = BoeGasTurProvider(
        source_url="https://boe.es/boe/dias/2026/03/30/pdfs/BOE-A-2026-7193.pdf",
        user_agent="test-agent",
        client=client,
    ).fetch_city(city)[0]

    assert item.monthly_amount == 17.03
    assert item.source_url == (
        "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-7193"
    )
    assert client.last_request["url"] == (
        "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-7193"
    )


def test_boe_gas_provider_rejects_non_boe_source_url() -> None:
    city = get_supported_city("Madrid")
    assert city is not None

    item = BoeGasTurProvider(
        source_url="https://example.com/gas-tariff.xml",
        user_agent="test-agent",
        enable_discovery=False,
        client=FakeTextClient(""),
    ).fetch_city(city)[0]

    assert item.data_mode.value == "manual_seed"
    assert "BOE source URL must use" in item.details["fallback_reason"]


class FakeBoeOpenDataClient:
    def __init__(self, summary_payload: dict, document_text: str) -> None:
        self.summary_payload = summary_payload
        self.document_text = document_text
        self.requests = []

    def get(self, url: str, headers: dict) -> FakeResponse | FakeTextResponse:
        self.requests.append({"url": url, "headers": headers})
        if "/datosabiertos/api/boe/sumario/" in url:
            return FakeResponse(self.summary_payload)
        return FakeTextResponse(self.document_text)


def test_boe_gas_provider_discovers_latest_tur_document_from_summary() -> None:
    city = get_supported_city("Madrid")
    assert city is not None
    summary_payload = {
        "data": {
            "sumario": {
                "diario": [
                    {
                        "seccion": [
                            {
                                "departamento": [
                                    {
                                        "epigrafe": [
                                            {
                                                "item": {
                                                    "titulo": (
                                                        "Resolución de 26 de junio "
                                                        "de 2025, de la Dirección "
                                                        "General de Política "
                                                        "Energética y Minas, por "
                                                        "la que se publica la "
                                                        "tarifa de último recurso "
                                                        "de gas natural."
                                                    ),
                                                    "url_xml": (
                                                        "https://www.boe.es/"
                                                        "diario_boe/xml.php?id="
                                                        "BOE-A-2025-13230"
                                                    ),
                                                }
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }
    }
    document_text = """
    Publicado en BOE núm. 156, de 30 de junio de 2025.
    Tarifa Término fijo €/cliente/mes Término variable cent/kWh
    TUR.1 Consumo inferior o igual a 5.000 kWh/año. 3,26 4,122575
    TUR.2 Consumo superior a 5.000 kWh/año e inferior o igual a 15.000 kWh/año.
    5,66 4,018571
    """
    client = FakeBoeOpenDataClient(summary_payload, document_text)

    item = BoeGasTurProvider(
        source_url=None,
        user_agent="test-agent",
        client=client,
    ).fetch_city(city)[0]

    assert item.data_mode == DataMode.OFFICIAL_API
    assert item.details["document_id"] == "BOE-A-2025-13230"
    assert item.details["fixed_term_eur_month"] == 3.26
    assert item.details["variable_term_eur_per_kwh"] == 0.041226
    assert item.monthly_amount == 17.12
    assert client.requests[0]["url"].startswith(
        "https://www.boe.es/datosabiertos/api/boe/sumario/"
    )
    assert client.requests[-1]["url"] == (
        "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2025-13230"
    )


def test_boe_gas_heating_profile_uses_tur2() -> None:
    city = get_supported_city("Madrid")
    assert city is not None
    text = """
    Publicado en BOE núm. 156, de 30 de junio de 2025.
    Tarifa Término fijo €/cliente/mes Término variable cent/kWh
    TUR.1 Consumo inferior o igual a 5.000 kWh/año. 3,26 4,122575
    TUR.2 Consumo superior a 5.000 kWh/año e inferior o igual a 15.000 kWh/año.
    5,66 4,018571
    """
    client = FakeTextClient(text)

    item = BoeGasTurProvider(
        source_url="https://www.boe.es/diario_boe/xml.php?id=BOE-A-2025-13230",
        user_agent="test-agent",
        default_profile="heating",
        gas_bill_assumptions=GasBillAssumptions(
            hydrocarbons_tax_eur_per_kwh=0.00234,
            vat_rate=0.21,
            meter_rental_monthly_eur=0,
        ),
        client=client,
    ).fetch_city(city)[0]

    assert item.details["gas_profile"] == "heating"
    assert item.details["rate_code"] == "TUR.2"
    assert item.details["annual_kwh"] == 8000
    assert item.monthly_amount == 41.15


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
        lookback_days=30,
        default_profile="standard",
        geo_name="Península",
        client=client,
    ).fetch_city(city)[0]

    assert item.category == CostCategory.ELECTRICITY
    assert item.monthly_amount == 44.75
    assert item.confidence == Confidence.MEDIUM
    assert item.data_mode == DataMode.OFFICIAL_API
    assert item.details["raw_values"] == 2
    assert item.details["average_eur_per_kwh"] == 0.15
    assert item.details["energy_term_eur"] == 27
    assert item.details["power_term_eur"] == 7.42
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
        lookback_days=30,
        default_profile="standard",
        geo_name="Península",
        client=client,
    )

    madrid_item = provider.fetch_city(madrid)[0]
    valencia_item = provider.fetch_city(valencia)[0]

    assert madrid_item.monthly_amount == valencia_item.monthly_amount == 44.75
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
        lookback_days=30,
        default_profile="standard",
        geo_name="Península",
        client=client,
    ).fetch_city(city)[0]

    assert item.details["geo_name"] == "Península"
    assert item.details["raw_values"] == 2
    assert item.details["average_raw_value"] == 150
    assert item.details["average_eur_per_kwh"] == 0.15
    assert item.monthly_amount == 44.75
