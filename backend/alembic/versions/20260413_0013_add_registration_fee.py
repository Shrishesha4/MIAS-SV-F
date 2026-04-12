"""add registration_fee to patient_category_options

Revision ID: 20260413_0013
Revises: 20260413_0012
Create Date: 2026-04-13 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '20260413_0013'
down_revision = '20260413_0012'
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
    
    # Add registration_fee to patient_category_options
    if 'patient_category_options' in tables:
        columns = _get_column_names(bind, 'patient_category_options')
        if 'registration_fee' not in columns:
            op.add_column('patient_category_options', sa.Column('registration_fee', sa.Integer(), nullable=False, server_default='100'))
    
    # Set default registration fees for existing categories
    op.execute("""
        UPDATE patient_category_options 
        SET registration_fee = CASE 
            WHEN name = 'Classic' THEN 100
            WHEN name = 'Prime' THEN 200
            WHEN name = 'Elite' THEN 500
            WHEN name = 'Community' THEN 50
            ELSE 100
        END
    """)


def downgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)
    
    # Remove registration_fee from patient_category_options
    if 'patient_category_options' in tables:
        columns = _get_column_names(bind, 'patient_category_options')
        if 'registration_fee' in columns:
            op.drop_column('patient_category_options', 'registration_fee')
