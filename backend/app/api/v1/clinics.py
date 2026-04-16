"""Clinic management endpoints accessible by all authenticated roles."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from datetime import datetime, date
import uuid
from typing import Optional, List

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.student import (
    Clinic, ClinicSession, ClinicAppointment,
    Student, StudentPatientAssignment,
)
from app.models.patient import Patient
from app.models.faculty import Faculty
from app.api.v1.patient_serialization import serialize_patient_badge_context, serialize_patient_insurance

router = APIRouter(prefix="/clinics", tags=["Clinics"])

CLINIC_ACCESS_MODES = {"WALK_IN", "APPOINTMENT_ONLY"}


def normalize_clinic_access_mode(value: Optional[str], default: str = "WALK_IN") -> str:
    normalized_value = (value or "").strip().upper()
    if not normalized_value:
        return default
    if normalized_value not in CLINIC_ACCESS_MODES:
        raise HTTPException(status_code=400, detail="Invalid clinic access mode")
    return normalized_value


@router.get("")
async def list_clinics(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all clinics with their faculty info."""
    query = select(Clinic).options(selectinload(Clinic.faculty))
    if user.role != UserRole.ADMIN:
        query = query.where(Clinic.is_active == True)
    result = await db.execute(query.order_by(Clinic.created_at.desc()))
    clinics = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "block": c.block,
            "clinic_type": c.clinic_type,
            "access_mode": c.access_mode,
            "walk_in_type": c.walk_in_type,
            "walk_in_types": c.walk_in_types or [],
            "department": c.department,
            "location": c.location,
            "faculty_id": c.faculty_id,
            "faculty_name": c.faculty.name if c.faculty else None,
            "is_active": c.is_active,
        }
        for c in clinics
    ]


class CreateClinicRequest(BaseModel):
    name: str
    block: Optional[str] = None
    clinic_type: str = "OP"
    access_mode: str = "WALK_IN"
    walk_in_type: str = "NO_WALK_IN"
    walk_in_types: Optional[List[str]] = None
    department: Optional[str] = None
    location: Optional[str] = None
    faculty_id: Optional[str] = None
    is_active: bool = True


@router.post("")
async def create_clinic(
    request: CreateClinicRequest,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new clinic (admin only)."""
    clinic = Clinic(
        id=str(uuid.uuid4()),
        name=request.name.strip(),
        block=request.block.strip() if request.block else None,
        clinic_type=request.clinic_type.strip(),
        access_mode=normalize_clinic_access_mode(request.access_mode),
        walk_in_type=request.walk_in_type.strip() if request.walk_in_type else "NO_WALK_IN",
        walk_in_types=[t.strip() for t in request.walk_in_types if t.strip()] if request.walk_in_types else None,
        department=request.department.strip() if request.department else "",
        location=request.location.strip() if request.location else None,
        faculty_id=request.faculty_id,
        is_active=request.is_active,
    )
    db.add(clinic)
    await db.commit()
    return {
        "id": clinic.id,
        "name": clinic.name,
        "block": clinic.block,
        "clinic_type": clinic.clinic_type,
        "access_mode": clinic.access_mode,
        "walk_in_type": clinic.walk_in_type,
        "walk_in_types": clinic.walk_in_types or [],
        "department": clinic.department,
        "location": clinic.location,
        "faculty_id": clinic.faculty_id,
        "is_active": clinic.is_active,
    }


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
    if not clinic or (user.role != UserRole.ADMIN and not clinic.is_active):
        raise HTTPException(status_code=404, detail="Clinic not found")
    return {
        "id": clinic.id,
        "name": clinic.name,
        "block": clinic.block,
        "clinic_type": clinic.clinic_type,
        "access_mode": clinic.access_mode,
        "walk_in_type": clinic.walk_in_type,
        "walk_in_types": clinic.walk_in_types or [],
        "department": clinic.department,
        "location": clinic.location,
        "faculty_id": clinic.faculty_id,
        "faculty_name": clinic.faculty.name if clinic.faculty else None,
        "is_active": clinic.is_active,
    }


class UpdateClinicRequest(BaseModel):
    name: Optional[str] = None
    block: Optional[str] = None
    clinic_type: Optional[str] = None
    access_mode: Optional[str] = None
    walk_in_type: Optional[str] = None
    walk_in_types: Optional[List[str]] = None
    department: Optional[str] = None
    location: Optional[str] = None
    faculty_id: Optional[str] = None
    is_active: Optional[bool] = None


@router.put("/{clinic_id}")
async def update_clinic(
    clinic_id: str,
    request: UpdateClinicRequest,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Update clinic details (admin only)."""
    result = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = result.scalar_one_or_none()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    
    if request.name is not None:
        clinic.name = request.name.strip()
    if request.block is not None:
        clinic.block = request.block.strip() if request.block else None
    if request.clinic_type is not None:
        clinic.clinic_type = request.clinic_type.strip()
    if request.access_mode is not None:
        clinic.access_mode = normalize_clinic_access_mode(request.access_mode, default=clinic.access_mode or "WALK_IN")
    if request.walk_in_type is not None:
        clinic.walk_in_type = request.walk_in_type.strip() if request.walk_in_type else "NO_WALK_IN"
    if request.walk_in_types is not None:
        clinic.walk_in_types = [t.strip() for t in request.walk_in_types if t.strip()] or None
    if request.department is not None:
        clinic.department = request.department.strip() if request.department else ""
    if request.location is not None:
        clinic.location = request.location.strip() if request.location else None
    if request.faculty_id is not None:
        clinic.faculty_id = request.faculty_id
    if request.is_active is not None:
        clinic.is_active = request.is_active
    
    await db.commit()
    await db.refresh(clinic)
    
    return {
        "id": clinic.id,
        "name": clinic.name,
        "block": clinic.block,
        "clinic_type": clinic.clinic_type,
        "access_mode": clinic.access_mode,
        "walk_in_type": clinic.walk_in_type,
        "walk_in_types": clinic.walk_in_types or [],
        "department": clinic.department,
        "location": clinic.location,
        "faculty_id": clinic.faculty_id,
        "is_active": clinic.is_active,
    }


@router.delete("/{clinic_id}")
async def delete_clinic(
    clinic_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Delete a clinic (admin only)."""
    result = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = result.scalar_one_or_none()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    
    await db.delete(clinic)
    await db.commit()
    return {"message": "Clinic deleted successfully"}


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
        .options(selectinload(ClinicAppointment.patient).selectinload(Patient.insurance_policies))
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

    clinic_patients = []
    included_patient_ids: set[str] = set()
    for appointment in appointments:
        if appointment.patient:
            included_patient_ids.add(appointment.patient.id)
        clinic_patients.append({
            "id": appointment.id,
            "patient_id": appointment.patient.patient_id if appointment.patient else None,
            "patient_db_id": appointment.patient.id if appointment.patient else None,
            "patient_name": appointment.patient.name if appointment.patient else None,
            "photo": appointment.patient.photo if appointment.patient else None,
            "appointment_time": appointment.appointment_time,
            "provider_name": appointment.provider_name,
            "status": appointment.status,
            "source": "appointment",
            "assignment_id": None,
            "assigned_student_name": None,
            **serialize_patient_badge_context(appointment.patient),
            "insurance_policies": serialize_patient_insurance(appointment.patient),
        })

    active_session_result = await db.execute(
        select(ClinicSession)
        .options(selectinload(ClinicSession.student))
        .where(
            and_(
                ClinicSession.clinic_id == clinic_id,
                ClinicSession.checked_in_at.is_not(None),
                ClinicSession.checked_out_at.is_(None),
            )
        )
    )
    active_sessions = active_session_result.scalars().all()
    active_students = {session.student_id: session.student for session in active_sessions if session.student}
    active_session_by_student = {session.student_id: session for session in active_sessions}

    if active_students:
        assignment_result = await db.execute(
            select(StudentPatientAssignment)
            .options(selectinload(StudentPatientAssignment.patient).selectinload(Patient.insurance_policies))
            .where(
                and_(
                    StudentPatientAssignment.student_id.in_(list(active_students.keys())),
                    StudentPatientAssignment.status == "Active",
                )
            )
        )
        assignments = assignment_result.scalars().all()
        for assignment in assignments:
            patient = assignment.patient
            if not patient or patient.id in included_patient_ids:
                continue
            session = active_session_by_student.get(assignment.student_id)
            student = active_students.get(assignment.student_id)
            clinic_patients.append({
                "id": assignment.id,
                "patient_id": patient.patient_id,
                "patient_db_id": patient.id,
                "patient_name": patient.name,
                "photo": patient.photo,
                "appointment_time": session.checked_in_at.strftime("%I:%M %p") if session and session.checked_in_at else "Now",
                "provider_name": student.name if student else None,
                "status": "Checked In",
                "source": "assignment",
                "assignment_id": assignment.id,
                "assigned_student_name": student.name if student else None,
                **serialize_patient_badge_context(patient),
                "insurance_policies": serialize_patient_insurance(patient),
            })
            included_patient_ids.add(patient.id)

    return clinic_patients


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


@router.get("/{clinic_id}/search-patient")
async def search_patient_for_checkin(
    clinic_id: str,
    q: str = Query(""),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search for a patient by ID or name for clinic check-in."""
    if not q or len(q) < 2:
        return []
    result = await db.execute(
        select(Patient)
        .options(selectinload(Patient.insurance_policies))
        .where(
            Patient.patient_id.ilike(f"%{q}%") | Patient.name.ilike(f"%{q}%")
        )
        .limit(10)
    )
    patients = result.scalars().all()
    
    # Batch-fetch clinic names
    clinic_ids = list({p.clinic_id for p in patients if p.clinic_id})
    clinic_map: dict = {}
    if clinic_ids:
        clinic_result = await db.execute(
            select(Clinic.id, Clinic.name).where(Clinic.id.in_(clinic_ids))
        )
        clinic_map = {row.id: row.name for row in clinic_result.all()}
    
    return [
        {
            "id": p.id,
            "patient_id": p.patient_id,
            "name": p.name,
            "photo": p.photo,
            "gender": p.gender.value if p.gender else None,
            "blood_group": p.blood_group,
            "phone": p.phone,
            "clinic_id": p.clinic_id,
            "clinic_name": clinic_map.get(p.clinic_id) if p.clinic_id else None,
            **serialize_patient_badge_context(p),
            "insurance_policies": serialize_patient_insurance(p),
        }
        for p in patients
    ]


@router.post("/{clinic_id}/check-in")
async def check_in_patient(
    clinic_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check in a patient to a clinic by creating an appointment."""
    patient_id = body.get("patient_id")
    if not patient_id:
        raise HTTPException(status_code=400, detail="patient_id is required")

    # Look up patient — accept either the internal UUID or the display patient_id
    result = await db.execute(
        select(Patient).where(
            (Patient.id == patient_id) | (Patient.patient_id == patient_id)
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Check clinic exists
    clinic_result = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = clinic_result.scalar_one_or_none()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    if clinic.access_mode == "APPOINTMENT_ONLY":
        raise HTTPException(status_code=400, detail="This clinic accepts appointments only")

    now = datetime.now()
    appointment = ClinicAppointment(
        id=str(uuid.uuid4()),
        clinic_id=clinic_id,
        patient_id=patient.id,
        appointment_date=now,
        appointment_time=now.strftime("%I:%M %p"),
        provider_name=body.get("provider_name", clinic.faculty.name if hasattr(clinic, 'faculty') and clinic.faculty else ""),
        status="Checked In",
    )
    db.add(appointment)
    await db.commit()

    return {
        "id": appointment.id,
        "patient_id": patient.patient_id,
        "patient_name": patient.name,
        "status": "Checked In",
        "message": f"{patient.name} checked in successfully",
    }


@router.post("/{clinic_id}/appointments")
async def create_appointment(
    clinic_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new clinic appointment."""
    patient_id = body.get("patient_id")
    if not patient_id:
        raise HTTPException(status_code=400, detail="patient_id is required")

    # Look up patient
    result = await db.execute(
        select(Patient).where(
            (Patient.id == patient_id) | (Patient.patient_id == patient_id)
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Verify clinic
    clinic_result = await db.execute(
        select(Clinic).options(selectinload(Clinic.faculty)).where(Clinic.id == clinic_id)
    )
    clinic = clinic_result.scalar_one_or_none()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    appt_date_str = body.get("date")
    if appt_date_str:
        appt_date = datetime.strptime(appt_date_str, "%Y-%m-%d")
    else:
        appt_date = datetime.now()

    appointment = ClinicAppointment(
        id=str(uuid.uuid4()),
        clinic_id=clinic_id,
        patient_id=patient.id,
        appointment_date=appt_date,
        appointment_time=body.get("time", "09:00 AM"),
        provider_name=body.get("provider_name", clinic.faculty.name if clinic.faculty else ""),
        status=body.get("status", "Scheduled"),
    )
    db.add(appointment)
    await db.commit()

    return {
        "id": appointment.id,
        "patient_id": patient.patient_id,
        "patient_name": patient.name,
        "status": appointment.status,
        "message": "Appointment created successfully",
    }


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
            "clinic_type": c.clinic_type,
            "access_mode": c.access_mode,
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
