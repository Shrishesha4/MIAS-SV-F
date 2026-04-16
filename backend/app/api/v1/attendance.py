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
    ensure_ip_auto_checkin,
)


router = APIRouter(prefix="/attendance", tags=["Attendance"])


class CheckInRequest(BaseModel):
    clinic_id: Optional[str] = None


@router.get("/today")
async def get_today_checkin_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Admin users are auto-checked-in and don't need daily check-in
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

    # For admitted patients (IP), auto-check-in on day 2+
    if user.role == UserRole.PATIENT:
        auto_checkin = await ensure_ip_auto_checkin(db, user_id=user.id)
        if auto_checkin:
            await db.commit()
            counts = await get_daily_checkin_counts(db)
            return build_daily_checkin_status(user=user, check_in=auto_checkin, counts=counts)

    check_in = await get_daily_checkin(db, user_id=user.id)
    counts = await get_daily_checkin_counts(db)
    return build_daily_checkin_status(user=user, check_in=check_in, counts=counts)


@router.post("/check-in")
async def check_in_today(
    body: CheckInRequest = CheckInRequest(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Admin users don't need to check in
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
    return build_daily_checkin_status(user=user, check_in=check_in, counts=counts)
