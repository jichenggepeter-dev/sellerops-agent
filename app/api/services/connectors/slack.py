"""Slack escalation actions."""

from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.api.config import get_settings


def send_slack_escalation(payload: dict, case: dict | None = None) -> dict:
    webhook_url = get_settings().slack_webhook_url
    request_payload = build_slack_payload(payload=payload, case=case)
    if not webhook_url:
        return {
            "status": "skipped",
            "response": {
                "message": "Slack webhook URL is not configured.",
                "dry_run": True,
                "payload": request_payload,
            },
        }

    request = Request(
        webhook_url,
        data=json.dumps(request_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            return {
                "status": "executed",
                "response": {
                    "status_code": response.status,
                    "body": body,
                },
            }
    except URLError as exc:
        return {
            "status": "failed",
            "response": {
                "message": str(exc),
            },
        }


def build_slack_payload(payload: dict, case: dict | None = None) -> dict:
    return {"text": build_slack_message(payload=payload, case=case)}


def build_slack_message(payload: dict, case: dict | None = None) -> str:
    case = case or {}
    title = case.get("title") or f"Case {payload.get('case_id')}"
    owner = payload.get("corrected_owner") or "unassigned"
    action = payload.get("corrected_action") or "slack_escalation"
    reason = payload.get("correction_reason") or "No reviewer note provided."
    severity = payload.get("corrected_severity") or "unknown"
    risk_score = payload.get("corrected_risk_score")
    score_text = f" · risk {risk_score}" if risk_score is not None else ""
    return (
        f"*SellerOps escalation*: {title}\n"
        f"- Action: `{action}`\n"
        f"- Owner: `{owner}`\n"
        f"- Severity: `{severity}`{score_text}\n"
        f"- Reviewer note: {reason}"
    )
