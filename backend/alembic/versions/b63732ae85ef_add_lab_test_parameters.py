"""add lab test parameters

Revision ID: b63732ae85ef
Revises: 20260426_0045
Create Date: 2026-04-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b63732ae85ef"
down_revision = "20260426_0045"
branch_labels = None
depends_on = None


def _table_exists(bind, name: str) -> bool:
    return name in set(sa.inspect(bind).get_table_names())


def upgrade() -> None:
    bind = op.get_bind()

    if not _table_exists(bind, "lab_test_parameters"):
        op.create_table(
            "lab_test_parameters",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("test_id", sa.String(), sa.ForeignKey("lab_tests.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("unit", sa.String(), nullable=True),
            sa.Column("reference_required", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("normal_range", sa.String(), nullable=True),
            sa.Column("low", sa.Numeric(12, 4), nullable=True),
            sa.Column("critically_low", sa.Numeric(12, 4), nullable=True),
            sa.Column("high", sa.Numeric(12, 4), nullable=True),
            sa.Column("critically_high", sa.Numeric(12, 4), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_lab_test_parameters_test_id", "lab_test_parameters", ["test_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if _table_exists(bind, "lab_test_parameters"):
        op.drop_index("ix_lab_test_parameters_test_id", table_name="lab_test_parameters")
        op.drop_table("lab_test_parameters")
