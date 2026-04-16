from __future__ import annotations

from datetime import datetime, time as dt_time
import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from app.models.student import Clinic, ClinicAppointment
from app.models.user import UserRole
from app.services.daily_checkins import ensure_daily_checkin


ACTIVE_CLINIC_APPOINTMENT_STATUSES = ("Scheduled", "Checked In", "In Progress")


async def get_same_day_clinic_appointment(
    db: AsyncSession,
    *,
    patient_id: str,
    clinic_id: str,
    target_datetime: datetime | None = None,
) -> ClinicAppointment | None:
    timestamp = target_datetime or datetime.utcnow()
    day_start = datetime.combine(timestamp.date(), dt_time.min)
    day_end = datetime.combine(timestamp.date(), dt_time.max)
    result = await db.execute(
        select(ClinicAppointment)
        .where(
            and_(
                ClinicAppointment.patient_id == patient_id,
                ClinicAppointment.clinic_id == clinic_id,
                ClinicAppointment.appointment_date >= day_start,
                ClinicAppointment.appointment_date <= day_end,
                ClinicAppointment.status.in_(ACTIVE_CLINIC_APPOINTMENT_STATUSES),
            )
        )
        .order_by(ClinicAppointment.appointment_date.desc())
    )
    return result.scalars().first()


async def ensure_clinic_checkin(
    db: AsyncSession,
    *,
    patient: Patient,
    clinic: Clinic,
    appointment_datetime: datetime | None = None,
    provider_name: str | None = None,
    status: str = "Checked In",
) -> tuple[ClinicAppointment, bool]:
    timestamp = appointment_datetime or datetime.utcnow()
    appointment = await get_same_day_clinic_appointment(
        db,
        patient_id=patient.id,
        clinic_id=clinic.id,
        target_datetime=timestamp,
    )
    resolved_provider = provider_name or (clinic.faculty.name if clinic.faculty else clinic.name)

    if appointment:
        if appointment.status == "Scheduled" and status in {"Checked In", "In Progress"}:
            appointment.status = status
        if status == "In Progress":
            appointment.status = "In Progress"
        if not appointment.provider_name:
            appointment.provider_name = resolved_provider
        patient.clinic_id = clinic.id
        if patient.user_id:
            await ensure_daily_checkin(db, user_id=patient.user_id, role=UserRole.PATIENT, checked_in_at=timestamp)
        await db.flush()
        return appointment, False

    appointment = ClinicAppointment(
        id=str(uuid.uuid4()),
        clinic_id=clinic.id,
        patient_id=patient.id,
        appointment_date=timestamp,
        appointment_time=timestamp.strftime("%I:%M %p"),
        provider_name=resolved_provider,
        status=status,
    )
    db.add(appointment)
    patient.clinic_id = clinic.id
    if patient.user_id:
        await ensure_daily_checkin(db, user_id=patient.user_id, role=UserRole.PATIENT, checked_in_at=timestamp)
    await db.flush()
    return appointment, True
