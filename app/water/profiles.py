from enum import StrEnum

from pydantic import BaseModel, Field

from app.affordability.models import CostLineItem

INE_WATER_SOURCE_URL = "https://www.ine.es/dyngs/Prensa/es/ESSA2022.htm"
BARCELONA_WATER_SOURCE_URL = (
    "https://www.aiguesdebarcelona.cat/es/servicio-agua/"
    "factura-y-tarifas-agua/tarifas-de-suministro"
)


class WaterProfile(StrEnum):
    LOW = "low"
    STANDARD = "standard"
    HIGH = "high"


class WaterProfileSource(BaseModel):
    name: str
    url: str
    relevance: str


class WaterProfileDefinition(BaseModel):
    key: WaterProfile
    label: str
    monthly_m3: float = Field(gt=0)
    description: str
    rationale: str


DEFAULT_WATER_PROFILE = WaterProfile.STANDARD
REFERENCE_MONTHLY_M3 = 6.0

WATER_PROFILE_METHODOLOGY = (
    "Spain has no single household water tariff: providers use local fixed fees, "
    "consumption bands, sanitation charges and taxes. Until city tariff adapters "
    "are implemented, these profiles scale the current city estimate from its "
    "6 m3/month reference. Actual bills are not necessarily linear."
)

WATER_PROFILE_SOURCES = [
    WaterProfileSource(
        name="INE household water consumption",
        url=INE_WATER_SOURCE_URL,
        relevance=(
            "INE reports 128 litres per inhabitant/day in 2022, approximately "
            "3.9 m3/month and rounded to the 4 m3 low scenario."
        ),
    ),
    WaterProfileSource(
        name="Aigues de Barcelona domestic bands",
        url=BARCELONA_WATER_SOURCE_URL,
        relevance=(
            "The published domestic bands end at 6 m3/month for band one and "
            "9 m3/month for band two, providing understandable standard and high "
            "scenario boundaries."
        ),
    ),
]

WATER_PROFILES = {
    WaterProfile.LOW: WaterProfileDefinition(
        key=WaterProfile.LOW,
        label="Low",
        monthly_m3=4,
        description="Careful one-person household use.",
        rationale="Rounded from the INE national per-person household average.",
    ),
    WaterProfile.STANDARD: WaterProfileDefinition(
        key=WaterProfile.STANDARD,
        label="Standard",
        monthly_m3=6,
        description="One adult with moderate daily water use.",
        rationale="Adds headroom above the INE average and matches a first-band cap.",
    ),
    WaterProfile.HIGH: WaterProfileDefinition(
        key=WaterProfile.HIGH,
        label="High",
        monthly_m3=9,
        description="Higher shower, laundry, cleaning or home-working use.",
        rationale="Matches the upper boundary of a published second domestic band.",
    ),
}


def water_profile_catalog() -> list[WaterProfileDefinition]:
    return list(WATER_PROFILES.values())


def water_profile_sources() -> list[WaterProfileSource]:
    return WATER_PROFILE_SOURCES


def get_water_profile(profile: WaterProfile) -> WaterProfileDefinition:
    return WATER_PROFILES[profile]


def apply_water_profile(
    item: CostLineItem,
    profile: WaterProfile,
) -> CostLineItem:
    profile_definition = get_water_profile(profile)
    reference_m3 = float(
        item.details.get("reference_monthly_m3")
        or item.details.get("monthly_m3")
        or REFERENCE_MONTHLY_M3
    )
    reference_amount = float(
        item.details.get("reference_monthly_amount_eur") or item.monthly_amount
    )
    scale_factor = profile_definition.monthly_m3 / reference_m3
    if profile == WaterProfile.STANDARD:
        scenario_methodology = (
            f"Standard water usage scenario at {profile_definition.monthly_m3:g} "
            "m3/month, using the current city estimate as its reference."
        )
    else:
        scenario_methodology = (
            f"{profile_definition.label} water usage scenario at "
            f"{profile_definition.monthly_m3:g} m3/month, estimated by scaling "
            f"the {reference_m3:g} m3/month city estimate."
        )

    details = {
        **item.details,
        "water_profile": profile.value,
        "water_profile_label": profile_definition.label,
        "water_profile_description": profile_definition.description,
        "water_profile_rationale": profile_definition.rationale,
        "monthly_m3": profile_definition.monthly_m3,
        "reference_monthly_m3": reference_m3,
        "reference_monthly_amount_eur": reference_amount,
        "profile_scale_factor": round(scale_factor, 6),
        "profile_sources": [source.model_dump() for source in WATER_PROFILE_SOURCES],
    }

    return item.model_copy(
        update={
            "monthly_amount": round(reference_amount * scale_factor, 2),
            "methodology": (
                f"{scenario_methodology} This is not an official municipal tariff "
                "bill; "
                "local fixed fees and progressive bands may make real bills differ."
            ),
            "details": details,
        }
    )


def water_profile_assumptions(profile: WaterProfile) -> list[str]:
    profile_definition = get_water_profile(profile)
    return [
        f"{profile_definition.monthly_m3:g} m3/month water usage "
        f"({profile_definition.label.lower()} profile)",
        "Water uses the current city estimate scaled as a simple scenario",
        "Municipal fixed fees, tariff bands and taxes are not yet modelled",
    ]
