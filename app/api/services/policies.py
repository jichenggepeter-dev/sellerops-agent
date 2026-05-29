"""Policy settings persistence and context assembly."""

from __future__ import annotations

from app.api.repositories import execute_insert, execute_write, fetch_all, fetch_one
from app.api.time_utils import utc_now


DEFAULT_POLICIES = {
    ("seller_support", "refund"): {
        "name": "Default refund policy",
        "body": (
            "Refunds require human approval. Prioritize requests involving delayed delivery, "
            "damaged goods, duplicate charges, chargeback threats, or public complaint risk. "
            "Do not promise a refund until order and delivery status are checked."
        ),
    },
    ("seller_support", "brand_tone"): {
        "name": "Default seller support tone",
        "body": (
            "Use a calm, helpful, concise tone. Acknowledge frustration, avoid blame, "
            "and clearly state that risky actions require teammate review."
        ),
    },
    ("seller_support", "routing"): {
        "name": "Default seller routing rules",
        "body": (
            "Refund and public complaint cases route to support_lead. Product quality patterns route "
            "to ops. Repeated logistics delays route to fulfillment."
        ),
    },
    ("saas_support", "support"): {
        "name": "Default SaaS support policy",
        "body": (
            "High-impact bugs, OAuth issues, data loss risk, billing disputes, and exposed credentials "
            "require human review. Feature requests should be routed to product."
        ),
    },
    ("saas_support", "brand_tone"): {
        "name": "Default SaaS support tone",
        "body": (
            "Use a precise, developer-friendly tone. Mention reproduction details when relevant and "
            "avoid promising timelines before engineering review."
        ),
    },
}


def ensure_default_policies() -> None:
    for (template_type, policy_type), policy in DEFAULT_POLICIES.items():
        existing = get_policy(template_type=template_type, policy_type=policy_type)
        if not existing:
            upsert_policy(
                {
                    "template_type": template_type,
                    "policy_type": policy_type,
                    "name": policy["name"],
                    "body": policy["body"],
                    "workspace_id": "default",
                    "active": True,
                }
            )


def list_policies(template_type: str | None = None) -> list[dict]:
    params: list[str] = []
    where = "WHERE active = 1"
    if template_type:
        where += " AND template_type = ?"
        params.append(template_type)
    return fetch_all(
        f"""
        SELECT *
        FROM policies
        {where}
        ORDER BY template_type, policy_type, version DESC, id DESC
        """,
        params,
    )


def get_policy(template_type: str, policy_type: str, workspace_id: str = "default") -> dict | None:
    return fetch_one(
        """
        SELECT *
        FROM policies
        WHERE workspace_id = ? AND template_type = ? AND policy_type = ? AND active = 1
        ORDER BY version DESC, id DESC
        LIMIT 1
        """,
        (workspace_id, template_type, policy_type),
    )


def upsert_policy(payload: dict) -> dict:
    workspace_id = payload.get("workspace_id") or "default"
    template_type = payload["template_type"]
    policy_type = payload["policy_type"]
    active = 1 if payload.get("active", True) else 0
    now = utc_now()
    existing = get_policy(template_type=template_type, policy_type=policy_type, workspace_id=workspace_id)
    if existing:
        version = int(existing["version"]) + 1
        execute_write(
            """
            UPDATE policies
            SET active = 0, updated_at = ?
            WHERE workspace_id = ? AND template_type = ? AND policy_type = ? AND active = 1
            """,
            (now, workspace_id, template_type, policy_type),
        )
    else:
        version = 1
    policy_id = execute_insert(
        """
        INSERT INTO policies (
          workspace_id, template_type, policy_type, name, body, version, active, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            workspace_id,
            template_type,
            policy_type,
            payload["name"],
            payload["body"],
            version,
            active,
            now,
            now,
        ),
    )
    policy = fetch_one("SELECT * FROM policies WHERE id = ?", (policy_id,))
    assert policy is not None
    return policy


def active_policy_context(template_type: str, workspace_id: str = "default") -> str:
    policies = [
        policy
        for policy in list_policies(template_type=template_type)
        if policy["workspace_id"] == workspace_id
    ]
    if not policies:
        return ""
    chunks = []
    for policy in policies:
        chunks.append(f"{policy['policy_type']}: {policy['body']}")
    return "\n".join(chunks)
