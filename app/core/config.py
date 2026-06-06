from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Is Here Affordable?"
    app_env: str = "development"
    default_currency: str = "EUR"
    safety_margin_percent: float = 15

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
