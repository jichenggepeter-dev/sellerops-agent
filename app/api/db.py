"""SQLite persistence helpers for the local MVP."""

from __future__ import annotations

import json
import sqlite3

from app.api.config import ROOT, get_settings


JSON_COLUMNS = {
    "risk_labels",
    "metadata_json",
    "request_payload_json",
    "response_payload_json",
}


def connect() -> sqlite3.Connection:
    db_path = get_settings().database_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row: sqlite3.Row) -> dict:
    item = dict(row)
    for key in JSON_COLUMNS:
        if key in item and item[key]:
            item[key] = json.loads(item[key])
    return item


def init_db() -> None:
    if run_migrations():
        return
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS cases (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    command.upgrade(config, "head")
    return True
