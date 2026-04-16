from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import date, datetime, timedelta
import uuid

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.nurse import Nurse, NurseNotification
from app.models.nurse_order import NurseOrder
from app.models.sbar_note import SBARNote
from app.models.patient import Patient, Appointment
from app.models.admission import Admission
from app.models.student import ClinicAppointment, Clinic
from app.schemas.nurse import NurseResponse, NurseUpdate, NurseStationSelect, SBARNoteCreate
from app.api.v1.patient_serialization import serialize_patient_badge_context, serialize_patient_insurance


router = APIRouter(prefix="/nurses", tags=["Nurses"])


@router.get("/clinics")
async def list_available_clinics(
    user: User = Depends(require_role(UserRole.NURSE)),
    db: AsyncSession = Depends(get_db),
):
    """Return active clinics for nurse station selection."""
    result = await db.execute(
        select(Clinic.id, Clinic.name, Clinic.location, Clinic.department)
        .where(Clinic.is_active == True)
        .order_by(Clinic.name.asc())
    )
    return [
        {"id": row.id, "name": row.name, "location": row.location, "department": row.department}
        for row in result.all()
    ]


@router.get("/wards", response_model=List[str])
async def list_available_wards(
    user: User = Depends(require_role(UserRole.NURSE)),
    db: AsyncSession = Depends(get_db),
):
    """Return distinct ward names derived from admissions data."""
    nurse_result = await db.execute(
        select(Nurse).where(Nurse.user_id == user.id)
    )
    nurse = nurse_result.scalar_one_or_none()

    if not nurse:
        raise HTTPException(status_code=404, detail="Nurse profile not found")

    ward_result = await db.execute(
        select(Admission.ward)
        .where(Admission.ward.is_not(None))
        .where(Admission.ward != "")
        .distinct()
        .order_by(Admission.ward.asc())
    )

    wards = [ward for ward in ward_result.scalars().all() if ward]
    if nurse.ward and nurse.ward not in wards:
        wards.append(nurse.ward)
        wards.sort()

    return wards


@router.get("/me", response_model=NurseResponse)
async def get_current_nurse(
    user: User = Depends(require_role(UserRole.NURSE)),
    db: AsyncSession = Depends(get_db),
):
    """Get the current logged-in nurse's profile"""
    result = await db.execute(
        select(Nurse).where(Nurse.user_id == user.id)
    )
    nurse = result.scalar_one_or_none()

    if not nurse:
        raise HTTPException(status_code=404, detail="Nurse profile not found")

    return nurse


@router.put("/me/station", response_model=NurseResponse)
async def select_nurse_station(
    station: NurseStationSelect,
    user: User = Depends(require_role(UserRole.NURSE)),
    db: AsyncSession = Depends(get_db),
):
    """First-time setup: select hospital and ward/station"""
    result = await db.execute(
        select(Nurse).where(Nurse.user_id == user.id)
    )
    nurse = result.scalar_one_or_none()

    if not nurse:
        raise HTTPException(status_code=404, detail="Nurse profile not found")

    nurse.hospital = station.hospital
    nurse.ward = station.ward
    nurse.shift = station.shift
    nurse.department = station.department
    nurse.has_selected_station = 1

    nurse_id = nurse.id  # Store ID before commit
    await db.commit()
    
    # Reload nurse to get fresh data
    result = await db.execute(
        select(Nurse).where(Nurse.id == nurse_id)
    )
    nurse = result.scalar_one()

    return nurse


@router.put("/me", response_model=NurseResponse)
async def update_nurse_profile(
    updates: NurseUpdate,
    user: User = Depends(require_role(UserRole.NURSE)),
    db: AsyncSession = Depends(get_db),
):
    """Update nurse profile information"""
    result = await db.execute(
        select(Nurse).where(Nurse.user_id == user.id)
    )
    nurse = result.scalar_one_or_none()

    if not nurse:
        raise HTTPException(status_code=404, detail="Nurse profile not found")

    # Update fields
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(nurse, field, value)

    nurse_id = nurse.id  # Store ID before commit
    await db.commit()
    
    # Reload nurse to get fresh data
    result = await db.execute(
        select(Nurse).where(Nurse.id == nurse_id)
    )
    nurse = result.scalar_one()

    return nurse


@router.get("/ward-patients")
async def get_ward_patients(
    user: User = Depends(require_role(UserRole.NURSE)),
    db: AsyncSession = Depends(get_db),
):
    """Get all active ward patients and newly registered patients visible to nurses."""
    result = await db.execute(
        select(Nurse).where(Nurse.user_id == user.id)
    )
    nurse = result.scalar_one_or_none()

    if not nurse:
        raise HTTPException(status_code=404, detail="Nurse profile not found")

    if not nurse.hospital:
        raise HTTPException(status_code=400, detail="Nurse has not selected a clinic yet")

    # All nurses can see all currently admitted ward patients.
    result = await db.execute(
        select(Admission)
        .options(selectinload(Admission.patient).selectinload(Patient.insurance_policies))
        .where(Admission.status == "Active")
        .order_by(Admission.admission_date.desc())
    )
    admissions = result.scalars().all()

    patients_data = []
    for admission in admissions:
        patient = admission.patient
        if patient:
            # Count pending tasks (simplified - you might want to add a proper tasks model)
            pending_count = 0
            
            # Calculate age from date_of_birth
            age = (date.today() - patient.date_of_birth).days // 365 if patient.date_of_birth else None
            
            patients_data.append({
                "id": patient.id,
                "patient_id": patient.patient_id,
                "name": patient.name,
                "photo": patient.photo,
                "age": age,
                "gender": patient.gender.value if patient.gender else None,
                "ward": admission.ward or "General Ward",
                "bed_number": admission.bed_number or "N/A",
                "admission_id": admission.id,
                "admission_date": admission.admission_date.isoformat() if admission.admission_date else None,
                "primary_diagnosis": admission.diagnosis,
                "pending_tasks": pending_count,
                "admission_status": admission.status,
                **serialize_patient_badge_context(patient),
                "insurance_policies": serialize_patient_insurance(patient),
            })

    recent_cutoff = datetime.utcnow() - timedelta(days=7)
    recent_patients_result = await db.execute(
        select(Patient)
        .options(selectinload(Patient.insurance_policies))
        .where(Patient.created_at >= recent_cutoff)
        .order_by(Patient.created_at.desc())
        .limit(50)
    )
    recent_patients = recent_patients_result.scalars().all()

    newly_registered = []
    for patient in recent_patients:
        appointment_result = await db.execute(
            select(func.count(Appointment.id)).where(Appointment.patient_id == patient.id)
        )
        clinic_appointment_result = await db.execute(
            select(func.count(ClinicAppointment.id)).where(ClinicAppointment.patient_id == patient.id)
        )
        admission_result = await db.execute(
            select(func.count(Admission.id)).where(Admission.patient_id == patient.id)
        )

        has_appointment = ((appointment_result.scalar() or 0) > 0) or ((clinic_appointment_result.scalar() or 0) > 0)
        has_admission = (admission_result.scalar() or 0) > 0

        age = None
        if patient.date_of_birth:
            age = (date.today() - patient.date_of_birth).days // 365

        newly_registered.append({
            "id": patient.id,
            "patient_id": patient.patient_id,
            "name": patient.name,
            "photo": patient.photo,
            "age": age,
            "gender": patient.gender.value if patient.gender else None,
            "phone": patient.phone,
            "registered_at": patient.created_at.isoformat(),
            "has_appointment": has_appointment,
            "has_admission": has_admission,
            **serialize_patient_badge_context(patient),
            "insurance_policies": serialize_patient_insurance(patient),
        })

    return {
        "nurse": {
            "name": nurse.name,
            "hospital": nurse.hospital,
            "ward": nurse.ward,
            "shift": nurse.shift,
        },
        "patients": patients_data,
        "newly_registered": newly_registered,
    }


@router.get("/notifications")
async def get_nurse_notifications(
    user: User = Depends(require_role(UserRole.NURSE)),
    db: AsyncSession = Depends(get_db),
):
    """Get notifications for the current nurse"""
    result = await db.execute(
        select(Nurse).where(Nurse.user_id == user.id)
    )
    nurse = result.scalar_one_or_none()

    if not nurse:
        raise HTTPException(status_code=404, detail="Nurse profile not found")

    result = await db.execute(
        select(NurseNotification)
        .where(NurseNotification.nurse_id == nurse.id)
        .order_by(NurseNotification.created_at.desc())
        .limit(50)
    )
    notifications = result.scalars().all()

    return [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifications
    ]


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user: User = Depends(require_role(UserRole.NURSE)),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read"""
    result = await db.execute(
        select(Nurse).where(Nurse.user_id == user.id)
    )
    nurse = result.scalar_one_or_none()

    if not nurse:
        raise HTTPException(status_code=404, detail="Nurse profile not found")

    result = await db.execute(
        select(NurseNotification)
        .where(
            and_(
                NurseNotification.id == notification_id,
                NurseNotification.nurse_id == nurse.id
            )
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = 1
    await db.commit()

    return {"message": "Notification marked as read"}


@router.get("/patients/{patient_id}/orders")
async def get_patient_orders(
    patient_id: str,
    user: User = Depends(require_role(UserRole.NURSE)),
    db: AsyncSession = Depends(get_db),
):
    """Get all orders for a specific patient"""
    result = await db.execute(
        select(NurseOrder)
        .where(NurseOrder.patient_id == patient_id)
        .order_by(NurseOrder.is_completed.asc(), NurseOrder.created_at.desc())
    )
    orders = result.scalars().all()

    return [
        {
            "id": o.id,
            "order_id": o.order_id,
            "order_type": o.order_type,
            "title": o.title,
            "description": o.description,
            "scheduled_time": o.scheduled_time,
            "is_completed": o.is_completed,
            "completed_at": o.completed_at.isoformat() if o.completed_at else None,
            "created_at": o.created_at.isoformat(),
        }
        for o in orders
    ]


@router.put("/orders/{order_id}/complete")
async def complete_order(
    order_id: str,
    user: User = Depends(require_role(UserRole.NURSE)),
    db: AsyncSession = Depends(get_db),
):
    """Mark an order as completed"""
    result = await db.execute(
        select(Nurse).where(Nurse.user_id == user.id)
    )
    nurse = result.scalar_one_or_none()

    if not nurse:
        raise HTTPException(status_code=404, detail="Nurse profile not found")

    result = await db.execute(
        select(NurseOrder).where(NurseOrder.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.is_completed = True
    order.completed_at = datetime.utcnow()
    order.nurse_id = nurse.id

    order_id = order.id  # Store ID before commit
    await db.commit()
    
    # Reload order to get fresh data
    result = await db.execute(
        select(NurseOrder).where(NurseOrder.id == order_id)
    )
    order = result.scalar_one()

    return {
        "id": order.id,
        "order_id": order.order_id,
        "is_completed": order.is_completed,
        "completed_at": order.completed_at.isoformat() if order.completed_at else None,
    }


@router.get("/patients/{patient_id}/sbar")
async def get_patient_sbar_notes(
    patient_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all SBAR notes for a specific patient (viewable by all authenticated users)"""
    result = await db.execute(
        select(SBARNote)
        .where(SBARNote.patient_id == patient_id)
        .order_by(SBARNote.created_at.desc())
    )
    notes = result.scalars().all()

    return [
        {
            "id": n.id,
            "sbar_id": n.sbar_id,
            "nurse_name": n.nurse_name,
            "situation": n.situation,
            "background": n.background,
            "assessment": n.assessment,
            "recommendation": n.recommendation,
            "created_at": n.created_at.isoformat(),
            "updated_at": n.updated_at.isoformat(),
        }
        for n in notes
    ]


@router.post("/patients/{patient_id}/sbar")
async def create_sbar_note(
    patient_id: str,
    admission_id: str,
    data: SBARNoteCreate,
    user: User = Depends(require_role(UserRole.NURSE)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new SBAR note for a patient"""
    result = await db.execute(
        select(Nurse).where(Nurse.user_id == user.id)
    )
    nurse = result.scalar_one_or_none()

    if not nurse:
        raise HTTPException(status_code=404, detail="Nurse profile not found")

    patient_result = await db.execute(
        select(Patient).where(Patient.id == patient_id)
    )
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    admission_result = await db.execute(
        select(Admission).where(
            Admission.id == admission_id,
            Admission.patient_id == patient_id,
        )
    )
    admission = admission_result.scalar_one_or_none()
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found for patient")

    # Generate SBAR ID
    result = await db.execute(select(SBARNote))
    existing_sbars = result.scalars().all()
    sbar_id = f"SBAR-{len(existing_sbars) + 1:03d}"

    sbar_note = SBARNote(
        id=str(uuid.uuid4()),
        sbar_id=sbar_id,
        patient_id=patient_id,
        admission_id=admission_id,
        nurse_id=nurse.id,
        nurse_name=nurse.name,
        situation=data.situation,
        background=data.background,
        assessment=data.assessment,
        recommendation=data.recommendation,
    )

    db.add(sbar_note)
    sbar_note_id = sbar_note.id  # Store ID before commit
    await db.commit()
    
    # Reload sbar_note to get fresh data
    result = await db.execute(
        select(SBARNote).where(SBARNote.id == sbar_note_id)
    )
    sbar_note = result.scalar_one()

    return {
        "id": sbar_note.id,
        "sbar_id": sbar_note.sbar_id,
        "nurse_name": sbar_note.nurse_name,
        "situation": sbar_note.situation,
        "background": sbar_note.background,
        "assessment": sbar_note.assessment,
        "recommendation": sbar_note.recommendation,
        "created_at": sbar_note.created_at.isoformat(),
    }
