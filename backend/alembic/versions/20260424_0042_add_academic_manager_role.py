"""add academic manager role

Revision ID: 20260424_0042
Revises: 20260424_0041
Create Date: 2026-04-24 00:42:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260424_0042"
down_revision = "20260424_0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'ACADEMIC_MANAGER'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely in-place.
    # This downgrade is intentionally a no-op.
    pass
