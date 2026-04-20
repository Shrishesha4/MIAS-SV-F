"""add MRD role and mrd_query_audit table

Revision ID: 20260420_0032
Revises: 20260419_0031
Create Date: 2026-04-20
"""
from alembic import op

revision = "20260420_0032"
down_revision = "20260419_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add MRD to userrole enum
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'MRD'")

    # Audit table on OLTP (lightweight — one INSERT per MRD query)
    op.execute("""
        CREATE TABLE IF NOT EXISTS mrd_query_audit (
            id VARCHAR NOT NULL,
            user_id VARCHAR NOT NULL,
            route VARCHAR NOT NULL,
            filter_json TEXT,
            rows_returned INTEGER DEFAULT 0,
            duration_ms INTEGER DEFAULT 0,
            status VARCHAR DEFAULT 'ok',
            created_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (id)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_mrd_query_audit_user_id "
        "ON mrd_query_audit (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_mrd_query_audit_created_at "
        "ON mrd_query_audit (created_at)"
    )


def downgrade() -> None:
    op.drop_table("mrd_query_audit")
    # Note: PostgreSQL does not support removing enum values
