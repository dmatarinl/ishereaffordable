from app.affordability.models import AffordabilityEstimate, CityCosts


class AffordabilityCalculator:
    def __init__(self, safety_margin_percent: float) -> None:
        if safety_margin_percent < 0:
            raise ValueError("safety_margin_percent must be positive")
        self.safety_margin_percent = safety_margin_percent

    def estimate(self, costs: CityCosts) -> AffordabilityEstimate:
        monthly_baseline = sum(
            [
                costs.monthly.rent,
                costs.monthly.utilities,
                costs.monthly.groceries,
                costs.monthly.transport,
                costs.monthly.leisure,
            ]
        )
        monthly_safety_margin = monthly_baseline * self.safety_margin_percent / 100
        monthly_required = monthly_baseline + monthly_safety_margin

        return AffordabilityEstimate(
            city=costs.city,
            country=costs.country,
            currency=costs.currency,
            monthly_baseline=round(monthly_baseline, 2),
            monthly_safety_margin=round(monthly_safety_margin, 2),
            monthly_required=round(monthly_required, 2),
            annual_required=round(monthly_required * 12, 2),
            source=costs.source,
            assumptions=[
                "Single adult household",
                "One-bedroom rental baseline",
                "Public transport instead of car ownership",
                f"{self.safety_margin_percent:g}% safety margin for irregular expenses",
            ],
        )
