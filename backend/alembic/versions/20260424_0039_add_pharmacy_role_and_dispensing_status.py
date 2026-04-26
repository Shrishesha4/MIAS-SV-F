"""add pharmacy role and prescription dispensing status

Revision ID: 20260424_0039
Revises: 20260424_0038
Create Date: 2026-04-24
"""
from alembic import op
import sqlalchemy as sa


revision = "20260424_0039"
down_revision = "20260424_0038"
branch_labels = None
depends_on = None


_dispensing_status_enum = sa.Enum(
    "PENDING_PREPARATION",
    "READY_FOR_DISPATCH",
    "ISSUED",
    name="prescriptiondispensingstatus",
)


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _fk_exists(inspector: sa.Inspector, table_name: str, fk_name: str) -> bool:
    return any(fk.get("name") == fk_name for fk in inspector.get_foreign_keys(table_name))


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(idx.get("name") == index_name for idx in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'PHARMACY'")
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE prescriptiondispensingstatus AS ENUM (
                'PENDING_PREPARATION',
                'READY_FOR_DISPATCH',
                'ISSUED'
            );
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    if not _column_exists(inspector, "prescriptions", "dispensing_status"):
        op.add_column(
            "prescriptions",
            sa.Column("dispensing_status", _dispensing_status_enum, nullable=True),
        )
    if not _column_exists(inspector, "prescriptions", "prepared_at"):
        op.add_column("prescriptions", sa.Column("prepared_at", sa.DateTime(), nullable=True))
    if not _column_exists(inspector, "prescriptions", "prepared_by"):
        op.add_column("prescriptions", sa.Column("prepared_by", sa.String(), nullable=True))
    if not _column_exists(inspector, "prescriptions", "issued_at"):
        op.add_column("prescriptions", sa.Column("issued_at", sa.DateTime(), nullable=True))
    if not _column_exists(inspector, "prescriptions", "issued_by"):
        op.add_column("prescriptions", sa.Column("issued_by", sa.String(), nullable=True))

    inspector = sa.inspect(bind)
    if not _fk_exists(inspector, "prescriptions", "fk_prescriptions_prepared_by_users"):
        op.create_foreign_key(
            "fk_prescriptions_prepared_by_users",
            "prescriptions",
            "users",
            ["prepared_by"],
            ["id"],
        )
    if not _fk_exists(inspector, "prescriptions", "fk_prescriptions_issued_by_users"):
        op.create_foreign_key(
            "fk_prescriptions_issued_by_users",
            "prescriptions",
            "users",
            ["issued_by"],
            ["id"],
        )

    op.execute(
        """
        UPDATE prescriptions
        SET dispensing_status = CASE
            WHEN status::text = 'RECEIVE' THEN 'READY_FOR_DISPATCH'::prescriptiondispensingstatus
            WHEN status::text IN ('BOUGHT', 'COMPLETED') THEN 'ISSUED'::prescriptiondispensingstatus
            ELSE 'PENDING_PREPARATION'::prescriptiondispensingstatus
        END
        WHERE dispensing_status IS NULL
        """
    )

    op.alter_column("prescriptions", "dispensing_status", nullable=False)

    inspector = sa.inspect(bind)
    if not _index_exists(inspector, "prescriptions", "idx_prescription_dispensing_status_date"):
        op.create_index(
            "idx_prescription_dispensing_status_date",
            "prescriptions",
            ["dispensing_status", "date"],
            unique=False,
        )
    if not _index_exists(inspector, "prescriptions", "ix_prescriptions_issued_at"):
        op.create_index("ix_prescriptions_issued_at", "prescriptions", ["issued_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_prescriptions_issued_at", table_name="prescriptions")
    op.drop_index("idx_prescription_dispensing_status_date", table_name="prescriptions")
    op.drop_constraint("fk_prescriptions_issued_by_users", "prescriptions", type_="foreignkey")
    op.drop_constraint("fk_prescriptions_prepared_by_users", "prescriptions", type_="foreignkey")
    op.drop_column("prescriptions", "issued_by")
    op.drop_column("prescriptions", "issued_at")
    op.drop_column("prescriptions", "prepared_by")
    op.drop_column("prescriptions", "prepared_at")
    op.drop_column("prescriptions", "dispensing_status")
    op.execute("DROP TYPE IF EXISTS prescriptiondispensingstatus")