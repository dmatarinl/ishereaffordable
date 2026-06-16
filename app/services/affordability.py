from app.affordability.calculator import AffordabilityCalculator
from app.affordability.models import AffordabilityEstimate, CityCostInputs
from app.cities import SupportedCity
from app.electricity.profiles import ElectricityProfile, electricity_profile_assumptions
from app.services.refresh import apply_request_profiles
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

        return self._estimate_from_observations(
            city,
            observations,
            ElectricityProfile.STANDARD,
        )

    def estimate_with_electricity_profile(
        self,
        city: SupportedCity,
        electricity_profile: ElectricityProfile,
    ) -> AffordabilityEstimate | None:
        observations = self.repository.latest_city_observations(city.key)
        if not observations:
            return None

        return self._estimate_from_observations(
            city,
            observations,
            electricity_profile,
        )

    def _estimate_from_observations(
        self,
        city: SupportedCity,
        observations,
        electricity_profile: ElectricityProfile,
    ) -> AffordabilityEstimate:
        adjusted_observations = apply_request_profiles(
            observations,
            electricity_profile,
        )
        return self.calculator.estimate(
            CityCostInputs(
                city=city.name,
                city_key=city.key,
                country=city.country,
                currency=city.currency,
                line_items=adjusted_observations,
                household_profile=(
                    "Single adult, one-bedroom rental, no car, Spain MVP "
                    f"({electricity_profile.value} electricity profile)"
                ),
                assumptions=[
                    "One adult household",
                    "Long-term one-bedroom rental",
                    "No private car ownership",
                    *electricity_profile_assumptions(electricity_profile),
                    "250 kWh/month gas usage where gas is applicable",
                    "6 m3/month water usage",
                    "Trash tax converted from annual to monthly cost",
                ],
            )
        )
