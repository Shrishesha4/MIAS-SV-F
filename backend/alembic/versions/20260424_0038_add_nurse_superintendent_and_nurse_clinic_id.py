"""add nurse superintendent role and clinic assignment to nurses

Revision ID: 20260424_0038
Revises: 20260423_0037
Create Date: 2026-04-24
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260424_0038"
down_revision = "20260423_0037"
branch_labels = None
depends_on = None


def _get_table_names(bind) -> set[str]:
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def _get_column_names(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def _get_index_names(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'NURSE_SUPERINTENDENT'")

    tables = _get_table_names(bind)
    if "nurses" not in tables:
        return

    columns = _get_column_names(bind, "nurses")
    if "clinic_id" not in columns:
        op.add_column("nurses", sa.Column("clinic_id", sa.String(), nullable=True))
        op.create_foreign_key(
            "fk_nurses_clinic_id",
            "nurses",
            "clinics",
            ["clinic_id"],
            ["id"],
        )

    indexes = _get_index_names(bind, "nurses")
    if "ix_nurses_clinic_id" not in indexes:
        op.create_index("ix_nurses_clinic_id", "nurses", ["clinic_id"], unique=False)

    if "clinics" in tables:
        bind.execute(sa.text("""
            UPDATE nurses AS n
            SET clinic_id = c.id
            FROM clinics AS c
            WHERE n.clinic_id IS NULL
              AND n.hospital IS NOT NULL
              AND lower(trim(n.hospital)) = lower(trim(c.name))
        """))


def downgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)
    if "nurses" not in tables:
        return

    indexes = _get_index_names(bind, "nurses")
    if "ix_nurses_clinic_id" in indexes:
        op.drop_index("ix_nurses_clinic_id", table_name="nurses")

    columns = _get_column_names(bind, "nurses")
    if "clinic_id" in columns:
        op.drop_constraint("fk_nurses_clinic_id", "nurses", type_="foreignkey")
        op.drop_column("nurses", "clinic_id")