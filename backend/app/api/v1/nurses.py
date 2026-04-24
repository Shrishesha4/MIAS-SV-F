from fastapi import APIRouter, Depends, HTTPException, Query
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

NURSE_ACCESS_ROLES = (UserRole.NURSE, UserRole.NURSE_SUPERINTENDENT)


async def _get_nurse_profile(db: AsyncSession, *, user_id: str) -> Nurse:
    result = await db.execute(select(Nurse).where(Nurse.user_id == user_id))
    nurse = result.scalar_one_or_none()
    if not nurse:
        raise HTTPException(status_code=404, detail="Nurse profile not found")
    return nurse


async def _get_active_clinic(db: AsyncSession, clinic_id: str) -> Clinic:
    result = await db.execute(
        select(Clinic).where(Clinic.id == clinic_id, Clinic.is_active == True)
    )
    clinic = result.scalar_one_or_none()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return clinic


async def _find_active_clinic_by_name(db: AsyncSession, clinic_name: str | None) -> Clinic | None:
    if not clinic_name:
        return None
    normalized_name = clinic_name.strip().lower()
    if not normalized_name:
        return None
    result = await db.execute(
        select(Clinic)
        .where(func.lower(Clinic.name) == normalized_name, Clinic.is_active == True)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _resolve_nurse_clinic(db: AsyncSession, nurse: Nurse) -> Clinic | None:
    if nurse.clinic_id:
        result = await db.execute(
            select(Clinic).where(Clinic.id == nurse.clinic_id, Clinic.is_active == True)
        )
        clinic = result.scalar_one_or_none()
        if clinic:
            return clinic
    return await _find_active_clinic_by_name(db, nurse.hospital)


async def _list_clinic_wards(db: AsyncSession, clinic_id: str) -> list[str]:
    result = await db.execute(
        select(Nurse.ward)
        .join(User, Nurse.user_id == User.id)
        .where(
            Nurse.clinic_id == clinic_id,
            User.role == UserRole.NURSE,
            Nurse.ward.is_not(None),
            Nurse.ward != "",
        )
        .distinct()
        .order_by(Nurse.ward.asc())
    )
    return [ward for ward in result.scalars().all() if ward]


async def _resolve_station_scope(
    db: AsyncSession,
    *,
    nurse: Nurse,
    clinic_id: str | None,
    ward: str | None,
) -> tuple[Clinic | None, list[str]]:
    clinic = None
    effective_wards: list[str] = []

    effective_clinic_id = clinic_id or nurse.clinic_id
    if effective_clinic_id:
        clinic = await _get_active_clinic(db, effective_clinic_id)

    normalized_ward = (ward or "").strip()
    if normalized_ward:
        effective_wards = [normalized_ward]
    elif not clinic_id and nurse.ward:
        effective_wards = [nurse.ward]
    elif clinic:
        effective_wards = await _list_clinic_wards(db, clinic.id)

    return clinic, effective_wards


@router.get("/clinics")
async def list_available_clinics(
    user: User = Depends(require_role(*NURSE_ACCESS_ROLES)),
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
    user: User = Depends(require_role(*NURSE_ACCESS_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """Return distinct ward names derived from admissions data."""
    nurse = await _get_nurse_profile(db, user_id=user.id)

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
    user: User = Depends(require_role(*NURSE_ACCESS_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """Get the current logged-in nurse's profile"""
    nurse = await _get_nurse_profile(db, user_id=user.id)
    clinic = await _resolve_nurse_clinic(db, nurse)
    if clinic:
        nurse.clinic_id = clinic.id
        nurse.hospital = clinic.name
        if not nurse.department:
            nurse.department = clinic.department

    return nurse


@router.get("/stations")
async def list_superintendent_stations(
    user: User = Depends(require_role(UserRole.NURSE_SUPERINTENDENT)),
    db: AsyncSession = Depends(get_db),
):
    clinics_result = await db.execute(
        select(Clinic)
        .where(Clinic.is_active == True)
        .order_by(Clinic.name.asc())
    )
    clinics = clinics_result.scalars().all()
    clinics_by_id = {clinic.id: clinic for clinic in clinics}

    nurse_rows_result = await db.execute(
        select(Nurse, User.role)
        .join(User, Nurse.user_id == User.id)
        .where(User.role.in_([UserRole.NURSE, UserRole.NURSE_SUPERINTENDENT]))
        .order_by(Nurse.name.asc())
    )

    active_admission_counts_result = await db.execute(
        select(Admission.ward, func.count(Admission.id))
        .where(Admission.status == "Active")
        .group_by(Admission.ward)
    )
    active_admission_counts = {
        ward: count for ward, count in active_admission_counts_result.all() if ward
    }

    stations = {
        clinic.id: {
            "clinic_id": clinic.id,
            "clinic_name": clinic.name,
            "location": clinic.location,
            "department": clinic.department,
            "wards": [],
            "assigned_nurses": [],
            "active_patient_count": 0,
        }
        for clinic in clinics
    }

    for nurse, role in nurse_rows_result.all():
        if role != UserRole.NURSE:
            continue
        clinic = clinics_by_id.get(nurse.clinic_id) or await _find_active_clinic_by_name(db, nurse.hospital)
        if not clinic:
            continue
        station = stations[clinic.id]
        if nurse.ward and nurse.ward not in station["wards"]:
            station["wards"].append(nurse.ward)
        station["assigned_nurses"].append(
            {
                "id": nurse.id,
                "nurse_id": nurse.nurse_id,
                "name": nurse.name,
                "ward": nurse.ward,
                "shift": nurse.shift,
            }
        )

    for station in stations.values():
        station["wards"].sort()
        station["assigned_nurses"].sort(key=lambda item: item["name"])
        station["active_patient_count"] = sum(
            active_admission_counts.get(ward, 0) for ward in station["wards"]
        )

    return list(stations.values())


@router.put("/me/station", response_model=NurseResponse)
async def select_nurse_station(
    station: NurseStationSelect,
    user: User = Depends(require_role(*NURSE_ACCESS_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """First-time setup: select hospital and ward/station"""
    nurse = await _get_nurse_profile(db, user_id=user.id)

    clinic = None
    if station.clinic_id:
        clinic = await _get_active_clinic(db, station.clinic_id)
        nurse.clinic_id = clinic.id
        nurse.hospital = clinic.name
    else:
        nurse.clinic_id = None
        nurse.hospital = station.hospital
    nurse.ward = station.ward
    nurse.shift = station.shift
    nurse.department = station.department or (clinic.department if clinic else nurse.department)
    nurse.has_selected_station = 1 if (nurse.clinic_id or nurse.hospital or user.role == UserRole.NURSE_SUPERINTENDENT) else 0

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
    user: User = Depends(require_role(*NURSE_ACCESS_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """Update nurse profile information"""
    nurse = await _get_nurse_profile(db, user_id=user.id)

    # Update fields
    update_data = updates.model_dump(exclude_unset=True)
    if "clinic_id" in update_data:
        clinic_id = update_data.pop("clinic_id")
        if clinic_id:
            clinic = await _get_active_clinic(db, clinic_id)
            nurse.clinic_id = clinic.id
            nurse.hospital = clinic.name
            if not update_data.get("department"):
                nurse.department = clinic.department
        else:
            nurse.clinic_id = None
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
    clinic_id: Optional[str] = Query(default=None),
    ward: Optional[str] = Query(default=None),
    user: User = Depends(require_role(*NURSE_ACCESS_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """Get all active ward patients and newly registered patients visible to nurses."""
    nurse = await _get_nurse_profile(db, user_id=user.id)
    clinic, station_wards = await _resolve_station_scope(
        db,
        nurse=nurse,
        clinic_id=clinic_id,
        ward=ward,
    )

    if user.role == UserRole.NURSE and not (clinic or nurse.hospital):
        raise HTTPException(status_code=400, detail="Nurse has not selected a clinic yet")
    if user.role == UserRole.NURSE_SUPERINTENDENT and not (clinic_id or ward):
        raise HTTPException(status_code=400, detail="Station context is required")

    admissions: list[Admission] = []
    if station_wards or not clinic:
        admissions_query = (
            select(Admission)
            .options(selectinload(Admission.patient).selectinload(Patient.insurance_policies))
            .where(Admission.status == "Active")
            .order_by(Admission.admission_date.desc())
        )
        if station_wards:
            admissions_query = admissions_query.where(Admission.ward.in_(station_wards))

        result = await db.execute(admissions_query)
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
        appointment_query = select(func.count(Appointment.id)).where(Appointment.patient_id == patient.id)
        clinic_appointment_query = select(func.count(ClinicAppointment.id)).where(ClinicAppointment.patient_id == patient.id)
        admission_query = select(func.count(Admission.id)).where(Admission.patient_id == patient.id)

        if clinic:
            clinic_appointment_query = clinic_appointment_query.where(ClinicAppointment.clinic_id == clinic.id)
            if station_wards:
                admission_query = admission_query.where(Admission.ward.in_(station_wards))

        appointment_result = await db.execute(appointment_query)
        clinic_appointment_result = await db.execute(clinic_appointment_query)
        admission_result = await db.execute(admission_query)

        has_appointment = ((appointment_result.scalar() or 0) > 0) or ((clinic_appointment_result.scalar() or 0) > 0)
        has_admission = (admission_result.scalar() or 0) > 0
        if clinic and not has_appointment and not has_admission:
            continue

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
            "hospital": clinic.name if clinic else nurse.hospital,
            "ward": ", ".join(station_wards) if station_wards else nurse.ward,
            "shift": nurse.shift,
            "clinic_id": clinic.id if clinic else nurse.clinic_id,
            "department": clinic.department if clinic else nurse.department,
        },
        "patients": patients_data,
        "newly_registered": newly_registered,
    }


@router.get("/notifications")
async def get_nurse_notifications(
    user: User = Depends(require_role(*NURSE_ACCESS_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """Get notifications for the current nurse"""
    nurse = await _get_nurse_profile(db, user_id=user.id)

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
    user: User = Depends(require_role(*NURSE_ACCESS_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read"""
    nurse = await _get_nurse_profile(db, user_id=user.id)

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
    user: User = Depends(require_role(*NURSE_ACCESS_ROLES)),
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
    user: User = Depends(require_role(*NURSE_ACCESS_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """Mark an order as completed"""
    nurse = await _get_nurse_profile(db, user_id=user.id)

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
    user: User = Depends(require_role(*NURSE_ACCESS_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new SBAR note for a patient"""
    nurse = await _get_nurse_profile(db, user_id=user.id)

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
