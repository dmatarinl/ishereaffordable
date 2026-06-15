from dataclasses import dataclass
from datetime import UTC, datetime

from app.affordability.models import CostLineItem
from app.cities import SUPPORTED_CITIES, SupportedCity, get_supported_city
from app.core.config import settings
from app.providers.base import CostProvider
from app.providers.esios import EsiosElectricityProvider
from app.providers.seed import (
    SeedFoodBasketProvider,
    SeedHousingProvider,
    SeedMunicipalTaxProvider,
    SeedTransportProvider,
    SeedUtilityProvider,
)
from app.storage.database import CostObservationRepository


@dataclass(frozen=True)
class RefreshResult:
    city_key: str
    observations: int
    warnings: list[str]


def default_providers() -> list[CostProvider]:
    return [
        SeedHousingProvider(),
        SeedFoodBasketProvider(),
        EsiosElectricityProvider(
            api_token=settings.esios_api_token,
            indicator_id=settings.esios_pvpc_indicator_id,
            monthly_kwh=settings.electricity_monthly_kwh,
            fixed_monthly_eur=settings.electricity_fixed_monthly_eur,
            lookback_days=settings.esios_lookback_days,
        ),
        SeedUtilityProvider(),
        SeedMunicipalTaxProvider(),
        SeedTransportProvider(),
    ]


def refresh_city(
    city_name: str,
    repository: CostObservationRepository,
    providers: list[CostProvider] | None = None,
) -> RefreshResult:
    city = get_supported_city(city_name)
    if city is None:
        supported = ", ".join(city.name for city in SUPPORTED_CITIES)
        raise ValueError(
            f"Unsupported city '{city_name}'. Supported cities: {supported}"
        )

    return _refresh_supported_city(city, repository, providers or default_providers())


def refresh_all(
    repository: CostObservationRepository,
    providers: list[CostProvider] | None = None,
) -> list[RefreshResult]:
    active_providers = providers or default_providers()
    return [
        _refresh_supported_city(city, repository, active_providers)
        for city in SUPPORTED_CITIES
    ]


def ensure_seed_data(repository: CostObservationRepository) -> None:
    if not repository.has_any_observations():
        refresh_all(repository)


def _refresh_supported_city(
    city: SupportedCity,
    repository: CostObservationRepository,
    providers: list[CostProvider],
) -> RefreshResult:
    observations: list[CostLineItem] = []
    warnings: list[str] = []

    for provider in providers:
        started_at = datetime.now(UTC)
        try:
            provider_items = provider.fetch_city(city)
        except Exception as error:  # pragma: no cover - defensive source boundary
            finished_at = datetime.now(UTC)
            message = f"{city.name}: {error}"
            warnings.append(message)
            repository.record_source_run(
                source_id=provider.source_id,
                source_name=provider.source_name,
                status="failed",
                started_at=started_at,
                finished_at=finished_at,
                message=message,
            )
            continue

        observations.extend(provider_items)
        repository.record_source_run(
            source_id=provider.source_id,
            source_name=provider.source_name,
            status="ok",
            started_at=started_at,
            finished_at=datetime.now(UTC),
            message=f"Refreshed {len(provider_items)} observations for {city.name}",
        )

    repository.replace_city_observations(
        city_key=city.key,
        city=city.name,
        country=city.country,
        observations=observations,
    )
    return RefreshResult(
        city_key=city.key,
        observations=len(observations),
        warnings=warnings,
    )
