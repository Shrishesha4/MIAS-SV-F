"""faculty clinic sessions

Revision ID: 20260411_0007
Revises: 20260411_0006
Create Date: 2026-04-11 23:15:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '20260411_0007'
down_revision = '20260411_0006'
branch_labels = None
depends_on = None


def _get_table_names(bind) -> set[str]:
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def _get_index_names(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {index['name'] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)

    if 'faculty' not in tables or 'clinics' not in tables:
        return

    if 'faculty_clinic_sessions' not in tables:
        op.create_table(
            'faculty_clinic_sessions',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('faculty_id', sa.String(), nullable=False),
            sa.Column('clinic_id', sa.String(), nullable=False),
            sa.Column('clinic_name', sa.String(), nullable=False),
            sa.Column('department', sa.String(), nullable=False),
            sa.Column('date', sa.DateTime(), nullable=False),
            sa.Column('status', sa.String(), nullable=False, server_default='Active'),
            sa.Column('checked_in_at', sa.DateTime(), nullable=False),
            sa.Column('checked_out_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id']),
            sa.ForeignKeyConstraint(['faculty_id'], ['faculty.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_faculty_clinic_sessions_faculty_id', 'faculty_clinic_sessions', ['faculty_id'], unique=False)
        op.create_index('ix_faculty_clinic_sessions_clinic_id', 'faculty_clinic_sessions', ['clinic_id'], unique=False)
        op.create_index('ix_faculty_clinic_sessions_date', 'faculty_clinic_sessions', ['date'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)

    if 'faculty_clinic_sessions' not in tables:
        return

    indexes = _get_index_names(bind, 'faculty_clinic_sessions')
    if 'ix_faculty_clinic_sessions_date' in indexes:
        op.drop_index('ix_faculty_clinic_sessions_date', table_name='faculty_clinic_sessions')
    if 'ix_faculty_clinic_sessions_clinic_id' in indexes:
        op.drop_index('ix_faculty_clinic_sessions_clinic_id', table_name='faculty_clinic_sessions')
    if 'ix_faculty_clinic_sessions_faculty_id' in indexes:
        op.drop_index('ix_faculty_clinic_sessions_faculty_id', table_name='faculty_clinic_sessions')
    op.drop_table('faculty_clinic_sessions')