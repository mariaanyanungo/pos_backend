import pytest
from sqlalchemy import text

import database


def test_get_database_url_reads_the_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./somewhere.db")
    assert database.get_database_url() == "sqlite:///./somewhere.db"


def test_get_database_url_fails_loudly_when_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="DATABASE_URL"):
        database.get_database_url()


def test_build_engine_for_in_memory_sqlite_shares_one_connection_and_enforces_foreign_keys():
    engine = database.build_engine("sqlite://")
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1
        connection.execute(text("CREATE TABLE t (id INTEGER)"))
    with engine.connect() as connection:  # still the same in-memory database
        assert connection.execute(text("SELECT count(*) FROM t")).scalar() == 0


def test_build_engine_defaults_to_the_configured_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    assert database.build_engine().dialect.name == "sqlite"