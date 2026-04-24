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


def upgrade() -> None:
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

    op.add_column(
        "prescriptions",
        sa.Column("dispensing_status", _dispensing_status_enum, nullable=True),
    )
    op.add_column("prescriptions", sa.Column("prepared_at", sa.DateTime(), nullable=True))
    op.add_column("prescriptions", sa.Column("prepared_by", sa.String(), nullable=True))
    op.add_column("prescriptions", sa.Column("issued_at", sa.DateTime(), nullable=True))
    op.add_column("prescriptions", sa.Column("issued_by", sa.String(), nullable=True))

    op.create_foreign_key(
        "fk_prescriptions_prepared_by_users",
        "prescriptions",
        "users",
        ["prepared_by"],
        ["id"],
    )
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
    op.create_index(
        "idx_prescription_dispensing_status_date",
        "prescriptions",
        ["dispensing_status", "date"],
        unique=False,
    )
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