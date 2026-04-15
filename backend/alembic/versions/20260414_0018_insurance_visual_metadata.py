"""add insurance visual metadata and registration policy linkage

Revision ID: 20260414_0018
Revises: 20260413_0017
Create Date: 2026-04-14 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '20260414_0018'
down_revision = '20260413_0017'
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

    if 'insurance_categories' in tables:
        category_columns = _get_column_names(bind, 'insurance_categories')
        if 'icon_key' not in category_columns:
            op.add_column('insurance_categories', sa.Column('icon_key', sa.String(), nullable=False, server_default='shield'))
        if 'color_primary' not in category_columns:
            op.add_column('insurance_categories', sa.Column('color_primary', sa.String(), nullable=False, server_default='#60A5FA'))
        if 'color_secondary' not in category_columns:
            op.add_column('insurance_categories', sa.Column('color_secondary', sa.String(), nullable=False, server_default='#1D4ED8'))

    if 'insurance_policies' in tables:
        policy_columns = _get_column_names(bind, 'insurance_policies')
        if 'insurance_category_id' not in policy_columns:
            op.add_column('insurance_policies', sa.Column('insurance_category_id', sa.String(), nullable=True))
            op.create_index('ix_insurance_policies_insurance_category_id', 'insurance_policies', ['insurance_category_id'], unique=False)
        if 'icon_key' not in policy_columns:
            op.add_column('insurance_policies', sa.Column('icon_key', sa.String(), nullable=True))
        if 'color_primary' not in policy_columns:
            op.add_column('insurance_policies', sa.Column('color_primary', sa.String(), nullable=True))
        if 'color_secondary' not in policy_columns:
            op.add_column('insurance_policies', sa.Column('color_secondary', sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)

    if 'insurance_policies' in tables:
        policy_columns = _get_column_names(bind, 'insurance_policies')
        if 'color_secondary' in policy_columns:
            op.drop_column('insurance_policies', 'color_secondary')
        if 'color_primary' in policy_columns:
            op.drop_column('insurance_policies', 'color_primary')
        if 'icon_key' in policy_columns:
            op.drop_column('insurance_policies', 'icon_key')
        if 'insurance_category_id' in policy_columns:
            op.drop_index('ix_insurance_policies_insurance_category_id', table_name='insurance_policies')
            op.drop_column('insurance_policies', 'insurance_category_id')

    if 'insurance_categories' in tables:
        category_columns = _get_column_names(bind, 'insurance_categories')
        if 'color_secondary' in category_columns:
            op.drop_column('insurance_categories', 'color_secondary')
        if 'color_primary' in category_columns:
            op.drop_column('insurance_categories', 'color_primary')
        if 'icon_key' in category_columns:
            op.drop_column('insurance_categories', 'icon_key')