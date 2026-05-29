"""phase 1 operational state

Revision ID: 0002_phase1_operational_state
Revises: 0001_initial_schema
Create Date: 2026-05-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_phase1_operational_state"
down_revision: Union[str, Sequence[str], None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cases",
        sa.Column("workspace_id", sa.Text(), nullable=False, server_default="default"),
    )
    op.add_column(
        "case_analyses",
        sa.Column("analysis_status", sa.Text(), nullable=False, server_default="succeeded"),
    )
    op.add_column("case_analyses", sa.Column("provider_name", sa.Text()))
    op.add_column("case_analyses", sa.Column("failure_reason", sa.Text()))
    op.add_column(
        "case_analyses",
        sa.Column("fallback_used", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("case_analyses", "fallback_used")
    op.drop_column("case_analyses", "failure_reason")
    op.drop_column("case_analyses", "provider_name")
    op.drop_column("case_analyses", "analysis_status")
    op.drop_column("cases", "workspace_id")
