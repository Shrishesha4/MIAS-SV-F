"""Add operation theaters and OT bookings

Revision ID: 20260418_0030
Revises: 20260418_0029
Create Date: 2026-04-18 15:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260418_0030"
down_revision = "20260418_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use execute with IF NOT EXISTS to be idempotent
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'otstatus') THEN
                CREATE TYPE otstatus AS ENUM ('SCHEDULED','CONFIRMED','IN_PROGRESS','COMPLETED','CANCELLED');
            END IF;
        END $$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS operation_theaters (
            id VARCHAR NOT NULL,
            ot_id VARCHAR NOT NULL,
            name VARCHAR,
            location VARCHAR,
            description VARCHAR,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE (ot_id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS ot_bookings (
            id VARCHAR NOT NULL,
            theater_id VARCHAR NOT NULL,
            patient_id VARCHAR NOT NULL,
            student_id VARCHAR,
            date VARCHAR NOT NULL,
            start_time VARCHAR NOT NULL,
            end_time VARCHAR NOT NULL,
            procedure VARCHAR NOT NULL,
            doctor_name VARCHAR NOT NULL,
            notes TEXT,
            status otstatus NOT NULL DEFAULT 'SCHEDULED',
            approved_by VARCHAR,
            approved_at TIMESTAMP,
            created_at TIMESTAMP,
            PRIMARY KEY (id),
            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (theater_id) REFERENCES operation_theaters(id)
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_ot_booking_date_theater ON ot_bookings (date, theater_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ot_booking_patient ON ot_bookings (patient_id)")


def downgrade() -> None:
    op.drop_index("idx_ot_booking_patient", table_name="ot_bookings")
    op.drop_index("idx_ot_booking_date_theater", table_name="ot_bookings")
    op.drop_table("ot_bookings")
    op.drop_table("operation_theaters")
    op.execute("DROP TYPE IF EXISTS otstatus")
