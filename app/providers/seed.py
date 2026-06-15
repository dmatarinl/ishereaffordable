from datetime import UTC, datetime

from app.affordability.models import Confidence, CostCategory, CostLineItem
from app.cities import SupportedCity

IDEALISTA_ACCESS_URL = "https://developers.idealista.com/access-request"
INE_API_URL = "https://www.ine.es/dyngs/DAB/index.htm?cid=1099"
ESIOS_API_URL = "https://api.esios.ree.es"
GITHUB_URL = "https://github.com/dmatarinl/ishereaffordable"


RENT_SEEDS = {
    "madrid": {"amount": 1250, "p25": 1050, "p75": 1500},
    "barcelona": {"amount": 1400, "p25": 1150, "p75": 1680},
    "valencia": {"amount": 950, "p25": 780, "p75": 1150},
    "sevilla": {"amount": 850, "p25": 690, "p75": 1020},
    "zaragoza": {"amount": 720, "p25": 610, "p75": 880},
    "malaga": {"amount": 1050, "p25": 850, "p75": 1280},
    "bilbao": {"amount": 1000, "p25": 830, "p75": 1220},
    "alicante": {"amount": 820, "p25": 670, "p75": 990},
}

CITY_FACTORS = {
    "madrid": 1.05,
    "barcelona": 1.06,
    "valencia": 1.0,
    "sevilla": 0.97,
    "zaragoza": 0.95,
    "malaga": 1.02,
    "bilbao": 1.04,
    "alicante": 0.98,
}

WATER_SEEDS = {
    "madrid": 18.5,
    "barcelona": 23.0,
    "valencia": 19.0,
    "sevilla": 21.0,
    "zaragoza": 18.0,
    "malaga": 22.0,
    "bilbao": 20.0,
    "alicante": 21.5,
}

TRASH_TAX_ANNUAL_SEEDS = {
    "madrid": 142.6,
    "barcelona": 148.0,
    "valencia": 115.0,
    "sevilla": 108.0,
    "zaragoza": 95.0,
    "malaga": 118.0,
    "bilbao": 125.0,
    "alicante": 102.0,
}

TRANSPORT_SEEDS = {
    "madrid": 54.6,
    "barcelona": 44.0,
    "valencia": 35.0,
    "sevilla": 35.3,
    "zaragoza": 40.0,
    "malaga": 39.95,
    "bilbao": 42.0,
    "alicante": 37.5,
}

FOOD_BASKET = [
    ("Milk", 8, 0.95),
    ("Bread", 12, 1.25),
    ("Rice", 2, 1.6),
    ("Pasta", 2.5, 1.5),
    ("Potatoes", 5, 1.4),
    ("Onions", 2, 1.5),
    ("Tomatoes", 3.5, 2.3),
    ("Lettuce", 4, 1.2),
    ("Bananas", 4, 1.6),
    ("Apples", 4, 2.1),
    ("Oranges", 3, 1.8),
    ("Eggs", 3, 2.5),
    ("Chicken", 4, 7.0),
    ("Minced beef", 1.2, 9.0),
    ("White fish", 1.5, 10.0),
    ("Canned tuna", 8, 1.1),
    ("Lentils", 2, 2.0),
    ("Chickpeas", 2, 1.8),
    ("Olive oil", 1.5, 8.0),
    ("Sunflower oil", 0.5, 1.8),
    ("Coffee", 1, 4.2),
    ("Yogurt", 12, 0.45),
    ("Cheese", 1, 8.0),
    ("Cooked ham or turkey", 1, 10.0),
    ("Oats or cereal", 2, 1.8),
    ("Sugar", 0.5, 1.2),
    ("Salt and spices", 1, 1.5),
    ("Frozen vegetables", 2, 2.0),
    ("Cleaning basics", 1, 10.0),
    ("Toiletries basics", 1, 12.0),
    ("Bottled water", 4, 1.5),
    ("Juice", 4, 1.3),
    ("Beans", 2, 1.5),
    ("Flour", 1, 1.1),
    ("Breakfast biscuits", 2, 1.8),
]


def _observed_at() -> datetime:
    return datetime.now(UTC)


class SeedHousingProvider:
    source_id = "seed_housing_idealista_pending"
    source_name = "Fallback rental seed pending Idealista Search API"

    def fetch_city(self, city: SupportedCity) -> list[CostLineItem]:
        seed = RENT_SEEDS[city.key]
        return [
            CostLineItem(
                category=CostCategory.RENT,
                label="One-bedroom rent",
                monthly_amount=seed["amount"],
                currency=city.currency,
                source_name=self.source_name,
                source_url=IDEALISTA_ACCESS_URL,
                observed_at=_observed_at(),
                confidence=Confidence.LOW,
                methodology=(
                    "Manual MVP fallback for the median monthly price of long-term "
                    "one-bedroom rentals. Replace with Idealista Search API listings "
                    "using median, P25 and P75 once credentials are available."
                ),
                details={
                    "target_source": "Idealista Search API",
                    "bedrooms": 1,
                    "operation": "rent",
                    "p25": seed["p25"],
                    "p75": seed["p75"],
                },
            )
        ]


class SeedFoodBasketProvider:
    source_id = "seed_food_basket"
    source_name = "Fallback supermarket basket seed"

    def fetch_city(self, city: SupportedCity) -> list[CostLineItem]:
        base_total = sum(quantity * price for _, quantity, price in FOOD_BASKET)
        total = round(base_total * CITY_FACTORS[city.key], 2)
        return [
            CostLineItem(
                category=CostCategory.FOOD,
                label="Food basket",
                monthly_amount=total,
                currency=city.currency,
                source_name=self.source_name,
                source_url=INE_API_URL,
                observed_at=_observed_at(),
                confidence=Confidence.LOW,
                methodology=(
                    "Fixed 35-item one-adult monthly basket. Current implementation "
                    "uses a seed price matrix and city factor; supermarket adapters "
                    "for Mercadona, Carrefour and Dia/Alcampo should replace item "
                    "prices during daily refreshes."
                ),
                details={
                    "basket_items": len(FOOD_BASKET),
                    "available_items": len(FOOD_BASKET),
                    "missing_products": 0,
                    "target_stores": ["Mercadona", "Carrefour", "Dia/Alcampo"],
                },
            )
        ]


class SeedUtilityProvider:
    source_id = "seed_utilities"
    source_name = "Fallback utilities seed"

    def fetch_city(self, city: SupportedCity) -> list[CostLineItem]:
        gas = round((250 * 0.065) + 8.0, 2)
        water = WATER_SEEDS[city.key]
        return [
            CostLineItem(
                category=CostCategory.GAS,
                label="Gas",
                monthly_amount=gas,
                currency=city.currency,
                source_name=self.source_name,
                source_url="https://www.boe.es/",
                observed_at=_observed_at(),
                confidence=Confidence.LOW,
                methodology=(
                    "250 kWh/month default usage with a maintained regulated-tariff "
                    "seed. Replace with official TUR data by quarter."
                ),
                details={"monthly_kwh": 250, "seed_variable_eur_per_kwh": 0.065},
            ),
            CostLineItem(
                category=CostCategory.WATER,
                label="Water",
                monthly_amount=water,
                currency=city.currency,
                source_name=self.source_name,
                source_url=GITHUB_URL,
                observed_at=_observed_at(),
                confidence=Confidence.LOW,
                methodology=(
                    "6 m3/month default usage with city-level seed tariffs. Replace "
                    "with municipal or local water provider tariffs."
                ),
                details={"monthly_m3": 6},
            ),
        ]


class SeedMunicipalTaxProvider:
    source_id = "seed_municipal_tax"
    source_name = "Fallback municipal tax seed"

    def fetch_city(self, city: SupportedCity) -> list[CostLineItem]:
        annual_tax = TRASH_TAX_ANNUAL_SEEDS[city.key]
        return [
            CostLineItem(
                category=CostCategory.TRASH_TAX,
                label="Trash tax",
                monthly_amount=round(annual_tax / 12, 2),
                currency=city.currency,
                source_name=self.source_name,
                source_url=GITHUB_URL,
                observed_at=_observed_at(),
                confidence=Confidence.LOW,
                methodology=(
                    "City-level annual waste tax seed converted to monthly cost. "
                    "Replace with official municipal ordinances or open data."
                ),
                details={"annual_amount": annual_tax},
            )
        ]


class SeedTransportProvider:
    source_id = "seed_transport"
    source_name = "Fallback public transport seed"

    def fetch_city(self, city: SupportedCity) -> list[CostLineItem]:
        return [
            CostLineItem(
                category=CostCategory.PUBLIC_TRANSPORT,
                label="Public transport",
                monthly_amount=TRANSPORT_SEEDS[city.key],
                currency=city.currency,
                source_name=self.source_name,
                source_url=GITHUB_URL,
                observed_at=_observed_at(),
                confidence=Confidence.LOW,
                methodology=(
                    "Monthly public transport pass seed for an adult without car. "
                    "Replace with official transport authority fares."
                ),
                details={"profile": "adult monthly pass"},
            )
        ]
