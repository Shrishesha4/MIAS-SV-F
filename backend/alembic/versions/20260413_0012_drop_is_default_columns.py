"""drop is_default columns from patient categories and insurance categories

Revision ID: 20260413_0012
Revises: 20260413_0011
Create Date: 2026-04-13 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '20260413_0012'
down_revision = '20260413_0011'
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
    
    # Drop is_default from patient_category_options
    if 'patient_category_options' in tables:
        columns = _get_column_names(bind, 'patient_category_options')
        if 'is_default' in columns:
            op.drop_column('patient_category_options', 'is_default')
    
    # Drop is_default from insurance_categories
    if 'insurance_categories' in tables:
        columns = _get_column_names(bind, 'insurance_categories')
        if 'is_default' in columns:
            op.drop_column('insurance_categories', 'is_default')


def downgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)
    
    # Add is_default back to patient_category_options
    if 'patient_category_options' in tables:
        columns = _get_column_names(bind, 'patient_category_options')
        if 'is_default' not in columns:
            op.add_column('patient_category_options', sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add is_default back to insurance_categories
    if 'insurance_categories' in tables:
        columns = _get_column_names(bind, 'insurance_categories')
        if 'is_default' not in columns:
            op.add_column('insurance_categories', sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'))
