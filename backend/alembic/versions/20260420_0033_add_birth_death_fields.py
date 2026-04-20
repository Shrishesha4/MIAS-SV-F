"""add birth/death structured fields

Revision ID: 20260420_0033
Revises: 20260420_0032
Create Date: 2026-04-20
"""
from alembic import op
import sqlalchemy as sa

revision = "20260420_0033"
down_revision = "20260420_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # DischargeType enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE dischargetype AS ENUM ('REGULAR', 'DEATH', 'LAMA', 'REFERRAL', 'ABSCONDED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Admission: discharge_type, is_birth_related
    op.add_column("admissions", sa.Column("discharge_type", sa.Enum(
        "REGULAR", "DEATH", "LAMA", "REFERRAL", "ABSCONDED",
        name="dischargetype", create_type=False
    ), nullable=True))
    op.add_column("admissions", sa.Column("is_birth_related", sa.Boolean(), server_default="false", nullable=False))

    # Patient: is_deceased, mother_patient_id
    op.add_column("patients", sa.Column("is_deceased", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("patients", sa.Column("mother_patient_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_patient_mother",
        "patients", "patients",
        ["mother_patient_id"], ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_patient_mother", "patients", type_="foreignkey")
    op.drop_column("patients", "mother_patient_id")
    op.drop_column("patients", "is_deceased")
    op.drop_column("admissions", "is_birth_related")
    op.drop_column("admissions", "discharge_type")
    op.execute("DROP TYPE IF EXISTS dischargetype")
