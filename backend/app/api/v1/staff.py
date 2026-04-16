from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, date, timedelta, time as dt_time
from pydantic import BaseModel
import uuid

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.patient import Patient, Appointment
from app.models.admission import Admission
from app.models.student import Clinic, ClinicAppointment, ClinicSession, Student, StudentPatientAssignment, StudentNotification
from app.models.nurse import Nurse
from app.api.v1.patient_serialization import serialize_patient_badge_context, serialize_patient_insurance

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
    scheduled_date: Optional[str] = None
    appointment_date: Optional[str] = None
    appointment_time: Optional[str] = None
    notes: Optional[str] = None


class AssignToStudentRequest(BaseModel):
    patient_id: str
    student_id: str
    clinic_id: Optional[str] = None


class AssignToWardRequest(BaseModel):
    patient_id: str
    ward: Optional[str] = None
    ward_type: Optional[str] = None
    room_number: Optional[str] = None
    bed_number: Optional[str] = None
    department: Optional[str] = None
    admission_date: Optional[str] = None
    chief_complaint: Optional[str] = None
    admitting_diagnosis: Optional[str] = None
    notes: Optional[str] = None


def _parse_iso_date(value: Optional[str]) -> datetime:
    if not value:
        return datetime.utcnow()
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        parsed = datetime.combine(date.fromisoformat(value), dt_time.min)
    if parsed.time() == dt_time.min:
        return datetime.combine(parsed.date(), dt_time(hour=9, minute=0))
    return parsed


def _parse_appointment_time(value: Optional[str], fallback: datetime) -> str:
    if not value:
        return fallback.strftime("%I:%M %p")
    normalized = value.strip()
    for fmt in ("%H:%M", "%I:%M %p"):
        try:
            return datetime.strptime(normalized, fmt).strftime("%I:%M %p")
        except ValueError:
            continue
    return normalized


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
        .options(selectinload(Patient.insurance_policies))
        .where(Patient.created_at >= recent_cutoff)
        .order_by(Patient.created_at.desc())
        .limit(limit)
    )
    patients = result.scalars().all()
    
    # Batch-fetch clinic names for all patients
    clinic_ids = list({p.clinic_id for p in patients if p.clinic_id})
    clinic_name_map: dict = {}
    if clinic_ids:
        clinic_result = await db.execute(
            select(Clinic.id, Clinic.name).where(Clinic.id.in_(clinic_ids))
        )
        clinic_name_map = {row.id: row.name for row in clinic_result.all()}
    
    pending_list = []
    for patient in patients:
        # Check if patient has any appointments
        appt_result = await db.execute(
            select(func.count(Appointment.id))
            .where(Appointment.patient_id == patient.id)
        )
        clinic_appt_result = await db.execute(
            select(func.count(ClinicAppointment.id))
            .where(ClinicAppointment.patient_id == patient.id)
        )
        has_appointment = (appt_result.scalar() or 0) > 0 or (clinic_appt_result.scalar() or 0) > 0

        assignment_result = await db.execute(
            select(StudentPatientAssignment)
            .options(selectinload(StudentPatientAssignment.student))
            .where(
                and_(
                    StudentPatientAssignment.patient_id == patient.id,
                    StudentPatientAssignment.status == "Active",
                )
            )
        )
        student_assignment = assignment_result.scalar_one_or_none()
        has_student_assignment = student_assignment is not None
        
        # Check if patient has any admissions
        adm_result = await db.execute(
            select(func.count(Admission.id))
            .where(Admission.patient_id == patient.id)
        )
        has_admission = adm_result.scalar() > 0
        
        # Calculate age
        age = None
        if patient.date_of_birth:
            today = date.today()
            dob = patient.date_of_birth
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        
        pending_list.append({
            "id": patient.id,
            "patient_id": patient.patient_id,
            "name": patient.name,
            "photo": patient.photo,
            "phone": patient.phone,
            "email": patient.email,
            "gender": patient.gender.value if patient.gender else None,
            "dob": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            "age": age,
            "blood_group": patient.blood_group,
            "registered_at": patient.created_at.isoformat(),
            "has_appointment": has_appointment,
            "has_student_assignment": has_student_assignment,
            "assigned_student_id": student_assignment.student_id if student_assignment else None,
            "assigned_student_name": student_assignment.student.name if student_assignment and student_assignment.student else None,
            "has_admission": has_admission,
            "clinic_id": patient.clinic_id,
            "clinic_name": clinic_name_map.get(patient.clinic_id) if patient.clinic_id else None,
            **serialize_patient_badge_context(patient),
            "insurance_policies": serialize_patient_insurance(patient),
        })
    
    return pending_list


@router.get("/clinics/{clinic_id}/active-students")
async def get_active_students_for_clinic(
    clinic_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List checked-in students currently present in a clinic TODAY."""
    if user.role not in [UserRole.RECEPTION, UserRole.NURSE, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Only sessions checked in today
    today_start = datetime.combine(date.today(), dt_time.min)
    today_end = datetime.combine(date.today(), dt_time.max)
    session_result = await db.execute(
        select(ClinicSession)
        .options(selectinload(ClinicSession.student))
        .where(
            and_(
                ClinicSession.clinic_id == clinic_id,
                ClinicSession.checked_in_at.is_not(None),
                ClinicSession.checked_in_at >= today_start,
                ClinicSession.checked_in_at <= today_end,
                ClinicSession.checked_out_at.is_(None),
            )
        )
        .order_by(ClinicSession.checked_in_at.asc())
    )
    sessions = session_result.scalars().all()

    active_students = []
    for session in sessions:
        if not session.student:
            continue
        assignment_count_result = await db.execute(
            select(func.count(StudentPatientAssignment.id)).where(
                and_(
                    StudentPatientAssignment.student_id == session.student_id,
                    StudentPatientAssignment.status == "Active",
                )
            )
        )
        active_students.append({
            "id": session.student.id,
            "student_id": session.student.student_id,
            "name": session.student.name,
            "year": session.student.year,
            "semester": session.student.semester,
            "checked_in_at": session.checked_in_at.isoformat() if session.checked_in_at else None,
            "session_id": session.id,
            "assigned_patient_count": assignment_count_result.scalar() or 0,
        })

    return active_students


@router.post("/assign-to-student")
async def assign_patient_to_student(
    data: AssignToStudentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign a patient directly to a checked-in student."""
    if user.role not in [UserRole.RECEPTION, UserRole.NURSE, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized")

    patient_result = await db.execute(
        select(Patient).where(Patient.id == data.patient_id)
    )
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    student_result = await db.execute(
        select(Student).where(Student.id == data.student_id)
    )
    student = student_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    existing_assignment_result = await db.execute(
        select(StudentPatientAssignment).where(
            and_(
                StudentPatientAssignment.patient_id == data.patient_id,
                StudentPatientAssignment.status == "Active",
            )
        )
    )
    if existing_assignment_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Patient is already assigned to a student")

    if data.clinic_id:
        active_session_result = await db.execute(
            select(ClinicSession).where(
                and_(
                    ClinicSession.student_id == data.student_id,
                    ClinicSession.clinic_id == data.clinic_id,
                    ClinicSession.checked_in_at.is_not(None),
                    ClinicSession.checked_out_at.is_(None),
                )
            )
        )
        if not active_session_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Student is not currently checked in to this clinic")
        patient.clinic_id = data.clinic_id

    assignment = StudentPatientAssignment(
        id=str(uuid.uuid4()),
        student_id=data.student_id,
        patient_id=data.patient_id,
        status="Active",
    )
    db.add(assignment)

    notification = StudentNotification(
        id=str(uuid.uuid4()),
        student_id=data.student_id,
        title="New Patient Assigned",
        message=f"Patient {patient.name} ({patient.patient_id}) has been assigned to you.",
        type="ASSIGNMENT",
        is_read=0,
    )
    db.add(notification)

    await db.commit()

    assignment_count_result = await db.execute(
        select(func.count(StudentPatientAssignment.id)).where(
            and_(
                StudentPatientAssignment.student_id == data.student_id,
                StudentPatientAssignment.status == "Active",
            )
        )
    )

    return {
        "message": f"Patient {patient.name} assigned to {student.name}",
        "assignment_id": assignment.id,
        "patient_id": patient.id,
        "patient_name": patient.name,
        "student_id": student.id,
        "student_name": student.name,
        "student_patient_count": assignment_count_result.scalar() or 0,
    }


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
        select(Clinic)
        .options(selectinload(Clinic.faculty))
        .where(Clinic.id == data.clinic_id)
    )
    clinic = clinic_result.scalar_one_or_none()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    scheduled_date = data.scheduled_date or data.appointment_date
    appt_datetime = _parse_iso_date(scheduled_date)
    appointment_time = _parse_appointment_time(data.appointment_time, appt_datetime)
    provider_name = clinic.faculty.name if clinic.faculty else clinic.name

    day_start = datetime.combine(appt_datetime.date(), dt_time.min)
    day_end = datetime.combine(appt_datetime.date(), dt_time.max)
    existing_clinic_appt_result = await db.execute(
        select(ClinicAppointment).where(
            and_(
                ClinicAppointment.patient_id == patient.id,
                ClinicAppointment.clinic_id == clinic.id,
                ClinicAppointment.appointment_date >= day_start,
                ClinicAppointment.appointment_date <= day_end,
                ClinicAppointment.status.in_(["Scheduled", "Checked In", "In Progress"]),
            )
        )
    )
    existing_clinic_appt = existing_clinic_appt_result.scalar_one_or_none()
    if existing_clinic_appt:
        raise HTTPException(status_code=400, detail="Patient already has a clinic assignment for this date")

    clinic_appointment = ClinicAppointment(
        id=str(uuid.uuid4()),
        clinic_id=clinic.id,
        patient_id=patient.id,
        appointment_date=appt_datetime,
        appointment_time=appointment_time,
        provider_name=provider_name,
        status="Scheduled",
    )
    patient.clinic_id = clinic.id

    appointment = Appointment(
        id=str(uuid.uuid4()),
        patient_id=patient.id,
        date=appt_datetime,
        time=appointment_time,
        doctor=provider_name,
        department=clinic.department,
        status="Scheduled",
        notes=data.notes or f"Assigned to clinic: {clinic.name}",
    )
    db.add(clinic_appointment)
    db.add(appointment)
    await db.commit()
    
    return {
        "message": f"Patient {patient.name} assigned to {clinic.name}",
        "appointment_id": appointment.id,
        "clinic_appointment_id": clinic_appointment.id,
        "patient_name": patient.name,
        "clinic_name": clinic.name,
        "appointment_date": appointment.date.isoformat(),
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

    nurse = None
    if user.role == UserRole.NURSE:
        nurse_result = await db.execute(
            select(Nurse).where(Nurse.user_id == user.id)
        )
        nurse = nurse_result.scalar_one_or_none()
        if not nurse:
            raise HTTPException(status_code=404, detail="Nurse profile not found")
    
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

    ward_name = data.ward or data.ward_type
    if not ward_name:
        raise HTTPException(status_code=400, detail="Ward is required")

    admission_dt = _parse_iso_date(data.admission_date)
    department = data.department or (nurse.department if nurse and nurse.department else None) or "General"
    diagnosis = data.admitting_diagnosis or data.chief_complaint
    attending_doctor = nurse.name if nurse else "Ward Staff"
    
    # Create admission
    admission = Admission(
        id=str(uuid.uuid4()),
        patient_id=patient.id,
        admission_date=admission_dt,
        status="Active",
        department=department,
        ward=ward_name,
        room_number=data.room_number,
        bed_number=data.bed_number,
        attending_doctor=attending_doctor,
        reason=data.chief_complaint,
        diagnosis=diagnosis,
        notes=data.notes,
    )
    db.add(admission)
    await db.commit()
    
    return {
        "message": f"Patient {patient.name} admitted to {ward_name}",
        "admission_id": admission.id,
        "patient_name": patient.name,
        "ward": ward_name,
        "admission_date": admission.admission_date.isoformat(),
    }


class AutoAssignRequest(BaseModel):
    patient_id: str
    clinic_id: str


@router.post("/auto-assign")
async def auto_assign_patient_to_student(
    data: AutoAssignRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Auto-assign a patient to a student in the same clinic.
    Picks the student with the lowest active patient assignment count.
    """
    if user.role not in [UserRole.RECEPTION, UserRole.NURSE, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Verify patient exists
    patient_result = await db.execute(
        select(Patient).where(Patient.id == data.patient_id)
    )
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Check if patient is already assigned to a student
    existing_assignment = await db.execute(
        select(StudentPatientAssignment).where(
            and_(
                StudentPatientAssignment.patient_id == data.patient_id,
                StudentPatientAssignment.status == "Active"
            )
        )
    )
    if existing_assignment.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Patient is already assigned to a student")
    
    # Get students who have active ClinicSessions for this clinic TODAY
    today_start = datetime.combine(date.today(), dt_time.min)
    today_end = datetime.combine(date.today(), dt_time.max)
    clinic_sessions_result = await db.execute(
        select(ClinicSession)
        .options(selectinload(ClinicSession.student))
        .where(
            and_(
                ClinicSession.clinic_id == data.clinic_id,
                ClinicSession.checked_in_at.is_not(None),
                ClinicSession.checked_in_at >= today_start,
                ClinicSession.checked_in_at <= today_end,
                ClinicSession.checked_out_at.is_(None),
            )
        )
    )
    clinic_sessions = clinic_sessions_result.scalars().all()
    
    if not clinic_sessions:
        raise HTTPException(
            status_code=400, 
            detail="No students are currently checked in to this clinic. Cannot auto-assign."
        )
    
    # Get unique students from clinic sessions
    students_in_clinic = {cs.student_id: cs.student for cs in clinic_sessions if cs.student}
    
    if not students_in_clinic:
        raise HTTPException(
            status_code=400, 
            detail="No students found in this clinic"
        )
    
    # Count active assignments for each student
    student_counts = []
    for student_id, student in students_in_clinic.items():
        count_result = await db.execute(
            select(func.count(StudentPatientAssignment.id)).where(
                and_(
                    StudentPatientAssignment.student_id == student_id,
                    StudentPatientAssignment.status == "Active"
                )
            )
        )
        count = count_result.scalar() or 0
        student_counts.append((student_id, student, count))
    
    # Sort by count (ascending) to find student with fewest patients
    student_counts.sort(key=lambda x: x[2])
    selected_student_id, selected_student, assignment_count = student_counts[0]
    patient.clinic_id = data.clinic_id
    
    # Create the assignment
    assignment = StudentPatientAssignment(
        id=str(uuid.uuid4()),
        student_id=selected_student_id,
        patient_id=data.patient_id,
        status="Active",
    )
    db.add(assignment)
    
    # Notify the student
    notification = StudentNotification(
        id=str(uuid.uuid4()),
        student_id=selected_student_id,
        title="New Patient Assigned",
        message=f"Patient {patient.name} ({patient.patient_id}) has been assigned to you.",
        type="ASSIGNMENT",
        is_read=0,
    )
    db.add(notification)
    
    await db.commit()
    
    return {
        "message": f"Patient {patient.name} assigned to {selected_student.name}",
        "assignment_id": assignment.id,
        "patient_id": patient.id,
        "patient_name": patient.name,
        "student_id": selected_student_id,
        "student_name": selected_student.name,
        "student_patient_count": assignment_count + 1,
    }


class ReassignRequest(BaseModel):
    patient_id: str
    student_id: str


@router.post("/reassign")
async def reassign_patient_to_student(
    data: ReassignRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate an existing student assignment and create a new one for a specific student."""
    if user.role not in [UserRole.RECEPTION, UserRole.NURSE, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Verify patient exists
    patient_result = await db.execute(select(Patient).where(Patient.id == data.patient_id))
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Verify target student exists
    student_result = await db.execute(select(Student).where(Student.id == data.student_id))
    student = student_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Deactivate any existing active assignment
    existing_result = await db.execute(
        select(StudentPatientAssignment).where(
            and_(
                StudentPatientAssignment.patient_id == data.patient_id,
                StudentPatientAssignment.status == "Active",
            )
        )
    )
    for old in existing_result.scalars().all():
        old.status = "Reassigned"

    # Create new assignment
    assignment = StudentPatientAssignment(
        id=str(uuid.uuid4()),
        student_id=data.student_id,
        patient_id=data.patient_id,
        status="Active",
    )
    db.add(assignment)

    # Notify new student
    notification = StudentNotification(
        id=str(uuid.uuid4()),
        student_id=data.student_id,
        title="Patient Reassigned",
        message=f"Patient {patient.name} ({patient.patient_id}) has been reassigned to you.",
        type="ASSIGNMENT",
        is_read=0,
    )
    db.add(notification)

    await db.commit()

    return {
        "message": f"Patient {patient.name} reassigned to {student.name}",
        "assignment_id": assignment.id,
        "patient_id": patient.id,
        "patient_name": patient.name,
        "student_id": data.student_id,
        "student_name": student.name,
    }
