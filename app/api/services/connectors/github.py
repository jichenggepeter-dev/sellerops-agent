"""GitHub issue and comment actions."""

from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.api.config import get_settings


def create_github_issue(payload: dict, case: dict | None = None) -> dict:
    settings = get_settings()
    case = case or {}
    request_payload = build_github_issue_payload(payload=payload, case=case)
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
    request_payload = build_github_comment_payload(payload=payload, case=case)
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


def build_github_issue_payload(payload: dict, case: dict | None = None) -> dict:
    case = case or {}
    case_title = case.get("title") or f"Case {payload.get('case_id')}"
    return {
        "title": f"[SellerOps] {case_title}",
        "body": build_github_issue_body(payload=payload, case=case),
        "labels": ["sellerops", payload.get("corrected_category") or "triage"],
    }


def build_github_comment_payload(payload: dict, case: dict | None = None) -> dict:
    return {"body": build_github_comment_body(payload=payload, case=case)}


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
