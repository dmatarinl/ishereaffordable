from app.affordability.models import (
    Confidence,
    CostCategory,
    CostLineItem,
    DataMode,
)
from app.cities import SupportedCity
from app.public_transport.fares import (
    STANDARD_ADULT_PROFILE,
    transport_fare_for_city,
)


class OfficialTransportFareProvider:
    source_id = "official_transport_fares"
    source_name = "Maintained official 2026 public transport fares"

    def fetch_city(self, city: SupportedCity) -> list[CostLineItem]:
        fare = transport_fare_for_city(city.key)
        included = ", ".join(fare.modes_included)
        methodology = (
            f"{fare.calculation_summary} Includes {included}. "
            f"The traveller profile is: {STANDARD_ADULT_PROFILE.lower()}."
        )
        if fare.excluded_modes:
            methodology += f" Excludes {', '.join(fare.excluded_modes)}."

        return [
            CostLineItem(
                category=CostCategory.PUBLIC_TRANSPORT,
                label="Public transport",
                monthly_amount=fare.monthly_amount_eur,
                currency=city.currency,
                data_mode=DataMode.OFFICIAL_PUBLICATION,
                source_name=fare.source_name,
                source_url=fare.source_url,
                observed_at=fare.observed_at,
                valid_until=fare.valid_until,
                confidence=Confidence.MEDIUM,
                methodology=methodology,
                details=fare.details(),
            )
        ]
