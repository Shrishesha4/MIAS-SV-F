"""add case record form snapshot

Revision ID: 20260416_0024
Revises: 20260416_0023
Create Date: 2026-04-16 10:25:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260416_0024"
down_revision = "20260416_0023"
branch_labels = None
depends_on = None


def _get_column_names(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    columns = _get_column_names(bind, "case_records")

    if "form_name" not in columns:
        op.add_column("case_records", sa.Column("form_name", sa.String(), nullable=True))
    if "form_description" not in columns:
        op.add_column("case_records", sa.Column("form_description", sa.Text(), nullable=True))
    if "form_fields" not in columns:
        op.add_column("case_records", sa.Column("form_fields", sa.JSON(), nullable=True))
    if "form_values" not in columns:
        op.add_column("case_records", sa.Column("form_values", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    columns = _get_column_names(bind, "case_records")

    if "form_values" in columns:
        op.drop_column("case_records", "form_values")
    if "form_fields" in columns:
        op.drop_column("case_records", "form_fields")
    if "form_description" in columns:
        op.drop_column("case_records", "form_description")
    if "form_name" in columns:
        op.drop_column("case_records", "form_name")
