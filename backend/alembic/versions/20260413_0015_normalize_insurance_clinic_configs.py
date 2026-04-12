"""normalize insurance_clinic_configs walk_in_type and add unique constraint

Revision ID: 20260413_0015
Revises: 20260413_0014
Create Date: 2026-04-13 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '20260413_0015'
down_revision = '20260413_0014'
branch_labels = None
depends_on = None


def _get_table_names(bind) -> set[str]:
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def _constraint_exists(bind, table_name: str, constraint_name: str) -> bool:
    inspector = sa.inspect(bind)
    for uc in inspector.get_unique_constraints(table_name):
        if uc['name'] == constraint_name:
            return True
    for idx in inspector.get_indexes(table_name):
        if idx['name'] == constraint_name:
            return True
    return False


def upgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)

    if 'insurance_clinic_configs' not in tables:
        return

    # Step B: Safely convert legacy walk_in_type values that match a patient
    # category name assigned to the same insurance category (exactly one match).
    bind.execute(sa.text("""
        WITH candidate_targets AS (
            SELECT
                icc.id,
                COUNT(*) AS candidate_count,
                MIN('WALKIN_' || upper(replace(replace(trim(pco.name), ' ', '_'), '-', '_'))) AS target_walk_in_type
            FROM insurance_clinic_configs icc
            JOIN insurance_categories ic
              ON ic.id = icc.insurance_category_id
            JOIN insurance_patient_category_association ipa
              ON ipa.insurance_category_id = ic.id
            JOIN patient_category_options pco
              ON pco.id = ipa.patient_category_id
            WHERE lower(replace(replace(icc.walk_in_type, 'WALKIN_', ''), '_', ' ')) = lower(trim(pco.name))
            GROUP BY icc.id
        )
        UPDATE insurance_clinic_configs icc
        SET walk_in_type = ct.target_walk_in_type,
            updated_at = NOW()
        FROM candidate_targets ct
        WHERE icc.id = ct.id
          AND ct.candidate_count = 1
          AND icc.walk_in_type <> ct.target_walk_in_type
    """))

    # Step C: Disable rows still invalid (not in valid patient-category-derived
    # set and not NO_WALK_IN) after safe conversion above.
    bind.execute(sa.text("""
        WITH valid_walkins AS (
            SELECT
                ipa.insurance_category_id,
                'WALKIN_' || upper(replace(replace(trim(pco.name), ' ', '_'), '-', '_')) AS walk_in_type
            FROM insurance_patient_category_association ipa
            JOIN patient_category_options pco
              ON pco.id = ipa.patient_category_id
        )
        UPDATE insurance_clinic_configs icc
        SET is_enabled = false,
            updated_at = NOW()
        WHERE icc.walk_in_type <> 'NO_WALK_IN'
          AND NOT EXISTS (
              SELECT 1
              FROM valid_walkins vw
              WHERE vw.insurance_category_id = icc.insurance_category_id
                AND vw.walk_in_type = icc.walk_in_type
          )
    """))

    # Step E: Delete losing duplicates deterministically.
    # Winning row per (insurance_category_id, clinic_id, walk_in_type):
    #   1. is_enabled=true preferred
    #   2. latest updated_at
    #   3. latest created_at
    #   4. max id
    bind.execute(sa.text("""
        WITH ranked AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY insurance_category_id, clinic_id, walk_in_type
                    ORDER BY is_enabled DESC, updated_at DESC NULLS LAST, created_at DESC NULLS LAST, id DESC
                ) AS rn
            FROM insurance_clinic_configs
        )
        DELETE FROM insurance_clinic_configs
        WHERE id IN (
            SELECT id FROM ranked WHERE rn > 1
        )
    """))

    # Step F: Add unique constraint on the business key.
    constraint_name = 'uq_insurance_clinic_configs_category_clinic_walkin'
    if not _constraint_exists(bind, 'insurance_clinic_configs', constraint_name):
        op.create_unique_constraint(
            constraint_name,
            'insurance_clinic_configs',
            ['insurance_category_id', 'clinic_id', 'walk_in_type'],
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)

    if 'insurance_clinic_configs' not in tables:
        return

    constraint_name = 'uq_insurance_clinic_configs_category_clinic_walkin'
    if _constraint_exists(bind, 'insurance_clinic_configs', constraint_name):
        op.drop_constraint(
            constraint_name,
            'insurance_clinic_configs',
            type_='unique',
        )
