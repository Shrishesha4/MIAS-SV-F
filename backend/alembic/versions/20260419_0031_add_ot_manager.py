"""add ot_manager role and ot_managers table

Revision ID: 20260419_0031
Revises: 20260418_0030
Create Date: 2026-04-19
"""
from alembic import op

revision = "20260419_0031"
down_revision = "20260418_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add OT_MANAGER to userrole enum
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'OT_MANAGER'")

    # Create ot_managers table (idempotent)
    op.execute("""
        CREATE TABLE IF NOT EXISTS ot_managers (
            id VARCHAR NOT NULL,
            manager_id VARCHAR NOT NULL,
            user_id VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            phone VARCHAR,
            email VARCHAR,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE (manager_id),
            UNIQUE (user_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_ot_managers_manager_id ON ot_managers (manager_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ot_managers_user_id ON ot_managers (user_id)")

    # Add student_name to ot_bookings if not already there
    op.execute("""
        ALTER TABLE ot_bookings
        ADD COLUMN IF NOT EXISTS student_name VARCHAR
    """)


def downgrade() -> None:
    op.drop_table("ot_managers")
