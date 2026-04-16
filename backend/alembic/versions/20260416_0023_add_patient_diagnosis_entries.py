"""add patient diagnosis entries

Revision ID: 20260416_0023
Revises: 20260416_0022
Create Date: 2026-04-16 09:10:00.000000

"""
from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa


revision = "20260416_0023"
down_revision = "20260416_0022"
branch_labels = None
depends_on = None


def _get_table_names(bind) -> set[str]:
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def _get_index_names(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)

    if "patient_diagnosis_entries" not in tables:
        op.create_table(
            "patient_diagnosis_entries",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("patient_id", sa.String(), nullable=False),
            sa.Column("diagnosis", sa.Text(), nullable=False),
            sa.Column("icd_code", sa.String(), nullable=True),
            sa.Column("icd_description", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("added_by", sa.String(), nullable=True),
            sa.Column("added_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("removed_by", sa.String(), nullable=True),
            sa.Column("removed_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    indexes = _get_index_names(bind, "patient_diagnosis_entries")
    if "idx_patient_diagnosis_patient_active" not in indexes:
        op.create_index(
            "idx_patient_diagnosis_patient_active",
            "patient_diagnosis_entries",
            ["patient_id", "is_active"],
            unique=False,
        )
    if "idx_patient_diagnosis_added_at" not in indexes:
        op.create_index(
            "idx_patient_diagnosis_added_at",
            "patient_diagnosis_entries",
            ["added_at"],
            unique=False,
        )

    patient_rows = bind.execute(
        sa.text(
            """
            SELECT id, primary_diagnosis, diagnosis_doctor, updated_at, created_at
            FROM patients
            WHERE primary_diagnosis IS NOT NULL
              AND TRIM(primary_diagnosis) != ''
            """
        )
    ).mappings().all()

    for row in patient_rows:
        existing = bind.execute(
            sa.text(
                """
                SELECT 1
                FROM patient_diagnosis_entries
                WHERE patient_id = :patient_id
                  AND diagnosis = :diagnosis
                  AND is_active = true
                LIMIT 1
                """
            ),
            {"patient_id": row["id"], "diagnosis": row["primary_diagnosis"]},
        ).first()
        if existing:
            continue

        bind.execute(
            sa.text(
                """
                INSERT INTO patient_diagnosis_entries (
                    id, patient_id, diagnosis, icd_code, icd_description,
                    is_active, added_by, added_at, removed_by, removed_at
                ) VALUES (
                    :id, :patient_id, :diagnosis, NULL, NULL,
                    true, :added_by, :added_at, NULL, NULL
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "patient_id": row["id"],
                "diagnosis": row["primary_diagnosis"].strip(),
                "added_by": row["diagnosis_doctor"],
                "added_at": row["updated_at"] or row["created_at"],
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)
    if "patient_diagnosis_entries" in tables:
        op.drop_table("patient_diagnosis_entries")
