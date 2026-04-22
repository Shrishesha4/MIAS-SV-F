"""cleanup orphaned charge_prices tier values

Charge prices accumulated tier values from two legacy sources that are no
longer semantically valid:

1. WALKIN_X values (e.g. WALKIN_PRIME, WALKIN_CLASSIC) — these were
   insurance-category walk-in type strings that leaked into charge_prices.tier
   before the pricing model was settled on patient-category-only tiers.

2. Duplicate rows for the same (item_id, tier) arising from concurrent syncs
   or mid-migration state where both a legacy and canonical row existed.

This migration applies the following steps in order:

  1. Remap WALKIN_X tier rows to the matching patient_category_options.name
     where the suffix resolves to a known patient category.  Rows that don't
     resolve (no matching patient category) are left for step 5 to delete.

  2. Normalise tier casing for all remaining rows using initcap() so that
     values like "CLASSIC", "classic", or "Classic " all become "Classic".
     This mirrors normalize_patient_category_name() in Python.

  3. Deduplicate rows with the same (item_id, lower(tier)) pair, keeping the
     row with the highest price (preserves non-zero configured values) and
     breaking ties by id to give a stable winner.

  4. Delete rows with NULL or empty tier that can never be resolved.

  5. Delete rows whose tier does not match any patient_category_options.name
     (case-insensitive).  These are the true orphans.

Downgrade removes nothing — deleted orphan rows were semantically invalid and
cannot be safely reconstructed.

Revision ID: 20260423_0037
Revises: 20260422_0036
Create Date: 2026-04-23
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260423_0037"
down_revision = "20260422_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "charge_prices" not in tables or "patient_category_options" not in tables:
        return

    # ------------------------------------------------------------------
    # Step 1 — Remap WALKIN_X tiers to the matching patient category name.
    # Strips the "WALKIN_" prefix, converts underscores to spaces, and
    # matches (case-insensitively) against patient_category_options.name.
    # ------------------------------------------------------------------
    bind.execute(sa.text("""
        UPDATE charge_prices cp
        SET    tier = pco.name
        FROM   patient_category_options pco
        WHERE  cp.tier ILIKE 'WALKIN_%'
          AND  lower(trim(regexp_replace(replace(substring(cp.tier FROM 8), '_', ' '), '\\s+', ' ', 'g')))
               = lower(trim(pco.name))
    """))

    # ------------------------------------------------------------------
    # Step 2 — Normalise tier casing for all remaining rows.
    # initcap() matches Python's title-case from normalize_patient_category_name.
    # Rows still carrying WALKIN_X (unresolved in step 1) are also normalised
    # here but will be deleted in step 5.
    # ------------------------------------------------------------------
    bind.execute(sa.text("""
        UPDATE charge_prices
        SET    tier = initcap(trim(regexp_replace(replace(tier, '_', ' '), '\\s+', ' ', 'g')))
        WHERE  tier IS NOT NULL
          AND  tier != initcap(trim(regexp_replace(replace(tier, '_', ' '), '\\s+', ' ', 'g')))
    """))

    # ------------------------------------------------------------------
    # Step 3 — Deduplicate rows with the same (item_id, normalised tier).
    # Keeps the row with the highest configured price; breaks ties by id.
    # ------------------------------------------------------------------
    bind.execute(sa.text("""
        DELETE FROM charge_prices
        WHERE id IN (
            SELECT id
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY item_id, lower(trim(tier))
                           ORDER BY price DESC, id ASC
                       ) AS rn
                FROM charge_prices
                WHERE tier IS NOT NULL AND trim(tier) != ''
            ) ranked
            WHERE rn > 1
        )
    """))

    # ------------------------------------------------------------------
    # Step 4 — Delete rows with NULL or empty tier.
    # ------------------------------------------------------------------
    bind.execute(sa.text("""
        DELETE FROM charge_prices
        WHERE tier IS NULL OR trim(tier) = ''
    """))

    # ------------------------------------------------------------------
    # Step 5 — Delete rows whose tier does not match any patient category.
    # After the remap and normalise steps, any remaining non-matching row
    # is a true orphan with no valid semantic meaning.
    # ------------------------------------------------------------------
    bind.execute(sa.text("""
        DELETE FROM charge_prices cp
        WHERE NOT EXISTS (
            SELECT 1
            FROM   patient_category_options pco
            WHERE  lower(trim(cp.tier)) = lower(trim(pco.name))
        )
    """))


def downgrade() -> None:
    # Orphaned rows are semantically invalid; they cannot be reconstructed.
    pass
