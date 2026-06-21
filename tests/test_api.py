from fastapi.testclient import TestClient

from app.main import app


def test_affordability_endpoint_returns_source_breakdown() -> None:
    with TestClient(app) as client:
        response = client.get("/api/affordability?city=Madrid&currency=EUR")

    assert response.status_code == 200
    payload = response.json()

    assert payload["city"] == "Madrid"
    assert payload["electricity_profile"] == "standard"
    assert payload["gas_profile"] == "standard"
    assert payload["water_profile"] == "standard"
    assert payload["monthly_required"] > payload["monthly_baseline"]
    assert len(payload["line_items"]) == 8
    assert {item["category"] for item in payload["line_items"]} >= {
        "rent",
        "food",
        "safety_margin",
    }
    rent = next(item for item in payload["line_items"] if item["category"] == "rent")
    safety_margin = next(
        item for item in payload["line_items"] if item["category"] == "safety_margin"
    )
    assert rent["data_mode"] == "manual_seed"
    assert rent["cached_at"]
    assert "observed" not in rent["source_name"].lower()
    assert safety_margin["data_mode"] == "calculated"
    assert payload["warnings"]


def test_electricity_profiles_endpoint_lists_supported_profiles() -> None:
    with TestClient(app) as client:
        response = client.get("/api/electricity/profiles")

    assert response.status_code == 200
    payload = response.json()

    assert payload["default"] == "standard"
    assert {profile["key"] for profile in payload["profiles"]} == {
        "light",
        "standard",
        "high",
    }


def test_gas_profiles_endpoint_lists_supported_profiles() -> None:
    with TestClient(app) as client:
        response = client.get("/api/gas/profiles")

    assert response.status_code == 200
    payload = response.json()

    assert payload["default"] == "standard"
    assert {profile["key"] for profile in payload["profiles"]} == {
        "low",
        "standard",
        "heating",
    }


def test_water_profiles_endpoint_lists_rationale_and_sources() -> None:
    with TestClient(app) as client:
        response = client.get("/api/water/profiles")

    assert response.status_code == 200
    payload = response.json()

    assert payload["default"] == "standard"
    assert [profile["monthly_m3"] for profile in payload["profiles"]] == [4, 6, 9]
    assert all(profile["rationale"] for profile in payload["profiles"])
    assert len(payload["sources"]) == 2
    assert "no single household water tariff" in payload["methodology"]


def test_trash_tax_rules_endpoint_exposes_hybrid_coverage() -> None:
    with TestClient(app) as client:
        response = client.get("/api/trash-tax/rules")

    assert response.status_code == 200
    payload = response.json()

    assert payload["model"] == "hybrid"
    assert payload["version"] == "2026.1"
    assert {rule["city_key"] for rule in payload["rules"]} == {
        "madrid",
        "zaragoza",
        "alicante",
    }
    assert "barcelona" in payload["fallback_cities"]


def test_affordability_endpoint_applies_electricity_profile() -> None:
    with TestClient(app) as client:
        light_response = client.get(
            "/api/affordability?city=Madrid&currency=EUR&electricity_profile=light"
        )
        high_response = client.get(
            "/api/affordability?city=Madrid&currency=EUR&electricity_profile=high"
        )

    assert light_response.status_code == 200
    assert high_response.status_code == 200

    light_payload = light_response.json()
    high_payload = high_response.json()
    light_electricity = next(
        item
        for item in light_payload["line_items"]
        if item["category"] == "electricity"
    )
    high_electricity = next(
        item
        for item in high_payload["line_items"]
        if item["category"] == "electricity"
    )

    assert light_payload["electricity_profile"] == "light"
    assert high_payload["electricity_profile"] == "high"
    assert light_electricity["monthly_amount"] < high_electricity["monthly_amount"]
    assert light_payload["monthly_required"] < high_payload["monthly_required"]


def test_affordability_endpoint_applies_gas_profile() -> None:
    with TestClient(app) as client:
        low_response = client.get(
            "/api/affordability?city=Madrid&currency=EUR&gas_profile=low"
        )
        heating_response = client.get(
            "/api/affordability?city=Madrid&currency=EUR&gas_profile=heating"
        )

    assert low_response.status_code == 200
    assert heating_response.status_code == 200

    low_payload = low_response.json()
    heating_payload = heating_response.json()
    low_gas = next(
        item
        for item in low_payload["line_items"]
        if item["category"] == "gas"
    )
    heating_gas = next(
        item
        for item in heating_payload["line_items"]
        if item["category"] == "gas"
    )

    assert low_payload["gas_profile"] == "low"
    assert heating_payload["gas_profile"] == "heating"
    assert low_gas["monthly_amount"] < heating_gas["monthly_amount"]
    assert low_payload["monthly_required"] < heating_payload["monthly_required"]


def test_affordability_endpoint_applies_water_profile() -> None:
    with TestClient(app) as client:
        low_response = client.get(
            "/api/affordability?city=Madrid&currency=EUR&water_profile=low"
        )
        high_response = client.get(
            "/api/affordability?city=Madrid&currency=EUR&water_profile=high"
        )

    assert low_response.status_code == 200
    assert high_response.status_code == 200

    low_payload = low_response.json()
    high_payload = high_response.json()
    low_water = next(
        item
        for item in low_payload["line_items"]
        if item["category"] == "water"
    )
    high_water = next(
        item
        for item in high_payload["line_items"]
        if item["category"] == "water"
    )

    assert low_payload["water_profile"] == "low"
    assert high_payload["water_profile"] == "high"
    assert low_water["details"]["monthly_m3"] == 4
    assert high_water["details"]["monthly_m3"] == 9
    assert low_water["monthly_amount"] < high_water["monthly_amount"]
    assert low_water["data_mode"] == high_water["data_mode"] == "manual_seed"


def test_zaragoza_trash_tax_uses_selected_water_profile() -> None:
    with TestClient(app) as client:
        standard_response = client.get(
            "/api/affordability?city=Zaragoza&water_profile=standard"
        )
        high_response = client.get(
            "/api/affordability?city=Zaragoza&water_profile=high"
        )

    assert standard_response.status_code == 200
    assert high_response.status_code == 200
    standard_tax = next(
        item
        for item in standard_response.json()["line_items"]
        if item["category"] == "trash_tax"
    )
    high_tax = next(
        item
        for item in high_response.json()["line_items"]
        if item["category"] == "trash_tax"
    )

    assert standard_tax["data_mode"] == "official_publication"
    assert standard_tax["monthly_amount"] == 6.06
    assert high_tax["monthly_amount"] == 6.67
    assert high_tax["details"]["annual_amount"] == 80.0


def test_affordability_endpoint_applies_safety_margin_percent() -> None:
    with TestClient(app) as client:
        low_margin_response = client.get(
            "/api/affordability?city=Madrid&currency=EUR&safety_margin_percent=5"
        )
        high_margin_response = client.get(
            "/api/affordability?city=Madrid&currency=EUR&safety_margin_percent=15"
        )

    assert low_margin_response.status_code == 200
    assert high_margin_response.status_code == 200

    low_margin_payload = low_margin_response.json()
    high_margin_payload = high_margin_response.json()
    low_margin_item = next(
        item
        for item in low_margin_payload["line_items"]
        if item["category"] == "safety_margin"
    )
    high_margin_item = next(
        item
        for item in high_margin_payload["line_items"]
        if item["category"] == "safety_margin"
    )

    assert low_margin_payload["safety_margin_percent"] == 5
    assert high_margin_payload["safety_margin_percent"] == 15
    assert low_margin_payload["monthly_baseline"] == high_margin_payload[
        "monthly_baseline"
    ]
    assert low_margin_item["monthly_amount"] < high_margin_item["monthly_amount"]
    assert low_margin_payload["monthly_required"] < high_margin_payload[
        "monthly_required"
    ]


def test_cities_endpoint_lists_spain_mvp_cities() -> None:
    with TestClient(app) as client:
        response = client.get("/api/cities")

    assert response.status_code == 200
    cities = response.json()["cities"]
    assert len(cities) == 8
    assert cities[0]["key"] == "madrid"


def test_sources_status_endpoint_returns_refresh_health() -> None:
    with TestClient(app) as client:
        response = client.get("/api/sources/status")

    assert response.status_code == 200
    assert response.json()["sources"]


def test_sources_rules_endpoint_returns_policy_catalog() -> None:
    with TestClient(app) as client:
        response = client.get("/api/sources/rules")

    assert response.status_code == 200
    rules = response.json()["rules"]
    rent = next(rule for rule in rules if rule["category"] == "rent")
    electricity = next(rule for rule in rules if rule["category"] == "electricity")
    gas = next(rule for rule in rules if rule["category"] == "gas")

    assert rent["first_choice"] == "Idealista Search API or approved real-estate API"
    assert "manual_seed" in rent["allowed_data_modes"]
    assert rent["freshness_days"] == 7
    assert electricity["first_choice"] == "eSIOS API"
    assert electricity["freshness_days"] == 1
    assert gas["first_choice"] == "BOE OpenData gas TUR resolution discovery"
    assert gas["freshness_days"] == 90


def test_unsupported_city_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.get("/api/affordability?city=Paris&currency=EUR")

    assert response.status_code == 404


def test_non_eur_currency_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.get("/api/affordability?city=Madrid&currency=USD")

    assert response.status_code == 400
