from typing import Protocol

from app.affordability.models import CostLineItem
from app.cities import SupportedCity


class CostProvider(Protocol):
    source_id: str
    source_name: str

    def fetch_city(self, city: SupportedCity) -> list[CostLineItem]:
        """Return cacheable monthly cost observations for one city."""


class HousingProvider(CostProvider, Protocol):
    pass


class FoodBasketProvider(CostProvider, Protocol):
    pass


class UtilityProvider(CostProvider, Protocol):
    pass


class ElectricityProvider(CostProvider, Protocol):
    pass


class MunicipalTaxProvider(CostProvider, Protocol):
    pass


class TransportProvider(CostProvider, Protocol):
    pass
