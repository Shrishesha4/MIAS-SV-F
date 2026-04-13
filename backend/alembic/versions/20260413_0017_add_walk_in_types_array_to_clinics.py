"""add walk_in_types array to clinics for ER multi-type support

Revision ID: 20260413_0017
Revises: 20260413_0016
Create Date: 2026-04-13 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '20260413_0017'
down_revision = '20260413_0016'
branch_labels = None
depends_on = None


def _get_column_names(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {column['name'] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if 'clinics' not in tables:
        return

    columns = _get_column_names(bind, 'clinics')
    if 'walk_in_types' not in columns:
        op.add_column(
            'clinics',
            sa.Column('walk_in_types', postgresql.ARRAY(sa.String()), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if 'clinics' not in tables:
        return

    columns = _get_column_names(bind, 'clinics')
    if 'walk_in_types' in columns:
        op.drop_column('clinics', 'walk_in_types')
