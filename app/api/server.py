#!/usr/bin/env python3
"""Dependency-free local API for the SellerOps Agent MVP.

This prototype intentionally uses only Python stdlib so Milestone 1 can run
without package installation. The API shape is kept close to the future
FastAPI service: cases, analyses, review decisions, and action logs.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = ROOT / "app" / "web"
DB_PATH = ROOT / "data" / "sellerops.db"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def row_to_dict(row: sqlite3.Row) -> dict:
    item = dict(row)
    for key in ("risk_labels", "metadata_json", "request_payload_json", "response_payload_json"):
        if key in item and item[key]:
            item[key] = json.loads(item[key])
    return item


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
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
            """
        )


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


@dataclass
class MockAnalysis:
    category: str
    severity: str
    sentiment: str
    risk_score: int
    risk_labels: list[str]
    policy_basis: str
    reason: str
    suggested_action: str
    suggested_owner: str
    reply_draft: str
    confidence_score: float
    requires_human_review: bool


def mock_analyze(case: dict, template_type: str) -> MockAnalysis:
    text = f"{case.get('title', '')} {case.get('message', '')}".lower()
    labels: list[str] = []
    score = 22
    category = "general_support"
    action = "reply_draft"
    owner = "support"
    sentiment = "neutral"
    severity = "low"

    def has(*words: str) -> bool:
        return any(word in text for word in words)

    if has("refund", "chargeback", "money back", "cancel order", "退款", "退货"):
        category = "refund_request"
        action = "refund_review"
        owner = "support_lead"
        labels.extend(["refund_policy_sensitive", "needs_human_escalation"])
        score += 34
    if has("late", "delay", "delayed", "tracking", "lost", "shipping", "物流", "延误"):
        category = "logistics_delay" if category == "general_support" else category
        labels.append("logistics_delay")
        score += 18
    if has("broken", "damaged", "defect", "quality", "doesn't work", "bug", "crash", "错误"):
        category = "product_quality_issue" if template_type == "seller_support" else "bug_report"
        labels.append("product_quality_issue")
        score += 20
    if has("angry", "terrible", "scam", "lawsuit", "never again", "hate", "投诉", "欺骗"):
        sentiment = "angry"
        labels.extend(["angry_customer", "churn_risk"])
        score += 25
    elif has("urgent", "asap", "immediately", "critical", "blocked", "紧急"):
        sentiment = "urgent"
        labels.append("needs_human_escalation")
        score += 18
    elif has("thanks", "love", "great", "works well"):
        sentiment = "positive"
        score -= 8
    else:
        sentiment = "negative" if score >= 45 else "neutral"

    if has("twitter", "tiktok", "reddit", "review", "public", "viral", "曝光"):
        labels.append("public_complaint_risk")
        score += 20
    if has("password", "ssn", "credit card", "api key", "token", "credential"):
        labels.append("pii_detected")
        score += 18
    if has("feature request", "would like", "can you add", "support for", "please add"):
        category = "feature_request"
        action = "create_issue"
        owner = "product"
        score += 8
    if has("docs", "documentation", "tutorial", "setup"):
        category = "documentation_gap"
        action = "create_issue"
        owner = "product"
        score += 8

    score = max(0, min(score, 100))
    if score >= 80:
        severity = "critical"
    elif score >= 60:
        severity = "high"
    elif score >= 35:
        severity = "medium"
    else:
        severity = "low"

    labels = sorted(set(labels or ["routine_support"]))
    requires_review = score >= 45 or action in {"refund_review", "create_issue"} or "pii_detected" in labels
    confidence = 0.84 if category != "general_support" else 0.68
    policy_basis = (
        "Refunds, external replies, and public escalations require human approval."
        if requires_review
        else "Low-risk support cases can be drafted for review."
    )
    reason = f"Detected {category.replace('_', ' ')} with risk labels: {', '.join(labels)}."

    name = case.get("customer_name") or "there"
    reply = (
        f"Hi {name}, thanks for reaching out. I understand the issue and have flagged it for review. "
        "Our team will confirm the next step before taking action."
    )
    if action == "refund_review":
        reply = (
            f"Hi {name}, sorry about the trouble. I am checking the order details and refund policy now. "
            "A teammate will review this before any refund action is taken."
        )

    return MockAnalysis(
        category=category,
        severity=severity,
        sentiment=sentiment,
        risk_score=score,
        risk_labels=labels,
        policy_basis=policy_basis,
        reason=reason,
        suggested_action=action,
        suggested_owner=owner,
        reply_draft=reply,
        confidence_score=confidence,
        requires_human_review=requires_review,
    )


def insert_case_and_analysis(row: dict, template_type: str, source_type: str) -> int:
    title = row.get("title") or row.get("category") or row.get("issue") or "Imported case"
    message = row.get("message") or row.get("body") or row.get("notes") or title
    amount = None
    if row.get("amount"):
        try:
            amount = float(re.sub(r"[^0-9.]", "", row["amount"]))
        except ValueError:
            amount = None
    metadata = {k: v for k, v in row.items() if k not in {
        "title", "message", "customer_name", "customer_email", "order_id",
        "amount", "currency", "product_name", "status", "created_at",
    }}
    now = utc_now()
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO cases (
              template_type, source_type, source_id, title, message, customer_name,
              customer_email, order_id, amount, currency, product_name, status,
              owner, created_at, imported_at, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                template_type,
                source_type,
                row.get("source_id") or row.get("id") or "",
                title,
                message,
                row.get("customer_name") or "",
                row.get("customer_email") or "",
                row.get("order_id") or "",
                amount,
                row.get("currency") or "USD",
                row.get("product_name") or "",
                row.get("status") or "new",
                "",
                row.get("created_at") or now,
                now,
                json.dumps(metadata),
            ),
        )
        case_id = int(cursor.lastrowid)
        case = dict(row)
        case["title"] = title
        case["message"] = message
        analysis = mock_analyze(case, template_type)
        conn.execute(
            """
            INSERT INTO case_analyses (
              case_id, category, severity, sentiment, risk_score, risk_labels,
              policy_basis, reason, suggested_action, suggested_owner, reply_draft,
              confidence_score, requires_human_review, model_name, prompt_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                analysis.category,
                analysis.severity,
                analysis.sentiment,
                analysis.risk_score,
                json.dumps(analysis.risk_labels),
                analysis.policy_basis,
                analysis.reason,
                analysis.suggested_action,
                analysis.suggested_owner,
                analysis.reply_draft,
                analysis.confidence_score,
                int(analysis.requires_human_review),
                "mock-triage-v0",
                "sellerops-mock-v1",
                now,
            ),
        )
        return case_id


def latest_cases(review_only: bool = False) -> list[dict]:
    where = "WHERE a.requires_human_review = 1 AND c.status NOT IN ('approved', 'rejected')" if review_only else ""
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT
              c.*, a.id AS analysis_id, a.category, a.severity, a.sentiment,
              a.risk_score, a.risk_labels, a.policy_basis, a.reason,
              a.suggested_action, a.suggested_owner, a.reply_draft,
              a.confidence_score, a.requires_human_review, a.created_at AS analyzed_at
            FROM cases c
            JOIN case_analyses a ON a.case_id = c.id
            JOIN (
              SELECT case_id, MAX(id) AS max_analysis_id
              FROM case_analyses
              GROUP BY case_id
            ) latest ON latest.case_id = c.id AND latest.max_analysis_id = a.id
            {where}
            ORDER BY c.imported_at DESC, c.id DESC
            """
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def audit_logs() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT l.*, c.title, c.template_type
            FROM action_logs l
            JOIN cases c ON c.id = l.case_id
            ORDER BY l.executed_at DESC, l.id DESC
            """
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def create_review(payload: dict) -> dict:
    now = utc_now()
    case_id = int(payload["case_id"])
    analysis_id = int(payload["analysis_id"])
    decision = payload.get("decision", "approve")
    corrected_action = payload.get("corrected_action") or payload.get("suggested_action") or "reply_draft"
    corrected_owner = payload.get("corrected_owner") or ""
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO review_decisions (
              case_id, analysis_id, reviewer_id, decision, corrected_category,
              corrected_severity, corrected_risk_score, corrected_risk_labels,
              corrected_action, corrected_owner, corrected_reply, correction_reason,
              add_to_eval_dataset, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                analysis_id,
                payload.get("reviewer_id") or "local-reviewer",
                decision,
                payload.get("corrected_category") or "",
                payload.get("corrected_severity") or "",
                payload.get("corrected_risk_score") or None,
                json.dumps(payload.get("corrected_risk_labels") or []),
                corrected_action,
                corrected_owner,
                payload.get("corrected_reply") or "",
                payload.get("correction_reason") or "",
                int(bool(payload.get("add_to_eval_dataset"))),
                now,
            ),
        )
        decision_id = int(cursor.lastrowid)
        status = "approved" if decision == "approve" else "rejected"
        conn.execute("UPDATE cases SET status = ?, owner = ? WHERE id = ?", (status, corrected_owner, case_id))
        conn.execute(
            """
            INSERT INTO action_logs (
              case_id, decision_id, action_type, status, request_payload_json,
              response_payload_json, executed_by, executed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                decision_id,
                corrected_action,
                "executed" if decision == "approve" else "skipped",
                json.dumps(payload),
                json.dumps({"message": f"{corrected_action} {status} in local MVP"}),
                payload.get("reviewer_id") or "local-reviewer",
                now,
            ),
        )
    return {"decision_id": decision_id, "status": status}


class SellerOpsHandler(BaseHTTPRequestHandler):
    server_version = "SellerOpsLocal/0.1"

    def log_message(self, fmt: str, *args) -> None:
        print(f"[{utc_now()}] {self.address_string()} {fmt % args}")

    def send_json(self, data: object, status: int = 200) -> None:
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(raw or "{}")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/health":
            self.send_json({"ok": True, "time": utc_now()})
            return
        if path == "/api/cases":
            self.send_json({"cases": latest_cases(False)})
            return
        if path == "/api/review-queue":
            self.send_json({"cases": latest_cases(True)})
            return
        if path == "/api/audit":
            self.send_json({"logs": audit_logs()})
            return
        if path == "/api/samples":
            samples = []
            for file in (ROOT / "samples").glob("*/*.csv"):
                samples.append({"name": file.stem, "path": str(file.relative_to(ROOT)), "text": file.read_text()})
            self.send_json({"samples": samples})
            return
        self.serve_static(path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            payload = self.read_json()
            if path == "/api/import/csv":
                rows = parse_csv_text(payload.get("csv_text", ""))
                template_type = payload.get("template_type") or "seller_support"
                source_type = payload.get("source_type") or "csv"
                ids = [insert_case_and_analysis(row, template_type, source_type) for row in rows]
                self.send_json({"imported": len(ids), "case_ids": ids}, HTTPStatus.CREATED)
                return
            if path == "/api/reviews":
                self.send_json(create_review(payload), HTTPStatus.CREATED)
                return
            self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except Exception as exc:  # keep local MVP debuggable
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def serve_static(self, path: str) -> None:
        rel = "index.html" if path in {"/", ""} else path.lstrip("/")
        file_path = (WEB_ROOT / rel).resolve()
        if not str(file_path).startswith(str(WEB_ROOT.resolve())) or not file_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = "text/plain"
        if file_path.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        elif file_path.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif file_path.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        body = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    init_db()
    host = "127.0.0.1"
    port = int(os.environ.get("SELLEROPS_PORT", "8000"))
    httpd = ThreadingHTTPServer((host, port), SellerOpsHandler)
    print(f"SellerOps Agent local MVP running at http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
