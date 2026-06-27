import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
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
from app.services.refresh import default_providers, ensure_seed_data
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
