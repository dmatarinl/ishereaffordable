from typing import Protocol

from app.affordability.models import CityCosts


class CostOfLivingProvider(Protocol):
    def get_city_costs(self, city: str, currency: str) -> CityCosts:
        """Return current cost-of-living inputs for a city."""
