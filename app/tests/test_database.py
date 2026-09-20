import pytest
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from database import build_engine, get_database_url, get_db


def test_get_database_url_returns_env_value(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    assert get_database_url() == "sqlite://"


def test_get_database_url_strips_whitespace(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "  sqlite://  ")
    assert get_database_url() == "sqlite://"


def test_get_database_url_missing_raises(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="DATABASE_URL"):
        get_database_url()


def test_get_database_url_blank_raises(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "   ")
    with pytest.raises(ValueError, match="DATABASE_URL"):
        get_database_url()


def test_build_engine_sqlite_memory_uses_static_pool():
    engine = build_engine("sqlite://")
    try:
        assert isinstance(engine.pool, StaticPool)
    finally:
        engine.dispose()


def test_build_engine_sqlite_file_connects(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'pos.db'}")
    try:
        assert not isinstance(engine.pool, StaticPool)
        with engine.connect() as connection:
            assert connection is not None
    finally:
        engine.dispose()


def test_get_db_yields_session_and_closes_it(monkeypatch):
    calls = []
    generator = get_db()
    db = next(generator)
    assert isinstance(db, Session)

    monkeypatch.setattr(db, "close", lambda: calls.append("close"))
    generator.close()

    assert calls == ["close"]


def test_get_db_rolls_back_then_closes_and_reraises_on_error(monkeypatch):
    calls = []
    generator = get_db()
    db = next(generator)

    monkeypatch.setattr(db, "rollback", lambda: calls.append("rollback"))
    monkeypatch.setattr(db, "close", lambda: calls.append("close"))

    with pytest.raises(RuntimeError, match="boom"):
        generator.throw(RuntimeError("boom"))

    assert calls == ["rollback", "close"]