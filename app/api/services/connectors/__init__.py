"""Approved action connector dispatcher."""

from __future__ import annotations

from app.api.services.connectors.github import create_github_comment, create_github_issue
from app.api.services.connectors.slack import send_slack_escalation
from app.api.services.connectors.stripe_refunds import create_stripe_sandbox_refund


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
