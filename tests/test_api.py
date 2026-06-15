from fastapi.testclient import TestClient

from app.main import app


def test_affordability_endpoint_returns_source_breakdown() -> None:
    with TestClient(app) as client:
        response = client.get("/api/affordability?city=Madrid&currency=EUR")

    assert response.status_code == 200
    payload = response.json()

    assert payload["city"] == "Madrid"
    assert payload["monthly_required"] > payload["monthly_baseline"]
    assert len(payload["line_items"]) == 8
    assert {item["category"] for item in payload["line_items"]} >= {
        "rent",
        "food",
        "safety_margin",
    }
    assert payload["warnings"]


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


def test_unsupported_city_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.get("/api/affordability?city=Paris&currency=EUR")

    assert response.status_code == 404


def test_non_eur_currency_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.get("/api/affordability?city=Madrid&currency=USD")

    assert response.status_code == 400
