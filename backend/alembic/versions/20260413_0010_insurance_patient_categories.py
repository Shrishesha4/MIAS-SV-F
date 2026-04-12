"""add patient categories to insurance categories

Revision ID: 20260413_0010
Revises: 20260413_0009
Create Date: 2026-04-13 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '20260413_0010'
down_revision = '20260413_0009'
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
    
    # Create association table for many-to-many relationship
    if 'insurance_patient_category_association' not in tables:
        op.create_table(
            'insurance_patient_category_association',
            sa.Column('insurance_category_id', sa.String(), nullable=False, primary_key=True),
            sa.Column('patient_category_id', sa.String(), nullable=False, primary_key=True),
            sa.ForeignKeyConstraint(['insurance_category_id'], ['insurance_categories.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['patient_category_id'], ['patient_category_options.id'], ondelete='CASCADE'),
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)
    
    if 'insurance_patient_category_association' in tables:
        op.drop_table('insurance_patient_category_association')
