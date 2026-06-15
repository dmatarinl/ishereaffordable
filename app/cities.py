from unicodedata import category, normalize

from pydantic import BaseModel


class SupportedCity(BaseModel):
    key: str
    name: str
    province: str
    region: str
    country: str = "Spain"
    currency: str = "EUR"


SUPPORTED_CITIES = [
    SupportedCity(key="madrid", name="Madrid", province="Madrid", region="Madrid"),
    SupportedCity(
        key="barcelona", name="Barcelona", province="Barcelona", region="Catalonia"
    ),
    SupportedCity(
        key="valencia",
        name="Valencia",
        province="Valencia",
        region="Valencian Community",
    ),
    SupportedCity(
        key="sevilla",
        name="Sevilla",
        province="Sevilla",
        region="Andalusia",
    ),
    SupportedCity(
        key="zaragoza",
        name="Zaragoza",
        province="Zaragoza",
        region="Aragon",
    ),
    SupportedCity(
        key="malaga",
        name="Málaga",
        province="Málaga",
        region="Andalusia",
    ),
    SupportedCity(
        key="bilbao",
        name="Bilbao",
        province="Bizkaia",
        region="Basque Country",
    ),
    SupportedCity(
        key="alicante",
        name="Alicante",
        province="Alicante",
        region="Valencian Community",
    ),
]


def normalize_city_key(value: str) -> str:
    normalized = normalize("NFKD", value.strip().lower())
    without_accents = "".join(
        char for char in normalized if category(char) != "Mn"
    )
    return without_accents.replace(" ", "-")


def get_supported_city(value: str) -> SupportedCity | None:
    key = normalize_city_key(value)
    return next((city for city in SUPPORTED_CITIES if city.key == key), None)
