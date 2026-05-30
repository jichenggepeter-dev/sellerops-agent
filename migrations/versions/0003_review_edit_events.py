"""review edit events

Revision ID: 0003_review_edit_events
Revises: 0002_phase1_operational_state
Create Date: 2026-05-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_review_edit_events"
down_revision: Union[str, Sequence[str], None] = "0002_phase1_operational_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "review_edit_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("review_id", sa.Integer(), sa.ForeignKey("review_decisions.id"), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("analysis_id", sa.Integer(), sa.ForeignKey("case_analyses.id"), nullable=False),
        sa.Column("field_name", sa.Text(), nullable=False),
        sa.Column("ai_value_json", sa.Text(), nullable=False),
        sa.Column("human_value_json", sa.Text(), nullable=False),
        sa.Column("changed", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("review_edit_events")
