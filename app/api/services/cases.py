"""Case, review, and audit persistence services."""

from __future__ import annotations

import json
import re

from app.api.repositories import execute_insert, execute_write, fetch_all, fetch_one
from app.api.services.connectors import execute_action
from app.api.services.triage_registry import get_triage_provider
from app.api.services.policies import active_policy_context
from app.api.time_utils import utc_now


def insert_case_and_analysis(row: dict, template_type: str, source_type: str) -> int:
    title = row.get("title") or row.get("category") or row.get("issue") or "Imported case"
    message = row.get("message") or row.get("body") or row.get("notes") or title
    amount = None
    if row.get("amount"):
        try:
            amount = float(re.sub(r"[^0-9.]", "", row["amount"]))
        except ValueError:
            amount = None
    metadata = {
        k: v
        for k, v in row.items()
        if k
        not in {
            "title",
            "message",
            "customer_name",
            "customer_email",
            "order_id",
            "amount",
            "currency",
            "product_name",
            "status",
            "created_at",
        }
    }
    now = utc_now()
    case_id = execute_insert(
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
    case = dict(row)
    case["title"] = title
    case["message"] = message
    policy_context = active_policy_context(template_type=template_type)
    analysis = get_triage_provider().analyze(case, template_type, policy_context)
    execute_insert(
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
            analysis.model_name,
            analysis.prompt_version,
            now,
        ),
    )
    return case_id


def latest_cases(review_only: bool = False) -> list[dict]:
    where = "WHERE a.requires_human_review = 1 AND c.status NOT IN ('approved', 'rejected')" if review_only else ""
    return fetch_all(
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
    )


def audit_logs() -> list[dict]:
    return fetch_all(
        """
        SELECT l.*, c.title, c.template_type
        FROM action_logs l
        JOIN cases c ON c.id = l.case_id
        ORDER BY l.executed_at DESC, l.id DESC
        """
    )


def create_review(payload: dict) -> dict:
    now = utc_now()
    case_id = int(payload["case_id"])
    analysis_id = int(payload["analysis_id"])
    decision = payload.get("decision", "approve")
    corrected_action = payload.get("corrected_action") or payload.get("suggested_action") or "reply_draft"
    corrected_owner = payload.get("corrected_owner") or ""
    case = fetch_one("SELECT * FROM cases WHERE id = ?", (case_id,)) or {}
    decision_id = execute_insert(
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
    status = "approved" if decision == "approve" else "rejected"
    execute_write(
        "UPDATE cases SET status = ?, owner = ? WHERE id = ?",
        (status, corrected_owner, case_id),
    )
    execution = (
        execute_action(corrected_action, payload, case)
        if decision == "approve"
        else {"status": "skipped", "response": {"message": f"{corrected_action} rejected in review"}}
    )
    execute_insert(
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
            execution["status"],
            json.dumps(payload),
            json.dumps(execution["response"]),
            payload.get("reviewer_id") or "local-reviewer",
            now,
        ),
    )
    return {"decision_id": decision_id, "status": status}
