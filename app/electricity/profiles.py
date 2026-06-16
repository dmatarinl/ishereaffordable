from enum import StrEnum

from pydantic import BaseModel, Field

from app.affordability.models import Confidence, CostLineItem


class ElectricityProfile(StrEnum):
    LIGHT = "light"
    STANDARD = "standard"
    HIGH = "high"


class ElectricityProfileDefinition(BaseModel):
    key: ElectricityProfile
    label: str
    monthly_kwh: float = Field(gt=0)
    contracted_power_p1_kw: float = Field(gt=0)
    contracted_power_p2_kw: float = Field(gt=0)
    description: str


class ElectricityBillAssumptions(BaseModel):
    days_per_month: float = Field(gt=0)
    power_price_p1_eur_kw_day: float = Field(ge=0)
    power_price_p2_eur_kw_day: float = Field(ge=0)
    electricity_tax_rate: float = Field(ge=0)
    vat_rate: float = Field(ge=0)
    meter_rental_monthly_eur: float = Field(ge=0)


class ElectricityBillBreakdown(BaseModel):
    monthly_amount: float = Field(ge=0)
    energy_term_eur: float = Field(ge=0)
    power_term_eur: float = Field(ge=0)
    electricity_tax_eur: float = Field(ge=0)
    meter_rental_eur: float = Field(ge=0)
    vat_eur: float = Field(ge=0)
    subtotal_before_tax_eur: float = Field(ge=0)


DEFAULT_ELECTRICITY_PROFILE = ElectricityProfile.STANDARD

ELECTRICITY_PROFILES = {
    ElectricityProfile.LIGHT: ElectricityProfileDefinition(
        key=ElectricityProfile.LIGHT,
        label="Light",
        monthly_kwh=120,
        contracted_power_p1_kw=3.45,
        contracted_power_p2_kw=3.45,
        description=(
            "Small one-person flat with careful use and no heavy electric "
            "heating."
        ),
    ),
    ElectricityProfile.STANDARD: ElectricityProfileDefinition(
        key=ElectricityProfile.STANDARD,
        label="Standard",
        monthly_kwh=180,
        contracted_power_p1_kw=3.45,
        contracted_power_p2_kw=3.45,
        description="Typical one-person flat with moderate appliance use.",
    ),
    ElectricityProfile.HIGH: ElectricityProfileDefinition(
        key=ElectricityProfile.HIGH,
        label="High",
        monthly_kwh=250,
        contracted_power_p1_kw=4.6,
        contracted_power_p2_kw=4.6,
        description=(
            "One-person home with higher appliance use, AC, or electric water "
            "heating."
        ),
    ),
}

REGULATED_BILL_ASSUMPTIONS = ElectricityBillAssumptions(
    days_per_month=365 / 12,
    power_price_p1_eur_kw_day=0.068041426,
    power_price_p2_eur_kw_day=0.002646239,
    electricity_tax_rate=0.0511269632,
    vat_rate=0.21,
    meter_rental_monthly_eur=0.81,
)


def electricity_profile_catalog() -> list[ElectricityProfileDefinition]:
    return list(ELECTRICITY_PROFILES.values())


def get_electricity_profile(
    profile: ElectricityProfile,
) -> ElectricityProfileDefinition:
    return ELECTRICITY_PROFILES[profile]


def calculate_monthly_regulated_bill(
    average_eur_per_kwh: float,
    profile: ElectricityProfile,
    assumptions: ElectricityBillAssumptions = REGULATED_BILL_ASSUMPTIONS,
) -> ElectricityBillBreakdown:
    profile_definition = get_electricity_profile(profile)
    energy_term = average_eur_per_kwh * profile_definition.monthly_kwh
    power_term = assumptions.days_per_month * (
        (
            profile_definition.contracted_power_p1_kw
            * assumptions.power_price_p1_eur_kw_day
        )
        + (
            profile_definition.contracted_power_p2_kw
            * assumptions.power_price_p2_eur_kw_day
        )
    )
    subtotal_before_tax = energy_term + power_term
    electricity_tax = subtotal_before_tax * assumptions.electricity_tax_rate
    vat_base = (
        subtotal_before_tax
        + electricity_tax
        + assumptions.meter_rental_monthly_eur
    )
    vat = vat_base * assumptions.vat_rate
    monthly_amount = vat_base + vat

    return ElectricityBillBreakdown(
        monthly_amount=round(monthly_amount, 2),
        energy_term_eur=round(energy_term, 2),
        power_term_eur=round(power_term, 2),
        electricity_tax_eur=round(electricity_tax, 2),
        meter_rental_eur=round(assumptions.meter_rental_monthly_eur, 2),
        vat_eur=round(vat, 2),
        subtotal_before_tax_eur=round(subtotal_before_tax, 2),
    )


def apply_electricity_profile(
    item: CostLineItem,
    profile: ElectricityProfile,
) -> CostLineItem:
    average_eur_per_kwh = item.details.get("average_eur_per_kwh")
    if average_eur_per_kwh is None:
        average_eur_per_kwh = item.details.get("seed_variable_eur_per_kwh")
    if average_eur_per_kwh is None:
        return item

    profile_definition = get_electricity_profile(profile)
    bill = calculate_monthly_regulated_bill(float(average_eur_per_kwh), profile)

    confidence = item.confidence
    if item.data_mode == item.data_mode.OFFICIAL_API:
        confidence = Confidence.MEDIUM

    source_name = item.source_name
    if item.data_mode == item.data_mode.OFFICIAL_API:
        source_name = "eSIOS PVPC energy term + maintained regulated bill estimate"

    methodology_intro = (
        "Official eSIOS PVPC energy-term average for Península"
        if item.data_mode == item.data_mode.OFFICIAL_API
        else "Fallback PVPC-style energy-term estimate"
    )
    methodology = (
        f"{methodology_intro}, applied to the {profile_definition.label.lower()} "
        f"profile at {profile_definition.monthly_kwh:g} kWh/month and combined "
        "with maintained 2.0TD power-term, meter-rental, electricity-tax, and "
        "VAT assumptions."
    )

    details = {
        **item.details,
        "electricity_profile": profile.value,
        "electricity_profile_label": profile_definition.label,
        "electricity_profile_description": profile_definition.description,
        "monthly_kwh": profile_definition.monthly_kwh,
        "contracted_power_p1_kw": profile_definition.contracted_power_p1_kw,
        "contracted_power_p2_kw": profile_definition.contracted_power_p2_kw,
        "power_price_p1_eur_kw_day": (
            REGULATED_BILL_ASSUMPTIONS.power_price_p1_eur_kw_day
        ),
        "power_price_p2_eur_kw_day": (
            REGULATED_BILL_ASSUMPTIONS.power_price_p2_eur_kw_day
        ),
        "electricity_tax_rate": REGULATED_BILL_ASSUMPTIONS.electricity_tax_rate,
        "vat_rate": REGULATED_BILL_ASSUMPTIONS.vat_rate,
        "meter_rental_monthly_eur": REGULATED_BILL_ASSUMPTIONS.meter_rental_monthly_eur,
        "days_per_month": REGULATED_BILL_ASSUMPTIONS.days_per_month,
        "energy_term_eur": bill.energy_term_eur,
        "power_term_eur": bill.power_term_eur,
        "electricity_tax_eur": bill.electricity_tax_eur,
        "vat_eur": bill.vat_eur,
        "subtotal_before_tax_eur": bill.subtotal_before_tax_eur,
    }

    return item.model_copy(
        update={
            "monthly_amount": bill.monthly_amount,
            "confidence": confidence,
            "source_name": source_name,
            "methodology": methodology,
            "details": details,
        }
    )


def electricity_profile_assumptions(profile: ElectricityProfile) -> list[str]:
    profile_definition = get_electricity_profile(profile)
    return [
        f"{profile_definition.monthly_kwh:g} kWh/month electricity usage "
        f"({profile_definition.label.lower()} profile)",
        "Single-tariff 2.0TD estimate uses maintained regulated power-term assumptions",
        "Electricity bill estimate includes meter rental, electricity tax, and VAT",
    ]
