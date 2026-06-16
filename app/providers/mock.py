from app.core.config import settings
from app.providers.esios import EsiosElectricityProvider
from app.providers.seed import (
    SeedFoodBasketProvider,
    SeedHousingProvider,
    SeedMunicipalTaxProvider,
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
            SeedUtilityProvider(),
            SeedMunicipalTaxProvider(),
            SeedTransportProvider(),
        ]
