from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, DateTime, Enum, Float, Integer, LargeBinary, Numeric, Time, BigInteger, Boolean, delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base

BACKUP_SCHEMA_VERSION = 1
EXCLUDED_TABLES = {"alembic_version"}


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).hex()
    return value


def _coerce_datetime(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return datetime.fromisoformat(normalized)


def _restore_value(value: Any, column_type: Any) -> Any:
    if value is None:
        return None

    if isinstance(column_type, DateTime):
        if isinstance(value, str):
            return _coerce_datetime(value)
        return value

    if isinstance(column_type, Date):
        if isinstance(value, str):
            return date.fromisoformat(value)
        return value

    if isinstance(column_type, Time):
        if isinstance(value, str):
            return time.fromisoformat(value)
        return value

    if isinstance(column_type, (Integer, BigInteger)):
        return int(value)

    if isinstance(column_type, (Float,)):
        return float(value)

    if isinstance(column_type, Numeric):
        return Decimal(str(value))

    if isinstance(column_type, Boolean):
        return bool(value)

    if isinstance(column_type, Enum):
        return str(value)

    if isinstance(column_type, LargeBinary):
        if isinstance(value, str):
            return bytes.fromhex(value)
        return bytes(value)

    return value


def _backup_tables():
    return [table for table in Base.metadata.sorted_tables if table.name not in EXCLUDED_TABLES]


async def export_system_backup(db: AsyncSession) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": BACKUP_SCHEMA_VERSION,
        "exported_at": datetime.utcnow().isoformat(),
        "tables": {},
        "table_counts": {},
    }

    for table in _backup_tables():
        result = await db.execute(select(table))
        rows = [dict(row) for row in result.mappings().all()]
        serialized_rows = [{key: _json_safe(value) for key, value in row.items()} for row in rows]
        payload["tables"][table.name] = serialized_rows
        payload["table_counts"][table.name] = len(serialized_rows)

    payload["total_rows"] = int(sum(payload["table_counts"].values()))
    return payload


async def import_system_backup(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Invalid backup payload")

    table_payload = payload.get("tables")
    if not isinstance(table_payload, dict):
        raise ValueError("Backup payload is missing tables")

    tables = _backup_tables()
    table_map = {table.name: table for table in tables}

    unknown_tables = sorted(name for name in table_payload.keys() if name not in table_map)
    if unknown_tables:
        raise ValueError(f"Backup contains unknown tables: {', '.join(unknown_tables)}")

    for table in reversed(tables):
        await db.execute(delete(table))

    imported_counts: dict[str, int] = {}
    for table in tables:
        raw_rows = table_payload.get(table.name, [])
        if not isinstance(raw_rows, list):
            raise ValueError(f"Invalid rows for table {table.name}")

        if not raw_rows:
            imported_counts[table.name] = 0
            continue

        columns = list(table.columns)
        restored_rows: list[dict[str, Any]] = []
        for row in raw_rows:
            if not isinstance(row, dict):
                raise ValueError(f"Invalid row format for table {table.name}")
            restored_row: dict[str, Any] = {}
            for column in columns:
                if column.name not in row:
                    continue
                restored_row[column.name] = _restore_value(row[column.name], column.type)
            restored_rows.append(restored_row)

        if restored_rows:
            await db.execute(insert(table), restored_rows)
        imported_counts[table.name] = len(restored_rows)

    return {
        "tables": imported_counts,
        "total_rows": int(sum(imported_counts.values())),
    }
