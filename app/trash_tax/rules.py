from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.affordability.models import CostLineItem
from app.water.profiles import WaterProfile, get_water_profile

MODEL_VERSION = "2026.1"
REFERENCE_MONTHLY_M3 = 6.0


class PublishedAverageRule(BaseModel):
    kind: Literal["published_city_average"] = "published_city_average"
    annual_amount_eur: float = Field(ge=0)


class WaterBand(BaseModel):
    label: str
    max_daily_m3: float | None = Field(default=None, gt=0)
    annual_amount_eur: float = Field(ge=0)
    components: dict[str, float] = Field(default_factory=dict)


class WaterBandsRule(BaseModel):
    kind: Literal["water_consumption_bands"] = "water_consumption_bands"
    bands: list[WaterBand]


class OfficialRangeRule(BaseModel):
    kind: Literal["official_range_midpoint"] = "official_range_midpoint"
    annual_min_eur: float = Field(ge=0)
    annual_max_eur: float = Field(ge=0)
    reference_property: str


WasteRule = PublishedAverageRule | WaterBandsRule | OfficialRangeRule


class MunicipalWasteTariff(BaseModel):
    city_key: str
    tariff_year: int
    source_name: str
    source_url: str
    source_urls: list[str] = Field(default_factory=list)
    observed_at: datetime
    valid_until: datetime
    billing_frequency: str = "annual"
    exact_inputs_required: list[str] = Field(default_factory=list)
    rule: WasteRule


class WasteTariffCalculation(BaseModel):
    annual_amount_eur: float = Field(ge=0)
    annual_min_eur: float | None = Field(default=None, ge=0)
    annual_max_eur: float | None = Field(default=None, ge=0)
    amount_kind: str
    methodology: str
    details: dict = Field(default_factory=dict)


MADRID_SOURCE_URL = "https://madrid.es/go/cuotatgr.r"
ZARAGOZA_COLLECTION_URL = (
    "https://www.zaragoza.es/sede/servicio/normativa/3503"
)
ZARAGOZA_TREATMENT_URL = (
    "https://www.zaragoza.es/sede/servicio/normativa/3504"
)
ALICANTE_SOURCE_URL = (
    "https://www.alicante.es/sites/default/files/documentos/202508/"
    "nueva-tasa-residuos-solidos-informacion-ciudadano-viviendas-3.pdf"
)


MUNICIPAL_WASTE_TARIFFS = {
    "madrid": MunicipalWasteTariff(
        city_key="madrid",
        tariff_year=2026,
        source_name="Madrid 2026 official waste-charge calculator",
        source_url=MADRID_SOURCE_URL,
        source_urls=[MADRID_SOURCE_URL],
        observed_at=datetime(2025, 12, 22, tzinfo=UTC),
        valid_until=datetime(2027, 1, 1, tzinfo=UTC),
        exact_inputs_required=[
            "cadastral value",
            "registered residents",
            "neighbourhood waste generation",
            "neighbourhood separation-quality coefficient",
        ],
        rule=PublishedAverageRule(annual_amount_eur=142.60),
    ),
    "zaragoza": MunicipalWasteTariff(
        city_key="zaragoza",
        tariff_year=2026,
        source_name="Zaragoza 2026 waste ordinances 17.1 and 17.2",
        source_url=ZARAGOZA_COLLECTION_URL,
        source_urls=[ZARAGOZA_COLLECTION_URL, ZARAGOZA_TREATMENT_URL],
        observed_at=datetime(2025, 12, 27, tzinfo=UTC),
        valid_until=datetime(2027, 1, 1, tzinfo=UTC),
        exact_inputs_required=["actual billed water consumption"],
        rule=WaterBandsRule(
            bands=[
                WaterBand(
                    label="Up to 0.283 m3/day",
                    max_daily_m3=0.283,
                    annual_amount_eur=72.68,
                    components={"collection": 41.26, "treatment": 31.42},
                ),
                WaterBand(
                    label="Above 0.283 m3/day",
                    annual_amount_eur=80.00,
                    components={"collection": 45.44, "treatment": 34.56},
                ),
            ]
        ),
    ),
    "alicante": MunicipalWasteTariff(
        city_key="alicante",
        tariff_year=2026,
        source_name="Alicante official residential waste-charge guide",
        source_url=ALICANTE_SOURCE_URL,
        source_urls=[ALICANTE_SOURCE_URL],
        observed_at=datetime(2025, 8, 1, tzinfo=UTC),
        valid_until=datetime(2027, 1, 1, tzinfo=UTC),
        exact_inputs_required=["constructed floor area", "cadastral value per m2"],
        rule=OfficialRangeRule(
            annual_min_eur=69.85,
            annual_max_eur=134.67,
            reference_property="Residential property up to 60 m2",
        ),
    ),
}


def municipal_waste_tariff_catalog() -> list[MunicipalWasteTariff]:
    return list(MUNICIPAL_WASTE_TARIFFS.values())


def calculate_waste_tariff(
    rule: WasteRule,
    monthly_water_m3: float = REFERENCE_MONTHLY_M3,
) -> WasteTariffCalculation:
    if isinstance(rule, PublishedAverageRule):
        return WasteTariffCalculation(
            annual_amount_eur=rule.annual_amount_eur,
            amount_kind="official_city_average",
            methodology=(
                f"Official published citywide average of "
                f"{rule.annual_amount_eur:.2f} EUR/year. Exact household bills "
                "vary with the property and local generation factors."
            ),
        )

    if isinstance(rule, WaterBandsRule):
        daily_m3 = monthly_water_m3 * 12 / 365
        band = next(
            (
                candidate
                for candidate in rule.bands
                if candidate.max_daily_m3 is None
                or daily_m3 <= candidate.max_daily_m3
            ),
            rule.bands[-1],
        )
        component_text = " + ".join(
            f"{name} {amount:.2f} EUR"
            for name, amount in band.components.items()
        )
        return WasteTariffCalculation(
            annual_amount_eur=band.annual_amount_eur,
            amount_kind="water_profile_estimate",
            methodology=(
                f"Official annual tariff band for {monthly_water_m3:g} m3/month "
                f"({daily_m3:.3f} m3/day): {component_text}. The selected water "
                "profile is a usage scenario rather than an actual meter reading."
            ),
            details={
                "monthly_water_m3": monthly_water_m3,
                "daily_water_m3": round(daily_m3, 6),
                "selected_band": band.label,
                "components": band.components,
            },
        )

    annual_amount = round((rule.annual_min_eur + rule.annual_max_eur) / 2, 2)
    return WasteTariffCalculation(
        annual_amount_eur=annual_amount,
        annual_min_eur=rule.annual_min_eur,
        annual_max_eur=rule.annual_max_eur,
        amount_kind="official_range_midpoint",
        methodology=(
            f"Representative midpoint of the official annual range "
            f"{rule.annual_min_eur:.2f}-{rule.annual_max_eur:.2f} EUR for "
            f"{rule.reference_property.lower()}. The exact bill depends on the "
            "property's tariff inputs."
        ),
        details={"reference_property": rule.reference_property},
    )


def apply_municipal_waste_profile(
    item: CostLineItem,
    water_profile: WaterProfile,
) -> CostLineItem:
    rule_payload = item.details.get("tariff_rule")
    if not rule_payload:
        return item

    rule = _parse_rule(rule_payload)
    water_definition = get_water_profile(water_profile)
    calculation = calculate_waste_tariff(rule, water_definition.monthly_m3)
    details = {
        **item.details,
        **calculation.details,
        "annual_amount": calculation.annual_amount_eur,
        "annual_min": calculation.annual_min_eur,
        "annual_max": calculation.annual_max_eur,
        "amount_kind": calculation.amount_kind,
        "water_profile": water_profile.value,
    }
    return item.model_copy(
        update={
            "monthly_amount": round(calculation.annual_amount_eur / 12, 2),
            "methodology": calculation.methodology,
            "details": details,
        }
    )


def municipal_waste_assumptions(item: CostLineItem) -> list[str]:
    if not item.details.get("tariff_rule"):
        return ["Trash tax remains a low-confidence manual city fallback"]

    assumptions = [
        "Trash tax is converted from an annual official tariff to a monthly cost",
        "The displayed trash-tax amount is representative, not an exact tax bill",
    ]
    required = item.details.get("exact_inputs_required") or []
    if required:
        assumptions.append("Exact trash-tax inputs required: " + ", ".join(required))
    return assumptions


def _parse_rule(payload: dict) -> WasteRule:
    rule_kind = payload.get("kind")
    if rule_kind == "published_city_average":
        return PublishedAverageRule.model_validate(payload)
    if rule_kind == "water_consumption_bands":
        return WaterBandsRule.model_validate(payload)
    if rule_kind == "official_range_midpoint":
        return OfficialRangeRule.model_validate(payload)
    raise ValueError(f"Unsupported municipal waste rule: {rule_kind}")
