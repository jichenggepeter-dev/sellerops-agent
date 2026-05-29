from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.api.config import reset_settings_cache


ROOT = Path(__file__).resolve().parents[1]


def _seed_refund_case(client: TestClient) -> dict:
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


def test_stripe_refund_without_key_is_dry_run(client: TestClient) -> None:
    review_case = _seed_refund_case(client)

    response = client.post(
        "/api/reviews",
        json={
            "case_id": review_case["id"],
            "analysis_id": review_case["analysis_id"],
            "decision": "approve",
            "corrected_category": "refund_request",
            "corrected_severity": "critical",
            "corrected_risk_score": 94,
            "corrected_action": "stripe_refund_sandbox",
            "corrected_owner": "support_lead",
            "correction_reason": "Approved test refund after delivery check.",
            "stripe_payment_intent": "pi_test_123",
        },
    )

    assert response.status_code == 201
    log = client.get("/api/audit").json()["logs"][0]
    assert log["action_type"] == "stripe_refund_sandbox"
    assert log["status"] == "skipped"
    assert log["response_payload_json"]["dry_run"] is True
    assert log["response_payload_json"]["payload"]["payment_reference"] == "pi_test_123"


def test_live_stripe_key_is_blocked_by_default(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SELLEROPS_DB_PATH", str(tmp_path / "sellerops-test.db"))
    monkeypatch.setenv("SELLEROPS_STRIPE_API_KEY", "sk_live_test")
    monkeypatch.setenv("SELLEROPS_STRIPE_ALLOW_LIVE_MODE", "false")
    reset_settings_cache()

    from app.api.db import init_db
    from app.api.main import app
    from app.api.services.policies import ensure_default_policies

    init_db()
    ensure_default_policies()
    with TestClient(app) as client:
        review_case = _seed_refund_case(client)
        response = client.post(
            "/api/reviews",
            json={
                "case_id": review_case["id"],
                "analysis_id": review_case["analysis_id"],
                "decision": "approve",
                "corrected_category": "refund_request",
                "corrected_severity": "critical",
                "corrected_risk_score": 94,
                "corrected_action": "stripe_refund_sandbox",
                "corrected_owner": "support_lead",
                "stripe_payment_intent": "pi_test_123",
            },
        )
        assert response.status_code == 201
        log = client.get("/api/audit").json()["logs"][0]

    assert log["status"] == "skipped"
    assert "Live Stripe keys are blocked" in log["response_payload_json"]["message"]
    reset_settings_cache()


def test_stripe_refund_executes_with_test_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SELLEROPS_DB_PATH", str(tmp_path / "sellerops-test.db"))
    monkeypatch.setenv("SELLEROPS_STRIPE_API_KEY", "sk_test_123")
    reset_settings_cache()

    from app.api.db import init_db
    from app.api.main import app
    from app.api.services.policies import ensure_default_policies
    import stripe

    init_db()
    ensure_default_policies()

    calls = []

    def fake_refund_create(**kwargs):
        calls.append(kwargs)
        return {"id": "re_test_123", "status": "succeeded"}

    monkeypatch.setattr(stripe.Refund, "create", fake_refund_create)

    with TestClient(app) as client:
        review_case = _seed_refund_case(client)
        response = client.post(
            "/api/reviews",
            json={
                "case_id": review_case["id"],
                "analysis_id": review_case["analysis_id"],
                "decision": "approve",
                "corrected_category": "refund_request",
                "corrected_severity": "critical",
                "corrected_risk_score": 94,
                "corrected_action": "stripe_refund_sandbox",
                "corrected_owner": "support_lead",
                "correction_reason": "Approved test refund after delivery check.",
                "stripe_payment_intent": "pi_test_123",
                "refund_amount": 12.34,
            },
        )
        assert response.status_code == 201
        log = client.get("/api/audit").json()["logs"][0]

    assert len(calls) == 1
    assert calls[0]["payment_intent"] == "pi_test_123"
    assert calls[0]["amount"] == 1234
    assert log["status"] == "executed"
    assert log["response_payload_json"]["id"] == "re_test_123"
    reset_settings_cache()

