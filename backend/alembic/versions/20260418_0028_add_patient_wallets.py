"""add patient_wallets stored balance table

Revision ID: 20260418_0028
Revises: 20260417_0027
Create Date: 2026-04-18 06:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260418_0028"
down_revision = "20260417_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent enum creation — safe if a previous run created it but crashed before finishing
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE wallettype AS ENUM ('HOSPITAL', 'PHARMACY');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS patient_wallets (
            id VARCHAR NOT NULL,
            patient_id VARCHAR NOT NULL,
            wallet_type wallettype NOT NULL,
            balance NUMERIC(12, 2) NOT NULL DEFAULT 0,
            updated_at TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE (patient_id, wallet_type),
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_patient_wallets_patient_id
        ON patient_wallets (patient_id)
    """)

    # Backfill stored balances from existing transactions
    op.execute("""
        INSERT INTO patient_wallets (id, patient_id, wallet_type, balance, updated_at)
        SELECT
            gen_random_uuid()::text,
            patient_id,
            wallet_type::wallettype,
            SUM(CASE WHEN type = 'CREDIT' THEN amount ELSE -amount END),
            NOW()
        FROM wallet_transactions
        GROUP BY patient_id, wallet_type
        ON CONFLICT (patient_id, wallet_type) DO UPDATE
            SET balance = EXCLUDED.balance,
                updated_at = NOW()
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_patient_wallets_patient_id")
    op.execute("DROP TABLE IF EXISTS patient_wallets")
    op.execute("DROP TYPE IF EXISTS wallettype")
