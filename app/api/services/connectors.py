"""Approved action execution connectors."""

from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.api.config import get_settings


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


def send_slack_escalation(payload: dict, case: dict | None = None) -> dict:
    webhook_url = get_settings().slack_webhook_url
    message = build_slack_message(payload=payload, case=case)
    request_payload = {"text": message}
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


def create_github_issue(payload: dict, case: dict | None = None) -> dict:
    settings = get_settings()
    case = case or {}
    title = f"[SellerOps] {case.get('title') or f'Case {payload.get('case_id')}'}"
    body = build_github_issue_body(payload=payload, case=case)
    request_payload = {
        "title": title,
        "body": body,
        "labels": ["sellerops", payload.get("corrected_category") or "triage"],
    }
    if not settings.github_token or not settings.github_repo:
        return {
            "status": "skipped",
            "response": {
                "message": "GitHub token or repo is not configured.",
                "dry_run": True,
                "payload": request_payload,
            },
        }
    url = f"https://api.github.com/repos/{settings.github_repo}/issues"
    return _post_github(url=url, token=settings.github_token, payload=request_payload)


def create_github_comment(payload: dict, case: dict | None = None) -> dict:
    settings = get_settings()
    case = case or {}
    issue_number = case.get("source_id") or payload.get("github_issue_number")
    body = build_github_comment_body(payload=payload, case=case)
    request_payload = {"body": body}
    if not settings.github_token or not settings.github_repo or not issue_number:
        return {
            "status": "skipped",
            "response": {
                "message": "GitHub token, repo, or issue number is not configured.",
                "dry_run": True,
                "payload": request_payload,
            },
        }
    issue_number = str(issue_number).removeprefix("GH-")
    url = f"https://api.github.com/repos/{settings.github_repo}/issues/{issue_number}/comments"
    return _post_github(url=url, token=settings.github_token, payload=request_payload)


def _post_github(url: str, token: str, payload: dict) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            parsed = json.loads(body) if body else {}
            return {
                "status": "executed",
                "response": {
                    "status_code": response.status,
                    "body": parsed,
                },
            }
    except URLError as exc:
        return {
            "status": "failed",
            "response": {
                "message": str(exc),
            },
        }


def build_github_issue_body(payload: dict, case: dict | None = None) -> str:
    case = case or {}
    return "\n".join(
        [
            "Created by SellerOps after human review.",
            "",
            f"Original case: {case.get('title') or payload.get('case_id')}",
            f"Suggested owner: {payload.get('corrected_owner') or 'unassigned'}",
            f"Severity: {payload.get('corrected_severity') or 'unknown'}",
            f"Risk score: {payload.get('corrected_risk_score')}",
            "",
            "Customer signal:",
            case.get("message") or "",
            "",
            "Reviewer note:",
            payload.get("correction_reason") or "No reviewer note provided.",
        ]
    )


def build_github_comment_body(payload: dict, case: dict | None = None) -> str:
    case = case or {}
    return "\n".join(
        [
            "SellerOps reviewed this signal.",
            "",
            f"Decision: {payload.get('decision')}",
            f"Action: {payload.get('corrected_action')}",
            f"Owner: {payload.get('corrected_owner') or 'unassigned'}",
            f"Reason: {payload.get('correction_reason') or 'No reviewer note provided.'}",
            "",
            f"Source case: {case.get('title') or payload.get('case_id')}",
        ]
    )


def create_stripe_sandbox_refund(payload: dict, case: dict | None = None) -> dict:
    settings = get_settings()
    case = case or {}
    payment_reference = (
        payload.get("stripe_payment_intent")
        or payload.get("stripe_charge")
        or case.get("source_id")
        or case.get("order_id")
    )
    amount = payload.get("refund_amount") or case.get("amount")
    request_payload = {
        "payment_reference": payment_reference,
        "amount": amount,
        "reason": payload.get("correction_reason") or "Approved SellerOps refund review.",
        "case_id": payload.get("case_id"),
    }
    if not settings.stripe_api_key:
        return {
            "status": "skipped",
            "response": {
                "message": "Stripe API key is not configured.",
                "dry_run": True,
                "payload": request_payload,
            },
        }
    if settings.stripe_api_key.startswith("sk_live") and not settings.stripe_allow_live_mode:
        return {
            "status": "skipped",
            "response": {
                "message": "Live Stripe keys are blocked unless SELLEROPS_STRIPE_ALLOW_LIVE_MODE=true.",
                "dry_run": True,
                "payload": request_payload,
            },
        }
    if not payment_reference:
        return {
            "status": "skipped",
            "response": {
                "message": "No Stripe payment reference was provided.",
                "dry_run": True,
                "payload": request_payload,
            },
        }

    try:
        import stripe
    except ImportError:
        return {
            "status": "failed",
            "response": {"message": "stripe package is not installed."},
        }

    stripe.api_key = settings.stripe_api_key
    refund_args = {
        "metadata": {
            "sellerops_case_id": str(payload.get("case_id")),
            "sellerops_decision": payload.get("decision", ""),
        }
    }
    if str(payment_reference).startswith("pi_"):
        refund_args["payment_intent"] = payment_reference
    else:
        refund_args["charge"] = payment_reference
    if amount is not None:
        try:
            refund_args["amount"] = int(round(float(amount) * 100))
        except (TypeError, ValueError):
            pass
    try:
        refund = stripe.Refund.create(**refund_args)
        return {
            "status": "executed",
            "response": {
                "id": refund.get("id") if hasattr(refund, "get") else getattr(refund, "id", None),
                "status": refund.get("status") if hasattr(refund, "get") else getattr(refund, "status", None),
                "object": dict(refund) if isinstance(refund, dict) else str(refund),
            },
        }
    except Exception as exc:
        return {
            "status": "failed",
            "response": {
                "message": str(exc),
                "payload": request_payload,
            },
        }
