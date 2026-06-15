import argparse

from app.core.config import settings
from app.services.refresh import refresh_city
from app.storage.database import CostObservationRepository


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh cached data for one city.")
    parser.add_argument("--city", required=True)
    args = parser.parse_args()

    repository = CostObservationRepository(settings.database_url)
    repository.init_schema()
    result = refresh_city(args.city, repository)
    print(
        f"{result.city_key}: {result.observations} observations"
        + (f" ({len(result.warnings)} warnings)" if result.warnings else "")
    )


if __name__ == "__main__":
    main()
