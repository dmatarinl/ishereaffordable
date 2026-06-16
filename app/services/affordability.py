from app.affordability.calculator import AffordabilityCalculator
from app.affordability.models import AffordabilityEstimate, CityCostInputs
from app.cities import SupportedCity
from app.core.config import settings
from app.electricity.profiles import ElectricityProfile, electricity_profile_assumptions
from app.gas.profiles import (
    DEFAULT_GAS_PROFILE,
    GasBillAssumptions,
    GasProfile,
    gas_profile_assumptions,
)
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
            DEFAULT_GAS_PROFILE,
        )

    def estimate_with_profiles(
        self,
        city: SupportedCity,
        electricity_profile: ElectricityProfile,
        gas_profile: GasProfile,
        safety_margin_percent: float | None = None,
    ) -> AffordabilityEstimate | None:
        observations = self.repository.latest_city_observations(city.key)
        if not observations:
            return None

        return self._estimate_from_observations(
            city,
            observations,
            electricity_profile,
            gas_profile,
            safety_margin_percent,
        )

    def _estimate_from_observations(
        self,
        city: SupportedCity,
        observations,
        electricity_profile: ElectricityProfile,
        gas_profile: GasProfile,
        safety_margin_percent: float | None = None,
    ) -> AffordabilityEstimate:
        adjusted_observations = apply_request_profiles(
            observations,
            electricity_profile,
            gas_profile,
            GasBillAssumptions(
                hydrocarbons_tax_eur_per_kwh=(
                    settings.gas_hydrocarbons_tax_eur_per_kwh
                ),
                vat_rate=settings.gas_vat_rate_percent / 100,
                meter_rental_monthly_eur=settings.gas_meter_rental_monthly_eur,
            ),
        )
        calculator = self.calculator
        if safety_margin_percent is not None:
            calculator = AffordabilityCalculator(safety_margin_percent)

        return calculator.estimate(
            CityCostInputs(
                city=city.name,
                city_key=city.key,
                country=city.country,
                currency=city.currency,
                line_items=adjusted_observations,
                household_profile=(
                    "Single adult, one-bedroom rental, no car, Spain MVP "
                    f"({electricity_profile.value} electricity, "
                    f"{gas_profile.value} gas)"
                ),
                assumptions=[
                    "One adult household",
                    "Long-term one-bedroom rental",
                    "No private car ownership",
                    *electricity_profile_assumptions(electricity_profile),
                    *gas_profile_assumptions(gas_profile),
                    "6 m3/month water usage",
                    "Trash tax converted from annual to monthly cost",
                ],
            )
        )
