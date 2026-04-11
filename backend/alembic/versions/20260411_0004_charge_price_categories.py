"""charge price categories

Revision ID: 20260411_0004
Revises: 20260411_0003
Create Date: 2026-04-11 16:15:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '20260411_0004'
down_revision = '20260411_0003'
branch_labels = None
depends_on = None


def _get_table_names(bind) -> set[str]:
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)

    if 'charge_prices' in tables:
        bind.execute(sa.text("ALTER TABLE charge_prices ALTER COLUMN tier TYPE VARCHAR USING tier::text"))
        bind.execute(sa.text("UPDATE charge_prices SET tier = 'Classic' WHERE lower(tier) = 'classic'"))
        bind.execute(sa.text("UPDATE charge_prices SET tier = 'Prime' WHERE lower(tier) = 'prime'"))
        bind.execute(sa.text("UPDATE charge_prices SET tier = 'Elite' WHERE lower(tier) = 'elite'"))
        bind.execute(sa.text("UPDATE charge_prices SET tier = 'Community' WHERE lower(tier) = 'community'"))
        bind.execute(sa.text("UPDATE charge_prices SET tier = 'General' WHERE lower(tier) = 'general'"))
        bind.execute(sa.text("DROP TYPE IF EXISTS chargetier"))


def downgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)

    if 'charge_prices' in tables:
        bind.execute(sa.text("UPDATE charge_prices SET tier = upper(tier)"))
        bind.execute(sa.text("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chargetier') THEN CREATE TYPE chargetier AS ENUM ('CLASSIC', 'PRIME', 'ELITE', 'COMMUNITY'); END IF; END $$;"))
        bind.execute(sa.text("DELETE FROM charge_prices WHERE tier NOT IN ('CLASSIC', 'PRIME', 'ELITE', 'COMMUNITY')"))
        bind.execute(sa.text("ALTER TABLE charge_prices ALTER COLUMN tier TYPE chargetier USING tier::chargetier"))