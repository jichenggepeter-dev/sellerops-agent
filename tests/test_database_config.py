from __future__ import annotations

from app.api.config import get_settings, reset_settings_cache
from app.api.db import bind_query


def test_default_database_url_uses_sqlite(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("SELLEROPS_DATABASE_URL", raising=False)
    monkeypatch.setenv("SELLEROPS_DB_PATH", str(tmp_path / "sellerops.db"))
    reset_settings_cache()

    settings = get_settings()

    assert settings.uses_sqlite is True
    assert settings.sqlalchemy_database_url.startswith("sqlite:///")
    reset_settings_cache()


def test_postgres_database_url_uses_psycopg_driver(monkeypatch) -> None:
    monkeypatch.setenv("SELLEROPS_DATABASE_URL", "postgresql://sellerops:sellerops@localhost:5432/sellerops")
    reset_settings_cache()

    settings = get_settings()

    assert settings.uses_sqlite is False
    assert settings.sqlalchemy_database_url == "postgresql+psycopg://sellerops:sellerops@localhost:5432/sellerops"
    reset_settings_cache()


def test_bind_query_converts_positional_placeholders() -> None:
    query, params = bind_query("SELECT * FROM cases WHERE id = ? AND status = ?", (1, "new"))

    assert query == "SELECT * FROM cases WHERE id = :p0 AND status = :p1"
    assert params == {"p0": 1, "p1": "new"}
