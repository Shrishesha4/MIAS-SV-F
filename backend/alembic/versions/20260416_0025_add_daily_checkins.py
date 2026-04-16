"""add daily checkins

Revision ID: 20260416_0025
Revises: 20260416_0024
Create Date: 2026-04-16 10:45:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260416_0025"
down_revision = "20260416_0024"
branch_labels = None
depends_on = None


def _get_table_names(bind) -> set[str]:
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def _get_index_names(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _get_column_names(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)
    existing_userrole = postgresql.ENUM(
        "PATIENT",
        "STUDENT",
        "FACULTY",
        "ADMIN",
        "RECEPTION",
        "NURSE",
        name="userrole",
        create_type=False,
    )

    if "daily_checkins" not in tables:
        op.create_table(
            "daily_checkins",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column(
                "role",
                existing_userrole,
                nullable=False,
            ),
            sa.Column("check_in_date", sa.Date(), nullable=False),
            sa.Column("checked_in_at", sa.DateTime(), nullable=False),
            sa.Column("clinic_id", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        # Add clinic_id column if table exists but column doesn't
        cols = _get_column_names(bind, "daily_checkins")
        if "clinic_id" not in cols:
            op.add_column("daily_checkins", sa.Column("clinic_id", sa.String(), nullable=True))
            op.create_foreign_key(
                "fk_daily_checkins_clinic_id",
                "daily_checkins",
                "clinics",
                ["clinic_id"],
                ["id"],
            )

    indexes = _get_index_names(bind, "daily_checkins")
    if "idx_daily_checkins_user_date" not in indexes:
        op.create_index(
            "idx_daily_checkins_user_date",
            "daily_checkins",
            ["user_id", "check_in_date"],
            unique=True,
        )
    if "idx_daily_checkins_role_date" not in indexes:
        op.create_index(
            "idx_daily_checkins_role_date",
            "daily_checkins",
            ["role", "check_in_date"],
            unique=False,
        )
    if "ix_daily_checkins_clinic_id" not in indexes:
        op.create_index(
            "ix_daily_checkins_clinic_id",
            "daily_checkins",
            ["clinic_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)
    if "daily_checkins" in tables:
        op.drop_table("daily_checkins")
