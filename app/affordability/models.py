from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class CostCategory(StrEnum):
    RENT = "rent"
    ELECTRICITY = "electricity"
    GAS = "gas"
    WATER = "water"
    TRASH_TAX = "trash_tax"
    FOOD = "food"
    PUBLIC_TRANSPORT = "public_transport"
    SAFETY_MARGIN = "safety_margin"


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DataMode(StrEnum):
    OFFICIAL_API = "official_api"
    PERMITTED_SCRAPE = "permitted_scrape"
    MANUAL_SEED = "manual_seed"
    CALCULATED = "calculated"
    UNAVAILABLE = "unavailable"


class CostLineItem(BaseModel):
    category: CostCategory
    label: str
    monthly_amount: float = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    data_mode: DataMode = DataMode.MANUAL_SEED
    source_name: str
    source_url: str
    observed_at: datetime
    cached_at: datetime | None = None
    valid_until: datetime | None = None
    confidence: Confidence
    methodology: str
    details: dict[str, Any] = Field(default_factory=dict)


class CityCostInputs(BaseModel):
    city: str
    city_key: str
    country: str
    currency: str
    line_items: list[CostLineItem]
    household_profile: str = "Single adult, one-bedroom rental, no car, Spain MVP"
    assumptions: list[str] = Field(
        default_factory=lambda: [
            "One adult household",
            "Long-term one-bedroom rental",
            "No private car ownership",
            "Gas usage depends on the selected household gas profile",
            "Water usage depends on the selected household water profile",
            "Trash tax converted from annual to monthly cost",
        ]
    )


class SourceStatus(BaseModel):
    source_id: str
    source_name: str
    status: str
    last_started_at: datetime | None = None
    last_finished_at: datetime | None = None
    message: str | None = None


class AffordabilityEstimate(BaseModel):
    city: str
    city_key: str
    country: str
    currency: str
    profile: str
    electricity_profile: str
    gas_profile: str
    water_profile: str
    safety_margin_percent: float
    monthly_baseline: float
    monthly_safety_margin: float
    monthly_required: float
    annual_required: float
    line_items: list[CostLineItem]
    assumptions: list[str]
    warnings: list[str]
    freshness: dict[str, datetime]
