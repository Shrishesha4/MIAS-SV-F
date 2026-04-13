"""system config tables

Revision ID: 20260411_0003
Revises: 20260411_0002
Create Date: 2026-04-11 12:00:00.000000

"""
from __future__ import annotations

from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = '20260411_0003'
down_revision = '20260411_0002'
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

    if 'patients' in tables:
        bind.execute(sa.text("ALTER TABLE patients ALTER COLUMN category TYPE VARCHAR USING category::text"))
        bind.execute(sa.text("UPDATE patients SET category = 'General' WHERE category = 'GENERAL'"))
        bind.execute(sa.text("UPDATE patients SET category = 'Elite' WHERE category = 'ELITE'"))
        bind.execute(sa.text("UPDATE patients SET category = 'Staff' WHERE category = 'STAFF'"))
        bind.execute(sa.text("DROP TYPE IF EXISTS patientcategory"))

    if 'patient_category_options' not in tables:
        op.create_table(
            'patient_category_options',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name'),
        )
        op.create_index('ix_patient_category_options_name', 'patient_category_options', ['name'], unique=True)

    if 'ai_provider_settings' in tables:
        columns = _get_column_names(bind, 'ai_provider_settings')
        with op.batch_alter_table('ai_provider_settings') as batch_op:
            if 'display_name' not in columns:
                batch_op.add_column(sa.Column('display_name', sa.String(), nullable=True))
            if 'batch_size' not in columns:
                batch_op.add_column(sa.Column('batch_size', sa.Integer(), nullable=True, server_default='10'))

        bind.execute(sa.text(
            """
            UPDATE ai_provider_settings
            SET display_name = CASE provider
                WHEN 'OPENAI' THEN 'OpenAI'
                WHEN 'ANTHROPIC' THEN 'Anthropic'
                WHEN 'GEMINI' THEN 'Gemini'
                WHEN 'OPENAI_COMPATIBLE' THEN 'OpenAI Compatible'
                ELSE 'AI Provider'
            END
            WHERE display_name IS NULL OR btrim(display_name) = ''
            """
        ))
        bind.execute(sa.text("UPDATE ai_provider_settings SET batch_size = COALESCE(batch_size, 10)"))

    if 'patient_category_options' in _get_table_names(bind):
        pco_columns = _get_column_names(bind, 'patient_category_options')
        has_is_default_col = 'is_default' in pco_columns

        existing_names = {
            row[0].casefold(): row[0]
            for row in bind.execute(sa.text("SELECT name FROM patient_category_options")).fetchall()
            if row[0]
        }
        defaults = [
            ('Classic', 'Standard hospital pricing and registration category.', True, 0),
            ('Prime', 'Priority services with upgraded access and benefits.', False, 1),
            ('Elite', 'Premium category for high-touch service workflows.', False, 2),
            ('Community', 'Community or subsidized patient support category.', False, 3),
        ]

        for name, description, is_default, sort_order in defaults:
            if name.casefold() in existing_names:
                continue
            if has_is_default_col:
                bind.execute(
                    sa.text(
                        """
                        INSERT INTO patient_category_options
                            (id, name, description, is_active, is_default, sort_order, created_at, updated_at)
                        VALUES
                            (:id, :name, :description, TRUE, :is_default, :sort_order, NOW(), NOW())
                        """
                    ),
                    {
                        'id': str(uuid4()),
                        'name': name,
                        'description': description,
                        'is_default': is_default,
                        'sort_order': sort_order,
                    },
                )
            else:
                bind.execute(
                    sa.text(
                        """
                        INSERT INTO patient_category_options
                            (id, name, description, is_active, sort_order, created_at, updated_at)
                        VALUES
                            (:id, :name, :description, TRUE, :sort_order, NOW(), NOW())
                        """
                    ),
                    {
                        'id': str(uuid4()),
                        'name': name,
                        'description': description,
                        'sort_order': sort_order,
                    },
                )
            existing_names[name.casefold()] = name

        if 'patients' in _get_table_names(bind):
            patient_names = bind.execute(sa.text("SELECT DISTINCT category FROM patients WHERE category IS NOT NULL")).fetchall()
            next_sort = bind.execute(sa.text("SELECT COALESCE(MAX(sort_order), 0) FROM patient_category_options")).scalar() or 0
            for row in patient_names:
                name = row[0]
                if not name or name.casefold() in existing_names:
                    continue
                next_sort += 1
                if has_is_default_col:
                    bind.execute(
                        sa.text(
                            """
                            INSERT INTO patient_category_options
                                (id, name, description, is_active, is_default, sort_order, created_at, updated_at)
                            VALUES
                                (:id, :name, :description, TRUE, FALSE, :sort_order, NOW(), NOW())
                            """
                        ),
                        {
                            'id': str(uuid4()),
                            'name': name,
                            'description': 'Imported from existing patient records.',
                            'sort_order': next_sort,
                        },
                    )
                else:
                    bind.execute(
                        sa.text(
                            """
                            INSERT INTO patient_category_options
                                (id, name, description, is_active, sort_order, created_at, updated_at)
                            VALUES
                                (:id, :name, :description, TRUE, :sort_order, NOW(), NOW())
                            """
                        ),
                        {
                            'id': str(uuid4()),
                            'name': name,
                            'description': 'Imported from existing patient records.',
                            'sort_order': next_sort,
                        },
                    )
                existing_names[name.casefold()] = name

        if has_is_default_col:
            has_default = bind.execute(sa.text("SELECT 1 FROM patient_category_options WHERE is_default = TRUE LIMIT 1")).first()
            if not has_default:
                bind.execute(sa.text(
                    """
                    UPDATE patient_category_options
                    SET is_default = TRUE
                    WHERE id = (
                        SELECT id FROM patient_category_options
                        ORDER BY CASE WHEN lower(name) = 'classic' THEN 0 ELSE 1 END, sort_order ASC, created_at ASC
                        LIMIT 1
                    )
                    """
                ))


def downgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)

    if 'patient_category_options' in tables:
        op.drop_index('ix_patient_category_options_name', table_name='patient_category_options')
        op.drop_table('patient_category_options')

    if 'ai_provider_settings' in tables:
        columns = _get_column_names(bind, 'ai_provider_settings')
        with op.batch_alter_table('ai_provider_settings') as batch_op:
            if 'batch_size' in columns:
                batch_op.drop_column('batch_size')
            if 'display_name' in columns:
                batch_op.drop_column('display_name')