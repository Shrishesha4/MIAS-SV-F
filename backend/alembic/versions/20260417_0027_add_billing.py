"""add billing users table, case_records price, BILLING role

Revision ID: 20260417_0027
Revises: 20260417_0026
Create Date: 2026-04-17 23:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260417_0027"
down_revision = "20260417_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add BILLING to user role enum
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'BILLING'")

    # Create billing_users table
    op.create_table(
        "billing_users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("billing_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("counter_name", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("billing_id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_billing_users_billing_id", "billing_users", ["billing_id"])
    op.create_index("ix_billing_users_user_id", "billing_users", ["user_id"])

    # Add price column to case_records
    op.add_column(
        "case_records",
        sa.Column("price", sa.Numeric(10, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("case_records", "price")
    op.drop_index("ix_billing_users_user_id", table_name="billing_users")
    op.drop_index("ix_billing_users_billing_id", table_name="billing_users")
    op.drop_table("billing_users")
