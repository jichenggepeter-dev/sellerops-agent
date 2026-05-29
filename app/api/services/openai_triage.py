"""OpenAI-backed triage provider using structured outputs."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.api.config import get_settings
from app.api.services.triage import TriageResult


class OpenAITriageOutput(BaseModel):
    category: str = Field(description="Normalized issue category.")
    severity: str = Field(description="One of low, medium, high, critical.")
    sentiment: str = Field(description="Customer sentiment, such as neutral, negative, angry, urgent.")
    risk_score: int = Field(ge=0, le=100, description="Risk score from 0 to 100.")
    risk_labels: list[str] = Field(description="Short machine-readable risk labels.")
    policy_basis: str = Field(description="The policy or business rule used for the decision.")
    reason: str = Field(description="Concise explanation of the triage decision.")
    suggested_action: str = Field(description="Suggested action, such as reply_draft, refund_review, create_issue, slack_escalation.")
    suggested_owner: str = Field(description="Suggested owner or team.")
    reply_draft: str = Field(description="Customer-facing draft, if appropriate. Must not claim an action was completed.")
    confidence_score: float = Field(ge=0, le=1, description="Model confidence from 0 to 1.")
    requires_human_review: bool = Field(description="Whether a human must review before action.")


class OpenAITriageProvider:
    name = "openai"
    prompt_version = "sellerops-openai-v1"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise ValueError("SELLEROPS_OPENAI_API_KEY is required when SELLEROPS_TRIAGE_PROVIDER=openai")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ValueError("The openai package is required for OpenAITriageProvider") from exc

        self.model_name = settings.openai_model
        self.client = OpenAI(api_key=settings.openai_api_key)

    def analyze(self, case: dict, template_type: str, policy_context: str = "") -> TriageResult:
        response = self.client.responses.parse(
            model=self.model_name,
            instructions=self._instructions(template_type, policy_context),
            input=self._input(case),
            text_format=OpenAITriageOutput,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise ValueError("OpenAI triage response did not include parsed structured output")
        return TriageResult(
            category=parsed.category,
            severity=parsed.severity,
            sentiment=parsed.sentiment,
            risk_score=parsed.risk_score,
            risk_labels=parsed.risk_labels,
            policy_basis=parsed.policy_basis,
            reason=parsed.reason,
            suggested_action=parsed.suggested_action,
            suggested_owner=parsed.suggested_owner,
            reply_draft=parsed.reply_draft,
            confidence_score=parsed.confidence_score,
            requires_human_review=parsed.requires_human_review,
            model_name=self.model_name,
            prompt_version=self.prompt_version,
        )

    def _instructions(self, template_type: str, policy_context: str) -> str:
        return f"""
You are SellerOps Agent's triage engine for {template_type}.

Analyze customer-facing operational signals and return only the structured output.
Use the active policy context as the source of truth for policy_basis.

Safety rules:
- Never say a refund, reply, escalation, or external action has already happened.
- Customer-facing replies must be drafts only.
- Refunds, public complaint risk, legal/compliance risk, exposed credentials, low confidence, and ambiguous high-impact cases require human review.
- If policy context is insufficient, say what policy is missing and require human review.

Active policy context:
{policy_context or "No active policy context provided."}
""".strip()

    def _input(self, case: dict) -> str:
        return f"""
Case:
- title: {case.get("title", "")}
- message: {case.get("message", "")}
- customer_name: {case.get("customer_name", "")}
- customer_email: {case.get("customer_email", "")}
- order_id: {case.get("order_id", "")}
- amount: {case.get("amount", "")}
- product_name: {case.get("product_name", "")}
- status: {case.get("status", "")}
""".strip()

