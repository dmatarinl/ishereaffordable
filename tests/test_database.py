from app.storage.database import _sqlalchemy_database_url


def test_postgresql_url_uses_psycopg_driver() -> None:
    assert (
        _sqlalchemy_database_url("postgresql://user:pass@example.com/db")
        == "postgresql+psycopg://user:pass@example.com/db"
    )


def test_postgres_url_uses_psycopg_driver() -> None:
    assert (
        _sqlalchemy_database_url("postgres://user:pass@example.com/db")
        == "postgresql+psycopg://user:pass@example.com/db"
    )


def test_sqlite_url_is_unchanged() -> None:
    assert _sqlalchemy_database_url("sqlite:///./data/app.db") == (
        "sqlite:///./data/app.db"
    )
