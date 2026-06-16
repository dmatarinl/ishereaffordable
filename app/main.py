from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.affordability.calculator import AffordabilityCalculator
from app.cities import SUPPORTED_CITIES, get_supported_city
from app.core.config import settings
from app.electricity.profiles import (
    DEFAULT_ELECTRICITY_PROFILE,
    ElectricityProfile,
    electricity_profile_catalog,
)
from app.services.affordability import AffordabilityService
from app.services.refresh import ensure_seed_data
from app.sources.catalog import source_rules
from app.storage.database import CostObservationRepository

repository = CostObservationRepository(settings.database_url)
calculator = AffordabilityCalculator(
    safety_margin_percent=settings.safety_margin_percent,
)
affordability_service = AffordabilityService(repository, calculator)
DEFAULT_ELECTRICITY_PROFILE_QUERY = Query(DEFAULT_ELECTRICITY_PROFILE)
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


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


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
    return {"sources": repository.source_statuses()}


@app.get("/api/sources/rules")
def sources_rules():
    return {"rules": source_rules()}


@app.get("/api/electricity/profiles")
def electricity_profiles():
    return {
        "default": DEFAULT_ELECTRICITY_PROFILE.value,
        "profiles": electricity_profile_catalog(),
    }


@app.get("/api/affordability")
def affordability(
    city: str = Query(..., min_length=2, examples=["Madrid"]),
    currency: str = Query(settings.default_currency, min_length=3, max_length=3),
    electricity_profile: ElectricityProfile = DEFAULT_ELECTRICITY_PROFILE_QUERY,
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

    estimate = affordability_service.estimate_with_electricity_profile(
        supported_city,
        electricity_profile,
        safety_margin_percent,
    )
    if estimate is None:
        raise HTTPException(
            status_code=503,
            detail="No cached observations found. Run python -m app.jobs.refresh_all.",
        )

    return estimate
