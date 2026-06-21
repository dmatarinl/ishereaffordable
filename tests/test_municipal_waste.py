from app.affordability.models import Confidence, DataMode
from app.cities import get_supported_city
from app.providers.municipal_waste import HybridMunicipalWasteProvider
from app.trash_tax.rules import apply_municipal_waste_profile
from app.water.profiles import WaterProfile


def _city(name: str):
    city = get_supported_city(name)
    assert city is not None
    return city


def test_madrid_uses_official_published_average() -> None:
    item = HybridMunicipalWasteProvider().fetch_city(_city("Madrid"))[0]

    assert item.data_mode == DataMode.OFFICIAL_PUBLICATION
    assert item.confidence == Confidence.MEDIUM
    assert item.monthly_amount == 11.88
    assert item.details["annual_amount"] == 142.60
    assert item.details["amount_kind"] == "official_city_average"
    assert item.details["exact"] is False
    assert "cadastral value" in item.details["exact_inputs_required"]


def test_zaragoza_waste_tariff_follows_water_profile_band() -> None:
    item = HybridMunicipalWasteProvider().fetch_city(_city("Zaragoza"))[0]

    standard = apply_municipal_waste_profile(item, WaterProfile.STANDARD)
    high = apply_municipal_waste_profile(item, WaterProfile.HIGH)

    assert standard.monthly_amount == 6.06
    assert standard.details["annual_amount"] == 72.68
    assert standard.details["components"] == {
        "collection": 41.26,
        "treatment": 31.42,
    }
    assert high.monthly_amount == 6.67
    assert high.details["annual_amount"] == 80.00
    assert high.details["selected_band"] == "Above 0.283 m3/day"


def test_alicante_uses_midpoint_and_preserves_official_range() -> None:
    item = HybridMunicipalWasteProvider().fetch_city(_city("Alicante"))[0]

    assert item.monthly_amount == 8.52
    assert item.details["annual_amount"] == 102.26
    assert item.details["annual_min"] == 69.85
    assert item.details["annual_max"] == 134.67
    assert item.details["amount_kind"] == "official_range_midpoint"
    assert "69.85-134.67 EUR" in item.methodology


def test_city_without_complete_rule_keeps_explicit_fallback() -> None:
    item = HybridMunicipalWasteProvider().fetch_city(_city("Barcelona"))[0]

    assert item.data_mode == DataMode.MANUAL_SEED
    assert item.confidence == Confidence.LOW
    assert "annual waste tax seed" in item.methodology
