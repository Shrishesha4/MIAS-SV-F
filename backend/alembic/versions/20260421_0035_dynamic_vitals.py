"""add dynamic vital storage and value style

Revision ID: 20260421_0035
Revises: 20260421_0034
Create Date: 2026-04-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260421_0035"
down_revision = "20260421_0034"
branch_labels = None
depends_on = None


def _get_column_names(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()

    vital_parameter_columns = _get_column_names(bind, "vital_parameters")
    if "value_style" not in vital_parameter_columns:
        op.add_column(
            "vital_parameters",
            sa.Column("value_style", sa.String(), nullable=False, server_default="single"),
        )

    vital_columns = _get_column_names(bind, "vitals")
    if "extra_values" not in vital_columns:
        op.add_column(
            "vitals",
            sa.Column("extra_values", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        )


def downgrade() -> None:
    bind = op.get_bind()

    vital_columns = _get_column_names(bind, "vitals")
    if "extra_values" in vital_columns:
        op.drop_column("vitals", "extra_values")

    vital_parameter_columns = _get_column_names(bind, "vital_parameters")
    if "value_style" in vital_parameter_columns:
        op.drop_column("vital_parameters", "value_style")
