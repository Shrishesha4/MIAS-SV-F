from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, date, timedelta
from pydantic import BaseModel
import uuid

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.patient import Patient, Appointment
from app.models.admission import Admission
from app.models.student import Clinic

router = APIRouter(prefix="/staff", tags=["Staff"])


class PendingPatient(BaseModel):
    id: str
    patient_id: str
    name: str
    phone: Optional[str]
    email: Optional[str]
    gender: Optional[str]
    dob: Optional[str]
    age: Optional[int]
    blood_group: Optional[str]
    registered_at: str
    has_appointment: bool
    has_admission: bool


class AssignToClinicRequest(BaseModel):
    patient_id: str
    clinic_id: str
    appointment_date: Optional[str] = None
    appointment_time: Optional[str] = None
    notes: Optional[str] = None


class AssignToWardRequest(BaseModel):
    patient_id: str
    ward: str
    room_number: Optional[str] = None
    bed_number: Optional[str] = None
    department: Optional[str] = None
    admitting_diagnosis: Optional[str] = None


@router.get("/pending-patients")
async def get_pending_patients(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50
):
    """Get recently registered patients without appointments or admissions (for reception/nurse assignment)"""
    if user.role not in [UserRole.RECEPTION, UserRole.NURSE, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get patients registered in last 7 days
    recent_cutoff = datetime.utcnow() - timedelta(days=7)
    
    result = await db.execute(
        select(Patient)
        .where(Patient.created_at >= recent_cutoff)
        .order_by(Patient.created_at.desc())
        .limit(limit)
    )
    patients = result.scalars().all()
    
    pending_list = []
    for patient in patients:
        # Check if patient has any appointments
        appt_result = await db.execute(
            select(func.count(Appointment.id))
            .where(Appointment.patient_id == patient.id)
        )
        has_appointment = appt_result.scalar() > 0
        
        # Check if patient has any admissions
        adm_result = await db.execute(
            select(func.count(Admission.id))
            .where(Admission.patient_id == patient.id)
        )
        has_admission = adm_result.scalar() > 0
        
        # Calculate age
        age = None
        if patient.dob:
            today = date.today()
            age = today.year - patient.dob.year - ((today.month, today.day) < (patient.dob.month, patient.dob.day))
        
        pending_list.append({
            "id": patient.id,
            "patient_id": patient.patient_id,
            "name": patient.name,
            "phone": patient.phone,
            "email": patient.email,
            "gender": patient.gender,
            "dob": patient.dob.isoformat() if patient.dob else None,
            "age": age,
            "blood_group": patient.blood_group,
            "registered_at": patient.created_at.isoformat(),
            "has_appointment": has_appointment,
            "has_admission": has_admission,
        })
    
    return pending_list


@router.post("/assign-to-clinic")
async def assign_patient_to_clinic(
    data: AssignToClinicRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create appointment for patient at clinic (reception/admin only)"""
    if user.role not in [UserRole.RECEPTION, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Verify patient exists
    patient_result = await db.execute(
        select(Patient).where(Patient.id == data.patient_id)
    )
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Verify clinic exists
    clinic_result = await db.execute(
        select(Clinic).where(Clinic.id == data.clinic_id)
    )
    clinic = clinic_result.scalar_one_or_none()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    
    # Parse appointment datetime
    if data.appointment_date and data.appointment_time:
        appt_datetime = datetime.fromisoformat(f"{data.appointment_date}T{data.appointment_time}")
    else:
        # Default to current time
        appt_datetime = datetime.utcnow()
    
    # Create appointment
    appointment = Appointment(
        id=str(uuid.uuid4()),
        patient_id=patient.id,
        clinic_id=clinic.id,
        appointment_date=appt_datetime,
        status="Scheduled",
        notes=data.notes,
    )
    db.add(appointment)
    await db.commit()
    
    return {
        "message": f"Patient {patient.name} assigned to {clinic.name}",
        "appointment_id": appointment.id,
        "patient_name": patient.name,
        "clinic_name": clinic.name,
        "appointment_date": appointment.appointment_date.isoformat(),
    }


@router.post("/assign-to-ward")
async def assign_patient_to_ward(
    data: AssignToWardRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create admission for patient to ward (nurse/admin only)"""
    if user.role not in [UserRole.NURSE, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Verify patient exists
    patient_result = await db.execute(
        select(Patient).where(Patient.id == data.patient_id)
    )
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Check if patient already has an active admission
    active_adm_result = await db.execute(
        select(Admission)
        .where(and_(
            Admission.patient_id == patient.id,
            Admission.status == "Active"
        ))
    )
    existing = active_adm_result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Patient already has an active admission")
    
    # Create admission
    admission = Admission(
        id=str(uuid.uuid4()),
        patient_id=patient.id,
        admission_date=datetime.utcnow(),
        status="Active",
        ward=data.ward,
        room_number=data.room_number,
        bed_number=data.bed_number,
        department=data.department,
        admitting_diagnosis=data.admitting_diagnosis,
    )
    db.add(admission)
    await db.commit()
    
    return {
        "message": f"Patient {patient.name} admitted to {data.ward}",
        "admission_id": admission.id,
        "patient_name": patient.name,
        "ward": data.ward,
        "admission_date": admission.admission_date.isoformat(),
    }
