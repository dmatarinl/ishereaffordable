from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.affordability.models import Confidence, CostCategory, CostLineItem, DataMode
from app.cities import SupportedCity
from app.electricity.profiles import (
    DEFAULT_ELECTRICITY_PROFILE,
    ElectricityProfile,
    apply_electricity_profile,
)
from app.providers.seed import ESIOS_API_URL


class EsiosElectricityProvider:
    source_id = "esios_electricity"
    source_name = "eSIOS PVPC electricity"

    def __init__(
        self,
        api_token: str | None,
        indicator_id: int,
        lookback_days: int,
        default_profile: str = DEFAULT_ELECTRICITY_PROFILE.value,
        geo_name: str | None = "Península",
        client: httpx.Client | None = None,
    ) -> None:
        self.api_token = api_token
        self.indicator_id = indicator_id
        self.lookback_days = lookback_days
        self.default_profile = default_profile
        self.geo_name = geo_name
        self.client = client
        self._cached_payload: dict[str, Any] | None = None

    def fetch_city(self, city: SupportedCity) -> list[CostLineItem]:
        if not self.api_token:
            return [self._fallback_item(city, "Missing ESIOS_API_TOKEN")]

        try:
            payload = self._fetch_indicator_values()
            return [self._item_from_payload(city, payload)]
        except Exception as error:
            return [self._fallback_item(city, f"eSIOS request failed: {error}")]

    def _fetch_indicator_values(self) -> dict[str, Any]:
        if self._cached_payload is not None:
            return self._cached_payload

        now = datetime.now(UTC)
        start = now - timedelta(days=self.lookback_days)
        url = f"{ESIOS_API_URL.rstrip('/')}/indicators/{self.indicator_id}"
        headers = {
            "Accept": "application/json; application/vnd.esios-api-v1+json",
            "Content-Type": "application/json",
            "x-api-key": self.api_token or "",
        }
        params = {
            "start_date": start.isoformat(),
            "end_date": now.isoformat(),
            "locale": "es",
        }

        if self.client is not None:
            response = self.client.get(url, headers=headers, params=params)
        else:
            with httpx.Client(timeout=20) as client:
                response = client.get(url, headers=headers, params=params)

        response.raise_for_status()
        self._cached_payload = response.json()
        return self._cached_payload

    def _item_from_payload(
        self,
        city: SupportedCity,
        payload: dict[str, Any],
    ) -> CostLineItem:
        indicator = payload.get("indicator", {})
        values = _filter_values_by_geo(
            indicator.get("values", []),
            self.geo_name,
        )
        numeric_values = [
            float(value["value"])
            for value in values
            if value.get("value") is not None
        ]
        if not numeric_values:
            raise ValueError("No numeric eSIOS indicator values returned")

        average_raw = sum(numeric_values) / len(numeric_values)
        unit = _indicator_unit(indicator)
        average_eur_per_kwh = _normalise_to_eur_per_kwh(average_raw, unit)
        item = CostLineItem(
            category=CostCategory.ELECTRICITY,
            label="Electricity",
            monthly_amount=round(average_eur_per_kwh, 6),
            currency=city.currency,
            data_mode=DataMode.OFFICIAL_API,
            source_name=self.source_name,
            source_url=f"{ESIOS_API_URL.rstrip('/')}/indicators/{self.indicator_id}",
            observed_at=_latest_observed_at(values),
            confidence=Confidence.MEDIUM,
            methodology=(
                f"Average eSIOS PVPC indicator value over the last "
                f"{self.lookback_days} days for {self.geo_name or 'all geographies'}, "
                "converted to EUR/kWh before applying household bill assumptions."
            ),
            details={
                "indicator_id": self.indicator_id,
                "geo_name": self.geo_name,
                "raw_unit": unit,
                "raw_values": len(numeric_values),
                "average_raw_value": round(average_raw, 6),
                "average_eur_per_kwh": round(average_eur_per_kwh, 6),
            },
        )
        return apply_electricity_profile(item, _default_profile(self.default_profile))

    def _fallback_item(self, city: SupportedCity, reason: str) -> CostLineItem:
        item = CostLineItem(
            category=CostCategory.ELECTRICITY,
            label="Electricity",
            monthly_amount=0.19,
            currency=city.currency,
            data_mode=DataMode.MANUAL_SEED,
            source_name="Fallback electricity seed pending eSIOS",
            source_url=ESIOS_API_URL,
            observed_at=datetime.now(UTC),
            confidence=Confidence.LOW,
            methodology=(
                "Fallback PVPC-style unit price before applying household bill "
                "assumptions. Configure ESIOS_API_TOKEN to replace this with "
                "official eSIOS data."
            ),
            details={
                "fallback_reason": reason,
                "target_source": self.source_name,
                "indicator_id": self.indicator_id,
                "geo_name": self.geo_name,
                "seed_variable_eur_per_kwh": 0.19,
            },
        )
        return apply_electricity_profile(item, _default_profile(self.default_profile))


def _normalise_to_eur_per_kwh(value: float, unit: str) -> float:
    unit_lower = unit.lower()
    if "mwh" in unit_lower or value > 10:
        return value / 1000
    return value


def _indicator_unit(indicator: dict[str, Any]) -> str:
    direct_unit = indicator.get("unit") or indicator.get("unit_name")
    if direct_unit:
        return str(direct_unit)

    magnitud = indicator.get("magnitud") or []
    if magnitud:
        name = magnitud[0].get("name")
        if name:
            return str(name)

    return ""


def _filter_values_by_geo(
    values: list[dict[str, Any]],
    geo_name: str | None,
) -> list[dict[str, Any]]:
    if not geo_name:
        return values

    filtered = [value for value in values if value.get("geo_name") == geo_name]
    return filtered or values


def _latest_observed_at(values: list[dict[str, Any]]) -> datetime:
    parsed = [
        _parse_datetime(value.get("datetime") or value.get("datetime_utc"))
        for value in values
    ]
    dates = [value for value in parsed if value is not None]
    if not dates:
        return datetime.now(UTC)
    return max(dates)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _default_profile(value: str):
    return ElectricityProfile(value)
