"""SQLModel table definitions for the current SellerOps schema.

The app still uses lightweight repository SQL for the MVP, but these models
document the database shape and are the bridge toward fuller ORM usage.
"""

from __future__ import annotations

from sqlmodel import Field, SQLModel


class Case(SQLModel, table=True):
    __tablename__ = "cases"

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: str = "default"
    template_type: str
    source_type: str
    source_id: str | None = None
    title: str
    message: str
    customer_name: str | None = None
    customer_email: str | None = None
    order_id: str | None = None
    amount: float | None = None
    currency: str | None = None
    product_name: str | None = None
    status: str | None = "new"
    owner: str | None = None
    created_at: str | None = None
    imported_at: str
    metadata_json: str | None = "{}"


class CaseAnalysis(SQLModel, table=True):
    __tablename__ = "case_analyses"

    id: int | None = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="cases.id")
    category: str
    severity: str
    sentiment: str
    risk_score: int
    risk_labels: str
    policy_basis: str
    reason: str
    suggested_action: str
    suggested_owner: str
    reply_draft: str | None = None
    confidence_score: float
    requires_human_review: int
    model_name: str
    prompt_version: str
    analysis_status: str = "succeeded"
    provider_name: str | None = None
    failure_reason: str | None = None
    fallback_used: int = 0
    created_at: str


class ReviewDecision(SQLModel, table=True):
    __tablename__ = "review_decisions"

    id: int | None = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="cases.id")
    analysis_id: int = Field(foreign_key="case_analyses.id")
    reviewer_id: str
    decision: str
    corrected_category: str | None = None
    corrected_severity: str | None = None
    corrected_risk_score: int | None = None
    corrected_risk_labels: str | None = None
    corrected_action: str | None = None
    corrected_owner: str | None = None
    corrected_reply: str | None = None
    correction_reason: str | None = None
    add_to_eval_dataset: int
    created_at: str


class ActionLog(SQLModel, table=True):
    __tablename__ = "action_logs"

    id: int | None = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="cases.id")
    decision_id: int | None = Field(default=None, foreign_key="review_decisions.id")
    action_type: str
    status: str
    request_payload_json: str
    response_payload_json: str
    executed_by: str
    executed_at: str


class Policy(SQLModel, table=True):
    __tablename__ = "policies"

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: str = "default"
    template_type: str
    policy_type: str
    name: str
    body: str
    version: int = 1
    active: int = 1
    created_at: str
    updated_at: str
