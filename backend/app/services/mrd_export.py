"""MRD export job runner — lightweight asyncio-based background exports.

Uses Redis for job state tracking and writes CSV output to the exports/ directory.
All database queries run exclusively against the analytics engine.
"""

import asyncio
import csv
import io
import os
import uuid
from datetime import datetime
from typing import Optional

from app.config import settings
from app.core.redis_client import get_redis
from app.database import _get_analytics_session_maker

EXPORTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "exports"
)
os.makedirs(EXPORTS_DIR, exist_ok=True)

_JOB_KEY_PREFIX = "mrd:export:job:"
_USER_JOBS_PREFIX = "mrd:export:user:"
_JOB_TTL = 86400  # 24 hours


async def enqueue_export(
    user_id: str,
    export_type: str,
    filters: dict,
) -> str:
    """Create an export job and schedule it in the background."""
    job_id = str(uuid.uuid4())
    redis = await get_redis()

    job_data = {
        "id": job_id,
        "user_id": user_id,
        "export_type": export_type,
        "filters": str(filters),
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "file_path": "",
        "row_count": "0",
        "error": "",
    }
    await redis.hset(f"{_JOB_KEY_PREFIX}{job_id}", mapping=job_data)
    await redis.expire(f"{_JOB_KEY_PREFIX}{job_id}", _JOB_TTL)
    await redis.lpush(f"{_USER_JOBS_PREFIX}{user_id}", job_id)
    await redis.expire(f"{_USER_JOBS_PREFIX}{user_id}", _JOB_TTL)

    # Fire-and-forget background task
    asyncio.create_task(_run_export(job_id, user_id, export_type, filters))

    return job_id


async def get_job_status(job_id: str) -> Optional[dict]:
    redis = await get_redis()
    data = await redis.hgetall(f"{_JOB_KEY_PREFIX}{job_id}")
    return data if data else None


async def list_user_jobs(user_id: str) -> list[dict]:
    redis = await get_redis()
    job_ids = await redis.lrange(f"{_USER_JOBS_PREFIX}{user_id}", 0, 49)
    jobs = []
    for jid in job_ids:
        data = await redis.hgetall(f"{_JOB_KEY_PREFIX}{jid}")
        if data:
            jobs.append(data)
    return jobs


async def _run_export(
    job_id: str, user_id: str, export_type: str, filters: dict
) -> None:
    """Execute the export query on the analytics DB and write CSV."""
    redis = await get_redis()
    await redis.hset(f"{_JOB_KEY_PREFIX}{job_id}", "status", "running")

    try:
        session_maker = _get_analytics_session_maker()
        async with session_maker() as db:
            rows, headers = await _execute_export_query(db, export_type, filters)

        # Write CSV
        filename = f"mrd_export_{export_type}_{job_id[:8]}.csv"
        filepath = os.path.join(EXPORTS_DIR, filename)

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(headers)
        writer.writerows(rows)

        with open(filepath, "w", newline="") as f:
            f.write(buf.getvalue())

        await redis.hset(
            f"{_JOB_KEY_PREFIX}{job_id}",
            mapping={
                "status": "complete",
                "file_path": filepath,
                "row_count": str(len(rows)),
            },
        )
    except Exception as exc:
        await redis.hset(
            f"{_JOB_KEY_PREFIX}{job_id}",
            mapping={"status": "failed", "error": str(exc)[:500]},
        )


async def _execute_export_query(db, export_type: str, filters: dict):
    """Run the appropriate export query. Returns (rows, headers)."""
    from sqlalchemy import select, text
    from datetime import date as date_type

    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    if export_type == "records":
        from app.models.medical_record import MedicalRecord

        from_dt = datetime.combine(date_type.fromisoformat(from_date), datetime.min.time())
        to_dt = datetime.combine(date_type.fromisoformat(to_date), datetime.max.time())

        stmt = select(MedicalRecord).where(
            MedicalRecord.date.between(from_dt, to_dt)
        )
        if filters.get("department"):
            stmt = stmt.where(MedicalRecord.department == filters["department"])
        if filters.get("patient_id"):
            stmt = stmt.where(MedicalRecord.patient_id == filters["patient_id"])

        stmt = stmt.order_by(MedicalRecord.date.desc())
        result = await db.execute(stmt)
        records = result.scalars().all()

        headers = [
            "id", "patient_id", "date", "type", "description",
            "performed_by", "department", "status", "diagnosis",
        ]
        rows = [
            [
                r.id, r.patient_id, str(r.date),
                r.type.value if r.type else "", r.description,
                r.performed_by, r.department, r.status, r.diagnosis or "",
            ]
            for r in records
        ]
        return rows, headers

    elif export_type == "prescriptions":
        from app.models.prescription import Prescription

        from_dt = datetime.combine(date_type.fromisoformat(from_date), datetime.min.time())
        to_dt = datetime.combine(date_type.fromisoformat(to_date), datetime.max.time())

        stmt = select(Prescription).where(
            Prescription.date.between(from_dt, to_dt)
        )
        if filters.get("department"):
            stmt = stmt.where(Prescription.department == filters["department"])

        stmt = stmt.order_by(Prescription.date.desc())
        result = await db.execute(stmt)
        records = result.scalars().all()

        headers = [
            "id", "prescription_id", "patient_id", "date", "doctor",
            "department", "status", "notes",
        ]
        rows = [
            [
                p.id, p.prescription_id or "", p.patient_id, str(p.date),
                p.doctor, p.department, p.status.value if p.status else "", p.notes or "",
            ]
            for p in records
        ]
        return rows, headers

    elif export_type == "admissions":
        from app.models.admission import Admission

        from_dt = datetime.combine(date_type.fromisoformat(from_date), datetime.min.time())
        to_dt = datetime.combine(date_type.fromisoformat(to_date), datetime.max.time())

        stmt = select(Admission).where(
            Admission.admission_date.between(from_dt, to_dt)
        )
        stmt = stmt.order_by(Admission.admission_date.desc())
        result = await db.execute(stmt)
        records = result.scalars().all()

        headers = [
            "id", "patient_id", "admission_date", "discharge_date",
            "department", "ward", "bed_number", "attending_doctor",
            "status", "diagnosis",
        ]
        rows = [
            [
                a.id, a.patient_id, str(a.admission_date),
                str(a.discharge_date) if a.discharge_date else "",
                a.department, a.ward or "", a.bed_number or "",
                a.attending_doctor, a.status, a.diagnosis or "",
            ]
            for a in records
        ]
        return rows, headers

    else:
        raise ValueError(f"Unknown export type: {export_type}")
