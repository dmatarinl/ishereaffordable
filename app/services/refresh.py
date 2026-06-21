from dataclasses import dataclass
from datetime import UTC, datetime

from app.affordability.models import CostLineItem, DataMode
from app.cities import SUPPORTED_CITIES, SupportedCity, get_supported_city
from app.core.config import settings
from app.electricity.profiles import ElectricityProfile, apply_electricity_profile
from app.gas.profiles import GasBillAssumptions, GasProfile, apply_gas_profile
from app.providers.base import CostProvider
from app.providers.boe_gas import BoeGasTurProvider
from app.providers.esios import EsiosElectricityProvider
from app.providers.municipal_waste import HybridMunicipalWasteProvider
from app.providers.seed import (
    SeedFoodBasketProvider,
    SeedHousingProvider,
    SeedTransportProvider,
    SeedUtilityProvider,
)
from app.storage.database import CostObservationRepository
from app.trash_tax.rules import MODEL_VERSION, apply_municipal_waste_profile
from app.water.profiles import WaterProfile, apply_water_profile


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
    if not repository.has_any_observations() or _needs_profile_ready_observations(
        repository
    ):
        refresh_all(repository)


def apply_request_profiles(
    observations: list[CostLineItem],
    electricity_profile: ElectricityProfile,
    gas_profile: GasProfile,
    water_profile: WaterProfile,
    gas_bill_assumptions: GasBillAssumptions,
) -> list[CostLineItem]:
    return [
        apply_electricity_profile(item, electricity_profile)
        if item.category.value == "electricity"
        else apply_gas_profile(item, gas_profile, gas_bill_assumptions)
        if item.category.value == "gas"
        else apply_water_profile(item, water_profile)
        if item.category.value == "water"
        else apply_municipal_waste_profile(item, water_profile)
        if item.category.value == "trash_tax"
        else item
        for item in observations
    ]


def _refresh_supported_city(
    city: SupportedCity,
    repository: CostObservationRepository,
    providers: list[CostProvider],
) -> RefreshResult:
    observations: list[CostLineItem] = []
    warnings: list[str] = []
    previous_by_category = {
        item.category: item
        for item in repository.latest_city_observations(city.key)
    }

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

        provider_items, preserved_categories = _preserve_stronger_cached_items(
            provider_items,
            previous_by_category,
        )
        observations.extend(provider_items)
        if preserved_categories:
            preserved = ", ".join(preserved_categories)
            message = (
                f"{city.name}: provider degraded; retained stronger cached "
                f"observations for {preserved}"
            )
            warnings.append(message)
            repository.record_source_run(
                source_id=provider.source_id,
                source_name=provider.source_name,
                status="degraded",
                started_at=started_at,
                finished_at=datetime.now(UTC),
                message=message,
            )
            continue

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


def _preserve_stronger_cached_items(
    incoming: list[CostLineItem],
    previous_by_category: dict,
) -> tuple[list[CostLineItem], list[str]]:
    mode_rank = {
        DataMode.UNAVAILABLE: 0,
        DataMode.MANUAL_SEED: 1,
        DataMode.PERMITTED_SCRAPE: 2,
        DataMode.OFFICIAL_PUBLICATION: 3,
        DataMode.OFFICIAL_API: 4,
        DataMode.CALCULATED: 4,
    }
    resolved: list[CostLineItem] = []
    preserved: list[str] = []
    for item in incoming:
        previous = previous_by_category.get(item.category)
        if previous and mode_rank[previous.data_mode] > mode_rank[item.data_mode]:
            resolved.append(previous)
            preserved.append(item.category.value)
        else:
            resolved.append(item)
    return resolved, preserved


def _needs_profile_ready_observations(repository: CostObservationRepository) -> bool:
    observations = repository.latest_city_observations(SUPPORTED_CITIES[0].key)
    gas = next(
        (
            item
            for item in observations
            if item.category.value == "gas"
        ),
        None,
    )
    tax = next(
        (
            item
            for item in observations
            if item.category.value == "trash_tax"
        ),
        None,
    )
    if gas is None or tax is None:
        return True

    return (
        "gas_terms" not in gas.details
        or tax.details.get("tariff_model_version") != MODEL_VERSION
    )
