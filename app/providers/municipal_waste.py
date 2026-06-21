from app.affordability.models import Confidence, CostCategory, CostLineItem, DataMode
from app.cities import SupportedCity
from app.providers.seed import SeedMunicipalTaxProvider
from app.trash_tax.rules import (
    MODEL_VERSION,
    MUNICIPAL_WASTE_TARIFFS,
    REFERENCE_MONTHLY_M3,
    calculate_waste_tariff,
)


class HybridMunicipalWasteProvider:
    source_id = "municipal_waste_hybrid"
    source_name = "Hybrid municipal waste-charge model"

    def __init__(self) -> None:
        self.fallback_provider = SeedMunicipalTaxProvider()

    def fetch_city(self, city: SupportedCity) -> list[CostLineItem]:
        tariff = MUNICIPAL_WASTE_TARIFFS.get(city.key)
        if tariff is None:
            return self.fallback_provider.fetch_city(city)

        calculation = calculate_waste_tariff(
            tariff.rule,
            monthly_water_m3=REFERENCE_MONTHLY_M3,
        )
        return [
            CostLineItem(
                category=CostCategory.TRASH_TAX,
                label="Trash tax",
                monthly_amount=round(calculation.annual_amount_eur / 12, 2),
                currency=city.currency,
                data_mode=DataMode.OFFICIAL_PUBLICATION,
                source_name=tariff.source_name,
                source_url=tariff.source_url,
                observed_at=tariff.observed_at,
                valid_until=tariff.valid_until,
                confidence=Confidence.MEDIUM,
                methodology=calculation.methodology,
                details={
                    **calculation.details,
                    "tariff_model_version": MODEL_VERSION,
                    "tariff_year": tariff.tariff_year,
                    "tariff_rule": tariff.rule.model_dump(mode="json"),
                    "annual_amount": calculation.annual_amount_eur,
                    "annual_min": calculation.annual_min_eur,
                    "annual_max": calculation.annual_max_eur,
                    "amount_kind": calculation.amount_kind,
                    "billing_frequency": tariff.billing_frequency,
                    "exact": False,
                    "exact_inputs_required": tariff.exact_inputs_required,
                    "source_urls": tariff.source_urls,
                },
            )
        ]
