"""Approved action connector dispatcher."""

from __future__ import annotations

from app.api.services.connectors.github import (
    build_github_comment_payload,
    build_github_issue_payload,
    create_github_comment,
    create_github_issue,
)
from app.api.services.connectors.slack import build_slack_payload, send_slack_escalation
from app.api.services.connectors.stripe_refunds import (
    build_stripe_refund_payload,
    create_stripe_sandbox_refund,
)


def execute_action(action_type: str, payload: dict, case: dict | None = None) -> dict:
    if action_type == "slack_escalation":
        return send_slack_escalation(payload=payload, case=case)
    if action_type == "create_issue":
        return create_github_issue(payload=payload, case=case)
    if action_type == "github_comment":
        return create_github_comment(payload=payload, case=case)
    if action_type == "stripe_refund_sandbox":
        return create_stripe_sandbox_refund(payload=payload, case=case)
    return {
        "status": "executed",
        "response": {"message": f"{action_type} approved in local MVP"},
    }


def preview_action(action_type: str, payload: dict, case: dict | None = None) -> dict:
    if action_type == "slack_escalation":
        return {
            "action_type": action_type,
            "connector": "slack",
            "requires_external_write": True,
            "payload": build_slack_payload(payload=payload, case=case),
        }
    if action_type == "create_issue":
        return {
            "action_type": action_type,
            "connector": "github",
            "requires_external_write": True,
            "payload": build_github_issue_payload(payload=payload, case=case),
        }
    if action_type == "github_comment":
        return {
            "action_type": action_type,
            "connector": "github",
            "requires_external_write": True,
            "payload": build_github_comment_payload(payload=payload, case=case),
        }
    if action_type == "stripe_refund_sandbox":
        return {
            "action_type": action_type,
            "connector": "stripe",
            "requires_external_write": True,
            "payload": build_stripe_refund_payload(payload=payload, case=case),
        }
    return {
        "action_type": action_type,
        "connector": "local",
        "requires_external_write": False,
        "payload": {"message": f"{action_type} would be approved in local MVP"},
    }
