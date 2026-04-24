"""add nutritionist note completion status

Revision ID: 20260424_0041
Revises: 20260424_0040
Create Date: 2026-04-24
"""

from alembic import op

revision = "20260424_0041"
down_revision = "20260424_0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE nutritionist_notes
        ADD COLUMN IF NOT EXISTS is_completed BOOLEAN NOT NULL DEFAULT FALSE
        """
    )
    op.execute(
        """
        ALTER TABLE nutritionist_notes
        ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP NULL
        """
    )
    op.execute(
        """
        UPDATE nutritionist_notes
        SET
            is_completed = TRUE,
            completed_at = COALESCE(completed_at, updated_at)
        WHERE NULLIF(BTRIM(content), '') IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE nutritionist_notes
        DROP COLUMN IF EXISTS completed_at
        """
    )
    op.execute(
        """
        ALTER TABLE nutritionist_notes
        DROP COLUMN IF EXISTS is_completed
        """
    )
