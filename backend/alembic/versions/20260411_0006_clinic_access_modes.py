"""clinic access modes

Revision ID: 20260411_0006
Revises: 20260411_0005
Create Date: 2026-04-11 21:30:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '20260411_0006'
down_revision = '20260411_0005'
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

    if 'clinics' not in tables:
        return

    columns = _get_column_names(bind, 'clinics')
    if 'access_mode' not in columns:
        with op.batch_alter_table('clinics') as batch_op:
            batch_op.add_column(sa.Column('access_mode', sa.String(), nullable=True, server_default='WALK_IN'))

    bind.execute(sa.text("UPDATE clinics SET access_mode = 'WALK_IN' WHERE access_mode IS NULL OR TRIM(access_mode) = ''"))

    with op.batch_alter_table('clinics') as batch_op:
        batch_op.alter_column('access_mode', existing_type=sa.String(), nullable=False, server_default='WALK_IN')


def downgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)

    if 'clinics' not in tables:
        return

    columns = _get_column_names(bind, 'clinics')
    if 'access_mode' in columns:
        with op.batch_alter_table('clinics') as batch_op:
            batch_op.drop_column('access_mode')
