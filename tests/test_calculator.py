from datetime import UTC, datetime

from app.affordability.calculator import AffordabilityCalculator
from app.affordability.models import (
    CityCostInputs,
    Confidence,
    CostCategory,
    CostLineItem,
)


def _item(category: CostCategory, amount: float) -> CostLineItem:
    return CostLineItem(
        category=category,
        label=category.value,
        monthly_amount=amount,
        currency="EUR",
        source_name="test",
        source_url="https://example.com",
        observed_at=datetime.now(UTC),
        confidence=Confidence.MEDIUM,
        methodology="test methodology",
    )


def test_estimate_adds_safety_margin() -> None:
    costs = CityCostInputs(
        city="Madrid",
        city_key="madrid",
        country="Spain",
        currency="EUR",
        line_items=[
            _item(CostCategory.RENT, 1000),
            _item(CostCategory.ELECTRICITY, 50),
            _item(CostCategory.GAS, 25),
            _item(CostCategory.WATER, 20),
            _item(CostCategory.TRASH_TAX, 10),
            _item(CostCategory.FOOD, 300),
            _item(CostCategory.PUBLIC_TRANSPORT, 50),
        ],
    )

    estimate = AffordabilityCalculator(safety_margin_percent=10).estimate(costs)

    assert estimate.monthly_baseline == 1455
    assert estimate.monthly_safety_margin == 145.5
    assert estimate.monthly_required == 1600.5
    assert estimate.annual_required == 19206
    assert estimate.line_items[-1].category == CostCategory.SAFETY_MARGIN


def test_missing_categories_are_reported() -> None:
    costs = CityCostInputs(
        city="Madrid",
        city_key="madrid",
        country="Spain",
        currency="EUR",
        line_items=[_item(CostCategory.RENT, 1000)],
    )

    estimate = AffordabilityCalculator(safety_margin_percent=15).estimate(costs)

    assert "Missing cached data for category: electricity" in estimate.warnings
    assert estimate.monthly_required == 1150


def test_low_confidence_items_are_reported() -> None:
    item = _item(CostCategory.RENT, 1000)
    item.confidence = Confidence.LOW
    costs = CityCostInputs(
        city="Madrid",
        city_key="madrid",
        country="Spain",
        currency="EUR",
        line_items=[item],
    )

    estimate = AffordabilityCalculator(safety_margin_percent=15).estimate(costs)

    assert "rent is based on low-confidence fallback data." in estimate.warnings


def test_negative_safety_margin_is_rejected() -> None:
    try:
        AffordabilityCalculator(safety_margin_percent=-1)
    except ValueError as error:
        assert "safety_margin_percent" in str(error)
    else:
        raise AssertionError("negative safety margin should fail")
