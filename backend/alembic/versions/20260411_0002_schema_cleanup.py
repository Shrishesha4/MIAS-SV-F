"""schema cleanup for nurse relations

Revision ID: 20260411_0002
Revises: 20260410_0001
Create Date: 2026-04-11 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260411_0002'
down_revision = '20260410_0001'
branch_labels = None
depends_on = None


def _get_existing_indexes(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {index['name'] for index in inspector.get_indexes(table_name)}


def _get_existing_foreign_keys(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {foreign_key['name'] for foreign_key in inspector.get_foreign_keys(table_name) if foreign_key.get('name')}


def upgrade() -> None:
    bind = op.get_bind()
    sbar_indexes = _get_existing_indexes(bind, 'sbar_notes')
    sbar_foreign_keys = _get_existing_foreign_keys(bind, 'sbar_notes')
    nurse_order_indexes = _get_existing_indexes(bind, 'nurse_orders')
    nurse_order_foreign_keys = _get_existing_foreign_keys(bind, 'nurse_orders')

    bind.execute(sa.text(
        """
        DELETE FROM sbar_notes
        WHERE patient_id NOT IN (SELECT id FROM patients)
           OR admission_id NOT IN (SELECT id FROM admissions)
           OR nurse_id NOT IN (SELECT id FROM nurses)
        """
    ))
    bind.execute(sa.text(
        """
        DELETE FROM nurse_orders
        WHERE patient_id NOT IN (SELECT id FROM patients)
           OR admission_id NOT IN (SELECT id FROM admissions)
        """
    ))
    bind.execute(sa.text(
        """
        UPDATE nurse_orders
        SET nurse_id = NULL
        WHERE nurse_id IS NOT NULL
          AND nurse_id NOT IN (SELECT id FROM nurses)
        """
    ))

    with op.batch_alter_table('sbar_notes') as batch_op:
        if 'idx_sbar_patient_created' not in sbar_indexes:
            batch_op.create_index('idx_sbar_patient_created', ['patient_id', 'created_at'], unique=False)
        if 'idx_sbar_admission_created' not in sbar_indexes:
            batch_op.create_index('idx_sbar_admission_created', ['admission_id', 'created_at'], unique=False)
        if 'idx_sbar_nurse_created' not in sbar_indexes:
            batch_op.create_index('idx_sbar_nurse_created', ['nurse_id', 'created_at'], unique=False)
        if 'fk_sbar_patient' not in sbar_foreign_keys:
            batch_op.create_foreign_key('fk_sbar_patient', 'patients', ['patient_id'], ['id'])
        if 'fk_sbar_admission' not in sbar_foreign_keys:
            batch_op.create_foreign_key('fk_sbar_admission', 'admissions', ['admission_id'], ['id'])
        if 'fk_sbar_nurse' not in sbar_foreign_keys:
            batch_op.create_foreign_key('fk_sbar_nurse', 'nurses', ['nurse_id'], ['id'])

    with op.batch_alter_table('nurse_orders') as batch_op:
        if 'idx_nurse_order_patient_created' not in nurse_order_indexes:
            batch_op.create_index('idx_nurse_order_patient_created', ['patient_id', 'created_at'], unique=False)
        if 'idx_nurse_order_admission_created' not in nurse_order_indexes:
            batch_op.create_index('idx_nurse_order_admission_created', ['admission_id', 'created_at'], unique=False)
        if 'idx_nurse_order_nurse_created' not in nurse_order_indexes:
            batch_op.create_index('idx_nurse_order_nurse_created', ['nurse_id', 'created_at'], unique=False)
        if 'fk_nurse_order_patient' not in nurse_order_foreign_keys:
            batch_op.create_foreign_key('fk_nurse_order_patient', 'patients', ['patient_id'], ['id'])
        if 'fk_nurse_order_admission' not in nurse_order_foreign_keys:
            batch_op.create_foreign_key('fk_nurse_order_admission', 'admissions', ['admission_id'], ['id'])
        if 'fk_nurse_order_nurse' not in nurse_order_foreign_keys:
            batch_op.create_foreign_key('fk_nurse_order_nurse', 'nurses', ['nurse_id'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('nurse_orders') as batch_op:
        batch_op.drop_constraint('fk_nurse_order_nurse', type_='foreignkey')
        batch_op.drop_constraint('fk_nurse_order_admission', type_='foreignkey')
        batch_op.drop_constraint('fk_nurse_order_patient', type_='foreignkey')
        batch_op.drop_index('idx_nurse_order_nurse_created')
        batch_op.drop_index('idx_nurse_order_admission_created')
        batch_op.drop_index('idx_nurse_order_patient_created')

    with op.batch_alter_table('sbar_notes') as batch_op:
        batch_op.drop_constraint('fk_sbar_nurse', type_='foreignkey')
        batch_op.drop_constraint('fk_sbar_admission', type_='foreignkey')
        batch_op.drop_constraint('fk_sbar_patient', type_='foreignkey')
        batch_op.drop_index('idx_sbar_nurse_created')
        batch_op.drop_index('idx_sbar_admission_created')
        batch_op.drop_index('idx_sbar_patient_created')
