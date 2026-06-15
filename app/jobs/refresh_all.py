from app.core.config import settings
from app.services.refresh import refresh_all
from app.storage.database import CostObservationRepository


def main() -> None:
    repository = CostObservationRepository(settings.database_url)
    repository.init_schema()
    results = refresh_all(repository)
    for result in results:
        print(
            f"{result.city_key}: {result.observations} observations"
            + (f" ({len(result.warnings)} warnings)" if result.warnings else "")
        )


if __name__ == "__main__":
    main()
