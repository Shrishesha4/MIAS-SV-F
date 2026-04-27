"""add geofencing tables

Revision ID: 20260427_0046
Revises: 20260426_0045
Create Date: 2026-04-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260427_0046"
down_revision = "20260426_0045"
branch_labels = None
depends_on = None


def _table_exists(bind, name: str) -> bool:
    return name in set(sa.inspect(bind).get_table_names())


def upgrade() -> None:
    bind = op.get_bind()

    if not _table_exists(bind, "geofence_zones"):
        op.create_table(
            "geofence_zones",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("polygon", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists(bind, "patient_geofence_proofs"):
        op.create_table(
            "patient_geofence_proofs",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("short_code", sa.String(8), nullable=True),
            sa.Column("patient_id", sa.String(), sa.ForeignKey("patients.id"), nullable=True),
            sa.Column("lat", sa.Float(), nullable=False),
            sa.Column("lng", sa.Float(), nullable=False),
            sa.Column("accuracy", sa.Float(), nullable=True),
            sa.Column("is_valid", sa.Boolean(), nullable=False),
            sa.Column("zone_id", sa.String(), sa.ForeignKey("geofence_zones.id"), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("consumed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "idx_geofence_proof_short_code",
            "patient_geofence_proofs",
            ["short_code"],
        )
        op.create_index(
            "idx_geofence_proof_patient",
            "patient_geofence_proofs",
            ["patient_id"],
        )
        op.create_index(
            "idx_geofence_proof_expires",
            "patient_geofence_proofs",
            ["expires_at"],
        )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_geofence_proof_expires")
    op.execute("DROP INDEX IF EXISTS idx_geofence_proof_patient")
    op.execute("DROP INDEX IF EXISTS idx_geofence_proof_short_code")
    op.execute("DROP TABLE IF EXISTS patient_geofence_proofs")
    op.execute("DROP TABLE IF EXISTS geofence_zones")
