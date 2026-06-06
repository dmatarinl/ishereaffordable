from app.affordability.calculator import AffordabilityCalculator
from app.affordability.models import CityCosts, MonthlyCostBreakdown


def test_estimate_adds_safety_margin() -> None:
    costs = CityCosts(
        city="Madrid",
        country="Spain",
        currency="EUR",
        monthly=MonthlyCostBreakdown(
            rent=1000,
            utilities=100,
            groceries=300,
            transport=50,
            leisure=150,
        ),
        source="test",
    )

    estimate = AffordabilityCalculator(safety_margin_percent=10).estimate(costs)

    assert estimate.monthly_baseline == 1600
    assert estimate.monthly_safety_margin == 160
    assert estimate.monthly_required == 1760
    assert estimate.annual_required == 21120


def test_negative_safety_margin_is_rejected() -> None:
    try:
        AffordabilityCalculator(safety_margin_percent=-1)
    except ValueError as error:
        assert "safety_margin_percent" in str(error)
    else:
        raise AssertionError("negative safety margin should fail")
