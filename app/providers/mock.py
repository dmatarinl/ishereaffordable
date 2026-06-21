from app.core.config import settings
from app.gas.profiles import GasBillAssumptions
from app.providers.boe_gas import BoeGasTurProvider
from app.providers.esios import EsiosElectricityProvider
from app.providers.municipal_waste import HybridMunicipalWasteProvider
from app.providers.seed import (
    SeedFoodBasketProvider,
    SeedHousingProvider,
    SeedTransportProvider,
    SeedUtilityProvider,
)


class MockCostOfLivingProvider:
    """Compatibility wrapper for early local experiments."""

    def __init__(self) -> None:
        self.providers = [
            SeedHousingProvider(),
            SeedFoodBasketProvider(),
            EsiosElectricityProvider(
                api_token=settings.esios_api_token,
                indicator_id=settings.esios_pvpc_indicator_id,
                lookback_days=settings.esios_lookback_days,
                default_profile=settings.electricity_default_profile,
                geo_name="Península",
            ),
            BoeGasTurProvider(
                source_url=settings.boe_gas_tur_url,
                user_agent=settings.source_user_agent,
                default_profile=settings.gas_default_profile,
                gas_bill_assumptions=GasBillAssumptions(
                    hydrocarbons_tax_eur_per_kwh=(
                        settings.gas_hydrocarbons_tax_eur_per_kwh
                    ),
                    vat_rate=settings.gas_vat_rate_percent / 100,
                    meter_rental_monthly_eur=settings.gas_meter_rental_monthly_eur,
                ),
                enable_discovery=settings.boe_gas_enable_discovery,
            ),
            SeedUtilityProvider(),
            HybridMunicipalWasteProvider(),
            SeedTransportProvider(),
        ]
