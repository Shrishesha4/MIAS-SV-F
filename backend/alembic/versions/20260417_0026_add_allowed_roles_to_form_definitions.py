"""add allowed_roles to form_definitions

Revision ID: 20260417_0026
Revises: 20260416_0025
Create Date: 2026-04-17 21:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260417_0026"
down_revision = "20260416_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "form_definitions",
        sa.Column("allowed_roles", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("form_definitions", "allowed_roles")
