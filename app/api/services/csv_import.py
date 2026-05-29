"""CSV parsing and header normalization."""

from __future__ import annotations

import csv
import re


def normalize_header(name: str) -> str:
    key = name.strip().lower()
    key = re.sub(r"[^a-z0-9]+", "_", key).strip("_")
    aliases = {
        "email": "customer_email",
        "customer": "customer_name",
        "name": "customer_name",
        "body": "message",
        "description": "message",
        "content": "message",
        "subject": "title",
        "issue_title": "title",
        "order": "order_id",
        "order_number": "order_id",
        "product": "product_name",
        "price": "amount",
    }
    return aliases.get(key, key)


def parse_csv_text(csv_text: str) -> list[dict]:
    csv_text = csv_text.strip("\ufeff\n ")
    if not csv_text:
        return []
    reader = csv.DictReader(csv_text.splitlines())
    rows: list[dict] = []
    for raw in reader:
        row = {normalize_header(k or ""): (v or "").strip() for k, v in raw.items()}
        rows.append(row)
    return rows

