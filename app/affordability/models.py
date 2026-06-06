from pydantic import BaseModel, Field


class MonthlyCostBreakdown(BaseModel):
    rent: float = Field(ge=0)
    utilities: float = Field(ge=0)
    groceries: float = Field(ge=0)
    transport: float = Field(ge=0)
    leisure: float = Field(ge=0)


class CityCosts(BaseModel):
    city: str
    country: str
    currency: str
    monthly: MonthlyCostBreakdown
    source: str


class AffordabilityEstimate(BaseModel):
    city: str
    country: str
    currency: str
    monthly_baseline: float
    monthly_safety_margin: float
    monthly_required: float
    annual_required: float
    source: str
    assumptions: list[str]
