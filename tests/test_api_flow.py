from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["service"] == "fastapi"


def test_samples_endpoint(client: TestClient) -> None:
    response = client.get("/api/samples")
    assert response.status_code == 200
    paths = {sample["path"] for sample in response.json()["samples"]}
    assert "samples/seller-support/refund_requests.csv" in paths
    assert "samples/saas-support/github_issues.csv" in paths


def test_csv_import_review_and_audit_flow(client: TestClient) -> None:
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
    assert import_response.json()["imported"] == 4

    cases_response = client.get("/api/cases")
    assert cases_response.status_code == 200
    cases = cases_response.json()["cases"]
    assert len(cases) == 4
    refund_case = next(case for case in cases if case["title"] == "Refund request for delayed package")
    assert refund_case["category"] == "refund_request"
    assert refund_case["suggested_action"] == "refund_review"
    assert refund_case["requires_human_review"] == 1
    assert refund_case["status"] == "needs_review"

    review_response = client.get("/api/review-queue")
    assert review_response.status_code == 200
    review_cases = review_response.json()["cases"]
    assert len(review_cases) >= 1
    review_case = next(case for case in review_cases if case["title"] == "Refund request for delayed package")

    approval_response = client.post(
        "/api/reviews",
        json={
            "case_id": review_case["id"],
            "analysis_id": review_case["analysis_id"],
            "decision": "approve",
            "corrected_category": "refund_request",
            "corrected_severity": "critical",
            "corrected_risk_score": 94,
            "corrected_action": "refund_review",
            "corrected_owner": "support_lead",
            "corrected_reply": "Approved for refund policy review after checking delivery status.",
            "correction_reason": "Public complaint risk and delayed package.",
            "add_to_eval_dataset": True,
        },
    )
    assert approval_response.status_code == 201
    assert approval_response.json()["status"] == "action_executed"

    audit_response = client.get("/api/audit")
    assert audit_response.status_code == 200
    logs = audit_response.json()["logs"]
    assert len(logs) == 1
    assert logs[0]["action_type"] == "refund_review"
    assert logs[0]["status"] == "executed"
    assert logs[0]["request_payload_json"]["add_to_eval_dataset"] is True

    remaining_review_cases = client.get("/api/review-queue").json()["cases"]
    assert all(case["id"] != review_case["id"] for case in remaining_review_cases)


def test_review_preview_does_not_execute_action(client: TestClient) -> None:
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

    preview_response = client.post(
        "/api/reviews/preview",
        json={
            "case_id": review_case["id"],
            "analysis_id": review_case["analysis_id"],
            "decision": "approve",
            "corrected_category": "refund_request",
            "corrected_severity": "critical",
            "corrected_risk_score": 94,
            "corrected_action": "slack_escalation",
            "corrected_owner": "support_lead",
            "correction_reason": "Public complaint risk needs team escalation.",
        },
    )

    assert preview_response.status_code == 200
    body = preview_response.json()
    assert body["case_id"] == review_case["id"]
    assert body["case_status"] == "needs_review"
    assert body["preview"]["connector"] == "slack"
    assert body["preview"]["requires_external_write"] is True
    assert "SellerOps escalation" in body["preview"]["payload"]["text"]
    assert client.get("/api/audit").json()["logs"] == []


def test_empty_csv_returns_400(client: TestClient) -> None:
    response = client.post(
        "/api/import/csv",
        json={"template_type": "seller_support", "source_type": "csv", "csv_text": ""},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "CSV input is empty or invalid."
