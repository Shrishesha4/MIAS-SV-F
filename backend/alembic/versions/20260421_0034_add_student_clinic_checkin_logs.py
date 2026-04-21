"""add student clinic checkin logs

Revision ID: 20260421_0034
Revises: 20260420_0033
Create Date: 2026-04-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260421_0034"
down_revision = "20260420_0033"
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

    if "student_clinic_checkin_logs" not in tables:
        op.create_table(
            "student_clinic_checkin_logs",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("student_id", sa.String(), nullable=False),
            sa.Column("clinic_id", sa.String(), nullable=False),
            sa.Column("clinic_session_id", sa.String(), nullable=False),
            sa.Column("checked_in_at", sa.DateTime(), nullable=False),
            sa.Column("checked_out_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
            sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
            sa.ForeignKeyConstraint(["clinic_session_id"], ["clinic_sessions.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("clinic_session_id"),
        )

    indexes = _get_index_names(bind, "student_clinic_checkin_logs")
    columns = _get_column_names(bind, "student_clinic_checkin_logs")

    if "ix_student_clinic_checkin_logs_student_id" not in indexes and "student_id" in columns:
        op.create_index(
            "ix_student_clinic_checkin_logs_student_id",
            "student_clinic_checkin_logs",
            ["student_id"],
            unique=False,
        )
    if "ix_student_clinic_checkin_logs_clinic_id" not in indexes and "clinic_id" in columns:
        op.create_index(
            "ix_student_clinic_checkin_logs_clinic_id",
            "student_clinic_checkin_logs",
            ["clinic_id"],
            unique=False,
        )
    if "ix_student_clinic_checkin_logs_clinic_session_id" not in indexes and "clinic_session_id" in columns:
        op.create_index(
            "ix_student_clinic_checkin_logs_clinic_session_id",
            "student_clinic_checkin_logs",
            ["clinic_session_id"],
            unique=True,
        )
    if "idx_student_clinic_checkin_logs_student_time" not in indexes:
        op.create_index(
            "idx_student_clinic_checkin_logs_student_time",
            "student_clinic_checkin_logs",
            ["student_id", "checked_in_at"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)
    if "student_clinic_checkin_logs" in tables:
        op.drop_table("student_clinic_checkin_logs")
