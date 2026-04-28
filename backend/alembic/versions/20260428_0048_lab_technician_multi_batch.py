"""lab technician many-to-many batch membership

Revision ID: 20260428_0048
Revises: 20260428_0047
Create Date: 2026-04-28
"""
from alembic import op

revision = "20260428_0048"
down_revision = "20260428_0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the new M2M join table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS lab_technician_batch_members (
            batch_id  VARCHAR NOT NULL,
            technician_id VARCHAR NOT NULL,
            PRIMARY KEY (batch_id, technician_id),
            FOREIGN KEY (batch_id)      REFERENCES lab_technician_groups(id) ON DELETE CASCADE,
            FOREIGN KEY (technician_id) REFERENCES lab_technicians(id)        ON DELETE CASCADE
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_lab_technician_batch_members_batch_id "
        "ON lab_technician_batch_members (batch_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_lab_technician_batch_members_technician_id "
        "ON lab_technician_batch_members (technician_id)"
    )

    # Migrate existing 1:N group_id data into the new M2M table
    op.execute(
        """
        INSERT INTO lab_technician_batch_members (batch_id, technician_id)
        SELECT group_id, id
        FROM   lab_technicians
        WHERE  group_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )

    # Drop the old FK column
    op.execute("DROP INDEX IF EXISTS ix_lab_technicians_group_id")
    op.execute("ALTER TABLE lab_technicians DROP COLUMN IF EXISTS group_id")


def downgrade() -> None:
    # Re-add the group_id column
    op.execute(
        "ALTER TABLE lab_technicians ADD COLUMN IF NOT EXISTS "
        "group_id VARCHAR REFERENCES lab_technician_groups(id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_lab_technicians_group_id ON lab_technicians (group_id)"
    )

    # Best-effort restore: assign each technician to the first batch they belong to
    op.execute(
        """
        UPDATE lab_technicians lt
        SET    group_id = m.batch_id
        FROM   (
            SELECT DISTINCT ON (technician_id) technician_id, batch_id
            FROM   lab_technician_batch_members
            ORDER  BY technician_id, batch_id
        ) m
        WHERE  lt.id = m.technician_id
        """
    )

    op.execute("DROP INDEX IF EXISTS ix_lab_technician_batch_members_technician_id")
    op.execute("DROP INDEX IF EXISTS ix_lab_technician_batch_members_batch_id")
    op.execute("DROP TABLE IF EXISTS lab_technician_batch_members")
