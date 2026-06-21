from datetime import UTC, datetime

from app.affordability.models import (
    AffordabilityEstimate,
    CityCostInputs,
    Confidence,
    CostCategory,
    CostLineItem,
    DataMode,
)
from app.sources.catalog import validate_line_items

CORE_CATEGORIES = [
    CostCategory.RENT,
    CostCategory.ELECTRICITY,
    CostCategory.GAS,
    CostCategory.WATER,
    CostCategory.TRASH_TAX,
    CostCategory.FOOD,
    CostCategory.PUBLIC_TRANSPORT,
]


class AffordabilityCalculator:
    def __init__(self, safety_margin_percent: float) -> None:
        if safety_margin_percent < 0:
            raise ValueError("safety_margin_percent must be positive")
        self.safety_margin_percent = safety_margin_percent

    def estimate(self, costs: CityCostInputs) -> AffordabilityEstimate:
        by_category = {item.category: item for item in costs.line_items}
        category_order = {
            category: position for position, category in enumerate(CORE_CATEGORIES)
        }
        missing_categories = [
            category.value
            for category in CORE_CATEGORIES
            if category not in by_category
        ]
        baseline_items = sorted(
            (
                item
                for item in costs.line_items
                if item.category != CostCategory.SAFETY_MARGIN
            ),
            key=lambda item: category_order.get(item.category, len(CORE_CATEGORIES)),
        )
        monthly_baseline = sum(item.monthly_amount for item in baseline_items)
        monthly_safety_margin = monthly_baseline * self.safety_margin_percent / 100

        safety_margin = CostLineItem(
            category=CostCategory.SAFETY_MARGIN,
            label="Safety margin",
            monthly_amount=round(monthly_safety_margin, 2),
            currency=costs.currency,
            data_mode=DataMode.CALCULATED,
            source_name="Is Here Affordable formula",
            source_url="https://github.com/dmatarinl/ishereaffordable",
            observed_at=datetime.now(UTC),
            cached_at=datetime.now(UTC),
            confidence=Confidence.MEDIUM,
            methodology=(
                f"{self.safety_margin_percent:g}% buffer applied to the monthly "
                "baseline for irregular expenses and small estimation errors."
            ),
            details={"safety_margin_percent": self.safety_margin_percent},
        )

        line_items = [*baseline_items, safety_margin]
        monthly_required = monthly_baseline + monthly_safety_margin
        warnings = [
            f"Missing cached data for category: {category}"
            for category in missing_categories
        ]
        warnings.extend(validate_line_items(line_items))

        return AffordabilityEstimate(
            city=costs.city,
            city_key=costs.city_key,
            country=costs.country,
            currency=costs.currency,
            profile=costs.household_profile,
            electricity_profile=_electricity_profile_from_costs(costs),
            gas_profile=_gas_profile_from_costs(costs),
            water_profile=_water_profile_from_costs(costs),
            safety_margin_percent=self.safety_margin_percent,
            monthly_baseline=round(monthly_baseline, 2),
            monthly_safety_margin=round(monthly_safety_margin, 2),
            monthly_required=round(monthly_required, 2),
            annual_required=round(monthly_required * 12, 2),
            line_items=line_items,
            assumptions=costs.assumptions,
            warnings=warnings,
            freshness={
                item.category.value: item.cached_at or item.observed_at
                for item in line_items
            },
        )


def _electricity_profile_from_costs(costs: CityCostInputs) -> str:
    electricity = next(
        (
            item
            for item in costs.line_items
            if item.category == CostCategory.ELECTRICITY
        ),
        None,
    )
    if electricity is None:
        return "standard"

    profile = electricity.details.get("electricity_profile")
    if isinstance(profile, str) and profile:
        return profile

    return "standard"


def _gas_profile_from_costs(costs: CityCostInputs) -> str:
    gas = next(
        (
            item
            for item in costs.line_items
            if item.category == CostCategory.GAS
        ),
        None,
    )
    if gas is None:
        return "standard"

    profile = gas.details.get("gas_profile")
    if isinstance(profile, str) and profile:
        return profile

    return "standard"


def _water_profile_from_costs(costs: CityCostInputs) -> str:
    water = next(
        (
            item
            for item in costs.line_items
            if item.category == CostCategory.WATER
        ),
        None,
    )
    if water is None:
        return "standard"

    profile = water.details.get("water_profile")
    if isinstance(profile, str) and profile:
        return profile

    return "standard"
