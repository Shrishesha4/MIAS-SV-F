from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User, UserRole
from app.services.daily_checkins import (
    build_daily_checkin_status,
    ensure_daily_checkin,
    get_daily_checkin,
    get_daily_checkin_counts,
    get_active_patient_admission,
)


router = APIRouter(prefix="/attendance", tags=["Attendance"])


class CheckInRequest(BaseModel):
    clinic_id: Optional[str] = None


async def _should_skip_daily_checkin_modal(
    db: AsyncSession,
    *,
    user: User,
) -> bool:
    if user.role in {UserRole.ADMIN, UserRole.STUDENT, UserRole.FACULTY, UserRole.NUTRITIONIST}:
        return True
    if user.role == UserRole.PATIENT:
        admission = await get_active_patient_admission(db, user_id=user.id)
        return admission is None
    return False


@router.get("/today")
async def get_today_checkin_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role == UserRole.ADMIN:
        counts = await get_daily_checkin_counts(db)
        return {
            "today": __import__("datetime").datetime.utcnow().date().isoformat(),
            "checked_in": True,
            "checked_in_at": None,
            "open_hour": 8,
            "role": user.role.value,
            "skip_modal": True,
            "counts": counts,
        }

    check_in = await get_daily_checkin(db, user_id=user.id)
    counts = await get_daily_checkin_counts(db)
    return build_daily_checkin_status(
        user=user,
        check_in=check_in,
        counts=counts,
        skip_modal=await _should_skip_daily_checkin_modal(db, user=user),
    )


@router.post("/check-in")
async def check_in_today(
    body: CheckInRequest = CheckInRequest(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role == UserRole.ADMIN:
        counts = await get_daily_checkin_counts(db)
        return {
            "today": __import__("datetime").datetime.utcnow().date().isoformat(),
            "checked_in": True,
            "checked_in_at": None,
            "open_hour": 8,
            "role": user.role.value,
            "skip_modal": True,
            "counts": counts,
        }

    check_in = await ensure_daily_checkin(
        db,
        user_id=user.id,
        role=user.role,
        clinic_id=body.clinic_id,
    )
    await db.commit()
    counts = await get_daily_checkin_counts(db)
    return build_daily_checkin_status(
        user=user,
        check_in=check_in,
        counts=counts,
        skip_modal=await _should_skip_daily_checkin_modal(db, user=user),
    )
