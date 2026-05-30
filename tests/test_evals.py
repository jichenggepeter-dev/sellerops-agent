from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]


def test_review_quality_metrics_and_eval_export(client: TestClient) -> None:
    csv_text = (ROOT / "samples" / "seller-support" / "refund_requests.csv").read_text()
    import_response = client.post(
        "/api/import/csv",
        json={
            "template_type": "seller_support",
            "source_type": "csv",
            "csv_text": csv_text,
        },
    )
    assert import_response.status_code == 201

    review_case = next(
        case
        for case in client.get("/api/review-queue").json()["cases"]
        if case["title"] == "Refund request for delayed package"
    )
    approval_response = client.post(
        "/api/reviews",
        json={
            "case_id": review_case["id"],
            "analysis_id": review_case["analysis_id"],
            "decision": "approve",
            "corrected_category": "public_refund_escalation",
            "corrected_severity": "critical",
            "corrected_risk_score": 99,
            "corrected_action": "slack_escalation",
            "corrected_owner": "support_lead",
            "corrected_reply": "Escalating for support lead review before replying.",
            "correction_reason": "Public complaint risk needs escalation before refund review.",
            "add_to_eval_dataset": True,
        },
    )
    assert approval_response.status_code == 201

    metrics_response = client.get("/api/metrics/review-quality")
    assert metrics_response.status_code == 200
    metrics = metrics_response.json()
    assert metrics["total_reviews"] == 1
    assert metrics["approved"] == 1
    assert metrics["approval_rate"] == 1.0
    assert metrics["edited"] == 1
    assert metrics["category_correction_rate"] == 1.0
    assert metrics["action_correction_rate"] == 1.0
    assert metrics["eval_cases"] == 1
    assert metrics["field_corrections"]["category"] == 1
    assert metrics["field_corrections"]["action"] == 1

    export_response = client.get("/api/evals/export")
    assert export_response.status_code == 200
    examples = export_response.json()["examples"]
    assert len(examples) == 1
    example = examples[0]
    assert example["case"]["title"] == "Refund request for delayed package"
    assert example["ai_output"]["category"] == "refund_request"
    assert example["human_correction"]["category"] == "public_refund_escalation"
    assert example["human_correction"]["action"] == "slack_escalation"
    edit_history = {event["field_name"]: event for event in example["edit_history"]}
    assert edit_history["category"]["ai_value_json"] == "refund_request"
    assert edit_history["category"]["human_value_json"] == "public_refund_escalation"
    assert edit_history["category"]["changed"] == 1
    assert edit_history["owner"]["changed"] == 0
