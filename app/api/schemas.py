"""Request schemas for the SellerOps API."""

from pydantic import BaseModel, ConfigDict, Field


class CsvImportRequest(BaseModel):
    template_type: str = Field(default="seller_support")
    source_type: str = Field(default="csv")
    csv_text: str


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    case_id: int
    analysis_id: int
    reviewer_id: str = "local-reviewer"
    decision: str = "approve"
    corrected_category: str | None = None
    corrected_severity: str | None = None
    corrected_risk_score: int | None = None
    corrected_risk_labels: list[str] = Field(default_factory=list)
    corrected_action: str | None = None
    corrected_owner: str | None = None
    corrected_reply: str | None = None
    correction_reason: str | None = None
    add_to_eval_dataset: bool = False


class PolicyUpsertRequest(BaseModel):
    template_type: str = "seller_support"
    policy_type: str
    name: str
    body: str
    workspace_id: str = "default"
    active: bool = True
