"""Triage provider interface and built-in mock implementation.

The production path is:
- keep this structured output contract stable
- keep a deterministic mock provider for tests and local demos
- add real LLM providers behind the same interface
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class TriageResult:
    category: str
    severity: str
    sentiment: str
    risk_score: int
    risk_labels: list[str]
    policy_basis: str
    reason: str
    suggested_action: str
    suggested_owner: str
    reply_draft: str
    confidence_score: float
    requires_human_review: bool
    model_name: str
    prompt_version: str
    analysis_status: str = "succeeded"
    provider_name: str = ""
    failure_reason: str = ""
    fallback_used: bool = False


class TriageProvider(Protocol):
    name: str

    def analyze(self, case: dict, template_type: str, policy_context: str = "") -> TriageResult:
        """Analyze a normalized case and return structured triage output."""


class MockTriageProvider:
    name = "mock"
    model_name = "mock-triage-v0"
    prompt_version = "sellerops-mock-v1"

    def analyze(self, case: dict, template_type: str, policy_context: str = "") -> TriageResult:
        text = f"{case.get('title', '')} {case.get('message', '')}".lower()
        labels: list[str] = []
        score = 22
        category = "general_support"
        action = "reply_draft"
        owner = "support"
        sentiment = "neutral"
        severity = "low"

        def has(*words: str) -> bool:
            return any(word in text for word in words)

        if has("refund", "chargeback", "money back", "cancel order", "退款", "退货"):
            category = "refund_request"
            action = "refund_review"
            owner = "support_lead"
            labels.extend(["refund_policy_sensitive", "needs_human_escalation"])
            score += 34
        if has("late", "delay", "delayed", "tracking", "lost", "shipping", "物流", "延误"):
            category = "logistics_delay" if category == "general_support" else category
            labels.append("logistics_delay")
            score += 18
        if has("broken", "damaged", "defect", "quality", "doesn't work", "bug", "crash", "错误"):
            category = "product_quality_issue" if template_type == "seller_support" else "bug_report"
            labels.append("product_quality_issue")
            score += 20
        if has("angry", "terrible", "scam", "lawsuit", "never again", "hate", "投诉", "欺骗"):
            sentiment = "angry"
            labels.extend(["angry_customer", "churn_risk"])
            score += 25
        elif has("urgent", "asap", "immediately", "critical", "blocked", "紧急"):
            sentiment = "urgent"
            labels.append("needs_human_escalation")
            score += 18
        elif has("thanks", "love", "great", "works well"):
            sentiment = "positive"
            score -= 8
        else:
            sentiment = "negative" if score >= 45 else "neutral"

        if has("twitter", "tiktok", "reddit", "review", "public", "viral", "曝光"):
            labels.append("public_complaint_risk")
            score += 20
        if has("password", "ssn", "credit card", "api key", "token", "credential"):
            labels.append("pii_detected")
            score += 18
        if has("feature request", "would like", "can you add", "support for", "please add"):
            category = "feature_request"
            action = "create_issue"
            owner = "product"
            score += 8
        if has("docs", "documentation", "tutorial", "setup"):
            category = "documentation_gap"
            action = "create_issue"
            owner = "product"
            score += 8

        score = max(0, min(score, 100))
        if score >= 80:
            severity = "critical"
        elif score >= 60:
            severity = "high"
        elif score >= 35:
            severity = "medium"
        else:
            severity = "low"

        labels = sorted(set(labels or ["routine_support"]))
        requires_review = score >= 45 or action in {"refund_review", "create_issue"} or "pii_detected" in labels
        confidence = 0.84 if category != "general_support" else 0.68
        policy_basis = self._policy_basis(requires_review, policy_context)
        reason = f"Detected {category.replace('_', ' ')} with risk labels: {', '.join(labels)}."

        name = case.get("customer_name") or "there"
        reply = (
            f"Hi {name}, thanks for reaching out. I understand the issue and have flagged it for review. "
            "Our team will confirm the next step before taking action."
        )
        if action == "refund_review":
            reply = (
                f"Hi {name}, sorry about the trouble. I am checking the order details and refund policy now. "
                "A teammate will review this before any refund action is taken."
            )

        return TriageResult(
            category=category,
            severity=severity,
            sentiment=sentiment,
            risk_score=score,
            risk_labels=labels,
            policy_basis=policy_basis,
            reason=reason,
            suggested_action=action,
            suggested_owner=owner,
            reply_draft=reply,
            confidence_score=confidence,
            requires_human_review=requires_review,
            model_name=self.model_name,
            prompt_version=self.prompt_version,
            provider_name=self.name,
        )

    def _policy_basis(self, requires_review: bool, policy_context: str) -> str:
        default = (
            "Refunds, external replies, and public escalations require human approval."
            if requires_review
            else "Low-risk support cases can be drafted for review."
        )
        if not policy_context:
            return default
        compact_context = " | ".join(line.strip() for line in policy_context.splitlines() if line.strip())
        return f"{default} Active policy context: {compact_context}"
