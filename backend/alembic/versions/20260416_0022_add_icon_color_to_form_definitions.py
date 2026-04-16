"""add icon and color to form_definitions

Revision ID: 20260416_0022
Revises: 20260415_0021
Create Date: 2026-04-16 08:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '20260416_0022'
down_revision = '20260415_0021'
branch_labels = None
depends_on = None


def _get_column_names(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {column['name'] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    columns = _get_column_names(bind, 'form_definitions')
    if 'icon' not in columns:
        op.add_column('form_definitions', sa.Column('icon', sa.String(), nullable=True))
    if 'color' not in columns:
        op.add_column('form_definitions', sa.Column('color', sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    columns = _get_column_names(bind, 'form_definitions')
    if 'color' in columns:
        op.drop_column('form_definitions', 'color')
    if 'icon' in columns:
        op.drop_column('form_definitions', 'icon')
