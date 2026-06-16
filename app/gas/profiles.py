from enum import StrEnum

from pydantic import BaseModel, Field

from app.affordability.models import Confidence, CostLineItem, DataMode


class GasProfile(StrEnum):
    LOW = "low"
    STANDARD = "standard"
    HEATING = "heating"


class GasProfileDefinition(BaseModel):
    key: GasProfile
    label: str
    monthly_kwh: float = Field(gt=0)
    annual_kwh: float = Field(gt=0)
    rate_code: str
    description: str


class GasBillAssumptions(BaseModel):
    hydrocarbons_tax_eur_per_kwh: float = Field(ge=0)
    vat_rate: float = Field(ge=0)
    meter_rental_monthly_eur: float = Field(ge=0)


class GasBillBreakdown(BaseModel):
    monthly_amount: float = Field(ge=0)
    fixed_term_eur: float = Field(ge=0)
    variable_term_eur: float = Field(ge=0)
    hydrocarbons_tax_eur: float = Field(ge=0)
    meter_rental_eur: float = Field(ge=0)
    vat_eur: float = Field(ge=0)
    subtotal_before_tax_eur: float = Field(ge=0)


DEFAULT_GAS_PROFILE = GasProfile.STANDARD

GAS_PROFILES = {
    GasProfile.LOW: GasProfileDefinition(
        key=GasProfile.LOW,
        label="Low",
        monthly_kwh=120,
        annual_kwh=1440,
        rate_code="TUR.1",
        description="Cooking and/or modest hot-water use without gas heating.",
    ),
    GasProfile.STANDARD: GasProfileDefinition(
        key=GasProfile.STANDARD,
        label="Standard",
        monthly_kwh=250,
        annual_kwh=3000,
        rate_code="TUR.1",
        description="One adult using gas for cooking and hot water.",
    ),
    GasProfile.HEATING: GasProfileDefinition(
        key=GasProfile.HEATING,
        label="Heating",
        monthly_kwh=8000 / 12,
        annual_kwh=8000,
        rate_code="TUR.2",
        description="One-person home with gas heating averaged across the year.",
    ),
}

DEFAULT_GAS_BILL_ASSUMPTIONS = GasBillAssumptions(
    hydrocarbons_tax_eur_per_kwh=0.00234,
    vat_rate=0.21,
    meter_rental_monthly_eur=0,
)


def gas_profile_catalog() -> list[GasProfileDefinition]:
    return list(GAS_PROFILES.values())


def get_gas_profile(profile: GasProfile) -> GasProfileDefinition:
    return GAS_PROFILES[profile]


def calculate_monthly_regulated_gas_bill(
    fixed_term_eur_month: float,
    variable_term_eur_per_kwh: float,
    profile: GasProfile,
    assumptions: GasBillAssumptions = DEFAULT_GAS_BILL_ASSUMPTIONS,
) -> GasBillBreakdown:
    profile_definition = get_gas_profile(profile)
    fixed_term = fixed_term_eur_month
    variable_term = variable_term_eur_per_kwh * profile_definition.monthly_kwh
    subtotal_before_tax = fixed_term + variable_term
    hydrocarbons_tax = (
        assumptions.hydrocarbons_tax_eur_per_kwh * profile_definition.monthly_kwh
    )
    vat_base = (
        subtotal_before_tax
        + hydrocarbons_tax
        + assumptions.meter_rental_monthly_eur
    )
    vat = vat_base * assumptions.vat_rate
    monthly_amount = vat_base + vat

    return GasBillBreakdown(
        monthly_amount=round(monthly_amount, 2),
        fixed_term_eur=round(fixed_term, 2),
        variable_term_eur=round(variable_term, 2),
        hydrocarbons_tax_eur=round(hydrocarbons_tax, 2),
        meter_rental_eur=round(assumptions.meter_rental_monthly_eur, 2),
        vat_eur=round(vat, 2),
        subtotal_before_tax_eur=round(subtotal_before_tax, 2),
    )


def apply_gas_profile(
    item: CostLineItem,
    profile: GasProfile,
    assumptions: GasBillAssumptions = DEFAULT_GAS_BILL_ASSUMPTIONS,
) -> CostLineItem:
    profile_definition = get_gas_profile(profile)
    terms = _terms_for_profile(item, profile_definition.rate_code)
    if terms is None:
        return item

    fixed_term = float(terms["fixed_term_eur_month"])
    variable_term = float(terms["variable_term_eur_per_kwh"])
    bill = calculate_monthly_regulated_gas_bill(
        fixed_term,
        variable_term,
        profile,
        assumptions,
    )

    methodology_intro = (
        "Official BOE TUR gas prices before taxes"
        if item.data_mode == DataMode.OFFICIAL_API
        else "Fallback regulated gas tariff seed before taxes"
    )
    methodology = (
        f"{methodology_intro}, applied to the {profile_definition.label.lower()} "
        f"profile at {profile_definition.monthly_kwh:g} kWh/month using "
        f"{profile_definition.rate_code}, then combined with maintained "
        "hydrocarbons-tax and VAT assumptions."
    )

    confidence = item.confidence
    source_name = item.source_name
    if item.data_mode == DataMode.OFFICIAL_API:
        confidence = Confidence.MEDIUM
        source_name = "BOE TUR gas tariff + maintained tax estimate"

    details = {
        **item.details,
        "gas_profile": profile.value,
        "gas_profile_label": profile_definition.label,
        "gas_profile_description": profile_definition.description,
        "monthly_kwh": profile_definition.monthly_kwh,
        "annual_kwh": profile_definition.annual_kwh,
        "rate_code": profile_definition.rate_code,
        "fixed_term_eur_month": round(fixed_term, 6),
        "variable_term_eur_per_kwh": round(variable_term, 6),
        "hydrocarbons_tax_eur_per_kwh": assumptions.hydrocarbons_tax_eur_per_kwh,
        "vat_rate": assumptions.vat_rate,
        "meter_rental_monthly_eur": assumptions.meter_rental_monthly_eur,
        "fixed_term_eur": bill.fixed_term_eur,
        "variable_term_eur": bill.variable_term_eur,
        "hydrocarbons_tax_eur": bill.hydrocarbons_tax_eur,
        "meter_rental_eur": bill.meter_rental_eur,
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


def gas_profile_assumptions(profile: GasProfile) -> list[str]:
    profile_definition = get_gas_profile(profile)
    return [
        f"{profile_definition.monthly_kwh:g} kWh/month gas usage "
        f"({profile_definition.label.lower()} profile)",
        f"Gas profile uses {profile_definition.rate_code} based on "
        f"{profile_definition.annual_kwh:g} kWh/year assumed consumption",
        "Gas bill estimate includes hydrocarbons tax and VAT; meter rental is "
        "a maintained assumption",
    ]


def _terms_for_profile(
    item: CostLineItem,
    rate_code: str,
) -> dict[str, float] | None:
    gas_terms = item.details.get("gas_terms")
    if isinstance(gas_terms, dict):
        terms = gas_terms.get(rate_code)
        if isinstance(terms, dict):
            return terms

    fixed_term = item.details.get("fixed_term_eur_month")
    variable_term = item.details.get("variable_term_eur_per_kwh")
    if fixed_term is None or variable_term is None:
        return None

    return {
        "fixed_term_eur_month": float(fixed_term),
        "variable_term_eur_per_kwh": float(variable_term),
    }
