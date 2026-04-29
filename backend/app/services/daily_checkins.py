from __future__ import annotations

from datetime import date, datetime
from typing import Optional
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.models.daily_checkin import DailyCheckIn
from app.models.user import User, UserRole
from app.models.admission import Admission
from app.models.patient import Patient
from app.models.student import Clinic


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
    location: Optional[str] = None,
) -> DailyCheckIn:
    timestamp = checked_in_at or datetime.utcnow()
    check_in = await get_daily_checkin(db, user_id=user_id, target_date=timestamp.date())
    if check_in:
        if check_in.checked_out_at is None:
            return check_in

        check_in.checked_in_at = timestamp
        check_in.checked_out_at = None
        if clinic_id and check_in.clinic_id != clinic_id:
            check_in.clinic_id = clinic_id
        if location:
            check_in.check_in_location = location
        check_in.check_out_location = None
        return check_in

    check_in = DailyCheckIn(
        id=str(uuid.uuid4()),
        user_id=user_id,
        role=role,
        check_in_date=timestamp.date(),
        checked_in_at=timestamp,
        clinic_id=clinic_id,
        check_in_location=location,
    )
    db.add(check_in)
    try:
        await db.flush()
    except IntegrityError:
        # Concurrent check-in requests can hit the unique index; return existing row.
        await db.rollback()
        existing = await get_daily_checkin(db, user_id=user_id, target_date=timestamp.date())
        if existing:
            return existing
        raise
    return check_in


async def check_out_daily_checkin(
    db: AsyncSession,
    *,
    user_id: str,
    checked_out_at: datetime | None = None,
    location: Optional[str] = None,
) -> DailyCheckIn | None:
    timestamp = checked_out_at or datetime.utcnow()
    check_in = await get_daily_checkin(db, user_id=user_id, target_date=timestamp.date())
    if not check_in:
        return None

    if check_in.checked_out_at is None:
        check_in.checked_out_at = timestamp
        if location:
            check_in.check_out_location = location
    return check_in


async def get_active_patient_admission(
    db: AsyncSession,
    *,
    user_id: str,
) -> Admission | None:
    patient_result = await db.execute(
        select(Patient).where(Patient.user_id == user_id)
    )
    patient = patient_result.scalar_one_or_none()
    if not patient:
        return None

    admission_result = await db.execute(
        select(Admission)
        .where(
            Admission.patient_id == patient.id,
            Admission.status == "Active",
        )
        .order_by(Admission.admission_date.desc())
    )
    return admission_result.scalar_one_or_none()


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
        "nutritionists": 0,
        "nurses": 0,
        "reception": 0,
        "admins": 0,
        "total": 0,
    }
    role_map = {
        UserRole.PATIENT: "patients",
        UserRole.STUDENT: "students",
        UserRole.FACULTY: "faculty",
        UserRole.NUTRITIONIST: "nutritionists",
        UserRole.NURSE: "nurses",
        UserRole.NURSE_SUPERINTENDENT: "nurses",
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
    skip_modal: bool = False,
) -> dict:
    currently_checked_in = check_in is not None and check_in.checked_out_at is None
    return {
        "today": datetime.utcnow().date().isoformat(),
        "checked_in": currently_checked_in,
        "checked_in_at": check_in.checked_in_at.isoformat() if check_in else None,
        "checked_out_at": check_in.checked_out_at.isoformat() if check_in and check_in.checked_out_at else None,
        "check_in_location": check_in.check_in_location if check_in else None,
        "check_out_location": check_in.check_out_location if check_in else None,
        "open_hour": CHECK_IN_OPEN_HOUR,
        "role": user.role.value,
        "skip_modal": skip_modal,
        "counts": counts,
    }


async def get_daily_checkin_logs(
    db: AsyncSession,
    *,
    role: UserRole | None = None,
    target_date: date | None = None,
    query: str | None = None,
    checked_in_only: bool = False,
    checked_out_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    base_query = (
        select(DailyCheckIn, User, Clinic)
        .join(User, User.id == DailyCheckIn.user_id)
        .outerjoin(Clinic, Clinic.id == DailyCheckIn.clinic_id)
    )

    if role is not None:
        base_query = base_query.where(DailyCheckIn.role == role)
    if target_date is not None:
        base_query = base_query.where(DailyCheckIn.check_in_date == target_date)
    if checked_in_only:
        base_query = base_query.where(DailyCheckIn.checked_in_at.is_not(None))
    if checked_out_only:
        base_query = base_query.where(DailyCheckIn.checked_out_at.is_not(None))
    if query:
        like_query = f"%{query.strip()}%"
        if like_query != "%%":
            base_query = base_query.where(
                User.username.ilike(like_query)
                | User.email.ilike(like_query)
            )

    count_query = select(func.count()).select_from(base_query.subquery())
    total = int((await db.execute(count_query)).scalar_one() or 0)

    result = await db.execute(
        base_query
        .order_by(DailyCheckIn.check_in_date.desc(), DailyCheckIn.checked_in_at.desc())
        .limit(limit)
        .offset(offset)
    )

    items = []
    for checkin, user, clinic in result.all():
        duration_minutes = None
        if checkin.checked_out_at:
            delta = checkin.checked_out_at - checkin.checked_in_at
            duration_minutes = max(0, int(delta.total_seconds() // 60))

        items.append(
            {
                "id": checkin.id,
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "role": checkin.role.value,
                "check_in_date": checkin.check_in_date.isoformat(),
                "checked_in_at": checkin.checked_in_at.isoformat() if checkin.checked_in_at else None,
                "checked_out_at": checkin.checked_out_at.isoformat() if checkin.checked_out_at else None,
                "check_in_location": checkin.check_in_location,
                "check_out_location": checkin.check_out_location,
                "clinic_id": checkin.clinic_id,
                "clinic_name": clinic.name if clinic else None,
                "currently_checked_in": checkin.checked_out_at is None,
                "duration_minutes": duration_minutes,
            }
        )

    return items, total
