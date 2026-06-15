import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    delete,
    func,
    select,
    update,
)
from sqlalchemy.engine import Engine

from app.affordability.models import (
    Confidence,
    CostCategory,
    CostLineItem,
    SourceStatus,
)

metadata = MetaData()

cost_observations = Table(
    "cost_observations",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("city_key", String(80), nullable=False, index=True),
    Column("city", String(120), nullable=False),
    Column("country", String(80), nullable=False),
    Column("category", String(40), nullable=False, index=True),
    Column("label", String(120), nullable=False),
    Column("monthly_amount", Float, nullable=False),
    Column("currency", String(3), nullable=False),
    Column("source_name", String(180), nullable=False),
    Column("source_url", Text, nullable=False),
    Column("observed_at", DateTime(timezone=True), nullable=False),
    Column("confidence", String(20), nullable=False),
    Column("methodology", Text, nullable=False),
    Column("details_json", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

source_runs = Table(
    "source_runs",
    metadata,
    Column("source_id", String(120), primary_key=True),
    Column("source_name", String(180), nullable=False),
    Column("status", String(40), nullable=False),
    Column("last_started_at", DateTime(timezone=True), nullable=True),
    Column("last_finished_at", DateTime(timezone=True), nullable=True),
    Column("message", Text, nullable=True),
)


def create_database_engine(database_url: str) -> Engine:
    if database_url.startswith("sqlite:///"):
        sqlite_path = database_url.removeprefix("sqlite:///")
        if sqlite_path != ":memory:":
            Path(sqlite_path).expanduser().parent.mkdir(parents=True, exist_ok=True)

    return create_engine(database_url, future=True)


class CostObservationRepository:
    def __init__(self, database_url: str) -> None:
        self.engine = create_database_engine(database_url)

    def init_schema(self) -> None:
        metadata.create_all(self.engine)

    def has_any_observations(self) -> bool:
        with self.engine.begin() as connection:
            count = connection.execute(
                select(func.count()).select_from(cost_observations)
            ).scalar_one()
        return bool(count)

    def replace_city_observations(
        self,
        city_key: str,
        city: str,
        country: str,
        observations: Iterable[CostLineItem],
    ) -> None:
        now = datetime.now(UTC)
        rows = [
            {
                "city_key": city_key,
                "city": city,
                "country": country,
                "category": item.category.value,
                "label": item.label,
                "monthly_amount": item.monthly_amount,
                "currency": item.currency,
                "source_name": item.source_name,
                "source_url": item.source_url,
                "observed_at": item.observed_at,
                "confidence": item.confidence.value,
                "methodology": item.methodology,
                "details_json": json.dumps(item.details, sort_keys=True),
                "created_at": now,
            }
            for item in observations
        ]

        with self.engine.begin() as connection:
            connection.execute(
                delete(cost_observations).where(
                    cost_observations.c.city_key == city_key
                )
            )
            if rows:
                connection.execute(cost_observations.insert(), rows)

    def latest_city_observations(self, city_key: str) -> list[CostLineItem]:
        with self.engine.begin() as connection:
            records = connection.execute(
                select(cost_observations)
                .where(cost_observations.c.city_key == city_key)
                .order_by(
                    cost_observations.c.observed_at.desc(),
                    cost_observations.c.id.desc(),
                )
            ).mappings()
            latest_by_category = {}
            for record in records:
                latest_by_category.setdefault(record["category"], record)

        return [
            CostLineItem(
                category=CostCategory(record["category"]),
                label=record["label"],
                monthly_amount=record["monthly_amount"],
                currency=record["currency"],
                source_name=record["source_name"],
                source_url=record["source_url"],
                observed_at=_coerce_datetime(record["observed_at"]),
                confidence=Confidence(record["confidence"]),
                methodology=record["methodology"],
                details=json.loads(record["details_json"]),
            )
            for record in latest_by_category.values()
        ]

    def record_source_run(
        self,
        source_id: str,
        source_name: str,
        status: str,
        started_at: datetime,
        finished_at: datetime,
        message: str | None = None,
    ) -> None:
        with self.engine.begin() as connection:
            existing = connection.execute(
                select(source_runs.c.source_id).where(
                    source_runs.c.source_id == source_id
                )
            ).first()
            values = {
                "source_name": source_name,
                "status": status,
                "last_started_at": started_at,
                "last_finished_at": finished_at,
                "message": message,
            }
            if existing:
                connection.execute(
                    update(source_runs)
                    .where(source_runs.c.source_id == source_id)
                    .values(**values)
                )
            else:
                connection.execute(
                    source_runs.insert().values(source_id=source_id, **values)
                )

    def source_statuses(self) -> list[SourceStatus]:
        with self.engine.begin() as connection:
            records = connection.execute(
                select(source_runs).order_by(source_runs.c.source_name)
            ).mappings()
            return [
                SourceStatus(
                    source_id=record["source_id"],
                    source_name=record["source_name"],
                    status=record["status"],
                    last_started_at=_coerce_datetime_or_none(record["last_started_at"]),
                    last_finished_at=_coerce_datetime_or_none(
                        record["last_finished_at"]
                    ),
                    message=record["message"],
                )
                for record in records
            ]


def _coerce_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


def _coerce_datetime_or_none(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    return _coerce_datetime(value)
