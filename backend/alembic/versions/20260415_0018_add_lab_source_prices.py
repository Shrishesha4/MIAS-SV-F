"""add source-owned pricing to lab tests and groups

Revision ID: 20260415_0018
Revises: 20260413_0017
Create Date: 2026-04-15 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '20260415_0018'
down_revision = '20260414_0019'
branch_labels = None
depends_on = None


def _get_column_names(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {column['name'] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if 'lab_tests' in tables:
        columns = _get_column_names(bind, 'lab_tests')
        if 'configured_prices' not in columns:
            op.add_column('lab_tests', sa.Column('configured_prices', sa.JSON(), nullable=True))

    if 'lab_test_groups' in tables:
        columns = _get_column_names(bind, 'lab_test_groups')
        if 'configured_prices' not in columns:
            op.add_column('lab_test_groups', sa.Column('configured_prices', sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if 'lab_test_groups' in tables:
        columns = _get_column_names(bind, 'lab_test_groups')
        if 'configured_prices' in columns:
            op.drop_column('lab_test_groups', 'configured_prices')

    if 'lab_tests' in tables:
        columns = _get_column_names(bind, 'lab_tests')
        if 'configured_prices' in columns:
            op.drop_column('lab_tests', 'configured_prices')