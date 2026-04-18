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

    # Create billing_users table (idempotent)
    op.execute("""
        CREATE TABLE IF NOT EXISTS billing_users (
            id VARCHAR NOT NULL,
            billing_id VARCHAR NOT NULL,
            user_id VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            counter_name VARCHAR,
            phone VARCHAR,
            email VARCHAR,
            created_at TIMESTAMP WITHOUT TIME ZONE,
            updated_at TIMESTAMP WITHOUT TIME ZONE,
            PRIMARY KEY (id),
            FOREIGN KEY(user_id) REFERENCES users (id),
            UNIQUE (billing_id),
            UNIQUE (user_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_billing_users_billing_id ON billing_users (billing_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_billing_users_user_id ON billing_users (user_id)")

    # Add price column to case_records (idempotent)
    bind = op.get_bind()
    cols = [row[0] for row in bind.execute(
        sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='case_records'")
    )]
    if "price" not in cols:
        op.add_column("case_records", sa.Column("price", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    cols = [row[0] for row in bind.execute(
        sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='case_records'")
    )]
    if "price" in cols:
        op.drop_column("case_records", "price")
    op.execute("DROP INDEX IF EXISTS ix_billing_users_user_id")
    op.execute("DROP INDEX IF EXISTS ix_billing_users_billing_id")
    op.execute("DROP TABLE IF EXISTS billing_users")
