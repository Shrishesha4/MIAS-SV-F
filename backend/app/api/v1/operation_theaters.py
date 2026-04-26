"""Operation Theater endpoints.

Admin:  CRUD OTs, update booking status
Student/Faculty: GET schedule, POST booking, GET own bookings
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.operation_theater import OperationTheater, OTBooking, OTStatus
from app.models.user import UserRole, User
from app.models.patient import Patient
from app.models.student import Student
from app.models.ot_manager import OTManager
from app.api.deps import require_role, get_current_user

router = APIRouter(prefix="/ot", tags=["Operation Theaters"])


# ─── helpers ────────────────────────────────────────────────────────────────

def _ot_out(t: OperationTheater) -> dict:
    return {
        "id": t.id,
        "ot_id": t.ot_id,
        "name": t.name,
        "location": t.location,
        "description": t.description,
        "is_active": t.is_active,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _booking_out(b: OTBooking) -> dict:
    from_date = b.from_date or b.date
    to_date = b.to_date or from_date
    return {
        "id": b.id,
        "theater_id": b.theater_id,
        "ot_id": b.theater.ot_id if b.theater else None,
        "ot_location": b.theater.location if b.theater else None,
        "patient_id": b.patient_id,
        "patient_name": b.patient.name if b.patient else None,
        "patient_display_id": b.patient.patient_id if b.patient else None,
        "student_id": b.student_id,
        "date": b.date,
        "from_date": from_date,
        "to_date": to_date,
        "start_time": b.start_time,
        "end_time": b.end_time,
        "procedure": b.procedure,
        "doctor_name": b.doctor_name,
        "notes": b.notes,
        "status": b.status.value,
        "approved_by": b.approved_by,
        "created_at": b.created_at.isoformat() if b.created_at else None,
    }


def _week_dates(anchor: date) -> list[str]:
    """Return the 7 dates of the week containing anchor (Mon-Sun)."""
    monday = anchor - timedelta(days=anchor.weekday())
    return [(monday + timedelta(days=i)).isoformat() for i in range(7)]


def _parse_iso_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(400, f"Invalid {field_name} format (expected YYYY-MM-DD)") from exc


# ─── Admin: OT CRUD ─────────────────────────────────────────────────────────

@router.get("/admin/theaters", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def list_theaters(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OperationTheater).order_by(OperationTheater.ot_id))
    return [_ot_out(t) for t in result.scalars().all()]


@router.post("/admin/theaters", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def create_theater(body: dict[str, Any], db: AsyncSession = Depends(get_db)):
    ot_id: str = (body.get("ot_id") or "").strip()
    if not ot_id:
        raise HTTPException(400, "ot_id required")
    existing = await db.execute(select(OperationTheater).where(OperationTheater.ot_id == ot_id))
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"OT ID '{ot_id}' already exists")
    theater = OperationTheater(
        id=str(uuid.uuid4()),
        ot_id=ot_id,
        name=body.get("name"),
        location=body.get("location"),
        description=body.get("description"),
        is_active=True,
    )
    db.add(theater)
    await db.flush()
    return _ot_out(theater)


@router.put("/admin/theaters/{theater_id}", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def update_theater(theater_id: str, body: dict[str, Any], db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OperationTheater).where(OperationTheater.id == theater_id))
    theater = result.scalar_one_or_none()
    if not theater:
        raise HTTPException(404, "OT not found")
    for field in ("name", "location", "description", "is_active"):
        if field in body:
            setattr(theater, field, body[field])
    await db.flush()
    return _ot_out(theater)


@router.delete("/admin/theaters/{theater_id}", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def delete_theater(theater_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OperationTheater).where(OperationTheater.id == theater_id))
    theater = result.scalar_one_or_none()
    if not theater:
        raise HTTPException(404, "OT not found")
    await db.delete(theater)
    return {"ok": True}


# ─── Admin: booking status update ───────────────────────────────────────────

@router.put("/admin/bookings/{booking_id}/status", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def admin_update_booking_status(
    booking_id: str,
    body: dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OTBooking)
        .options(selectinload(OTBooking.theater), selectinload(OTBooking.patient))
        .where(OTBooking.id == booking_id)
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(404, "Booking not found")
    try:
        booking.status = OTStatus(body["status"])
    except (KeyError, ValueError):
        raise HTTPException(400, "Invalid status")
    if body.get("approved_by"):
        booking.approved_by = body["approved_by"]
    await db.flush()
    return _booking_out(booking)


# ─── Shared: list active theaters ───────────────────────────────────────────

@router.get("/theaters")
async def get_active_theaters(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OperationTheater)
        .where(OperationTheater.is_active == True)  # noqa: E712
        .order_by(OperationTheater.ot_id)
    )
    return [_ot_out(t) for t in result.scalars().all()]


# ─── Shared: weekly schedule ─────────────────────────────────────────────────

@router.get("/schedule")
async def get_schedule(
    anchor_date: str = Query(default=None, description="YYYY-MM-DD, defaults to today"),
    db: AsyncSession = Depends(get_db),
):
    try:
        anchor = date.fromisoformat(anchor_date) if anchor_date else date.today()
    except ValueError:
        raise HTTPException(400, "Invalid date format")

    week = _week_dates(anchor)
    week_start = week[0]
    week_end = week[-1]

    booking_start_expr = func.coalesce(OTBooking.from_date, OTBooking.date)
    booking_end_expr = func.coalesce(OTBooking.to_date, OTBooking.from_date, OTBooking.date)

    result = await db.execute(
        select(OTBooking)
        .options(
            selectinload(OTBooking.theater),
            selectinload(OTBooking.patient),
        )
        .where(
            booking_start_expr <= week_end,
            booking_end_expr >= week_start,
        )
        .order_by(booking_start_expr, OTBooking.start_time)
    )
    bookings = result.scalars().all()

    theaters_result = await db.execute(
        select(OperationTheater)
        .where(OperationTheater.is_active == True)  # noqa: E712
        .order_by(OperationTheater.ot_id)
    )
    theaters = theaters_result.scalars().all()

    return {
        "week_dates": week,
        "theaters": [_ot_out(t) for t in theaters],
        "bookings": [_booking_out(b) for b in bookings],
    }


# ─── Student/Faculty: create booking ─────────────────────────────────────────

@router.post("/bookings")
async def create_booking(
    body: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    required = ("theater_id", "patient_id", "start_time", "end_time", "procedure", "doctor_name")
    for field in required:
        if not body.get(field):
            raise HTTPException(400, f"{field} required")

    from_date_raw = (body.get("from_date") or body.get("date") or "").strip()
    to_date_raw = (body.get("to_date") or from_date_raw).strip()
    if not from_date_raw:
        raise HTTPException(400, "from_date required")

    from_dt = _parse_iso_date(from_date_raw, "from_date")
    to_dt = _parse_iso_date(to_date_raw, "to_date")
    if to_dt < from_dt:
        raise HTTPException(400, "to_date cannot be before from_date")

    start_time = str(body.get("start_time") or "").strip()
    end_time = str(body.get("end_time") or "").strip()
    if len(start_time) != 5 or len(end_time) != 5:
        raise HTTPException(400, "Invalid time format (expected HH:MM)")
    if start_time >= end_time:
        raise HTTPException(400, "end_time must be after start_time")

    # Verify theater exists and is active
    theater_result = await db.execute(
        select(OperationTheater).where(OperationTheater.id == body["theater_id"])
    )
    theater = theater_result.scalar_one_or_none()
    if not theater or not theater.is_active:
        raise HTTPException(404, "OT not found or inactive")

    # Verify patient
    patient_result = await db.execute(
        select(Patient).where(Patient.id == body["patient_id"])
    )
    if not patient_result.scalar_one_or_none():
        raise HTTPException(404, "Patient not found")

    booking_start_expr = func.coalesce(OTBooking.from_date, OTBooking.date)
    booking_end_expr = func.coalesce(OTBooking.to_date, OTBooking.from_date, OTBooking.date)

    # Check for conflict on same theater where date ranges and time windows overlap
    conflict = await db.execute(
        select(OTBooking).where(
            OTBooking.theater_id == body["theater_id"],
            booking_start_expr <= to_date_raw,
            booking_end_expr >= from_date_raw,
            OTBooking.status != OTStatus.CANCELLED,
            OTBooking.start_time < end_time,
            OTBooking.end_time > start_time,
        )
    )
    if conflict.scalar_one_or_none():
        raise HTTPException(409, "Time slot conflict — another booking exists for this OT at the requested time")

    # Resolve student_id if caller is STUDENT
    student_id: str | None = None
    if current_user.role == UserRole.STUDENT:
        st_result = await db.execute(
            select(Student).where(Student.user_id == current_user.id)
        )
        st = st_result.scalar_one_or_none()
        if st:
            student_id = st.id

    booking = OTBooking(
        id=str(uuid.uuid4()),
        theater_id=body["theater_id"],
        patient_id=body["patient_id"],
        student_id=student_id,
        date=from_date_raw,
        from_date=from_date_raw,
        to_date=to_date_raw,
        start_time=start_time,
        end_time=end_time,
        procedure=body["procedure"],
        doctor_name=body["doctor_name"],
        notes=body.get("notes"),
        status=OTStatus.SCHEDULED,
    )
    db.add(booking)
    await db.flush()

    # Reload with relations for response
    await db.refresh(booking, ["theater", "patient"])
    return _booking_out(booking)


# ─── Student: my bookings ────────────────────────────────────────────────────

@router.get("/bookings/mine")
async def get_my_bookings(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    st_result = await db.execute(
        select(Student).where(Student.user_id == current_user.id)
    )
    student = st_result.scalar_one_or_none()
    if not student:
        return []

    result = await db.execute(
        select(OTBooking)
        .options(selectinload(OTBooking.theater), selectinload(OTBooking.patient))
        .where(OTBooking.student_id == student.id)
        .order_by(func.coalesce(OTBooking.from_date, OTBooking.date).desc(), OTBooking.start_time)
    )
    return [_booking_out(b) for b in result.scalars().all()]


# ─── OT Manager: profile ─────────────────────────────────────────────────────

@router.get("/manager/me")
async def get_ot_manager_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.OT_MANAGER)),
):
    mgr = (await db.execute(
        select(OTManager).where(OTManager.user_id == current_user.id)
    )).scalar_one_or_none()
    if not mgr:
        raise HTTPException(status_code=404, detail="OT Manager profile not found")
    return {
        "id": mgr.id,
        "manager_id": mgr.manager_id,
        "name": mgr.name,
        "phone": mgr.phone,
        "email": mgr.email,
        "username": current_user.username,
    }


# ─── OT Manager: all bookings (for dashboard) ────────────────────────────────

@router.get("/manager/bookings")
async def manager_get_all_bookings(
    date_filter: str | None = Query(None, alias="date"),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.OT_MANAGER)),
):
    """Return all bookings visible to OT Manager (for wall view)."""
    q = (
        select(OTBooking)
        .options(selectinload(OTBooking.theater), selectinload(OTBooking.patient))
        .where(OTBooking.status != OTStatus.CANCELLED)
    )
    if date_filter:
        try:
            _parse_iso_date(date_filter, "date")
        except HTTPException:
            date_filter = None
        if date_filter:
            booking_start_expr = func.coalesce(OTBooking.from_date, OTBooking.date)
            booking_end_expr = func.coalesce(OTBooking.to_date, OTBooking.from_date, OTBooking.date)
            q = q.where(
                booking_start_expr <= date_filter,
                booking_end_expr >= date_filter,
            )
    if status_filter:
        try:
            q = q.where(OTBooking.status == OTStatus(status_filter))
        except ValueError:
            pass
    q = q.order_by(func.coalesce(OTBooking.from_date, OTBooking.date), OTBooking.theater_id, OTBooking.start_time)
    result = await db.execute(q)
    return [_booking_out(b) for b in result.scalars().all()]


# ─── OT Manager: approve / reject booking ────────────────────────────────────

@router.put("/manager/bookings/{booking_id}/approve")
async def manager_approve_booking(
    booking_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.OT_MANAGER)),
):
    booking = (await db.execute(
        select(OTBooking)
        .options(selectinload(OTBooking.theater), selectinload(OTBooking.patient))
        .where(OTBooking.id == booking_id)
    )).scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != OTStatus.SCHEDULED:
        raise HTTPException(status_code=400, detail=f"Booking is already {booking.status.value}")

    mgr = (await db.execute(
        select(OTManager).where(OTManager.user_id == current_user.id)
    )).scalar_one_or_none()

    booking.status = OTStatus.CONFIRMED
    booking.approved_by = mgr.name if mgr else current_user.username
    await db.commit()
    await db.refresh(booking)
    return _booking_out(booking)


@router.put("/manager/bookings/{booking_id}/reject")
async def manager_reject_booking(
    booking_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.OT_MANAGER)),
):
    booking = (await db.execute(
        select(OTBooking)
        .where(OTBooking.id == booking_id)
    )).scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking.status = OTStatus.CANCELLED
    await db.commit()
    return {"message": "Booking rejected"}


# ─── OT Manager: update any booking status (full control) ────────────────────

@router.put("/manager/bookings/{booking_id}/status")
async def manager_update_booking_status(
    booking_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.OT_MANAGER)),
):
    booking = (await db.execute(
        select(OTBooking)
        .options(selectinload(OTBooking.theater), selectinload(OTBooking.patient))
        .where(OTBooking.id == booking_id)
    )).scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    try:
        booking.status = OTStatus(body["status"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid status")

    if body.get("approved_by"):
        booking.approved_by = body["approved_by"]

    await db.commit()
    await db.refresh(booking, ["theater", "patient"])
    return _booking_out(booking)
