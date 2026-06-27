import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

import httpx

from app.affordability.models import Confidence, CostCategory, CostLineItem, DataMode
from app.cities import SupportedCity
from app.gas.profiles import (
    DEFAULT_GAS_PROFILE,
    GasBillAssumptions,
    GasProfile,
    apply_gas_profile,
)

BOE_HOME_URL = "https://www.boe.es/"
BOE_SUMMARY_API_URL = "https://www.boe.es/datosabiertos/api/boe/sumario"
BOE_ALLOWED_HOSTS = frozenset({"boe.es", "www.boe.es"})
GAS_TUR_TITLE_KEYWORDS = ("tarifa", "ultimo recurso", "gas natural")
GAS_TUR_RATE_CODES = (
    "TUR.1",
    "TUR.2",
    "TUR.3",
    "TUR.4",
    "TUR.5",
    "TUR.6",
    "TUR.7",
    "TUR.8",
    "TUR.9",
    "TUR.10",
    "TUR.11",
)


@dataclass(frozen=True)
class GasTurTerm:
    rate_code: str
    fixed_term_eur_month: float
    variable_term_eur_per_kwh: float


@dataclass(frozen=True)
class GasTurDocument:
    terms_by_rate: dict[str, GasTurTerm]
    observed_at: datetime
    source_url: str
    document_id: str | None = None


class BoeGasTurProvider:
    source_id = "boe_gas_tur"
    source_name = "BOE regulated gas TUR"

    def __init__(
        self,
        source_url: str | None,
        user_agent: str,
        default_profile: str = DEFAULT_GAS_PROFILE.value,
        gas_bill_assumptions: GasBillAssumptions | None = None,
        enable_discovery: bool = True,
        summary_api_url: str = BOE_SUMMARY_API_URL,
        client: httpx.Client | None = None,
    ) -> None:
        self.configured_source_url = source_url
        self.source_url = source_url
        self.default_profile = GasProfile(default_profile)
        self.gas_bill_assumptions = (
            gas_bill_assumptions or GasBillAssumptions(
                hydrocarbons_tax_eur_per_kwh=0.00234,
                vat_rate=0.21,
                meter_rental_monthly_eur=0,
            )
        )
        self.enable_discovery = enable_discovery
        self.summary_api_url = _validated_boe_url(summary_api_url).rstrip("/")
        self.user_agent = user_agent
        self.client = client
        self._cached_document: GasTurDocument | None = None

    def fetch_city(self, city: SupportedCity) -> list[CostLineItem]:
        try:
            document = self._fetch_document()
            return [self._item_from_document(city, document)]
        except Exception as error:
            return [self._fallback_item(city, f"BOE TUR gas request failed: {error}")]

    def _fetch_document(self) -> GasTurDocument:
        if self._cached_document is not None:
            return self._cached_document

        source_url = (
            normalise_boe_document_url(self.source_url) if self.source_url else None
        )
        if source_url is None:
            if not self.enable_discovery:
                raise ValueError("Missing BOE_GAS_TUR_URL and discovery is disabled")
            source_url = self._discover_latest_tur_document_url()

        headers = {
            "Accept": "application/xml,text/html,text/plain;q=0.9,*/*;q=0.8",
            "User-Agent": self.user_agent,
        }
        if self.client is not None:
            response = self.client.get(source_url, headers=headers)
        else:
            with httpx.Client(timeout=20) as client:
                response = client.get(source_url, headers=headers)

        response.raise_for_status()
        self._cached_document = parse_gas_tur_document(
            response.text,
            source_url=source_url,
        )
        return self._cached_document

    def _discover_latest_tur_document_url(self) -> str:
        headers = {
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }
        for candidate_date in _candidate_summary_dates(date.today()):
            url = f"{self.summary_api_url}/{candidate_date:%Y%m%d}"
            if self.client is not None:
                response = self.client.get(url, headers=headers)
            else:
                with httpx.Client(timeout=20) as client:
                    response = client.get(url, headers=headers)

            if response.status_code == 404:
                continue
            response.raise_for_status()
            document_url = _find_tur_document_url(response.json())
            if document_url:
                return normalise_boe_document_url(document_url)

        raise ValueError("Could not discover a BOE gas TUR resolution")

    def _item_from_document(
        self,
        city: SupportedCity,
        document: GasTurDocument,
    ) -> CostLineItem:
        details = {
            "document_id": document.document_id,
            "configured_source_url": self.configured_source_url,
            "resolved_source_url": document.source_url,
            "gas_terms": {
                rate_code: {
                    "fixed_term_eur_month": round(term.fixed_term_eur_month, 6),
                    "variable_term_eur_per_kwh": round(
                        term.variable_term_eur_per_kwh,
                        6,
                    ),
                }
                for rate_code, term in document.terms_by_rate.items()
            },
            "source_format": "BOE OpenData discovery + BOE XML/HTML/TXT",
        }

        item = CostLineItem(
            category=CostCategory.GAS,
            label="Gas",
            monthly_amount=0,
            currency=city.currency,
            data_mode=DataMode.OFFICIAL_API,
            source_name=self.source_name,
            source_url=document.source_url,
            observed_at=document.observed_at,
            valid_until=_next_quarter_start(datetime.now(UTC)),
            confidence=Confidence.MEDIUM,
            methodology=(
                "Official BOE TUR gas terms before taxes. The monthly user-facing "
                "amount is calculated by applying a gas usage profile plus "
                "maintained tax assumptions."
            ),
            details=details,
        )
        return apply_gas_profile(
            item,
            self.default_profile,
            self.gas_bill_assumptions,
        )

    def _fallback_item(self, city: SupportedCity, reason: str) -> CostLineItem:
        gas_terms = {
            "TUR.1": {
                "fixed_term_eur_month": 8.0,
                "variable_term_eur_per_kwh": 0.065,
            },
            "TUR.2": {
                "fixed_term_eur_month": 12.0,
                "variable_term_eur_per_kwh": 0.062,
            },
        }
        item = CostLineItem(
            category=CostCategory.GAS,
            label="Gas",
            monthly_amount=0,
            currency=city.currency,
            data_mode=DataMode.MANUAL_SEED,
            source_name="Fallback gas seed pending BOE TUR",
            source_url=self.source_url or BOE_SUMMARY_API_URL,
            observed_at=datetime.now(UTC),
            confidence=Confidence.LOW,
            methodology=(
                "Maintained regulated-tariff seed before taxes. Enable BOE "
                "OpenData discovery or configure BOE_GAS_TUR_URL to replace this "
                "fallback with official BOE TUR gas terms."
            ),
            details={
                "fallback_reason": reason,
                "target_source": self.source_name,
                "gas_terms": gas_terms,
            },
        )
        return apply_gas_profile(
            item,
            self.default_profile,
            self.gas_bill_assumptions,
        )


def parse_gas_tur_document(raw_text: str, source_url: str) -> GasTurDocument:
    text = _plain_text(raw_text)
    terms_by_rate = parse_gas_tur_terms_catalog(text)
    observed_at = _parse_publication_date(text) or datetime.now(UTC)
    document_id = _parse_document_id(source_url, text)
    return GasTurDocument(
        terms_by_rate=terms_by_rate,
        observed_at=observed_at,
        source_url=source_url,
        document_id=document_id,
    )


def parse_gas_tur_terms(raw_text: str, rate_code: str) -> GasTurTerm:
    text = _plain_text(raw_text)
    terms = _parse_terms_from_text(text, rate_code)
    return GasTurTerm(
        rate_code=rate_code,
        fixed_term_eur_month=terms[0],
        variable_term_eur_per_kwh=terms[1],
    )


def parse_gas_tur_terms_catalog(raw_text: str) -> dict[str, GasTurTerm]:
    terms_by_rate: dict[str, GasTurTerm] = {}
    for rate_code in GAS_TUR_RATE_CODES:
        try:
            terms_by_rate[rate_code] = parse_gas_tur_terms(raw_text, rate_code)
        except ValueError:
            continue

    if not terms_by_rate:
        raise ValueError("Could not parse BOE TUR terms")
    return terms_by_rate


def normalise_boe_document_url(source_url: str) -> str:
    match = re.search(r"(BOE-A-\d{4}-\d+)", source_url, re.IGNORECASE)
    if match:
        return _validated_boe_url(
            f"https://www.boe.es/diario_boe/txt.php?id={match.group(1).upper()}"
        )
    return _validated_boe_url(source_url)


def _validated_boe_url(source_url: str) -> str:
    parsed = urlparse(source_url)
    if parsed.scheme != "https" or parsed.hostname not in BOE_ALLOWED_HOSTS:
        raise ValueError("BOE source URL must use https://boe.es or https://www.boe.es")
    return source_url


def _candidate_summary_dates(reference: date) -> list[date]:
    candidates: set[date] = set()

    for days_back in range(15):
        candidates.add(reference - timedelta(days=days_back))

    for year in range(reference.year, reference.year - 3, -1):
        for month in (1, 4, 7, 10):
            effective_date = date(year, month, 1)
            if effective_date > reference + timedelta(days=7):
                continue

            for delta_days in range(-8, 9):
                candidate = effective_date + timedelta(days=delta_days)
                if candidate <= reference:
                    candidates.add(candidate)

    return sorted(candidates, reverse=True)


def _find_tur_document_url(payload: dict[str, Any]) -> str | None:
    for item in _iter_boe_items(payload):
        title = str(item.get("titulo") or "")
        if not _is_gas_tur_title(title):
            continue

        for key in ("url_xml", "url_html", "url_pdf"):
            url = _extract_url(item.get(key))
            if url:
                return url

    return None


def _iter_boe_items(node: Any):
    if isinstance(node, dict):
        if "titulo" in node and any(
            key in node for key in ("url_xml", "url_html", "url_pdf")
        ):
            yield node

        for value in node.values():
            yield from _iter_boe_items(value)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_boe_items(value)


def _extract_url(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        text = value.get("texto")
        return str(text) if text else None
    return None


def _is_gas_tur_title(title: str) -> bool:
    normalized = _normalise_text(title)
    return all(keyword in normalized for keyword in GAS_TUR_TITLE_KEYWORDS)


def _normalise_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return without_marks.lower()


def _parse_document_id(source_url: str, text: str) -> str | None:
    match = re.search(r"(BOE-A-\d{4}-\d+)", f"{source_url} {text}", re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def _parse_terms_from_text(text: str, rate_code: str) -> tuple[float, float]:
    compact = _compact_text(text)
    aliases = {
        rate_code,
        rate_code.replace(".", " "),
        rate_code.replace(".", ""),
    }
    for alias in aliases:
        pattern = re.compile(rf"\b{re.escape(alias)}\b", re.IGNORECASE)
        for match in pattern.finditer(compact):
            window = compact[match.end() : match.end() + 260]
            parsed_values = (
                _parse_decimal(value) for value in _NUMBER_RE.findall(window)
            )
            numbers = [
                value
                for value in parsed_values
                if 0 <= value < 100
            ]
            if len(numbers) >= 2:
                fixed_term = numbers[0]
                variable_term = _normalise_variable_term(numbers[1], compact)
                return fixed_term, variable_term

    raise ValueError(f"Could not parse BOE TUR terms for {rate_code}")


_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


def _parse_decimal(value: str) -> float:
    if "," in value:
        normalized = value.replace(".", "").replace(",", ".")
        return float(normalized)

    if "." in value:
        before, after = value.split(".", maxsplit=1)
        if len(after) == 3:
            return float(before + after)
    return float(value)


def _normalise_variable_term(value: float, text: str) -> float:
    lower_text = text.lower()
    if "c€/kwh" in lower_text or "cent" in lower_text or value > 1:
        return value / 100
    return value


def _plain_text(raw_text: str) -> str:
    try:
        root = ET.fromstring(raw_text)
    except ET.ParseError:
        return re.sub(r"<[^>]+>", " ", raw_text)

    return " ".join(root.itertext())


def _compact_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


SPANISH_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def _parse_publication_date(text: str) -> datetime | None:
    match = re.search(
        r"de\s+(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+de\s+(\d{4})",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None

    month = SPANISH_MONTHS.get(match.group(2).lower())
    if month is None:
        return None

    return datetime(int(match.group(3)), month, int(match.group(1)), tzinfo=UTC)


def _next_quarter_start(reference: datetime) -> datetime:
    for month in (1, 4, 7, 10):
        if reference.month < month:
            return datetime(reference.year, month, 1, tzinfo=UTC)
    return datetime(reference.year + 1, 1, 1, tzinfo=UTC)
