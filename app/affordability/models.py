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


class CostLineItem(BaseModel):
    category: CostCategory
    label: str
    monthly_amount: float = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    source_name: str
    source_url: str
    observed_at: datetime
    confidence: Confidence
    methodology: str
    details: dict[str, Any] = Field(default_factory=dict)


class CityCostInputs(BaseModel):
    city: str
    city_key: str
    country: str
    currency: str
    line_items: list[CostLineItem]


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
    monthly_baseline: float
    monthly_safety_margin: float
    monthly_required: float
    annual_required: float
    line_items: list[CostLineItem]
    assumptions: list[str]
    warnings: list[str]
    freshness: dict[str, datetime]
