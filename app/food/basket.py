from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

FOOD_BASKET_PATH = Path(__file__).resolve().parents[1] / "data" / "food_basket.json"


class BasketSourceBasis(BaseModel):
    name: str
    url: str
    use: str


class BasketConfidenceThreshold(BaseModel):
    minimum_product_coverage: float = Field(ge=0, le=1)
    minimum_valid_sources: int = Field(ge=0)
    maximum_substitution_ratio: float = Field(ge=0, le=1)


class BasketItem(BaseModel):
    id: str
    name: str
    category: str
    monthly_quantity: float = Field(gt=0)
    unit: str
    required: bool
    reference_terms: list[str] = Field(min_length=1)
    substitutions: list[str] = Field(default_factory=list)
    seed_unit_price_eur: float = Field(ge=0)
    price_notes: str


class FoodBasketDefinition(BaseModel):
    version: str
    profile: str
    period: str
    currency: str = Field(min_length=3, max_length=3)
    aggregation_method: str
    pricing_policy: dict[str, str]
    source_basis: list[BasketSourceBasis] = Field(min_length=3)
    confidence_thresholds: dict[str, BasketConfidenceThreshold]
    items: list[BasketItem] = Field(min_length=30, max_length=50)

    @model_validator(mode="after")
    def validate_basket(self) -> "FoodBasketDefinition":
        ids = [item.id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("food basket item ids must be unique")
        required_thresholds = {"high", "medium", "low"}
        missing = required_thresholds - set(self.confidence_thresholds)
        if missing:
            raise ValueError(f"missing confidence thresholds: {sorted(missing)}")
        return self

    @property
    def required_item_count(self) -> int:
        return sum(1 for item in self.items if item.required)

    @property
    def optional_item_count(self) -> int:
        return len(self.items) - self.required_item_count

    def seed_monthly_total_eur(self) -> float:
        total = sum(
            item.monthly_quantity * item.seed_unit_price_eur for item in self.items
        )
        return round(
            total,
            2,
        )


def load_food_basket(path: Path = FOOD_BASKET_PATH) -> FoodBasketDefinition:
    return FoodBasketDefinition.model_validate_json(path.read_text(encoding="utf-8"))


@lru_cache
def canonical_food_basket() -> FoodBasketDefinition:
    return load_food_basket()
