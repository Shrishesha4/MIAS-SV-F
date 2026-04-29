"""add checkout fields to daily checkins

Revision ID: 20260428_0049
Revises: 20260428_0048
Create Date: 2026-04-28
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260428_0049"
down_revision = "20260428_0048"
branch_labels = None
depends_on = None


def _get_table_names(bind) -> set[str]:
	inspector = sa.inspect(bind)
	return set(inspector.get_table_names())


def _get_column_names(bind, table_name: str) -> set[str]:
	inspector = sa.inspect(bind)
	return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
	bind = op.get_bind()
	tables = _get_table_names(bind)
	if "daily_checkins" not in tables:
		return

	columns = _get_column_names(bind, "daily_checkins")

	if "checked_out_at" not in columns:
		op.add_column("daily_checkins", sa.Column("checked_out_at", sa.DateTime(), nullable=True))
	if "check_in_location" not in columns:
		op.add_column("daily_checkins", sa.Column("check_in_location", sa.String(), nullable=True))
	if "check_out_location" not in columns:
		op.add_column("daily_checkins", sa.Column("check_out_location", sa.String(), nullable=True))


def downgrade() -> None:
	bind = op.get_bind()
	tables = _get_table_names(bind)
	if "daily_checkins" not in tables:
		return

	columns = _get_column_names(bind, "daily_checkins")
	if "check_out_location" in columns:
		op.drop_column("daily_checkins", "check_out_location")
	if "check_in_location" in columns:
		op.drop_column("daily_checkins", "check_in_location")
	if "checked_out_at" in columns:
		op.drop_column("daily_checkins", "checked_out_at")
