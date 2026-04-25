"""add feedback forms

Revision ID: 20260425_0044
Revises: 20260424_0043
Create Date: 2026-04-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260425_0044"
down_revision = "20260424_0043"
branch_labels = None
depends_on = None


def _get_table_names(bind) -> set[str]:
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)

    if "feedback_forms" not in tables:
        op.create_table(
            "feedback_forms",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("target_type", sa.String(), nullable=False),
            sa.Column("target_id", sa.String(), nullable=False),
            sa.Column("target_name", sa.String(), nullable=True),
            sa.Column("recipient_type", sa.String(), nullable=False, server_default="PATIENTS"),
            sa.Column("questions", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("is_deployed", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_by", sa.String(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_feedback_forms_target", "feedback_forms", ["target_type", "target_id"])
        op.create_index("idx_feedback_forms_created_by", "feedback_forms", ["created_by"])

    if "feedback_form_responses" not in tables:
        op.create_table(
            "feedback_form_responses",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("form_id", sa.String(), sa.ForeignKey("feedback_forms.id", ondelete="CASCADE"), nullable=False),
            sa.Column("respondent_id", sa.String(), nullable=True),
            sa.Column("ratings", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("overall_satisfaction", sa.String(), nullable=True),
            sa.Column("submitted_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_ffr_form_id", "feedback_form_responses", ["form_id"])
        op.create_index("idx_ffr_respondent", "feedback_form_responses", ["respondent_id"])


def downgrade() -> None:
    op.drop_table("feedback_form_responses")
    op.drop_table("feedback_forms")
