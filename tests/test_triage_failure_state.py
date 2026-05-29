from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.api.services import cases


ROOT = Path(__file__).resolve().parents[1]


class FailingProvider:
    name = "openai"
    model_name = "gpt-test"
    prompt_version = "test-prompt"

    def analyze(self, case: dict, template_type: str, policy_context: str = ""):
        raise RuntimeError("provider unavailable")


def test_triage_provider_failure_falls_back_and_requires_review(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(cases, "get_triage_provider", lambda: FailingProvider())
    csv_text = (ROOT / "samples" / "seller-support" / "refund_requests.csv").read_text()

    response = client.post(
        "/api/import/csv",
        json={
            "workspace_id": "workspace_demo",
            "template_type": "seller_support",
            "source_type": "csv",
            "csv_text": csv_text,
        },
    )

    assert response.status_code == 201
    review_cases = client.get("/api/review-queue").json()["cases"]
    target = next(case for case in review_cases if case["title"] == "Refund request for delayed package")
    assert target["workspace_id"] == "workspace_demo"
    assert target["analysis_status"] == "fallback_used"
    assert target["provider_name"] == "openai"
    assert target["fallback_used"] == 1
    assert "provider unavailable" in target["failure_reason"]
    assert "ai_provider_failed" in target["risk_labels"]


def test_unsupported_provider_creates_failed_analysis(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("SELLEROPS_TRIAGE_PROVIDER", "unsupported")
    from app.api.config import reset_settings_cache

    reset_settings_cache()
    csv_text = "title,message\nBroken import,Please help\n"

    response = client.post(
        "/api/import/csv",
        json={
            "template_type": "seller_support",
            "source_type": "csv",
            "csv_text": csv_text,
        },
    )

    assert response.status_code == 201
    review_cases = client.get("/api/review-queue").json()["cases"]
    target = next(case for case in review_cases if case["title"] == "Broken import")
    assert target["analysis_status"] == "failed"
    assert target["category"] == "analysis_failed"
    assert target["suggested_action"] == "manual_review"
    assert target["requires_human_review"] == 1
    assert "Unsupported triage provider" in target["failure_reason"]
    reset_settings_cache()
