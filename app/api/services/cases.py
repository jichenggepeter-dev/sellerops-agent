"""Case, review, and audit persistence services."""

from __future__ import annotations

import json
import re

from app.api.repositories import execute_insert, execute_write, fetch_all, fetch_one
from app.api.config import get_settings
from app.api.services.connectors import execute_action, preview_action
from app.api.services.triage import MockTriageProvider, TriageResult
from app.api.services.triage_registry import get_triage_provider
from app.api.services.policies import active_policy_context
from app.api.time_utils import utc_now


def insert_case_and_analysis(
    row: dict,
    template_type: str,
    source_type: str,
    workspace_id: str = "default",
) -> int:
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
          workspace_id, template_type, source_type, source_id, title, message, customer_name,
          customer_email, order_id, amount, currency, product_name, status,
          owner, created_at, imported_at, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            workspace_id,
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
    analysis = analyze_case_safely(case, template_type, policy_context)
    execute_insert(
        """
        INSERT INTO case_analyses (
          case_id, category, severity, sentiment, risk_score, risk_labels,
          policy_basis, reason, suggested_action, suggested_owner, reply_draft,
          confidence_score, requires_human_review, model_name, prompt_version,
          analysis_status, provider_name, failure_reason, fallback_used, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            analysis.analysis_status,
            analysis.provider_name,
            analysis.failure_reason,
            int(analysis.fallback_used),
            now,
        ),
    )
    next_status = "needs_review" if analysis.requires_human_review else "analyzed"
    execute_write("UPDATE cases SET status = ? WHERE id = ?", (next_status, case_id))
    return case_id


def analyze_case_safely(case: dict, template_type: str, policy_context: str) -> TriageResult:
    try:
        provider = get_triage_provider()
    except Exception as exc:
        return failed_triage_result(
            provider_name=get_settings().triage_provider,
            failure_reason=str(exc),
        )
    try:
        return provider.analyze(case, template_type, policy_context)
    except Exception as exc:
        failure_reason = str(exc)
        if provider.name != "mock" and get_settings().triage_fallback_to_mock:
            try:
                fallback = MockTriageProvider().analyze(case, template_type, policy_context)
                fallback.analysis_status = "fallback_used"
                fallback.provider_name = provider.name
                fallback.failure_reason = failure_reason
                fallback.fallback_used = True
                fallback.requires_human_review = True
                fallback.risk_labels = sorted(set([*fallback.risk_labels, "ai_provider_failed"]))
                fallback.policy_basis = f"{fallback.policy_basis} AI provider failed; human review required."
                return fallback
            except Exception as fallback_exc:
                failure_reason = f"{failure_reason}; fallback failed: {fallback_exc}"
        return failed_triage_result(
            provider_name=provider.name,
            failure_reason=failure_reason,
            model_name=getattr(provider, "model_name", provider.name),
            prompt_version=getattr(provider, "prompt_version", "unknown"),
        )


def failed_triage_result(
    provider_name: str,
    failure_reason: str,
    model_name: str | None = None,
    prompt_version: str = "unknown",
) -> TriageResult:
    return TriageResult(
        category="analysis_failed",
        severity="high",
        sentiment="unknown",
        risk_score=75,
        risk_labels=["ai_provider_failed", "needs_human_escalation"],
        policy_basis="AI analysis failed. Human review is required before any action.",
        reason="The triage provider failed before producing a validated analysis.",
        suggested_action="manual_review",
        suggested_owner="support_lead",
        reply_draft="",
        confidence_score=0.0,
        requires_human_review=True,
        model_name=model_name or provider_name,
        prompt_version=prompt_version,
        analysis_status="failed",
        provider_name=provider_name,
        failure_reason=failure_reason,
    )


def latest_cases(review_only: bool = False) -> list[dict]:
    where = (
        "WHERE a.requires_human_review = 1 "
        "AND c.status NOT IN ('approved', 'rejected', 'action_executed', 'action_failed')"
        if review_only
        else ""
    )
    return fetch_all(
        f"""
        SELECT
          c.*, a.id AS analysis_id, a.category, a.severity, a.sentiment,
          a.risk_score, a.risk_labels, a.policy_basis, a.reason,
          a.suggested_action, a.suggested_owner, a.reply_draft,
          a.confidence_score, a.requires_human_review, a.analysis_status,
          a.provider_name, a.failure_reason, a.fallback_used, a.created_at AS analyzed_at
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


def preview_review_action(payload: dict) -> dict:
    case_id = int(payload["case_id"])
    analysis_id = int(payload["analysis_id"])
    case = fetch_one("SELECT * FROM cases WHERE id = ?", (case_id,))
    if not case:
        raise ValueError(f"Case {case_id} was not found.")
    analysis = fetch_one("SELECT * FROM case_analyses WHERE id = ? AND case_id = ?", (analysis_id, case_id))
    if not analysis:
        raise ValueError(f"Analysis {analysis_id} was not found for case {case_id}.")
    action_type = payload.get("corrected_action") or analysis.get("suggested_action") or "reply_draft"
    preview_payload = {
        **payload,
        "corrected_category": payload.get("corrected_category") or analysis.get("category"),
        "corrected_severity": payload.get("corrected_severity") or analysis.get("severity"),
        "corrected_risk_score": payload.get("corrected_risk_score") or analysis.get("risk_score"),
        "corrected_action": action_type,
        "corrected_owner": payload.get("corrected_owner") or analysis.get("suggested_owner"),
        "corrected_reply": payload.get("corrected_reply") or analysis.get("reply_draft"),
    }
    return {
        "case_id": case_id,
        "analysis_id": analysis_id,
        "case_status": case.get("status"),
        "decision": payload.get("decision", "approve"),
        "preview": preview_action(action_type, preview_payload, case),
    }


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
    execution = (
        execute_action(corrected_action, payload, case)
        if decision == "approve"
        else {"status": "skipped", "response": {"message": f"{corrected_action} rejected in review"}}
    )
    status = review_case_status(decision=decision, execution_status=execution["status"])
    execute_write(
        "UPDATE cases SET status = ?, owner = ? WHERE id = ?",
        (status, corrected_owner, case_id),
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


def review_case_status(decision: str, execution_status: str) -> str:
    if decision != "approve":
        return "rejected"
    if execution_status == "executed":
        return "action_executed"
    if execution_status == "failed":
        return "action_failed"
    return "approved"
