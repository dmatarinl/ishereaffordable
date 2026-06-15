from app.affordability.calculator import AffordabilityCalculator
from app.affordability.models import AffordabilityEstimate, CityCostInputs
from app.cities import SupportedCity
from app.storage.database import CostObservationRepository


class AffordabilityService:
    def __init__(
        self,
        repository: CostObservationRepository,
        calculator: AffordabilityCalculator,
    ) -> None:
        self.repository = repository
        self.calculator = calculator

    def estimate(self, city: SupportedCity) -> AffordabilityEstimate | None:
        observations = self.repository.latest_city_observations(city.key)
        if not observations:
            return None

        return self.calculator.estimate(
            CityCostInputs(
                city=city.name,
                city_key=city.key,
                country=city.country,
                currency=city.currency,
                line_items=observations,
            )
        )
