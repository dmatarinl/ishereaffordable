from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.affordability.models import Confidence, CostCategory, CostLineItem, DataMode
from app.cities import SupportedCity
from app.providers.seed import ESIOS_API_URL


class EsiosElectricityProvider:
    source_id = "esios_electricity"
    source_name = "eSIOS PVPC electricity"

    def __init__(
        self,
        api_token: str | None,
        indicator_id: int,
        monthly_kwh: float,
        fixed_monthly_eur: float,
        lookback_days: int,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_token = api_token
        self.indicator_id = indicator_id
        self.monthly_kwh = monthly_kwh
        self.fixed_monthly_eur = fixed_monthly_eur
        self.lookback_days = lookback_days
        self.client = client

    def fetch_city(self, city: SupportedCity) -> list[CostLineItem]:
        if not self.api_token:
            return [self._fallback_item(city, "Missing ESIOS_API_TOKEN")]

        try:
            payload = self._fetch_indicator_values()
            return [self._item_from_payload(city, payload)]
        except Exception as error:
            return [self._fallback_item(city, f"eSIOS request failed: {error}")]

    def _fetch_indicator_values(self) -> dict[str, Any]:
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
        return response.json()

    def _item_from_payload(
        self,
        city: SupportedCity,
        payload: dict[str, Any],
    ) -> CostLineItem:
        indicator = payload.get("indicator", {})
        values = indicator.get("values", [])
        numeric_values = [
            float(value["value"])
            for value in values
            if value.get("value") is not None
        ]
        if not numeric_values:
            raise ValueError("No numeric eSIOS indicator values returned")

        average_raw = sum(numeric_values) / len(numeric_values)
        unit = indicator.get("unit") or indicator.get("unit_name") or ""
        average_eur_per_kwh = _normalise_to_eur_per_kwh(average_raw, unit)
        variable_amount = average_eur_per_kwh * self.monthly_kwh
        monthly_amount = round(variable_amount + self.fixed_monthly_eur, 2)

        return CostLineItem(
            category=CostCategory.ELECTRICITY,
            label="Electricity",
            monthly_amount=monthly_amount,
            currency=city.currency,
            data_mode=DataMode.OFFICIAL_API,
            source_name=self.source_name,
            source_url=f"{ESIOS_API_URL.rstrip('/')}/indicators/{self.indicator_id}",
            observed_at=_latest_observed_at(values),
            confidence=Confidence.HIGH,
            methodology=(
                f"Average eSIOS PVPC indicator value over the last "
                f"{self.lookback_days} days, converted to EUR/kWh and applied to "
                f"{self.monthly_kwh:g} kWh/month plus "
                f"{self.fixed_monthly_eur:g} EUR/month fixed estimate."
            ),
            details={
                "indicator_id": self.indicator_id,
                "raw_unit": unit,
                "raw_values": len(numeric_values),
                "average_raw_value": round(average_raw, 6),
                "average_eur_per_kwh": round(average_eur_per_kwh, 6),
                "monthly_kwh": self.monthly_kwh,
                "fixed_monthly_eur": self.fixed_monthly_eur,
            },
        )

    def _fallback_item(self, city: SupportedCity, reason: str) -> CostLineItem:
        electricity = round((self.monthly_kwh * 0.19) + self.fixed_monthly_eur, 2)
        return CostLineItem(
            category=CostCategory.ELECTRICITY,
            label="Electricity",
            monthly_amount=electricity,
            currency=city.currency,
            data_mode=DataMode.MANUAL_SEED,
            source_name="Fallback electricity seed pending eSIOS",
            source_url=ESIOS_API_URL,
            observed_at=datetime.now(UTC),
            confidence=Confidence.LOW,
            methodology=(
                f"{self.monthly_kwh:g} kWh/month default usage with a maintained "
                "PVPC-style seed price and fixed component. Configure "
                "ESIOS_API_TOKEN to replace this with official eSIOS data."
            ),
            details={
                "fallback_reason": reason,
                "target_source": self.source_name,
                "indicator_id": self.indicator_id,
                "monthly_kwh": self.monthly_kwh,
                "seed_variable_eur_per_kwh": 0.19,
                "fixed_monthly_eur": self.fixed_monthly_eur,
            },
        )


def _normalise_to_eur_per_kwh(value: float, unit: str) -> float:
    unit_lower = unit.lower()
    if "mwh" in unit_lower or value > 10:
        return value / 1000
    return value


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
