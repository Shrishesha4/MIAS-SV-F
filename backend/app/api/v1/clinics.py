"""Clinic management endpoints accessible by all authenticated roles."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from datetime import datetime, date
import uuid

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.student import (
    Clinic, ClinicSession, ClinicAppointment,
    Student, StudentPatientAssignment,
)
from app.models.patient import Patient
from app.models.faculty import Faculty

router = APIRouter(prefix="/clinics", tags=["Clinics"])


@router.get("")
async def list_clinics(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all clinics with their faculty info."""
    result = await db.execute(
        select(Clinic).options(selectinload(Clinic.faculty))
    )
    clinics = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "department": c.department,
            "location": c.location,
            "faculty_id": c.faculty_id,
            "faculty_name": c.faculty.name if c.faculty else None,
        }
        for c in clinics
    ]


@router.get("/{clinic_id}")
async def get_clinic(
    clinic_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get clinic details."""
    result = await db.execute(
        select(Clinic)
        .options(selectinload(Clinic.faculty))
        .where(Clinic.id == clinic_id)
    )
    clinic = result.scalar_one_or_none()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return {
        "id": clinic.id,
        "name": clinic.name,
        "department": clinic.department,
        "location": clinic.location,
        "faculty_id": clinic.faculty_id,
        "faculty_name": clinic.faculty.name if clinic.faculty else None,
    }


@router.get("/{clinic_id}/patients")
async def get_clinic_patients_today(
    clinic_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get patients with appointments at a clinic for today."""
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())

    result = await db.execute(
        select(ClinicAppointment)
        .options(selectinload(ClinicAppointment.patient))
        .where(
            and_(
                ClinicAppointment.clinic_id == clinic_id,
                ClinicAppointment.appointment_date >= today_start,
                ClinicAppointment.appointment_date <= today_end,
            )
        )
        .order_by(ClinicAppointment.appointment_time)
    )
    appointments = result.scalars().all()

    return [
        {
            "id": a.id,
            "patient_id": a.patient.patient_id if a.patient else None,
            "patient_db_id": a.patient.id if a.patient else None,
            "patient_name": a.patient.name if a.patient else None,
            "appointment_time": a.appointment_time,
            "provider_name": a.provider_name,
            "status": a.status,
        }
        for a in appointments
    ]


@router.put("/{clinic_id}/appointments/{appointment_id}/status")
async def update_appointment_status(
    clinic_id: str,
    appointment_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update appointment status (Scheduled, Checked In, In Progress, Completed)."""
    result = await db.execute(
        select(ClinicAppointment)
        .where(
            and_(
                ClinicAppointment.id == appointment_id,
                ClinicAppointment.clinic_id == clinic_id,
            )
        )
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    new_status = body.get("status")
    if new_status not in ("Scheduled", "Checked In", "In Progress", "Completed"):
        raise HTTPException(status_code=400, detail="Invalid status")

    appointment.status = new_status
    await db.commit()
    return {"message": "Status updated", "status": new_status}


@router.get("/faculty/{faculty_id}/clinics")
async def get_faculty_clinics(
    faculty_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get clinics managed by a specific faculty member."""
    result = await db.execute(
        select(Clinic)
        .options(selectinload(Clinic.faculty))
        .where(Clinic.faculty_id == faculty_id)
    )
    clinics = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "department": c.department,
            "location": c.location,
            "faculty_name": c.faculty.name if c.faculty else None,
        }
        for c in clinics
    ]


@router.get("/patient/{patient_id}/appointments")
async def get_patient_clinic_appointments(
    patient_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get clinic appointments for a specific patient."""
    # Look up patient by internal id
    result = await db.execute(
        select(ClinicAppointment)
        .options(
            selectinload(ClinicAppointment.clinic).selectinload(Clinic.faculty),
            selectinload(ClinicAppointment.patient),
        )
        .where(ClinicAppointment.patient_id == patient_id)
        .order_by(ClinicAppointment.appointment_date.desc())
    )
    appointments = result.scalars().all()
    return [
        {
            "id": a.id,
            "clinic_name": a.clinic.name if a.clinic else None,
            "clinic_location": a.clinic.location if a.clinic else None,
            "clinic_department": a.clinic.department if a.clinic else None,
            "doctor_name": a.clinic.faculty.name if a.clinic and a.clinic.faculty else None,
            "appointment_date": a.appointment_date.isoformat() if a.appointment_date else None,
            "appointment_time": a.appointment_time,
            "provider_name": a.provider_name,
            "status": a.status,
        }
        for a in appointments
    ]
