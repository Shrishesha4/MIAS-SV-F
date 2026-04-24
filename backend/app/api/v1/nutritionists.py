import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_role
from app.api.v1.patient_serialization import (
    serialize_patient_badge_context,
    serialize_patient_insurance,
)
from app.database import get_db
from app.models.nutritionist import (
    Nutritionist,
    NutritionistClinicSession,
    NutritionistNote,
)
from app.models.patient import Patient
from app.models.student import (
    ClinicAppointment,
    ClinicSession,
    StudentPatientAssignment,
)
from app.models.user import User, UserRole
from app.services.daily_checkins import ensure_daily_checkin

router = APIRouter(prefix="/nutritionists", tags=["Nutritionists"])


class NutritionistNoteRequest(BaseModel):
    content: str


class NutritionistNoteStatusRequest(BaseModel):
    is_completed: bool


def _serialize_session(session: NutritionistClinicSession | None) -> dict | None:
    if not session:
        return None
    return {
        "id": session.id,
        "clinic_id": session.clinic_id,
        "clinic_name": session.clinic_name,
        "department": session.department,
        "status": session.status,
        "date": session.date.isoformat() if session.date else None,
        "checked_in_at": session.checked_in_at.isoformat()
        if session.checked_in_at
        else None,
        "checked_out_at": session.checked_out_at.isoformat()
        if session.checked_out_at
        else None,
    }


def _serialize_profile(
    nutritionist: Nutritionist, active_session: NutritionistClinicSession | None
) -> dict:
    clinic = nutritionist.clinic
    return {
        "id": nutritionist.id,
        "nutritionist_id": nutritionist.nutritionist_id,
        "name": nutritionist.name,
        "phone": nutritionist.phone,
        "email": nutritionist.email,
        "photo": nutritionist.photo,
        "clinic": {
            "id": clinic.id,
            "name": clinic.name,
            "department": clinic.department,
            "location": clinic.location,
            "block": clinic.block,
            "clinic_type": clinic.clinic_type,
        }
        if clinic
        else None,
        "active_session": _serialize_session(active_session),
    }


async def _get_nutritionist_or_404(db: AsyncSession, *, user_id: str) -> Nutritionist:
    result = await db.execute(
        select(Nutritionist)
        .options(selectinload(Nutritionist.clinic))
        .where(Nutritionist.user_id == user_id)
    )
    nutritionist = result.scalar_one_or_none()
    if not nutritionist:
        raise HTTPException(status_code=404, detail="Nutritionist profile not found")
    return nutritionist


async def _get_active_session(
    db: AsyncSession,
    *,
    nutritionist_id: str,
) -> NutritionistClinicSession | None:
    result = await db.execute(
        select(NutritionistClinicSession)
        .where(
            and_(
                NutritionistClinicSession.nutritionist_id == nutritionist_id,
                NutritionistClinicSession.checked_out_at.is_(None),
            )
        )
        .order_by(NutritionistClinicSession.checked_in_at.desc())
    )
    return result.scalars().first()


async def _patient_belongs_to_clinic_today(
    db: AsyncSession,
    *,
    clinic_id: str,
    patient_id: str,
) -> bool:
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())

    appointment_result = await db.execute(
        select(ClinicAppointment.id)
        .where(
            and_(
                ClinicAppointment.clinic_id == clinic_id,
                ClinicAppointment.patient_id == patient_id,
                ClinicAppointment.appointment_date >= today_start,
                ClinicAppointment.appointment_date <= today_end,
            )
        )
        .limit(1)
    )
    if appointment_result.scalar_one_or_none():
        return True

    assignment_result = await db.execute(
        select(StudentPatientAssignment.id)
        .join(
            ClinicSession,
            and_(
                ClinicSession.student_id == StudentPatientAssignment.student_id,
                ClinicSession.clinic_id == clinic_id,
                ClinicSession.checked_in_at.is_not(None),
                ClinicSession.checked_out_at.is_(None),
            ),
        )
        .where(
            and_(
                StudentPatientAssignment.patient_id == patient_id,
                StudentPatientAssignment.status == "Active",
            )
        )
        .limit(1)
    )
    return assignment_result.scalar_one_or_none() is not None


@router.get("/me")
async def get_current_nutritionist(
    user: User = Depends(require_role(UserRole.NUTRITIONIST)),
    db: AsyncSession = Depends(get_db),
):
    nutritionist = await _get_nutritionist_or_404(db, user_id=user.id)
    active_session = await _get_active_session(db, nutritionist_id=nutritionist.id)
    return _serialize_profile(nutritionist, active_session)


@router.get("/me/patients")
async def get_nutritionist_clinic_patients(
    user: User = Depends(require_role(UserRole.NUTRITIONIST)),
    db: AsyncSession = Depends(get_db),
):
    nutritionist = await _get_nutritionist_or_404(db, user_id=user.id)
    clinic = nutritionist.clinic
    if not clinic:
        raise HTTPException(status_code=404, detail="Assigned clinic not found")

    active_session = await _get_active_session(db, nutritionist_id=nutritionist.id)
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())

    note_result = await db.execute(
        select(NutritionistNote).where(
            NutritionistNote.nutritionist_id == nutritionist.id,
            NutritionistNote.clinic_id == clinic.id,
            NutritionistNote.note_date == date.today(),
        )
    )
    note_by_patient = {note.patient_id: note for note in note_result.scalars().all()}

    appointment_result = await db.execute(
        select(ClinicAppointment)
        .options(
            selectinload(ClinicAppointment.patient).selectinload(
                Patient.insurance_policies
            )
        )
        .where(
            and_(
                ClinicAppointment.clinic_id == clinic.id,
                ClinicAppointment.appointment_date >= today_start,
                ClinicAppointment.appointment_date <= today_end,
            )
        )
        .order_by(ClinicAppointment.appointment_time)
    )
    appointments = appointment_result.scalars().all()

    clinic_patients = []
    included_patient_ids: set[str] = set()
    for appointment in appointments:
        patient = appointment.patient
        if patient:
            included_patient_ids.add(patient.id)
        note = note_by_patient.get(patient.id) if patient else None
        clinic_patients.append(
            {
                "id": appointment.id,
                "patient_id": patient.patient_id if patient else None,
                "patient_db_id": patient.id if patient else None,
                "patient_name": patient.name if patient else None,
                "photo": patient.photo if patient else None,
                "appointment_time": appointment.appointment_time,
                "provider_name": appointment.provider_name,
                "status": appointment.status,
                "source": "appointment",
                "assignment_id": None,
                "assigned_student_name": None,
                "nutrition_note_id": note.id if note else None,
                "nutrition_note": note.content if note else "",
                "nutrition_note_is_completed": note.is_completed if note else False,
                "nutrition_note_completed_at": note.completed_at.isoformat()
                if note and note.completed_at
                else None,
                "nutrition_note_updated_at": note.updated_at.isoformat()
                if note and note.updated_at
                else None,
                **serialize_patient_badge_context(patient),
                "insurance_policies": serialize_patient_insurance(patient),
            }
        )

    active_session_result = await db.execute(
        select(ClinicSession)
        .options(selectinload(ClinicSession.student))
        .where(
            and_(
                ClinicSession.clinic_id == clinic.id,
                ClinicSession.checked_in_at.is_not(None),
                ClinicSession.checked_out_at.is_(None),
            )
        )
    )
    active_sessions = active_session_result.scalars().all()
    active_students = {
        session.student_id: session.student
        for session in active_sessions
        if session.student
    }
    active_session_by_student = {
        session.student_id: session for session in active_sessions
    }

    if active_students:
        assignment_result = await db.execute(
            select(StudentPatientAssignment)
            .options(
                selectinload(StudentPatientAssignment.patient).selectinload(
                    Patient.insurance_policies
                )
            )
            .where(
                and_(
                    StudentPatientAssignment.student_id.in_(
                        list(active_students.keys())
                    ),
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
            note = note_by_patient.get(patient.id)
            clinic_patients.append(
                {
                    "id": assignment.id,
                    "patient_id": patient.patient_id,
                    "patient_db_id": patient.id,
                    "patient_name": patient.name,
                    "photo": patient.photo,
                    "appointment_time": session.checked_in_at.strftime("%I:%M %p")
                    if session and session.checked_in_at
                    else "Now",
                    "provider_name": active_students[assignment.student_id].name
                    if active_students.get(assignment.student_id)
                    else None,
                    "status": "Checked In",
                    "source": "assignment",
                    "assignment_id": assignment.id,
                    "assigned_student_name": active_students[assignment.student_id].name
                    if active_students.get(assignment.student_id)
                    else None,
                    "nutrition_note_id": note.id if note else None,
                    "nutrition_note": note.content if note else "",
                    "nutrition_note_is_completed": note.is_completed if note else False,
                    "nutrition_note_completed_at": note.completed_at.isoformat()
                    if note and note.completed_at
                    else None,
                    "nutrition_note_updated_at": note.updated_at.isoformat()
                    if note and note.updated_at
                    else None,
                    **serialize_patient_badge_context(patient),
                    "insurance_policies": serialize_patient_insurance(patient),
                }
            )
            included_patient_ids.add(patient.id)

    return {
        "clinic": {
            "id": clinic.id,
            "name": clinic.name,
            "department": clinic.department,
            "location": clinic.location,
            "block": clinic.block,
            "clinic_type": clinic.clinic_type,
        },
        "checked_in": active_session is not None,
        "active_session": _serialize_session(active_session),
        "patients": clinic_patients,
    }


@router.post("/me/check-in")
async def check_in_to_assigned_clinic(
    user: User = Depends(require_role(UserRole.NUTRITIONIST)),
    db: AsyncSession = Depends(get_db),
):
    nutritionist = await _get_nutritionist_or_404(db, user_id=user.id)
    clinic = nutritionist.clinic
    if not clinic or not clinic.is_active:
        raise HTTPException(status_code=404, detail="Assigned clinic not found")

    active_session = await _get_active_session(db, nutritionist_id=nutritionist.id)
    now = datetime.utcnow()

    if active_session and active_session.clinic_id == clinic.id:
        await ensure_daily_checkin(
            db,
            user_id=user.id,
            role=UserRole.NUTRITIONIST,
            checked_in_at=active_session.checked_in_at or now,
            clinic_id=clinic.id,
        )
        await db.commit()
        return {
            "status": "already_checked_in",
            "session_id": active_session.id,
            "checked_in_at": active_session.checked_in_at.isoformat()
            if active_session.checked_in_at
            else None,
            "clinic_id": clinic.id,
            "clinic_name": clinic.name,
        }

    if active_session:
        active_session.checked_out_at = now
        active_session.status = "Completed"

    session = NutritionistClinicSession(
        id=str(uuid.uuid4()),
        nutritionist_id=nutritionist.id,
        clinic_id=clinic.id,
        clinic_name=clinic.name,
        department=clinic.department,
        date=now,
        status="Active",
        checked_in_at=now,
    )
    db.add(session)
    await ensure_daily_checkin(
        db,
        user_id=user.id,
        role=UserRole.NUTRITIONIST,
        checked_in_at=now,
        clinic_id=clinic.id,
    )
    await db.commit()

    return {
        "status": "checked_in",
        "session_id": session.id,
        "checked_in_at": now.isoformat(),
        "clinic_id": clinic.id,
        "clinic_name": clinic.name,
    }


@router.post("/me/check-out/{session_id}")
async def check_out_from_assigned_clinic(
    session_id: str,
    user: User = Depends(require_role(UserRole.NUTRITIONIST)),
    db: AsyncSession = Depends(get_db),
):
    nutritionist = await _get_nutritionist_or_404(db, user_id=user.id)
    result = await db.execute(
        select(NutritionistClinicSession).where(
            and_(
                NutritionistClinicSession.id == session_id,
                NutritionistClinicSession.nutritionist_id == nutritionist.id,
            )
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Clinic session not found")
    if session.checked_out_at:
        raise HTTPException(
            status_code=400, detail="Already checked out from this clinic"
        )

    now = datetime.utcnow()
    session.checked_out_at = now
    session.status = "Completed"
    await db.commit()

    return {
        "status": "checked_out",
        "session_id": session.id,
        "checked_in_at": session.checked_in_at.isoformat()
        if session.checked_in_at
        else None,
        "checked_out_at": now.isoformat(),
        "clinic_name": session.clinic_name,
    }


@router.put("/me/patients/{patient_id}/note")
async def upsert_patient_note(
    patient_id: str,
    body: NutritionistNoteRequest,
    user: User = Depends(require_role(UserRole.NUTRITIONIST)),
    db: AsyncSession = Depends(get_db),
):
    nutritionist = await _get_nutritionist_or_404(db, user_id=user.id)
    clinic = nutritionist.clinic
    if not clinic:
        raise HTTPException(status_code=404, detail="Assigned clinic not found")

    active_session = await _get_active_session(db, nutritionist_id=nutritionist.id)
    if not active_session:
        raise HTTPException(
            status_code=400, detail="Check in to your clinic before saving notes"
        )

    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Note content is required")

    patient_result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    belongs_to_clinic = await _patient_belongs_to_clinic_today(
        db,
        clinic_id=clinic.id,
        patient_id=patient_id,
    )
    if not belongs_to_clinic:
        raise HTTPException(
            status_code=404, detail="Patient is not active in your clinic today"
        )

    today = date.today()
    note_result = await db.execute(
        select(NutritionistNote).where(
            NutritionistNote.nutritionist_id == nutritionist.id,
            NutritionistNote.patient_id == patient_id,
            NutritionistNote.note_date == today,
        )
    )
    note = note_result.scalar_one_or_none()

    if note:
        note.content = content
        note.clinic_id = clinic.id
    else:
        note = NutritionistNote(
            id=str(uuid.uuid4()),
            nutritionist_id=nutritionist.id,
            patient_id=patient_id,
            clinic_id=clinic.id,
            note_date=today,
            content=content,
            is_completed=False,
        )
        db.add(note)

    await db.commit()
    await db.refresh(note)

    return {
        "id": note.id,
        "patient_id": patient.id,
        "patient_name": patient.name,
        "clinic_id": clinic.id,
        "clinic_name": clinic.name,
        "note_date": note.note_date.isoformat(),
        "content": note.content,
        "is_completed": note.is_completed,
        "completed_at": note.completed_at.isoformat() if note.completed_at else None,
        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
    }


@router.put("/me/patients/{patient_id}/status")
async def update_patient_note_status(
    patient_id: str,
    body: NutritionistNoteStatusRequest,
    user: User = Depends(require_role(UserRole.NUTRITIONIST)),
    db: AsyncSession = Depends(get_db),
):
    nutritionist = await _get_nutritionist_or_404(db, user_id=user.id)
    clinic = nutritionist.clinic
    if not clinic:
        raise HTTPException(status_code=404, detail="Assigned clinic not found")

    active_session = await _get_active_session(db, nutritionist_id=nutritionist.id)
    if not active_session:
        raise HTTPException(
            status_code=400, detail="Check in to your clinic before saving notes"
        )

    patient_result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    belongs_to_clinic = await _patient_belongs_to_clinic_today(
        db,
        clinic_id=clinic.id,
        patient_id=patient_id,
    )
    if not belongs_to_clinic:
        raise HTTPException(
            status_code=404, detail="Patient is not active in your clinic today"
        )

    today = date.today()
    note_result = await db.execute(
        select(NutritionistNote).where(
            NutritionistNote.nutritionist_id == nutritionist.id,
            NutritionistNote.patient_id == patient_id,
            NutritionistNote.note_date == today,
        )
    )
    note = note_result.scalar_one_or_none()
    if not note:
        raise HTTPException(
            status_code=404,
            detail="Save a nutrition note before updating completion status",
        )

    if body.is_completed and not note.content.strip():
        raise HTTPException(status_code=400, detail="Note content is required")

    note.is_completed = body.is_completed
    note.completed_at = datetime.utcnow() if body.is_completed else None
    note.clinic_id = clinic.id

    await db.commit()
    await db.refresh(note)

    return {
        "id": note.id,
        "patient_id": patient.id,
        "patient_name": patient.name,
        "clinic_id": clinic.id,
        "clinic_name": clinic.name,
        "note_date": note.note_date.isoformat(),
        "content": note.content,
        "is_completed": note.is_completed,
        "completed_at": note.completed_at.isoformat() if note.completed_at else None,
        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
    }
