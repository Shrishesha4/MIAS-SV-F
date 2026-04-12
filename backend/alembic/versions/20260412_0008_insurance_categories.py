"""insurance categories and clinic configurations

Revision ID: 20260412_0008
Revises: 20260411_0007
Create Date: 2026-04-12 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '20260412_0008'
down_revision = '20260411_0007'
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
    
    # Create insurance_categories table
    if 'insurance_categories' not in tables:
        op.create_table(
            'insurance_categories',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )
        op.create_index('ix_insurance_categories_name', 'insurance_categories', ['name'], unique=False)
    
    # Create insurance_clinic_configs table
    if 'insurance_clinic_configs' not in tables:
        op.create_table(
            'insurance_clinic_configs',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('insurance_category_id', sa.String(), nullable=False),
            sa.Column('clinic_id', sa.String(), nullable=False),
            sa.Column('walk_in_type', sa.String(), nullable=False, server_default='NO_WALK_IN'),
            sa.Column('registration_fee', sa.Float(), nullable=False, server_default='100.0'),
            sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['insurance_category_id'], ['insurance_categories.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='CASCADE'),
        )
        op.create_index('ix_insurance_clinic_configs_category', 'insurance_clinic_configs', ['insurance_category_id'])
        op.create_index('ix_insurance_clinic_configs_clinic', 'insurance_clinic_configs', ['clinic_id'])


def downgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)
    
    if 'insurance_clinic_configs' in tables:
        op.drop_index('ix_insurance_clinic_configs_category', table_name='insurance_clinic_configs')
        op.drop_index('ix_insurance_clinic_configs_clinic', table_name='insurance_clinic_configs')
        op.drop_table('insurance_clinic_configs')
    
    if 'insurance_categories' in tables:
        op.drop_index('ix_insurance_categories_name', table_name='insurance_categories')
        op.drop_table('insurance_categories')
