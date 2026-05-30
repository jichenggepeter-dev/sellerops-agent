"""action result details

Revision ID: 0004_action_result_details
Revises: 0003_review_edit_events
Create Date: 2026-05-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_action_result_details"
down_revision: Union[str, Sequence[str], None] = "0003_review_edit_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "action_logs",
        sa.Column("preview_payload_json", sa.Text(), nullable=False, server_default="{}"),
    )
    op.add_column("action_logs", sa.Column("external_url", sa.Text()))
    op.add_column("action_logs", sa.Column("failure_reason", sa.Text()))
    op.add_column(
        "action_logs",
        sa.Column("retryable", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("action_logs", "retryable")
    op.drop_column("action_logs", "failure_reason")
    op.drop_column("action_logs", "external_url")
    op.drop_column("action_logs", "preview_payload_json")
