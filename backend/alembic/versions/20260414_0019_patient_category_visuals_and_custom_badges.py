"""add patient category visuals and insurance custom badge symbols

Revision ID: 20260414_0019
Revises: 20260414_0018
Create Date: 2026-04-14 00:30:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '20260414_0019'
down_revision = '20260414_0018'
branch_labels = None
depends_on = None


def _get_table_names(bind) -> set[str]:
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def _get_column_names(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {column['name'] for column in inspector.get_columns(table_name)}


def _apply_patient_category_colors(bind, table_name: str, name_column: str, primary_column: str, secondary_column: str) -> None:
    bind.execute(
        sa.text(
            f"""
            UPDATE {table_name}
            SET {primary_column} = CASE lower(coalesce({name_column}, ''))
                WHEN 'classic' THEN '#60A5FA'
                WHEN 'prime' THEN '#A78BFA'
                WHEN 'elite' THEN '#FBBF24'
                WHEN 'community' THEN '#34D399'
                ELSE '#60A5FA'
            END,
            {secondary_column} = CASE lower(coalesce({name_column}, ''))
                WHEN 'classic' THEN '#1D4ED8'
                WHEN 'prime' THEN '#6D28D9'
                WHEN 'elite' THEN '#D97706'
                WHEN 'community' THEN '#047857'
                ELSE '#1D4ED8'
            END
            """
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)

    if 'patient_category_options' in tables:
        columns = _get_column_names(bind, 'patient_category_options')
        if 'color_primary' not in columns:
            op.add_column('patient_category_options', sa.Column('color_primary', sa.String(), nullable=False, server_default='#60A5FA'))
        if 'color_secondary' not in columns:
            op.add_column('patient_category_options', sa.Column('color_secondary', sa.String(), nullable=False, server_default='#1D4ED8'))
        _apply_patient_category_colors(bind, 'patient_category_options', 'name', 'color_primary', 'color_secondary')

    if 'patients' in tables:
        columns = _get_column_names(bind, 'patients')
        if 'category_color_primary' not in columns:
            op.add_column('patients', sa.Column('category_color_primary', sa.String(), nullable=False, server_default='#60A5FA'))
        if 'category_color_secondary' not in columns:
            op.add_column('patients', sa.Column('category_color_secondary', sa.String(), nullable=False, server_default='#1D4ED8'))
        _apply_patient_category_colors(bind, 'patients', 'category', 'category_color_primary', 'category_color_secondary')

    if 'insurance_categories' in tables:
        columns = _get_column_names(bind, 'insurance_categories')
        if 'custom_badge_symbol' not in columns:
            op.add_column('insurance_categories', sa.Column('custom_badge_symbol', sa.String(), nullable=True))

    if 'insurance_policies' in tables:
        columns = _get_column_names(bind, 'insurance_policies')
        if 'custom_badge_symbol' not in columns:
            op.add_column('insurance_policies', sa.Column('custom_badge_symbol', sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)

    if 'insurance_policies' in tables:
        columns = _get_column_names(bind, 'insurance_policies')
        if 'custom_badge_symbol' in columns:
            op.drop_column('insurance_policies', 'custom_badge_symbol')

    if 'insurance_categories' in tables:
        columns = _get_column_names(bind, 'insurance_categories')
        if 'custom_badge_symbol' in columns:
            op.drop_column('insurance_categories', 'custom_badge_symbol')

    if 'patients' in tables:
        columns = _get_column_names(bind, 'patients')
        if 'category_color_secondary' in columns:
            op.drop_column('patients', 'category_color_secondary')
        if 'category_color_primary' in columns:
            op.drop_column('patients', 'category_color_primary')

    if 'patient_category_options' in tables:
        columns = _get_column_names(bind, 'patient_category_options')
        if 'color_secondary' in columns:
            op.drop_column('patient_category_options', 'color_secondary')
        if 'color_primary' in columns:
            op.drop_column('patient_category_options', 'color_primary')