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


def upgrade() -> None:
    bind = op.get_bind()

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
        batch_op.create_index('idx_sbar_patient_created', ['patient_id', 'created_at'], unique=False)
        batch_op.create_index('idx_sbar_admission_created', ['admission_id', 'created_at'], unique=False)
        batch_op.create_index('idx_sbar_nurse_created', ['nurse_id', 'created_at'], unique=False)
        batch_op.create_foreign_key('fk_sbar_patient', 'patients', ['patient_id'], ['id'])
        batch_op.create_foreign_key('fk_sbar_admission', 'admissions', ['admission_id'], ['id'])
        batch_op.create_foreign_key('fk_sbar_nurse', 'nurses', ['nurse_id'], ['id'])

    with op.batch_alter_table('nurse_orders') as batch_op:
        batch_op.create_index('idx_nurse_order_patient_created', ['patient_id', 'created_at'], unique=False)
        batch_op.create_index('idx_nurse_order_admission_created', ['admission_id', 'created_at'], unique=False)
        batch_op.create_index('idx_nurse_order_nurse_created', ['nurse_id', 'created_at'], unique=False)
        batch_op.create_foreign_key('fk_nurse_order_patient', 'patients', ['patient_id'], ['id'])
        batch_op.create_foreign_key('fk_nurse_order_admission', 'admissions', ['admission_id'], ['id'])
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
