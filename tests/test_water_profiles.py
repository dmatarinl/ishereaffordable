from datetime import UTC, datetime

from app.affordability.models import (
    Confidence,
    CostCategory,
    CostLineItem,
    DataMode,
)
from app.water.profiles import (
    WaterProfile,
    apply_water_profile,
    water_profile_catalog,
    water_profile_sources,
)


def _water_item() -> CostLineItem:
    return CostLineItem(
        category=CostCategory.WATER,
        label="Water",
        monthly_amount=18,
        currency="EUR",
        data_mode=DataMode.MANUAL_SEED,
        source_name="Fallback water seed",
        source_url="https://example.com",
        observed_at=datetime.now(UTC),
        confidence=Confidence.LOW,
        methodology="test seed",
        details={
            "reference_monthly_m3": 6,
            "reference_monthly_amount_eur": 18,
        },
    )


def test_water_profiles_scale_six_m3_reference() -> None:
    item = _water_item()

    low = apply_water_profile(item, WaterProfile.LOW)
    standard = apply_water_profile(item, WaterProfile.STANDARD)
    high = apply_water_profile(item, WaterProfile.HIGH)

    assert low.monthly_amount == 12
    assert standard.monthly_amount == 18
    assert high.monthly_amount == 27
    assert low.details["monthly_m3"] == 4
    assert standard.details["monthly_m3"] == 6
    assert high.details["monthly_m3"] == 9
    assert "Standard water usage scenario at 6 m3/month" in standard.methodology
    assert "from 6 to 6" not in standard.methodology
    assert "Low water usage scenario at 4 m3/month" in low.methodology
    assert "High water usage scenario at 9 m3/month" in high.methodology
    assert all(
        result.data_mode == DataMode.MANUAL_SEED
        for result in (low, standard, high)
    )
    assert all(
        result.confidence == Confidence.LOW
        for result in (low, standard, high)
    )


def test_water_profile_reapplication_keeps_original_reference() -> None:
    low = apply_water_profile(_water_item(), WaterProfile.LOW)
    high = apply_water_profile(low, WaterProfile.HIGH)

    assert high.monthly_amount == 27
    assert high.details["reference_monthly_amount_eur"] == 18


def test_water_profile_catalog_exposes_rationale_and_sources() -> None:
    profiles = water_profile_catalog()
    sources = water_profile_sources()

    assert [profile.monthly_m3 for profile in profiles] == [4, 6, 9]
    assert all(profile.rationale for profile in profiles)
    assert {source.name for source in sources} == {
        "INE household water consumption",
        "Aigues de Barcelona domestic bands",
    }
    assert all(source.url.startswith("https://") for source in sources)
