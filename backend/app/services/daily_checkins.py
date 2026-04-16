from __future__ import annotations

from datetime import date, datetime
from typing import Optional
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.daily_checkin import DailyCheckIn
from app.models.user import User, UserRole
from app.models.admission import Admission
from app.models.patient import Patient


CHECK_IN_OPEN_HOUR = 8


async def get_daily_checkin(
    db: AsyncSession,
    *,
    user_id: str,
    target_date: date | None = None,
) -> DailyCheckIn | None:
    resolved_date = target_date or datetime.utcnow().date()
    result = await db.execute(
        select(DailyCheckIn).where(
            DailyCheckIn.user_id == user_id,
            DailyCheckIn.check_in_date == resolved_date,
        )
    )
    return result.scalar_one_or_none()


async def ensure_daily_checkin(
    db: AsyncSession,
    *,
    user_id: str,
    role: UserRole,
    checked_in_at: datetime | None = None,
    clinic_id: Optional[str] = None,
) -> DailyCheckIn:
    timestamp = checked_in_at or datetime.utcnow()
    check_in = await get_daily_checkin(db, user_id=user_id, target_date=timestamp.date())
    if check_in:
        # If clinic_id provided and not yet set, update it
        if clinic_id and not check_in.clinic_id:
            check_in.clinic_id = clinic_id
        return check_in

    check_in = DailyCheckIn(
        id=str(uuid.uuid4()),
        user_id=user_id,
        role=role,
        check_in_date=timestamp.date(),
        checked_in_at=timestamp,
        clinic_id=clinic_id,
    )
    db.add(check_in)
    await db.flush()
    return check_in


async def ensure_ip_auto_checkin(
    db: AsyncSession,
    *,
    user_id: str,
) -> DailyCheckIn | None:
    """
    Auto-check-in for admitted (inpatient) patients on day 2+.
    Returns the check-in record if auto-created, else None (needs manual check-in).
    """
    # Find patient record for this user
    patient_result = await db.execute(
        select(Patient).where(Patient.user_id == user_id)
    )
    patient = patient_result.scalar_one_or_none()
    if not patient:
        return None

    # Find active admission
    admission_result = await db.execute(
        select(Admission)
        .where(
            Admission.patient_id == patient.id,
            Admission.status == "Active",
        )
        .order_by(Admission.admission_date.desc())
    )
    admission = admission_result.scalar_one_or_none()
    if not admission:
        return None  # Not admitted, needs manual check-in

    # Check if admission is day 2+ (admission date is before today)
    today = datetime.utcnow().date()
    if admission.admission_date >= today:
        return None  # Day 1, needs manual check-in

    # Day 2+: auto-check-in to the same ward/clinic
    existing = await get_daily_checkin(db, user_id=user_id, target_date=today)
    if existing:
        return existing

    check_in = DailyCheckIn(
        id=str(uuid.uuid4()),
        user_id=user_id,
        role=UserRole.PATIENT,
        check_in_date=today,
        checked_in_at=datetime.utcnow(),
        clinic_id=admission.clinic_id,  # Re-use the admission's clinic
    )
    db.add(check_in)
    await db.flush()
    return check_in


async def get_daily_checkin_counts(
    db: AsyncSession,
    *,
    target_date: date | None = None,
) -> dict[str, int]:
    resolved_date = target_date or datetime.utcnow().date()
    counts_result = await db.execute(
        select(DailyCheckIn.role, func.count(DailyCheckIn.id))
        .where(DailyCheckIn.check_in_date == resolved_date)
        .group_by(DailyCheckIn.role)
    )
    counts = {
        "patients": 0,
        "students": 0,
        "faculty": 0,
        "nurses": 0,
        "reception": 0,
        "admins": 0,
        "total": 0,
    }
    role_map = {
        UserRole.PATIENT: "patients",
        UserRole.STUDENT: "students",
        UserRole.FACULTY: "faculty",
        UserRole.NURSE: "nurses",
        UserRole.RECEPTION: "reception",
        UserRole.ADMIN: "admins",
    }
    for role, count in counts_result.all():
        key = role_map.get(role)
        if not key:
            continue
        counts[key] = count
        counts["total"] += count
    return counts


def build_daily_checkin_status(
    *,
    user: User,
    check_in: DailyCheckIn | None,
    counts: dict[str, int],
) -> dict:
    return {
        "today": datetime.utcnow().date().isoformat(),
        "checked_in": check_in is not None,
        "checked_in_at": check_in.checked_in_at.isoformat() if check_in else None,
        "open_hour": CHECK_IN_OPEN_HOUR,
        "role": user.role.value,
        "counts": counts,
    }
