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
