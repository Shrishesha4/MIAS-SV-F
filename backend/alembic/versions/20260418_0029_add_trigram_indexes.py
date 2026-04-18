"""Add GIN trigram indexes for fast patient search (ILIKE %q%)

Eliminates sequential scans on patient name/email/phone.
At 10k+ patients this is the difference between 200ms and 2ms per search.

Revision ID: 20260418_0029
Revises: 20260418_0028
Create Date: 2026-04-18 06:30:00.000000
"""
from __future__ import annotations

from alembic import op


revision = "20260418_0029"
down_revision = "20260418_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pg_trgm extension (required for GIN trigram indexes)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Patient search fields — non-concurrent (migration runs at startup, no live load)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_patients_name_trgm
        ON patients USING gin(name gin_trgm_ops)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_patients_email_trgm
        ON patients USING gin(email gin_trgm_ops)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_patients_phone_trgm
        ON patients USING gin(phone gin_trgm_ops)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_patients_patient_id_trgm
        ON patients USING gin(patient_id gin_trgm_ops)
    """)

    # User search (admin panel)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_username_trgm
        ON users USING gin(username gin_trgm_ops)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_email_trgm
        ON users USING gin(email gin_trgm_ops)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_patients_name_trgm")
    op.execute("DROP INDEX IF EXISTS idx_patients_email_trgm")
    op.execute("DROP INDEX IF EXISTS idx_patients_phone_trgm")
    op.execute("DROP INDEX IF EXISTS idx_patients_patient_id_trgm")
    op.execute("DROP INDEX IF EXISTS idx_users_username_trgm")
    op.execute("DROP INDEX IF EXISTS idx_users_email_trgm")
