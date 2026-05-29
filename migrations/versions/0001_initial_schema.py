"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("template_type", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_id", sa.Text()),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("customer_name", sa.Text()),
        sa.Column("customer_email", sa.Text()),
        sa.Column("order_id", sa.Text()),
        sa.Column("amount", sa.Float()),
        sa.Column("currency", sa.Text()),
        sa.Column("product_name", sa.Text()),
        sa.Column("status", sa.Text(), server_default="new"),
        sa.Column("owner", sa.Text()),
        sa.Column("created_at", sa.Text()),
        sa.Column("imported_at", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), server_default="{}"),
    )
    op.create_table(
        "case_analyses",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("sentiment", sa.Text(), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("risk_labels", sa.Text(), nullable=False),
        sa.Column("policy_basis", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("suggested_action", sa.Text(), nullable=False),
        sa.Column("suggested_owner", sa.Text(), nullable=False),
        sa.Column("reply_draft", sa.Text()),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("requires_human_review", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_table(
        "review_decisions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("analysis_id", sa.Integer(), sa.ForeignKey("case_analyses.id"), nullable=False),
        sa.Column("reviewer_id", sa.Text(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("corrected_category", sa.Text()),
        sa.Column("corrected_severity", sa.Text()),
        sa.Column("corrected_risk_score", sa.Integer()),
        sa.Column("corrected_risk_labels", sa.Text()),
        sa.Column("corrected_action", sa.Text()),
        sa.Column("corrected_owner", sa.Text()),
        sa.Column("corrected_reply", sa.Text()),
        sa.Column("correction_reason", sa.Text()),
        sa.Column("add_to_eval_dataset", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_table(
        "action_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("decision_id", sa.Integer(), sa.ForeignKey("review_decisions.id")),
        sa.Column("action_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("request_payload_json", sa.Text(), nullable=False),
        sa.Column("response_payload_json", sa.Text(), nullable=False),
        sa.Column("executed_by", sa.Text(), nullable=False),
        sa.Column("executed_at", sa.Text(), nullable=False),
    )
    op.create_table(
        "policies",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("workspace_id", sa.Text(), nullable=False, server_default="default"),
        sa.Column("template_type", sa.Text(), nullable=False),
        sa.Column("policy_type", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("policies")
    op.drop_table("action_logs")
    op.drop_table("review_decisions")
    op.drop_table("case_analyses")
    op.drop_table("cases")

