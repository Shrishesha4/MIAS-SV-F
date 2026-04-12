"""drop default_walk_in_type from insurance categories

Revision ID: 20260413_0011
Revises: 20260413_0010
Create Date: 2026-04-13 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '20260413_0011'
down_revision = '20260413_0010'
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
        columns = _get_column_names(bind, 'insurance_categories')
        if 'default_walk_in_type' in columns:
            op.drop_column('insurance_categories', 'default_walk_in_type')


def downgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)
    
    if 'insurance_categories' in tables:
        columns = _get_column_names(bind, 'insurance_categories')
        if 'default_walk_in_type' not in columns:
            op.add_column('insurance_categories', sa.Column('default_walk_in_type', sa.String(), nullable=False, server_default='NO_WALK_IN'))
