"""form categories

Revision ID: 20260411_0005
Revises: 20260411_0004
Create Date: 2026-04-11 18:10:00.000000

"""
from __future__ import annotations

from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = '20260411_0005'
down_revision = '20260411_0004'
branch_labels = None
depends_on = None


def _get_table_names(bind) -> set[str]:
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def _get_column_names(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {column['name'] for column in inspector.get_columns(table_name)}


def _infer_section(form_type: str | None) -> str:
    normalized = (form_type or '').strip().upper()
    if normalized in {
        'CLINICAL',
        'CASE_RECORD',
        'ADMISSION',
        'ADMISSION_REQUEST',
        'ADMISSION_INTAKE',
        'ADMISSION_DISCHARGE',
        'ADMISSION_TRANSFER',
        'PRESCRIPTION',
        'PRESCRIPTION_CREATE',
        'PRESCRIPTION_EDIT',
        'PRESCRIPTION_REQUEST',
        'VITAL_ENTRY',
    }:
        return 'CLINICAL'
    if normalized in {'LABORATORY', 'LAB', 'LABS'}:
        return 'LABORATORY'
    if normalized in {'ADMINISTRATIVE', 'PROFILE', 'PROFILE_EDIT', 'CUSTOM', ''}:
        return 'ADMINISTRATIVE'
    return normalized or 'ADMINISTRATIVE'


def upgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)

    if 'form_definitions' in tables:
        columns = _get_column_names(bind, 'form_definitions')
        with op.batch_alter_table('form_definitions') as batch_op:
            if 'section' not in columns:
                batch_op.add_column(sa.Column('section', sa.String(), nullable=True))
        form_rows = bind.execute(sa.text("SELECT id, form_type FROM form_definitions")).fetchall()
        for form_id, form_type in form_rows:
            bind.execute(
                sa.text("UPDATE form_definitions SET section = :section WHERE id = :id"),
                {'section': _infer_section(form_type), 'id': form_id},
            )
        with op.batch_alter_table('form_definitions') as batch_op:
            batch_op.alter_column('section', existing_type=sa.String(), nullable=False)
        op.create_index('idx_form_definition_section_active', 'form_definitions', ['section', 'is_active'], unique=False)

    if 'form_category_options' not in tables:
        op.create_table(
            'form_category_options',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('is_system', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name', name='uq_form_category_options_name'),
        )
        op.create_index('ix_form_category_options_name', 'form_category_options', ['name'], unique=False)

    if 'form_category_options' in _get_table_names(bind):
        existing_names = {
            row[0].casefold(): row[0]
            for row in bind.execute(sa.text("SELECT name FROM form_category_options")).fetchall()
            if row[0]
        }
        defaults = [
            ('CLINICAL', 0, True),
            ('LABORATORY', 1, True),
            ('ADMINISTRATIVE', 2, True),
        ]
        for name, sort_order, is_system in defaults:
            if name.casefold() in existing_names:
                continue
            bind.execute(
                sa.text(
                    """
                    INSERT INTO form_category_options
                        (id, name, sort_order, is_active, is_system, created_at, updated_at)
                    VALUES
                        (:id, :name, :sort_order, TRUE, :is_system, NOW(), NOW())
                    """
                ),
                {'id': str(uuid4()), 'name': name, 'sort_order': sort_order, 'is_system': is_system},
            )
            existing_names[name.casefold()] = name

        if 'form_definitions' in _get_table_names(bind):
            section_rows = bind.execute(sa.text("SELECT DISTINCT section FROM form_definitions WHERE section IS NOT NULL")).fetchall()
            next_sort = bind.execute(sa.text("SELECT COALESCE(MAX(sort_order), 0) FROM form_category_options")).scalar() or 0
            for row in section_rows:
                name = (row[0] or '').strip().upper()
                if not name or name.casefold() in existing_names:
                    continue
                next_sort += 1
                bind.execute(
                    sa.text(
                        """
                        INSERT INTO form_category_options
                            (id, name, sort_order, is_active, is_system, created_at, updated_at)
                        VALUES
                            (:id, :name, :sort_order, TRUE, FALSE, NOW(), NOW())
                        """
                    ),
                    {'id': str(uuid4()), 'name': name, 'sort_order': next_sort},
                )
                existing_names[name.casefold()] = name


def downgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)

    if 'form_category_options' in tables:
        op.drop_index('ix_form_category_options_name', table_name='form_category_options')
        op.drop_table('form_category_options')

    if 'form_definitions' in tables:
        columns = _get_column_names(bind, 'form_definitions')
        if 'section' in columns:
            op.drop_index('idx_form_definition_section_active', table_name='form_definitions')
            with op.batch_alter_table('form_definitions') as batch_op:
                batch_op.drop_column('section')