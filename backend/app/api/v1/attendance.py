from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User, UserRole
from app.services.daily_checkins import (
    build_daily_checkin_status,
    check_out_daily_checkin,
    ensure_daily_checkin,
    get_daily_checkin,
    get_daily_checkin_counts,
    get_daily_checkin_logs,
    get_active_patient_admission,
)


router = APIRouter(prefix="/attendance", tags=["Attendance"])


class CheckInRequest(BaseModel):
    clinic_id: Optional[str] = None
    location: Optional[str] = None


class CheckOutRequest(BaseModel):
    location: Optional[str] = None


async def _should_skip_daily_checkin_modal(
    db: AsyncSession,
    *,
    user: User,
) -> bool:
    if user.role == UserRole.ADMIN:
        return True
    if user.role == UserRole.PATIENT:
        admission = await get_active_patient_admission(db, user_id=user.id)
        return admission is None
    return False


def _parse_optional_role(value: str | None) -> UserRole | None:
    if not value:
        return None
    normalized = value.strip().upper()
    if not normalized:
        return None
    try:
        return UserRole(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Unsupported role '{value}'") from exc


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
        location=body.location,
    )
    await db.commit()
    counts = await get_daily_checkin_counts(db)
    return build_daily_checkin_status(
        user=user,
        check_in=check_in,
        counts=counts,
        skip_modal=await _should_skip_daily_checkin_modal(db, user=user),
    )


@router.post("/check-out")
async def check_out_today(
    body: CheckOutRequest = CheckOutRequest(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role == UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Admin users do not require daily check-out")

    check_in = await check_out_daily_checkin(
        db,
        user_id=user.id,
        location=body.location,
    )
    if not check_in:
        raise HTTPException(status_code=400, detail="No check-in found for today")

    await db.commit()
    counts = await get_daily_checkin_counts(db)
    return build_daily_checkin_status(
        user=user,
        check_in=check_in,
        counts=counts,
        skip_modal=await _should_skip_daily_checkin_modal(db, user=user),
    )


@router.get("/logs")
async def list_attendance_logs(
    role: str | None = Query(default=None),
    target_date: date | None = Query(default=None),
    query: str | None = Query(default=None),
    checked_in_only: bool = Query(default=False),
    checked_out_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admin users can access attendance logs")

    items, total = await get_daily_checkin_logs(
        db,
        role=_parse_optional_role(role),
        target_date=target_date,
        query=query,
        checked_in_only=checked_in_only,
        checked_out_only=checked_out_only,
        limit=limit,
        offset=offset,
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }
