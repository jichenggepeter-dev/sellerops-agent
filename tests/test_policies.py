from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]


def test_default_policies_are_created(client: TestClient) -> None:
    response = client.get("/api/policies?template_type=seller_support")

    assert response.status_code == 200
    policies = response.json()["policies"]
    policy_types = {policy["policy_type"] for policy in policies}
    assert {"refund", "brand_tone", "routing"}.issubset(policy_types)


def test_policy_upsert_versions_active_policy(client: TestClient) -> None:
    response = client.post(
        "/api/policies",
        json={
            "template_type": "seller_support",
            "policy_type": "refund",
            "name": "Strict refund review",
            "body": "Refunds above $100 require support lead approval and delivery status verification.",
        },
    )

    assert response.status_code == 201
    policy = response.json()["policy"]
    assert policy["version"] == 2
    assert policy["active"] == 1

    list_response = client.get("/api/policies?template_type=seller_support")
    active_refunds = [
        item
        for item in list_response.json()["policies"]
        if item["policy_type"] == "refund" and item["active"] == 1
    ]
    assert len(active_refunds) == 1
    assert active_refunds[0]["body"].startswith("Refunds above $100")


def test_triage_policy_basis_uses_active_policy_context(client: TestClient) -> None:
    client.post(
        "/api/policies",
        json={
            "template_type": "seller_support",
            "policy_type": "refund",
            "name": "Strict refund review",
            "body": "Refunds above $100 require support lead approval and delivery status verification.",
        },
    )
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
    cases = client.get("/api/cases").json()["cases"]
    refund_case = next(case for case in cases if case["title"] == "Refund request for delayed package")
    assert "Active policy context" in refund_case["policy_basis"]
    assert "Refunds above $100" in refund_case["policy_basis"]

