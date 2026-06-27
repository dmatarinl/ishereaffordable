from datetime import UTC, datetime, timedelta

from app.affordability.models import Confidence, CostCategory, CostLineItem, DataMode
from app.sources.catalog import SOURCE_RULES, is_stale, validate_line_items


def _line_item(
    category: CostCategory,
    data_mode: DataMode,
    cached_at: datetime | None = None,
) -> CostLineItem:
    return CostLineItem(
        category=category,
        label=category.value,
        monthly_amount=10,
        currency="EUR",
        data_mode=data_mode,
        source_name="test",
        source_url="https://example.com",
        observed_at=cached_at or datetime.now(UTC),
        cached_at=cached_at,
        confidence=Confidence.LOW,
        methodology="test",
    )


def test_source_rules_cover_all_categories() -> None:
    assert set(SOURCE_RULES) == set(CostCategory)


def test_manual_seed_warns_with_preferred_source() -> None:
    warnings = validate_line_items(
        [_line_item(CostCategory.RENT, DataMode.MANUAL_SEED)]
    )

    assert warnings == [
        "rent uses manual seed fallback data; preferred source is "
        "Official rental reference/open data."
    ]


def test_invalid_data_mode_warns() -> None:
    warnings = validate_line_items(
        [_line_item(CostCategory.ELECTRICITY, DataMode.PERMITTED_SCRAPE)]
    )

    assert (
        "electricity uses permitted_scrape, which is not allowed for Electricity."
        in warnings
    )


def test_stale_data_warns_by_category_freshness() -> None:
    stale_item = _line_item(
        CostCategory.FOOD,
        DataMode.PERMITTED_SCRAPE,
        cached_at=datetime.now(UTC) - timedelta(days=8),
    )

    warnings = validate_line_items([stale_item])

    assert "food is stale; Food should refresh within 7 days." in warnings
    assert is_stale(stale_item, SOURCE_RULES[CostCategory.FOOD])


def test_calculated_safety_margin_is_never_stale() -> None:
    item = _line_item(
        CostCategory.SAFETY_MARGIN,
        DataMode.CALCULATED,
        cached_at=datetime.now(UTC) - timedelta(days=400),
    )

    assert not is_stale(item, SOURCE_RULES[CostCategory.SAFETY_MARGIN])
    assert validate_line_items([item]) == []


def test_expired_official_tariff_produces_specific_warning() -> None:
    item = CostLineItem(
        category=CostCategory.PUBLIC_TRANSPORT,
        label="Public transport",
        monthly_amount=20,
        currency="EUR",
        data_mode=DataMode.OFFICIAL_PUBLICATION,
        source_name="Official transport authority",
        source_url="https://example.com/transport",
        observed_at=datetime.now(UTC) - timedelta(days=30),
        valid_until=datetime.now(UTC) - timedelta(days=1),
        confidence=Confidence.MEDIUM,
        methodology="Adult 30-day official fare.",
    )

    warnings = validate_line_items([item])

    assert len(warnings) == 1
    assert "tariff validity ended" in warnings[0]
