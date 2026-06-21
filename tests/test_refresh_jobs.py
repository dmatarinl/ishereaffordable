from datetime import UTC, datetime

from app.affordability.models import (
    Confidence,
    CostCategory,
    CostLineItem,
    DataMode,
)
from app.cities import get_supported_city
from app.services.refresh import refresh_all, refresh_city
from app.storage.database import CostObservationRepository


def test_refresh_city_is_idempotent(tmp_path) -> None:
    repository = CostObservationRepository(f"sqlite:///{tmp_path}/test.db")
    repository.init_schema()

    first = refresh_city("Madrid", repository)
    second = refresh_city("Madrid", repository)

    assert first.observations == 7
    assert second.observations == 7
    observations = repository.latest_city_observations("madrid")
    assert len(observations) == 7
    assert all(observation.cached_at for observation in observations)
    assert {observation.data_mode for observation in observations}


def test_refresh_all_covers_supported_cities(tmp_path) -> None:
    repository = CostObservationRepository(f"sqlite:///{tmp_path}/test.db")
    repository.init_schema()

    results = refresh_all(repository)

    assert len(results) == 8
    assert all(result.observations == 7 for result in results)
    assert repository.source_statuses()


class FallbackElectricityProvider:
    source_id = "fallback_electricity_test"
    source_name = "Fallback electricity test"

    def fetch_city(self, city):
        return [
            CostLineItem(
                category=CostCategory.ELECTRICITY,
                label="Electricity",
                monthly_amount=60,
                currency="EUR",
                data_mode=DataMode.MANUAL_SEED,
                source_name=self.source_name,
                source_url="https://example.com/fallback",
                observed_at=datetime.now(UTC),
                confidence=Confidence.LOW,
                methodology="Fallback after temporary source failure.",
            )
        ]


def test_refresh_preserves_stronger_cached_observation(tmp_path) -> None:
    repository = CostObservationRepository(f"sqlite:///{tmp_path}/test.db")
    repository.init_schema()
    city = get_supported_city("Madrid")
    assert city is not None
    official = CostLineItem(
        category=CostCategory.ELECTRICITY,
        label="Electricity",
        monthly_amount=40,
        currency="EUR",
        data_mode=DataMode.OFFICIAL_API,
        source_name="Official electricity source",
        source_url="https://example.com/official",
        observed_at=datetime.now(UTC),
        confidence=Confidence.MEDIUM,
        methodology="Official cached electricity observation.",
    )
    repository.replace_city_observations(
        city_key=city.key,
        city=city.name,
        country=city.country,
        observations=[official],
    )

    result = refresh_city(
        city.name,
        repository,
        providers=[FallbackElectricityProvider()],
    )
    refreshed = repository.latest_city_observations(city.key)
    status = repository.source_statuses()[0]

    assert refreshed[0].data_mode == DataMode.OFFICIAL_API
    assert refreshed[0].monthly_amount == 40
    assert result.warnings
    assert status.status == "degraded"
