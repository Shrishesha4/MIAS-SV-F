"""add lab_test_id to reports

Revision ID: 20260428_0047
Revises: 20260427_0046
Create Date: 2026-04-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260428_0047"
down_revision = "20260427_0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("reports")}
    if "lab_test_id" not in cols:
        op.add_column(
            "reports",
            sa.Column("lab_test_id", sa.String(), sa.ForeignKey("lab_tests.id"), nullable=True),
        )
        op.create_index(
            "ix_reports_lab_test_id",
            "reports",
            ["lab_test_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("reports")}
    if "lab_test_id" in cols:
        op.drop_index("ix_reports_lab_test_id", table_name="reports")
        op.drop_column("reports", "lab_test_id")
