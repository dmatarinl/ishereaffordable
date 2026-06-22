from dataclasses import asdict, dataclass
from datetime import UTC, datetime

MODEL_VERSION = "2026.2"
STANDARD_ADULT_PROFILE = "Adult without age, income, or family discounts"


@dataclass(frozen=True)
class TransportFare:
    city_key: str
    product_name: str
    monthly_amount_eur: float
    calculation_type: str
    calculation_summary: str
    modes_available: tuple[str, ...]
    modes_included: tuple[str, ...]
    source_name: str
    source_url: str
    observed_at: datetime
    valid_until: datetime
    fare_scope: str
    base_monthly_amount_eur: float | None = None
    subsidy_percent: float | None = None
    monthly_journeys: int | None = None
    unit_fare_eur: float | None = None
    excluded_modes: tuple[str, ...] = ()
    supporting_source_urls: tuple[str, ...] = ()

    def details(self) -> dict:
        details = asdict(self)
        details.pop("city_key")
        details.pop("monthly_amount_eur")
        details.pop("source_name")
        details.pop("source_url")
        details.pop("observed_at")
        details["model_version"] = MODEL_VERSION
        details["traveller_profile"] = STANDARD_ADULT_PROFILE
        details["modes_available"] = list(self.modes_available)
        details["modes_included"] = list(self.modes_included)
        details["excluded_modes"] = list(self.excluded_modes)
        details["supporting_source_urls"] = list(self.supporting_source_urls)
        details["valid_until"] = self.valid_until.isoformat()
        return details


def _end_of_2026() -> datetime:
    return datetime(2026, 12, 31, 23, 59, 59, tzinfo=UTC)


TRANSPORT_FARES = {
    "madrid": TransportFare(
        city_key="madrid",
        product_name="Abono Transporte 30 días - Zona A",
        monthly_amount_eur=32.70,
        base_monthly_amount_eur=54.60,
        subsidy_percent=40,
        calculation_type="30_day_pass",
        calculation_summary=(
            "One adult 30-day Zone A pass with unlimited journeys."
        ),
        modes_available=("EMT bus", "Metro", "Metro Ligero", "Cercanías"),
        modes_included=("EMT bus", "Metro", "Metro Ligero", "Cercanías"),
        source_name="Consorcio Regional de Transportes de Madrid",
        source_url=(
            "https://www.crtm.es/billetes-y-tarifas/buscador/"
            "abono-30-dias/?lang=es&zona=A"
        ),
        observed_at=datetime(2026, 1, 1, tzinfo=UTC),
        valid_until=_end_of_2026(),
        fare_scope="Madrid transport Zone A",
    ),
    "barcelona": TransportFare(
        city_key="barcelona",
        product_name="T-usual - 1 zone",
        monthly_amount_eur=22.80,
        base_monthly_amount_eur=45.60,
        subsidy_percent=50,
        calculation_type="30_day_pass",
        calculation_summary=(
            "One adult 30-day one-zone pass with unlimited integrated journeys."
        ),
        modes_available=("Bus", "Metro", "Tranvía", "Rodalies"),
        modes_included=("Bus", "Metro", "Tranvía", "Rodalies"),
        source_name="ATM Barcelona - T-mobilitat",
        source_url=(
            "https://t-mobilitat.atm.cat/es/web/t-mobilitat/tarifas/t-usual"
        ),
        observed_at=datetime(2026, 1, 15, tzinfo=UTC),
        valid_until=_end_of_2026(),
        fare_scope="One integrated fare zone",
    ),
    "valencia": TransportFare(
        city_key="valencia",
        product_name="SUMA Mensual - 1 zone",
        monthly_amount_eur=21.00,
        base_monthly_amount_eur=35.00,
        subsidy_percent=40,
        calculation_type="30_day_pass",
        calculation_summary=(
            "One adult 30-day one-zone pass with unlimited integrated journeys."
        ),
        modes_available=("EMT bus", "Metrovalencia", "Metrobus", "Cercanías"),
        modes_included=("EMT bus", "Metrovalencia", "Metrobus", "Cercanías"),
        source_name="Autoritat de Transport Metropolità de València",
        source_url="https://sede.gva.es/es/detall-tramit?id_proc=G105759",
        observed_at=datetime(2025, 12, 31, tzinfo=UTC),
        valid_until=datetime(2026, 6, 30, 23, 59, 59, tzinfo=UTC),
        fare_scope="One integrated fare zone",
    ),
    "sevilla": TransportFare(
        city_key="sevilla",
        product_name="TUSSAM 30 días",
        monthly_amount_eur=21.20,
        base_monthly_amount_eur=35.30,
        subsidy_percent=40,
        calculation_type="30_day_pass",
        calculation_summary=(
            "One adult 30-day TUSSAM pass with unlimited ordinary journeys."
        ),
        modes_available=("TUSSAM bus", "Metrocentro tram", "Metro Line 1"),
        modes_included=("TUSSAM bus", "Metrocentro tram"),
        excluded_modes=("Metro Line 1", "Airport bus", "Special services"),
        source_name="TUSSAM - Ayuntamiento de Sevilla",
        source_url="https://www.tussam.es/es/30-dias",
        observed_at=datetime(2026, 1, 1, tzinfo=UTC),
        valid_until=_end_of_2026(),
        fare_scope="TUSSAM ordinary urban network",
    ),
    "zaragoza": TransportFare(
        city_key="zaragoza",
        product_name="Tarjeta Bus / multiviaje",
        monthly_amount_eur=22.00,
        subsidy_percent=40,
        calculation_type="monthly_journey_scenario",
        calculation_summary=(
            "Forty one-way urban journeys per month at EUR 0.55 per journey."
        ),
        monthly_journeys=40,
        unit_fare_eur=0.55,
        modes_available=("Urban bus", "Tram"),
        modes_included=("Urban bus", "Tram"),
        source_name="Ayuntamiento de Zaragoza",
        source_url="https://www.zaragoza.es/sede/servicio/noticia/346533",
        observed_at=datetime(2025, 12, 30, tzinfo=UTC),
        valid_until=_end_of_2026(),
        fare_scope="Zaragoza urban bus and tram network",
    ),
    "malaga": TransportFare(
        city_key="malaga",
        product_name="EMT Tarjeta Mensual",
        monthly_amount_eur=23.97,
        base_monthly_amount_eur=39.95,
        subsidy_percent=40,
        calculation_type="30_day_pass",
        calculation_summary=(
            "One adult monthly EMT pass with unlimited urban bus journeys."
        ),
        modes_available=("EMT urban bus", "Metro de Malaga"),
        modes_included=("EMT urban bus",),
        excluded_modes=("Metro de Malaga", "Airport bus"),
        source_name="Ayuntamiento de Málaga / EMT",
        source_url=(
            "https://www.malaga.eu/visorcontenido/"
            "ANUDocumentDisplayer/178782/COMUNICADO.pdf"
        ),
        supporting_source_urls=(
            "https://www.malaga.eu/visorcontenido/NRMDocumentDisplayer/676/"
            "DocumentoNormativa676",
        ),
        observed_at=datetime(2026, 1, 11, tzinfo=UTC),
        valid_until=_end_of_2026(),
        fare_scope="EMT Málaga urban bus network",
    ),
    "bilbao": TransportFare(
        city_key="bilbao",
        product_name="Bidai Oro - 1 zone",
        monthly_amount_eur=30.25,
        calculation_type="30_day_pass",
        calculation_summary=(
            "One adult 30-day one-zone multimodal pass with unlimited journeys."
        ),
        modes_available=(
            "Bilbobus",
            "Bizkaibus",
            "Metro Bilbao",
            "Euskotren",
            "Bilbao tram",
            "Funiculars",
        ),
        modes_included=(
            "Bilbobus",
            "Bizkaibus",
            "Metro Bilbao",
            "Euskotren",
            "Bilbao tram",
            "Funiculars",
        ),
        source_name="Consorcio de Transportes de Bizkaia",
        source_url="https://www.ctb.eus/es/tarifas_2022",
        supporting_source_urls=("https://www.ctb.eus/es/tarifas-barik",),
        observed_at=datetime(2026, 2, 21, tzinfo=UTC),
        valid_until=_end_of_2026(),
        fare_scope="One Barik fare zone",
    ),
    "alicante": TransportFare(
        city_key="alicante",
        product_name="TAM Bono 30 días - Zone A",
        monthly_amount_eur=24.00,
        base_monthly_amount_eur=40.00,
        subsidy_percent=40,
        calculation_type="30_day_pass",
        calculation_summary=(
            "One adult 30-day Zone A pass with unlimited integrated journeys."
        ),
        modes_available=("Urban bus", "Interurban TAM bus", "TRAM d'Alacant"),
        modes_included=("Urban bus", "Interurban TAM bus", "TRAM d'Alacant"),
        source_name="Ayuntamiento de Alicante / TAM",
        source_url=(
            "https://www.alicante.es/es/noticias/"
            "alicante-amplia-final-ano-gratuidad-del-autobus-urbano-14-anos"
        ),
        observed_at=datetime(2026, 6, 11, tzinfo=UTC),
        valid_until=_end_of_2026(),
        fare_scope="TAM Zone A",
    ),
}


def transport_fare_for_city(city_key: str) -> TransportFare:
    return TRANSPORT_FARES[city_key]


def transport_fare_catalog() -> list[dict]:
    return [
        {
            "city_key": fare.city_key,
            "monthly_amount_eur": fare.monthly_amount_eur,
            **fare.details(),
            "source_name": fare.source_name,
            "source_url": fare.source_url,
            "observed_at": fare.observed_at,
        }
        for fare in TRANSPORT_FARES.values()
    ]


def public_transport_assumption(details: dict) -> str:
    product = details.get("product_name", "published adult transport fare")
    summary = details.get("calculation_summary", "")
    return f"Public transport uses {product}: {summary}"
