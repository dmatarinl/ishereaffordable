from app.affordability.models import CityCosts, MonthlyCostBreakdown


class MockCostOfLivingProvider:
    def __init__(self) -> None:
        self._cities = {
            "madrid": CityCosts(
                city="Madrid",
                country="Spain",
                currency="EUR",
                monthly=MonthlyCostBreakdown(
                    rent=1150,
                    utilities=160,
                    groceries=330,
                    transport=55,
                    leisure=260,
                ),
                source="Seed data for product development",
            ),
            "barcelona": CityCosts(
                city="Barcelona",
                country="Spain",
                currency="EUR",
                monthly=MonthlyCostBreakdown(
                    rent=1350,
                    utilities=170,
                    groceries=350,
                    transport=45,
                    leisure=290,
                ),
                source="Seed data for product development",
            ),
            "valencia": CityCosts(
                city="Valencia",
                country="Spain",
                currency="EUR",
                monthly=MonthlyCostBreakdown(
                    rent=850,
                    utilities=145,
                    groceries=310,
                    transport=45,
                    leisure=220,
                ),
                source="Seed data for product development",
            ),
        }

    def get_city_costs(self, city: str, currency: str) -> CityCosts:
        normalized_city = city.strip().lower()
        costs = self._cities.get(normalized_city)

        if costs is None:
            costs = CityCosts(
                city=city.strip().title(),
                country="Unknown",
                currency=currency,
                monthly=MonthlyCostBreakdown(
                    rent=1000,
                    utilities=150,
                    groceries=320,
                    transport=60,
                    leisure=240,
                ),
                source="Generic fallback seed data",
            )

        return costs.model_copy(update={"currency": currency})
