from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Is Here Affordable?"
    app_env: str = "development"
    default_currency: str = "EUR"
    safety_margin_percent: float = 15
    database_url: str = "sqlite:///./data/affordability.db"
    esios_api_token: str | None = None
    esios_pvpc_indicator_id: int = 1001
    esios_lookback_days: int = 30
    electricity_monthly_kwh: float = 180
    electricity_fixed_monthly_eur: float = 14
    electricity_default_profile: str = "standard"
    boe_gas_tur_url: str | None = None
    boe_gas_enable_discovery: bool = True
    gas_default_profile: str = "standard"
    gas_vat_rate_percent: float = 21
    gas_hydrocarbons_tax_eur_per_kwh: float = 0.00234
    gas_meter_rental_monthly_eur: float = 0
    enable_supermarket_scraping: bool = False
    source_user_agent: str = Field(
        default="IsHereAffordableBot/0.1 (+https://ishereaffordable.com)"
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
