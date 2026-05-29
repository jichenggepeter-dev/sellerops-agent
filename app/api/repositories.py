"""Repository helpers for SellerOps persistence.

This module centralizes SQL so service modules can stay focused on workflow
logic. It deliberately keeps explicit SQL for now while the table models and
Alembic migrations stabilize.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.api.db import connect, row_to_dict


def fetch_one(query: str, params: Sequence[Any] = ()) -> dict | None:
    with connect() as conn:
        row = conn.execute(query, params).fetchone()
    return row_to_dict(row) if row else None


def fetch_all(query: str, params: Sequence[Any] = ()) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [row_to_dict(row) for row in rows]


def execute_insert(query: str, params: Sequence[Any] = ()) -> int:
    with connect() as conn:
        cursor = conn.execute(query, params)
        return int(cursor.lastrowid)


def execute_write(query: str, params: Sequence[Any] = ()) -> None:
    with connect() as conn:
        conn.execute(query, params)

