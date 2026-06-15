from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel

from app.affordability.models import Confidence, CostCategory, CostLineItem, DataMode

FreshnessWindow = int | Literal["always"]


class SourceRule(BaseModel):
    category: CostCategory
    label: str
    first_choice: str
    second_choice: str | None
    fallback: str | None
    allowed_data_modes: list[DataMode]
    freshness_days: FreshnessWindow
    stale_confidence: Confidence
    user_guidance: str


SOURCE_RULES = {
    CostCategory.RENT: SourceRule(
        category=CostCategory.RENT,
        label="Rent",
        first_choice="Idealista Search API or approved real-estate API",
        second_choice="Permitted portal scrape",
        fallback="Manual rental seed",
        allowed_data_modes=[
            DataMode.OFFICIAL_API,
            DataMode.PERMITTED_SCRAPE,
            DataMode.MANUAL_SEED,
            DataMode.UNAVAILABLE,
        ],
        freshness_days=7,
        stale_confidence=Confidence.LOW,
        user_guidance="Rent should be refreshed weekly because listings move quickly.",
    ),
    CostCategory.ELECTRICITY: SourceRule(
        category=CostCategory.ELECTRICITY,
        label="Electricity",
        first_choice="eSIOS API",
        second_choice=None,
        fallback="Manual electricity seed",
        allowed_data_modes=[
            DataMode.OFFICIAL_API,
            DataMode.MANUAL_SEED,
            DataMode.UNAVAILABLE,
        ],
        freshness_days=1,
        stale_confidence=Confidence.LOW,
        user_guidance="Electricity should come from eSIOS and refresh daily.",
    ),
    CostCategory.GAS: SourceRule(
        category=CostCategory.GAS,
        label="Gas",
        first_choice="Official TUR, BOE, or CNMC data",
        second_choice=None,
        fallback="Manual gas seed",
        allowed_data_modes=[
            DataMode.OFFICIAL_API,
            DataMode.MANUAL_SEED,
            DataMode.UNAVAILABLE,
        ],
        freshness_days=90,
        stale_confidence=Confidence.LOW,
        user_guidance="Gas regulated tariff data should be refreshed quarterly.",
    ),
    CostCategory.WATER: SourceRule(
        category=CostCategory.WATER,
        label="Water",
        first_choice="Municipal/provider tariff data",
        second_choice="Permitted provider or city scrape",
        fallback="Manual water seed",
        allowed_data_modes=[
            DataMode.OFFICIAL_API,
            DataMode.PERMITTED_SCRAPE,
            DataMode.MANUAL_SEED,
            DataMode.UNAVAILABLE,
        ],
        freshness_days=180,
        stale_confidence=Confidence.LOW,
        user_guidance="Water tariffs change slowly but vary by municipality.",
    ),
    CostCategory.TRASH_TAX: SourceRule(
        category=CostCategory.TRASH_TAX,
        label="Trash tax",
        first_choice="Municipal ordinance/open data",
        second_choice="Permitted city tax-page scrape",
        fallback="Manual trash-tax seed",
        allowed_data_modes=[
            DataMode.OFFICIAL_API,
            DataMode.PERMITTED_SCRAPE,
            DataMode.MANUAL_SEED,
            DataMode.UNAVAILABLE,
        ],
        freshness_days=365,
        stale_confidence=Confidence.LOW,
        user_guidance="Trash tax should be checked annually against municipal rules.",
    ),
    CostCategory.FOOD: SourceRule(
        category=CostCategory.FOOD,
        label="Food",
        first_choice="Supermarket API/feed",
        second_choice="Permitted supermarket scrape",
        fallback="Manual basket seed",
        allowed_data_modes=[
            DataMode.OFFICIAL_API,
            DataMode.PERMITTED_SCRAPE,
            DataMode.MANUAL_SEED,
            DataMode.UNAVAILABLE,
        ],
        freshness_days=7,
        stale_confidence=Confidence.LOW,
        user_guidance="Food basket prices should be refreshed weekly or better.",
    ),
    CostCategory.PUBLIC_TRANSPORT: SourceRule(
        category=CostCategory.PUBLIC_TRANSPORT,
        label="Public transport",
        first_choice="Official transport authority fares",
        second_choice="Permitted fare-page scrape",
        fallback="Manual transport seed",
        allowed_data_modes=[
            DataMode.OFFICIAL_API,
            DataMode.PERMITTED_SCRAPE,
            DataMode.MANUAL_SEED,
            DataMode.UNAVAILABLE,
        ],
        freshness_days=90,
        stale_confidence=Confidence.LOW,
        user_guidance="Transport fares should be refreshed quarterly.",
    ),
    CostCategory.SAFETY_MARGIN: SourceRule(
        category=CostCategory.SAFETY_MARGIN,
        label="Safety margin",
        first_choice="Calculated formula",
        second_choice=None,
        fallback=None,
        allowed_data_modes=[DataMode.CALCULATED],
        freshness_days="always",
        stale_confidence=Confidence.MEDIUM,
        user_guidance="Safety margin is calculated from the current baseline.",
    ),
}


def source_rules() -> list[SourceRule]:
    return list(SOURCE_RULES.values())


def validate_line_items(line_items: list[CostLineItem]) -> list[str]:
    warnings: list[str] = []
    for item in line_items:
        rule = SOURCE_RULES.get(item.category)
        if rule is None:
            warnings.append(f"{item.label} has no source rule.")
            continue

        if item.data_mode not in rule.allowed_data_modes:
            warnings.append(
                f"{item.label} uses {item.data_mode.value}, which is not allowed "
                f"for {rule.label}."
            )

        if item.data_mode == DataMode.MANUAL_SEED:
            warnings.append(
                f"{item.label} uses manual seed fallback data; preferred source is "
                f"{rule.first_choice}."
            )

        if item.data_mode == DataMode.UNAVAILABLE:
            warnings.append(f"{item.label} is unavailable.")

        if is_stale(item, rule):
            warnings.append(
                f"{item.label} is stale; {rule.label} should refresh within "
                f"{rule.freshness_days} days."
            )
    return warnings


def is_stale(item: CostLineItem, rule: SourceRule) -> bool:
    if rule.freshness_days == "always":
        return False
    reference_time = item.cached_at or item.observed_at
    return reference_time < datetime.now(UTC) - timedelta(days=rule.freshness_days)
