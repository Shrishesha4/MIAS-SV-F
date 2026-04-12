"""add clinic_id to patients table

Revision ID: 20260413_0014
Revises: 20260413_0013
Create Date: 2026-04-13 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '20260413_0014'
down_revision = '20260413_0013'
branch_labels = None
depends_on = None


def _get_table_names(bind) -> set[str]:
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def _get_column_names(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {column['name'] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)
    
    # Add clinic_id to patients table
    if 'patients' in tables:
        columns = _get_column_names(bind, 'patients')
        if 'clinic_id' not in columns:
            op.add_column('patients', sa.Column('clinic_id', sa.String(), nullable=True))
            # Create foreign key constraint
            op.create_foreign_key(
                'fk_patients_clinic_id',
                'patients', 'clinics',
                ['clinic_id'], ['id']
            )


def downgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)
    
    # Remove clinic_id from patients table
    if 'patients' in tables:
        columns = _get_column_names(bind, 'patients')
        if 'clinic_id' in columns:
            op.drop_constraint('fk_patients_clinic_id', 'patients', type_='foreignkey')
            op.drop_column('patients', 'clinic_id')
