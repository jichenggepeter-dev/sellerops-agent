"""Review quality metrics and eval export services."""

from __future__ import annotations

from app.api.repositories import fetch_all


def review_quality_metrics() -> dict:
    rows = fetch_all(
        """
        SELECT
          rd.*,
          ca.category AS ai_category,
          ca.severity AS ai_severity,
          ca.risk_score AS ai_risk_score,
          ca.suggested_action AS ai_action,
          ca.suggested_owner AS ai_owner,
          ca.reply_draft AS ai_reply
        FROM review_decisions rd
        JOIN case_analyses ca ON ca.id = rd.analysis_id
        """
    )

    total = len(rows)
    approved = sum(1 for row in rows if row["decision"] == "approve")
    rejected = sum(1 for row in rows if row["decision"] == "reject")
    edited = 0
    category_corrections = 0
    severity_corrections = 0
    risk_score_corrections = 0
    action_corrections = 0
    owner_corrections = 0
    reply_corrections = 0
    eval_cases = 0

    for row in rows:
        category_changed = bool(row["corrected_category"]) and row["corrected_category"] != row["ai_category"]
        severity_changed = bool(row["corrected_severity"]) and row["corrected_severity"] != row["ai_severity"]
        risk_changed = row["corrected_risk_score"] is not None and int(row["corrected_risk_score"]) != int(row["ai_risk_score"])
        action_changed = bool(row["corrected_action"]) and row["corrected_action"] != row["ai_action"]
        owner_changed = bool(row["corrected_owner"]) and row["corrected_owner"] != row["ai_owner"]
        reply_changed = bool(row["corrected_reply"]) and row["corrected_reply"] != (row["ai_reply"] or "")
        if any([category_changed, severity_changed, risk_changed, action_changed, owner_changed, reply_changed]):
            edited += 1
        category_corrections += int(category_changed)
        severity_corrections += int(severity_changed)
        risk_score_corrections += int(risk_changed)
        action_corrections += int(action_changed)
        owner_corrections += int(owner_changed)
        reply_corrections += int(reply_changed)
        eval_cases += int(bool(row["add_to_eval_dataset"]))

    def rate(count: int) -> float:
        return round(count / total, 4) if total else 0.0

    return {
        "total_reviews": total,
        "approved": approved,
        "rejected": rejected,
        "edited": edited,
        "approval_rate": rate(approved),
        "rejection_rate": rate(rejected),
        "edit_rate": rate(edited),
        "category_correction_rate": rate(category_corrections),
        "severity_correction_rate": rate(severity_corrections),
        "risk_score_correction_rate": rate(risk_score_corrections),
        "action_correction_rate": rate(action_corrections),
        "owner_correction_rate": rate(owner_corrections),
        "reply_correction_rate": rate(reply_corrections),
        "eval_cases": eval_cases,
    }


def export_eval_examples() -> list[dict]:
    rows = fetch_all(
        """
        SELECT
          c.*,
          ca.id AS analysis_id,
          ca.category AS ai_category,
          ca.severity AS ai_severity,
          ca.sentiment AS ai_sentiment,
          ca.risk_score AS ai_risk_score,
          ca.risk_labels AS ai_risk_labels,
          ca.policy_basis AS ai_policy_basis,
          ca.reason AS ai_reason,
          ca.suggested_action AS ai_action,
          ca.suggested_owner AS ai_owner,
          ca.reply_draft AS ai_reply,
          ca.confidence_score AS ai_confidence_score,
          ca.requires_human_review AS ai_requires_human_review,
          ca.model_name,
          ca.prompt_version,
          rd.id AS review_id,
          rd.decision,
          rd.corrected_category,
          rd.corrected_severity,
          rd.corrected_risk_score,
          rd.corrected_risk_labels,
          rd.corrected_action,
          rd.corrected_owner,
          rd.corrected_reply,
          rd.correction_reason,
          rd.created_at AS reviewed_at
        FROM review_decisions rd
        JOIN cases c ON c.id = rd.case_id
        JOIN case_analyses ca ON ca.id = rd.analysis_id
        WHERE rd.add_to_eval_dataset = 1
        ORDER BY rd.created_at DESC, rd.id DESC
        """
    )

    examples = []
    for row in rows:
        item = row
        examples.append(
            {
                "case": {
                    "id": item["id"],
                    "template_type": item["template_type"],
                    "source_type": item["source_type"],
                    "title": item["title"],
                    "message": item["message"],
                    "customer_name": item["customer_name"],
                    "order_id": item["order_id"],
                    "amount": item["amount"],
                    "product_name": item["product_name"],
                    "metadata": item["metadata_json"],
                },
                "ai_output": {
                    "analysis_id": item["analysis_id"],
                    "category": item["ai_category"],
                    "severity": item["ai_severity"],
                    "sentiment": item["ai_sentiment"],
                    "risk_score": item["ai_risk_score"],
                    "risk_labels": item["ai_risk_labels"],
                    "policy_basis": item["ai_policy_basis"],
                    "reason": item["ai_reason"],
                    "suggested_action": item["ai_action"],
                    "suggested_owner": item["ai_owner"],
                    "reply_draft": item["ai_reply"],
                    "confidence_score": item["ai_confidence_score"],
                    "requires_human_review": bool(item["ai_requires_human_review"]),
                    "model_name": item["model_name"],
                    "prompt_version": item["prompt_version"],
                },
                "human_correction": {
                    "review_id": item["review_id"],
                    "decision": item["decision"],
                    "category": item["corrected_category"],
                    "severity": item["corrected_severity"],
                    "risk_score": item["corrected_risk_score"],
                    "risk_labels": item["corrected_risk_labels"],
                    "action": item["corrected_action"],
                    "owner": item["corrected_owner"],
                    "reply": item["corrected_reply"],
                    "reason": item["correction_reason"],
                    "reviewed_at": item["reviewed_at"],
                },
            }
        )
    return examples
