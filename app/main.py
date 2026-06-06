from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.affordability.calculator import AffordabilityCalculator
from app.core.config import settings
from app.providers.mock import MockCostOfLivingProvider

app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory="static"), name="static")

provider = MockCostOfLivingProvider()
calculator = AffordabilityCalculator(
    safety_margin_percent=settings.safety_margin_percent,
)


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}


@app.get("/api/affordability")
def affordability(
    city: str = Query(..., min_length=2, examples=["Madrid"]),
    currency: str = Query(settings.default_currency, min_length=3, max_length=3),
):
    city_costs = provider.get_city_costs(city=city, currency=currency.upper())
    return calculator.estimate(city_costs)
