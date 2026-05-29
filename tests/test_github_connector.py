from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.config import reset_settings_cache
from app.api.services.connectors import github


ROOT = Path(__file__).resolve().parents[1]


def _seed_saas_review_case(client: TestClient) -> dict:
    csv_text = (ROOT / "samples" / "saas-support" / "github_issues.csv").read_text()
    response = client.post(
        "/api/import/csv",
        json={
            "template_type": "saas_support",
            "source_type": "csv",
            "csv_text": csv_text,
        },
    )
    assert response.status_code == 201
    return next(
        case
        for case in client.get("/api/review-queue").json()["cases"]
        if case["title"] == "Feature request: Slack digest"
    )


def test_create_github_issue_without_config_is_dry_run(client: TestClient) -> None:
    review_case = _seed_saas_review_case(client)

    response = client.post(
        "/api/reviews",
        json={
            "case_id": review_case["id"],
            "analysis_id": review_case["analysis_id"],
            "decision": "approve",
            "corrected_category": "feature_request",
            "corrected_severity": "medium",
            "corrected_risk_score": 30,
            "corrected_action": "create_issue",
            "corrected_owner": "product",
            "correction_reason": "Feature request should be tracked in GitHub.",
            "add_to_eval_dataset": True,
        },
    )

    assert response.status_code == 201
    log = client.get("/api/audit").json()["logs"][0]
    assert log["action_type"] == "create_issue"
    assert log["status"] == "skipped"
    assert log["response_payload_json"]["dry_run"] is True
    assert log["response_payload_json"]["payload"]["title"].startswith("[SellerOps]")


def test_create_github_issue_posts_when_configured(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("SELLEROPS_DATABASE_URL", raising=False)
    monkeypatch.setenv("SELLEROPS_DB_PATH", str(tmp_path / "sellerops-test.db"))
    monkeypatch.setenv("SELLEROPS_GITHUB_TOKEN", "ghp_test")
    monkeypatch.setenv("SELLEROPS_GITHUB_REPO", "owner/repo")
    reset_settings_cache()

    from app.api.db import init_db
    from app.api.main import app
    from app.api.services.policies import ensure_default_policies

    init_db()
    ensure_default_policies()

    calls = []

    class FakeResponse:
        status = 201

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({"html_url": "https://github.com/owner/repo/issues/123"}).encode()

    def fake_urlopen(request, timeout=10):
        calls.append((request, timeout))
        return FakeResponse()

    monkeypatch.setattr(github, "urlopen", fake_urlopen)

    with TestClient(app) as client:
        review_case = _seed_saas_review_case(client)
        response = client.post(
            "/api/reviews",
            json={
                "case_id": review_case["id"],
                "analysis_id": review_case["analysis_id"],
                "decision": "approve",
                "corrected_category": "feature_request",
                "corrected_severity": "medium",
                "corrected_risk_score": 30,
                "corrected_action": "create_issue",
                "corrected_owner": "product",
                "correction_reason": "Feature request should be tracked in GitHub.",
            },
        )
        assert response.status_code == 201
        log = client.get("/api/audit").json()["logs"][0]

    assert len(calls) == 1
    request = calls[0][0]
    assert request.full_url == "https://api.github.com/repos/owner/repo/issues"
    assert request.headers["Authorization"] == "Bearer ghp_test"
    assert log["status"] == "executed"
    assert log["response_payload_json"]["status_code"] == 201
    assert log["response_payload_json"]["body"]["html_url"].endswith("/123")
    reset_settings_cache()
