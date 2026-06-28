import secrets
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.affordability.calculator import AffordabilityCalculator
from app.affordability.models import SourceStatus
from app.cities import SUPPORTED_CITIES, get_supported_city
from app.core.config import settings
from app.electricity.profiles import (
    DEFAULT_ELECTRICITY_PROFILE,
    ElectricityProfile,
    electricity_profile_catalog,
)
from app.gas.profiles import DEFAULT_GAS_PROFILE, GasProfile, gas_profile_catalog
from app.public_transport.fares import MODEL_VERSION as TRANSPORT_MODEL_VERSION
from app.public_transport.fares import transport_fare_catalog
from app.services.affordability import AffordabilityService
from app.services.refresh import (
    RefreshResult,
    default_providers,
    ensure_seed_data,
)
from app.services.refresh import (
    refresh_all as refresh_all_observations,
)
from app.services.refresh import (
    refresh_city as refresh_city_observations,
)
from app.sources.catalog import source_rules
from app.storage.database import CostObservationRepository
from app.trash_tax.rules import (
    MODEL_VERSION,
    MUNICIPAL_WASTE_TARIFFS,
    municipal_waste_tariff_catalog,
)
from app.water.profiles import (
    DEFAULT_WATER_PROFILE,
    WATER_PROFILE_METHODOLOGY,
    WaterProfile,
    water_profile_catalog,
    water_profile_sources,
)

repository = CostObservationRepository(settings.database_url)
calculator = AffordabilityCalculator(
    safety_margin_percent=settings.safety_margin_percent,
)
affordability_service = AffordabilityService(repository, calculator)
DEFAULT_ELECTRICITY_PROFILE_QUERY = Query(DEFAULT_ELECTRICITY_PROFILE)
DEFAULT_GAS_PROFILE_QUERY = Query(DEFAULT_GAS_PROFILE)
DEFAULT_WATER_PROFILE_QUERY = Query(DEFAULT_WATER_PROFILE)
SAFETY_MARGIN_PERCENT_QUERY = Query(
    settings.safety_margin_percent,
    ge=0,
    le=100,
)
admin_refresh_lock = Lock()
admin_refresh_state: dict[str, Any] = {
    "running": False,
    "last_scope": None,
    "last_started_at": None,
    "last_finished_at": None,
    "last_status": None,
    "last_message": None,
    "last_results": [],
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    repository.init_schema()
    ensure_seed_data(repository)
    yield


production = settings.app_env == "production"
app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    docs_url=None if production else "/docs",
    redoc_url=None if production else "/redoc",
    openapi_url=None if production else "/openapi.json",
)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.middleware("http")
async def require_proxy_secret_for_api(request: Request, call_next):
    if request.url.path.startswith("/api/") and settings.backend_proxy_secret:
        provided = request.headers.get("x-ishereaffordable-proxy-secret")
        if provided is None or not secrets.compare_digest(
            provided,
            settings.backend_proxy_secret,
        ):
            return JSONResponse({"detail": "Not found"}, status_code=404)

    return await call_next(request)


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}


@app.get("/api/cities")
def cities():
    return {"cities": SUPPORTED_CITIES}


@app.get("/api/sources/status")
def sources_status():
    active_source_ids = {provider.source_id for provider in default_providers()}
    active_statuses = [
        status
        for status in repository.source_statuses()
        if status.source_id in active_source_ids
    ]
    return {"sources": public_source_statuses(active_statuses)}


def public_source_statuses(statuses: list[SourceStatus]) -> list[SourceStatus]:
    return [
        status.model_copy(update={"message": _public_source_status_message(status)})
        for status in statuses
    ]


def _public_source_status_message(status: SourceStatus) -> str | None:
    if status.message is None:
        return None
    if status.status == "failed":
        return "Source refresh failed. Check server logs for details."
    if _contains_sensitive_term(status.message):
        return "Source refresh completed with hidden operational details."
    if len(status.message) > 240:
        return f"{status.message[:237]}..."
    return status.message


def _contains_sensitive_term(message: str) -> bool:
    sensitive_terms = (
        "api_key",
        "apikey",
        "authorization",
        "bearer",
        "password",
        "secret",
        "token",
        "x-api-key",
    )
    normalized = message.lower()
    return any(term in normalized for term in sensitive_terms)


def _require_admin_secret(request: Request) -> None:
    if not settings.admin_api_secret:
        raise HTTPException(status_code=503, detail="Admin API is not configured.")

    provided = _admin_secret_from_request(request)
    if provided is None or not secrets.compare_digest(
        provided,
        settings.admin_api_secret,
    ):
        raise HTTPException(status_code=401, detail="Admin credentials required.")


def _admin_secret_from_request(request: Request) -> str | None:
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        return token
    return request.headers.get("x-ishereaffordable-admin-secret")


def _admin_source_statuses(statuses: list[SourceStatus]) -> list[SourceStatus]:
    return [
        status.model_copy(update={"message": _admin_source_status_message(status)})
        for status in statuses
    ]


def _admin_source_status_message(status: SourceStatus) -> str | None:
    if status.message is None:
        return None
    if _contains_sensitive_term(status.message):
        return "Source refresh completed with hidden sensitive details."
    if len(status.message) > 500:
        return f"{status.message[:497]}..."
    return status.message


def _admin_observation_snapshot() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for city in SUPPORTED_CITIES:
        observations = repository.latest_city_observations(city.key)
        rows.extend(
            {
                "city_key": city.key,
                "city": city.name,
                "category": item.category.value,
                "label": item.label,
                "data_mode": item.data_mode.value,
                "source_name": item.source_name,
                "observed_at": item.observed_at,
                "cached_at": item.cached_at,
                "valid_until": item.valid_until,
            }
            for item in observations
        )
    return rows


def _admin_status_payload() -> dict[str, Any]:
    statuses = _admin_source_statuses(repository.source_statuses())
    observations = _admin_observation_snapshot()
    latest_cached_at = max(
        (item["cached_at"] for item in observations if item["cached_at"] is not None),
        default=None,
    )
    return {
        "summary": {
            "sources_total": len(statuses),
            "sources_failed": sum(
                1 for status in statuses if status.status == "failed"
            ),
            "sources_degraded": sum(
                1 for status in statuses if status.status == "degraded"
            ),
            "observations_total": len(observations),
            "latest_cached_at": latest_cached_at,
        },
        "cities": [
            {"key": city.key, "name": city.name, "country": city.country}
            for city in SUPPORTED_CITIES
        ],
        "sources": statuses,
        "observations": observations,
        "manual_refresh": admin_refresh_state.copy(),
    }


def _refresh_result_payload(result: RefreshResult) -> dict[str, Any]:
    return {
        "city_key": result.city_key,
        "observations": result.observations,
        "warnings": result.warnings,
    }


def _set_admin_refresh_state(**values: Any) -> None:
    admin_refresh_state.update(values)


def _run_admin_refresh(city: str | None) -> None:
    started_at = datetime.now(UTC)
    scope = city or "all"
    _set_admin_refresh_state(
        running=True,
        last_scope=scope,
        last_started_at=started_at,
        last_finished_at=None,
        last_status="running",
        last_message=f"Refresh started for {scope}.",
        last_results=[],
    )
    try:
        repository.init_schema()
        if city:
            results = [refresh_city_observations(city, repository)]
        else:
            results = refresh_all_observations(repository)
        _set_admin_refresh_state(
            running=False,
            last_finished_at=datetime.now(UTC),
            last_status="ok",
            last_message=f"Refresh completed for {scope}.",
            last_results=[_refresh_result_payload(result) for result in results],
        )
    except Exception:
        _set_admin_refresh_state(
            running=False,
            last_finished_at=datetime.now(UTC),
            last_status="failed",
            last_message="Refresh failed. Check server logs for details.",
            last_results=[],
        )
        raise
    finally:
        admin_refresh_lock.release()


@app.get("/api/admin/sources/status")
def admin_sources_status(request: Request):
    _require_admin_secret(request)
    return _admin_status_payload()


@app.post("/api/admin/refresh", status_code=202)
def admin_refresh(
    request: Request,
    background_tasks: BackgroundTasks,
    city: str | None = Query(None, min_length=2),
):
    _require_admin_secret(request)
    if city is not None and get_supported_city(city) is None:
        raise HTTPException(
            status_code=404,
            detail="City is not supported in the Spain MVP.",
        )
    if not admin_refresh_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="A refresh is already running.")

    normalized_city = get_supported_city(city).name if city else None
    _set_admin_refresh_state(
        running=True,
        last_scope=normalized_city or "all",
        last_started_at=datetime.now(UTC),
        last_finished_at=None,
        last_status="queued",
        last_message=f"Refresh queued for {normalized_city or 'all'}.",
        last_results=[],
    )
    background_tasks.add_task(_run_admin_refresh, normalized_city)
    return {
        "status": "queued",
        "scope": normalized_city or "all",
        "message": f"Refresh queued for {normalized_city or 'all'}.",
    }


@app.get("/api/sources/rules")
def sources_rules():
    return {"rules": source_rules()}


@app.get("/api/electricity/profiles")
def electricity_profiles():
    return {
        "default": DEFAULT_ELECTRICITY_PROFILE.value,
        "profiles": electricity_profile_catalog(),
    }


@app.get("/api/gas/profiles")
def gas_profiles():
    return {
        "default": DEFAULT_GAS_PROFILE.value,
        "profiles": gas_profile_catalog(),
    }


@app.get("/api/water/profiles")
def water_profiles():
    return {
        "default": DEFAULT_WATER_PROFILE.value,
        "profiles": water_profile_catalog(),
        "methodology": WATER_PROFILE_METHODOLOGY,
        "sources": water_profile_sources(),
    }


@app.get("/api/trash-tax/rules")
def trash_tax_rules():
    fallback_cities = [
        city.key for city in SUPPORTED_CITIES if city.key not in MUNICIPAL_WASTE_TARIFFS
    ]
    return {
        "model": "hybrid",
        "version": MODEL_VERSION,
        "rules": municipal_waste_tariff_catalog(),
        "fallback_cities": fallback_cities,
    }


@app.get("/api/public-transport/fares")
def public_transport_fares():
    return {
        "model": "official-city-fare",
        "version": TRANSPORT_MODEL_VERSION,
        "profile": "adult without special discounts",
        "fares": transport_fare_catalog(),
    }


@app.get("/api/affordability")
def affordability(
    city: str = Query(..., min_length=2, examples=["Madrid"]),
    currency: str = Query(settings.default_currency, min_length=3, max_length=3),
    electricity_profile: ElectricityProfile = DEFAULT_ELECTRICITY_PROFILE_QUERY,
    gas_profile: GasProfile = DEFAULT_GAS_PROFILE_QUERY,
    water_profile: WaterProfile = DEFAULT_WATER_PROFILE_QUERY,
    safety_margin_percent: float = SAFETY_MARGIN_PERCENT_QUERY,
):
    if currency.upper() != settings.default_currency:
        raise HTTPException(
            status_code=400,
            detail="Spain MVP currently supports EUR only.",
        )

    supported_city = get_supported_city(city)
    if supported_city is None:
        raise HTTPException(
            status_code=404,
            detail="City is not supported in the Spain MVP.",
        )

    estimate = affordability_service.estimate_with_profiles(
        supported_city,
        electricity_profile,
        gas_profile,
        water_profile,
        safety_margin_percent,
    )
    if estimate is None:
        raise HTTPException(
            status_code=503,
            detail="No cached observations found. Run python -m app.jobs.refresh_all.",
        )

    return estimate
