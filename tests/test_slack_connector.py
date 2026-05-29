from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.api.config import reset_settings_cache
from app.api.services import connectors


ROOT = Path(__file__).resolve().parents[1]


def _seed_review_case(client: TestClient) -> dict:
    csv_text = (ROOT / "samples" / "seller-support" / "refund_requests.csv").read_text()
    response = client.post(
        "/api/import/csv",
        json={
            "template_type": "seller_support",
            "source_type": "csv",
            "csv_text": csv_text,
        },
    )
    assert response.status_code == 201
    return next(
        case
        for case in client.get("/api/review-queue").json()["cases"]
        if case["title"] == "Refund request for delayed package"
    )


def test_slack_escalation_without_webhook_is_dry_run(client: TestClient) -> None:
    review_case = _seed_review_case(client)

    response = client.post(
        "/api/reviews",
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
            "add_to_eval_dataset": True,
        },
    )

    assert response.status_code == 201
    log = client.get("/api/audit").json()["logs"][0]
    assert log["action_type"] == "slack_escalation"
    assert log["status"] == "skipped"
    assert log["response_payload_json"]["dry_run"] is True
    assert "SellerOps escalation" in log["response_payload_json"]["payload"]["text"]


def test_slack_escalation_posts_when_webhook_configured(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SELLEROPS_DB_PATH", str(tmp_path / "sellerops-test.db"))
    monkeypatch.setenv("SELLEROPS_SLACK_WEBHOOK_URL", "https://hooks.slack.test/services/T000/B000/XXX")
    reset_settings_cache()

    from app.api.db import init_db
    from app.api.main import app
    from app.api.services.policies import ensure_default_policies

    init_db()
    ensure_default_policies()

    calls = []

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b"ok"

    def fake_urlopen(request, timeout=10):
        calls.append((request, timeout))
        return FakeResponse()

    monkeypatch.setattr(connectors, "urlopen", fake_urlopen)

    with TestClient(app) as client:
        review_case = _seed_review_case(client)
        response = client.post(
            "/api/reviews",
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
        assert response.status_code == 201
        log = client.get("/api/audit").json()["logs"][0]

    assert len(calls) == 1
    assert calls[0][1] == 10
    assert log["status"] == "executed"
    assert log["response_payload_json"]["status_code"] == 200
    reset_settings_cache()

