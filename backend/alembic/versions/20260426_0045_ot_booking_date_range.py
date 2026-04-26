"""add from/to date support to ot bookings

Revision ID: 20260426_0045
Revises: 20260425_0044
Create Date: 2026-04-26
"""

from alembic import op

revision = "20260426_0045"
down_revision = "20260425_0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE ot_bookings ADD COLUMN IF NOT EXISTS from_date VARCHAR")
    op.execute("ALTER TABLE ot_bookings ADD COLUMN IF NOT EXISTS to_date VARCHAR")

    # Backfill legacy rows so range fields are always populated.
    op.execute(
        """
        UPDATE ot_bookings
        SET from_date = COALESCE(from_date, date),
            to_date = COALESCE(to_date, from_date, date)
        """
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ot_booking_range_theater ON ot_bookings (from_date, to_date, theater_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_ot_booking_range_theater")
    op.execute("ALTER TABLE ot_bookings DROP COLUMN IF EXISTS to_date")
    op.execute("ALTER TABLE ot_bookings DROP COLUMN IF EXISTS from_date")
