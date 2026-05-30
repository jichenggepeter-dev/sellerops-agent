"""Database helpers for the local MVP and production database path."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from functools import lru_cache
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, RowMapping

from app.api.config import ROOT, get_settings


JSON_COLUMNS = {
    "risk_labels",
    "metadata_json",
    "request_payload_json",
    "response_payload_json",
    "ai_value_json",
    "human_value_json",
}


def connect() -> sqlite3.Connection:
    if not get_settings().uses_sqlite:
        raise RuntimeError("sqlite connect() is only available when using a SQLite database URL.")
    db_path = get_settings().database_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row: sqlite3.Row | RowMapping) -> dict:
    item = dict(row)
    for key in JSON_COLUMNS:
        if key in item and item[key]:
            item[key] = json.loads(item[key])
    return item


def init_db() -> None:
    if run_migrations():
        return
    if not get_settings().uses_sqlite:
        raise RuntimeError("Alembic migrations are required for non-SQLite databases.")
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS cases (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              workspace_id TEXT NOT NULL DEFAULT 'default',
              template_type TEXT NOT NULL,
              source_type TEXT NOT NULL,
              source_id TEXT,
              title TEXT NOT NULL,
              message TEXT NOT NULL,
              customer_name TEXT,
              customer_email TEXT,
              order_id TEXT,
              amount REAL,
              currency TEXT,
              product_name TEXT,
              status TEXT DEFAULT 'new',
              owner TEXT,
              created_at TEXT,
              imported_at TEXT NOT NULL,
              metadata_json TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS case_analyses (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              case_id INTEGER NOT NULL,
              category TEXT NOT NULL,
              severity TEXT NOT NULL,
              sentiment TEXT NOT NULL,
              risk_score INTEGER NOT NULL,
              risk_labels TEXT NOT NULL,
              policy_basis TEXT NOT NULL,
              reason TEXT NOT NULL,
              suggested_action TEXT NOT NULL,
              suggested_owner TEXT NOT NULL,
              reply_draft TEXT,
              confidence_score REAL NOT NULL,
              requires_human_review INTEGER NOT NULL,
              model_name TEXT NOT NULL,
              prompt_version TEXT NOT NULL,
              analysis_status TEXT NOT NULL DEFAULT 'succeeded',
              provider_name TEXT,
              failure_reason TEXT,
              fallback_used INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL,
              FOREIGN KEY(case_id) REFERENCES cases(id)
            );

            CREATE TABLE IF NOT EXISTS review_decisions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              case_id INTEGER NOT NULL,
              analysis_id INTEGER NOT NULL,
              reviewer_id TEXT NOT NULL,
              decision TEXT NOT NULL,
              corrected_category TEXT,
              corrected_severity TEXT,
              corrected_risk_score INTEGER,
              corrected_risk_labels TEXT,
              corrected_action TEXT,
              corrected_owner TEXT,
              corrected_reply TEXT,
              correction_reason TEXT,
              add_to_eval_dataset INTEGER NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(case_id) REFERENCES cases(id),
              FOREIGN KEY(analysis_id) REFERENCES case_analyses(id)
            );

            CREATE TABLE IF NOT EXISTS review_edit_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              review_id INTEGER NOT NULL,
              case_id INTEGER NOT NULL,
              analysis_id INTEGER NOT NULL,
              field_name TEXT NOT NULL,
              ai_value_json TEXT NOT NULL,
              human_value_json TEXT NOT NULL,
              changed INTEGER NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(review_id) REFERENCES review_decisions(id),
              FOREIGN KEY(case_id) REFERENCES cases(id),
              FOREIGN KEY(analysis_id) REFERENCES case_analyses(id)
            );

            CREATE TABLE IF NOT EXISTS action_logs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              case_id INTEGER NOT NULL,
              decision_id INTEGER,
              action_type TEXT NOT NULL,
              status TEXT NOT NULL,
              request_payload_json TEXT NOT NULL,
              response_payload_json TEXT NOT NULL,
              executed_by TEXT NOT NULL,
              executed_at TEXT NOT NULL,
              FOREIGN KEY(case_id) REFERENCES cases(id),
              FOREIGN KEY(decision_id) REFERENCES review_decisions(id)
            );

            CREATE TABLE IF NOT EXISTS policies (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              workspace_id TEXT NOT NULL DEFAULT 'default',
              template_type TEXT NOT NULL,
              policy_type TEXT NOT NULL,
              name TEXT NOT NULL,
              body TEXT NOT NULL,
              version INTEGER NOT NULL DEFAULT 1,
              active INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            """
        )


def run_migrations() -> bool:
    try:
        from alembic import command
        from alembic.config import Config
    except ImportError:
        return False

    alembic_ini = ROOT / "alembic.ini"
    if not alembic_ini.exists():
        return False

    config = Config(str(alembic_ini))
    stamp_legacy_sqlite_schema(config)
    command.upgrade(config, "head")
    return True


def stamp_legacy_sqlite_schema(config) -> None:
    settings = get_settings()
    if not settings.uses_sqlite or not settings.database_path.exists():
        return
    with sqlite3.connect(settings.database_path) as conn:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
    if "cases" not in tables:
        return
    if "alembic_version" in tables:
        with sqlite3.connect(settings.database_path) as conn:
            current = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        if current is not None:
            return
    from alembic import command

    command.stamp(config, "0001_initial_schema")


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().sqlalchemy_database_url, future=True)


def reset_engine_cache() -> None:
    get_engine.cache_clear()


def bind_query(query: str, params: Sequence[Any]) -> tuple[str, dict[str, Any]]:
    if not params:
        return query, {}
    parts = query.split("?")
    if len(parts) - 1 != len(params):
        raise ValueError("SQL parameter count does not match placeholder count.")
    named_params = {f"p{index}": value for index, value in enumerate(params)}
    bound_query = parts[0]
    for index, part in enumerate(parts[1:]):
        bound_query += f":p{index}{part}"
    return bound_query, named_params


def fetch_one_sqlalchemy(query: str, params: Sequence[Any] = ()) -> dict | None:
    bound_query, named_params = bind_query(query, params)
    with get_engine().connect() as conn:
        row = conn.execute(text(bound_query), named_params).mappings().fetchone()
    return row_to_dict(row) if row else None


def fetch_all_sqlalchemy(query: str, params: Sequence[Any] = ()) -> list[dict]:
    bound_query, named_params = bind_query(query, params)
    with get_engine().connect() as conn:
        rows = conn.execute(text(bound_query), named_params).mappings().fetchall()
    return [row_to_dict(row) for row in rows]


def execute_insert_sqlalchemy(query: str, params: Sequence[Any] = ()) -> int:
    bound_query, named_params = bind_query(query, params)
    if " returning " not in bound_query.lower():
        bound_query = f"{bound_query.rstrip()} RETURNING id"
    with get_engine().begin() as conn:
        row = conn.execute(text(bound_query), named_params).mappings().fetchone()
    if not row or "id" not in row:
        raise RuntimeError("Insert did not return an id.")
    return int(row["id"])


def execute_write_sqlalchemy(query: str, params: Sequence[Any] = ()) -> None:
    bound_query, named_params = bind_query(query, params)
    with get_engine().begin() as conn:
        conn.execute(text(bound_query), named_params)
