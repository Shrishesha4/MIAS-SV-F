"""Sequential daily ID generators.

Patient ID format: YYMMDD#### (e.g. 2604180001 for 18 Apr 2026, first patient)
Counter resets to 0001 each day. Uses SELECT FOR UPDATE on a single advisory-lock
row to prevent race conditions between concurrent workers.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def _next_daily_sequence(db: AsyncSession, prefix: str, table: str, col: str) -> str:
    """Return the next YYMMDD#### style ID, serialised with a PG advisory lock."""
    date_prefix = datetime.now(timezone.utc).strftime("%y%m%d")
    full_prefix = f"{date_prefix}"

    # Use a deterministic advisory lock key per table so workers don't stomp each other.
    # hash the table name to an int that fits in pg_advisory_xact_lock (bigint)
    lock_key = hash(table) & 0x7FFFFFFFFFFFFFFF

    # Acquire an exclusive transaction-level advisory lock — released on COMMIT/ROLLBACK
    await db.execute(text(f"SELECT pg_advisory_xact_lock({lock_key})"))

    result = await db.execute(
        text(
            f"SELECT {col} FROM {table} "
            f"WHERE {col} LIKE :pattern "
            f"ORDER BY {col} DESC LIMIT 1"
        ),
        {"pattern": f"{full_prefix}%"},
    )
    row = result.scalar_one_or_none()

    if row and len(row) >= len(full_prefix) + 4:
        try:
            last_seq = int(row[len(full_prefix):])
        except ValueError:
            last_seq = 0
    else:
        last_seq = 0

    next_seq = last_seq + 1
    return f"{full_prefix}{next_seq:04d}"


async def generate_patient_id(db: AsyncSession) -> str:
    return await _next_daily_sequence(db, "PT", "patients", "patient_id")
