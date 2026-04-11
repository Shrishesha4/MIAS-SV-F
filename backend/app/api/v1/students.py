from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from datetime import datetime, date
import uuid

from app.database import AsyncSessionLocal, get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.student import (
    Student, StudentPatientAssignment, StudentAttendance,
    DisciplinaryAction, ClinicSession, Clinic, ClinicAppointment,
)
from app.models.case_record import CaseRecord, Approval, ApprovalType, ApprovalStatus
from app.models.patient import Patient, Allergy, MedicalAlert
from app.models.faculty import Faculty, FacultyNotification
from app.models.admission import Admission
from app.models.department import Department
from app.models.form_definition import FormDefinition
from app.models.prescription import Prescription, PrescriptionMedication, PrescriptionStatus
from app.models.notification import PatientNotification
from app.models.student import StudentNotification
from app.services.ai_provider import AIProviderError, generate_case_record_draft

router = APIRouter(prefix="/students", tags=["Students"])


async def _complete_case_record_generation(
    *,
    record_id: str,
    patient_id: str,
    faculty_id: str | None,
    student_id: str,
    student_name: str,
    form_name: str | None,
    form_description: str | None,
    form_values: dict | None,
):
    async with AsyncSessionLocal() as db:
        record = (
            await db.execute(
                select(CaseRecord).where(CaseRecord.id == record_id)
            )
        ).scalar_one_or_none()
        if not record:
            return

        patient = (
            await db.execute(
                select(Patient)
                .options(
                    selectinload(Patient.allergies),
                    selectinload(Patient.medical_alerts),
                )
                .where(Patient.id == patient_id)
            )
        ).scalar_one_or_none()
        if not patient:
            return

        try:
            draft = await generate_case_record_draft(
                db=db,
                patient=patient,
                department=record.department,
                procedure=record.procedure_name or record.type,
                form_name=form_name,
                form_description=form_description,
                form_values=form_values or {},
            )
        except AIProviderError:
            return

        record.findings = draft["findings"]
        record.diagnosis = draft["diagnosis"]
        record.treatment = draft["treatment"]
        record.last_modified_by = "AI Summary Generator"
        record.last_modified_at = datetime.utcnow()

        # Approval and notification are now created immediately in submit_case_record_for_approval
        # (not deferred to background task) to ensure faculty sees pending approvals even if AI fails
        await db.commit()


@router.get("/me")
async def get_current_student(
    user: User = Depends(require_role(UserRole.STUDENT)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Student)
        .options(
            selectinload(Student.attendance),
            selectinload(Student.disciplinary_actions),
            selectinload(Student.emergency_contact),
        )
        .where(Student.user_id == user.id)
    )
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    attendance_data = None
    if student.attendance:
        attendance_data = {
            "overall": student.attendance.overall,
            "clinical": student.attendance.clinical,
            "lecture": student.attendance.lecture,
            "lab": student.attendance.lab,
        }

    emergency_contact_data = None
    if student.emergency_contact:
        emergency_contact_data = {
            "name": student.emergency_contact.name,
            "relationship": student.emergency_contact.relationship_,
            "phone": student.emergency_contact.phone,
            "email": student.emergency_contact.email,
            "address": student.emergency_contact.address,
        }

    return {
        "id": student.id,
        "student_id": student.student_id,
        "name": student.name,
        "year": student.year,
        "semester": student.semester,
        "program": student.program,
        "degree": student.degree,
        "photo": student.photo,
        "gpa": student.gpa,
        "academic_standing": student.academic_standing,
        "academic_advisor": student.academic_advisor,
        "attendance": attendance_data,
        "disciplinary_actions": [
            {
                "id": da.id,
                "type": da.type,
                "description": da.description,
                "date": da.date,
                "status": da.status,
                "details": da.details,
                "resolution": da.resolution,
            }
            for da in student.disciplinary_actions
        ],
        "emergency_contact": emergency_contact_data,
    }


@router.get("/emergency-contacts")
async def get_emergency_contacts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all doctors as emergency contacts for students"""
    result = await db.execute(
        select(Faculty).order_by(Faculty.name)
    )
    faculty = result.scalars().all()
    
    return [
        {
            "id": f.id,
            "name": f.name,
            "department": f.department,
            "specialty": f.specialty,
            "phone": f.phone,
            "email": f.email,
            "photo": f.photo,
            "availability": f.availability,
            "availability_status": f.availability_status,
        }
        for f in faculty
    ]


@router.get("/procedures")
async def get_procedures(db: AsyncSession = Depends(get_db)):
    """Get available procedures grouped by department from active form definitions."""
    result = await db.execute(
        select(FormDefinition.department, FormDefinition.procedure_name)
        .where(
            FormDefinition.form_type == "CASE_RECORD",
            FormDefinition.is_active == True,
            FormDefinition.department.is_not(None),
            FormDefinition.procedure_name.is_not(None),
        )
        .order_by(
            FormDefinition.department.asc(),
            FormDefinition.sort_order.asc(),
            FormDefinition.procedure_name.asc(),
        )
    )

    procedures: dict[str, list[str]] = {}
    for department, procedure_name in result.all():
        if not department or not procedure_name:
            continue
        department_procedures = procedures.setdefault(department, [])
        if procedure_name not in department_procedures:
            department_procedures.append(procedure_name)

    return procedures


@router.get("/departments")
async def get_departments(db: AsyncSession = Depends(get_db)):
    """Get list of active departments configured by admin."""
    result = await db.execute(
        select(Department.name)
        .where(Department.is_active == True)
        .order_by(Department.name.asc())
    )
    return [name for name in result.scalars().all() if name]


@router.get("/faculty-approvers")
async def get_faculty_approvers(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get faculty members who can approve case records"""
    result = await db.execute(select(Faculty))
    faculty = result.scalars().all()
    
    return [
        {
            "id": f.id,
            "name": f.name,
            "department": f.department,
        }
        for f in faculty
    ]


@router.get("/clinics")
async def get_all_clinics(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all available clinics"""
    result = await db.execute(
        select(Clinic)
        .options(selectinload(Clinic.faculty))
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


@router.get("/clinic/{clinic_id}/patients")
async def get_clinic_patients_static(
    clinic_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get patients with appointments at a clinic for today"""
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


@router.get("/{student_id}")
async def get_student(
    student_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Student)
        .options(
            selectinload(Student.attendance),
            selectinload(Student.disciplinary_actions),
        )
        .where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return {
        "id": student.id,
        "student_id": student.student_id,
        "name": student.name,
        "year": student.year,
        "semester": student.semester,
        "program": student.program,
        "gpa": student.gpa,
        "academic_standing": student.academic_standing,
        "academic_advisor": student.academic_advisor,
    }


@router.get("/{student_id}/patients")
async def get_assigned_patients(
    student_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(StudentPatientAssignment)
        .options(
            selectinload(StudentPatientAssignment.patient)
            .selectinload(Patient.allergies)
        )
        .where(StudentPatientAssignment.student_id == student_id)
    )
    assignments = result.scalars().all()

    patients = []
    for a in assignments:
        if not a.patient:
            continue
        
        # Calculate age from date_of_birth
        age = None
        if a.patient.date_of_birth:
            today = date.today()
            dob = a.patient.date_of_birth
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        
        # Get primary diagnosis from medical records or case records
        primary_diagnosis = None
        diag_result = await db.execute(
            select(CaseRecord)
            .where(CaseRecord.patient_id == a.patient.id)
            .order_by(CaseRecord.date.desc())
            .limit(1)
        )
        latest_record = diag_result.scalar_one_or_none()
        if latest_record and latest_record.diagnosis:
            primary_diagnosis = latest_record.diagnosis
        
        patients.append({
            "id": a.patient.id,
            "patient_id": a.patient.patient_id,
            "name": a.patient.name,
            "age": age,
            "gender": a.patient.gender.value if a.patient.gender else None,
            "blood_group": a.patient.blood_group,
            "photo": a.patient.photo,
            "primary_diagnosis": primary_diagnosis,
            "status": a.status,
            "assigned_date": a.assigned_date.isoformat() if a.assigned_date else None,
        })
    
    return patients


@router.get("/{student_id}/case-records")
async def get_student_case_records(
    student_id: str,
    patient_id: str = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(CaseRecord).where(CaseRecord.student_id == student_id)
    if patient_id:
        query = query.where(CaseRecord.patient_id == patient_id)
    result = await db.execute(
        query.order_by(CaseRecord.date.desc())
    )
    records = result.scalars().all()

    return [
        {
            "id": r.id,
            "patient_id": r.patient_id,
            "student_id": r.student_id,
            "date": r.date.isoformat() if r.date else None,
            "time": r.time,
            "type": r.type,
            "description": r.description,
            "department": r.department,
            "findings": r.findings,
            "diagnosis": r.diagnosis,
            "icd_code": r.icd_code,
            "icd_description": r.icd_description,
            "treatment": r.treatment,
            "notes": r.notes,
            "grade": r.grade,
            "provider": r.provider,
            "status": r.status,
            "approved_by": r.approved_by,
            "approved_at": r.approved_at,
            "created_by_name": r.created_by_name,
            "created_by_role": r.created_by_role,
            "last_modified_by": r.last_modified_by,
            "last_modified_at": r.last_modified_at.isoformat() if r.last_modified_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


@router.post("/{student_id}/case-records")
async def create_case_record(
    student_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid
    from datetime import datetime

    record = CaseRecord(
        id=str(uuid.uuid4()),
        patient_id=body.get("patient_id"),
        student_id=student_id,
        date=datetime.utcnow(),
        time=body.get("time"),
        type=body.get("type", "Examination"),
        description=body.get("description", ""),
        department=body.get("department"),
        findings=body.get("findings"),
        diagnosis=body.get("diagnosis"),
        icd_code=body.get("icd_code"),
        icd_description=body.get("icd_description"),
        treatment=body.get("treatment"),
        notes=body.get("notes"),
        provider=body.get("provider"),
        status="Pending",
    )

    db.add(record)
    await db.commit()
    await db.refresh(record)
    return {"id": record.id, "status": "created"}


@router.get("/{student_id}/progress")
async def get_academic_progress(
    student_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Student)
        .options(selectinload(Student.attendance))
        .where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    attendance_data = {}
    if student.attendance:
        attendance_data = {
            "overall": student.attendance.overall,
            "clinical": student.attendance.clinical,
            "lecture": student.attendance.lecture,
            "lab": student.attendance.lab,
        }

    return {
        "gpa": student.gpa,
        "academic_standing": student.academic_standing,
        "attendance": attendance_data,
    }


@router.get("/{student_id}/clinic-sessions")
async def get_clinic_sessions(
    student_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ClinicSession)
        .options(selectinload(ClinicSession.clinic).selectinload(Clinic.faculty))
        .where(ClinicSession.student_id == student_id)
        .order_by(ClinicSession.date.desc())
    )
    sessions = result.scalars().all()
    return [
        {
            "id": s.id,
            "clinic_id": s.clinic_id,
            "clinic_name": s.clinic_name,
            "department": s.department,
            "date": s.date.strftime("%B %d, %Y") if s.date else None,
            "time_start": s.time_start,
            "time_end": s.time_end,
            "status": s.status,
            "is_selected": bool(s.is_selected),
            "doctor_name": s.clinic.faculty.name if s.clinic and s.clinic.faculty else None,
            "location": s.clinic.location if s.clinic else None,
        }
        for s in sessions
    ]


@router.get("/{student_id}/clinics")
async def get_available_clinics(
    student_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all available clinics for the student to choose from"""
    result = await db.execute(
        select(Clinic)
        .options(selectinload(Clinic.faculty))
    )
    clinics = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "department": c.department,
            "location": c.location,
            "doctor_name": c.faculty.name if c.faculty else None,
        }
        for c in clinics
    ]


@router.get("/{student_id}/clinic/{clinic_id}/patients")
async def get_clinic_patients(
    student_id: str,
    clinic_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get patients with appointments at a clinic for today"""
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

    patient_ids = [a.patient.id for a in appointments if a.patient]
    assigned_patient_ids: set[str] = set()
    if patient_ids:
        assignment_result = await db.execute(
            select(StudentPatientAssignment.patient_id).where(
                and_(
                    StudentPatientAssignment.student_id == student_id,
                    StudentPatientAssignment.patient_id.in_(patient_ids),
                    StudentPatientAssignment.status == "Active",
                )
            )
        )
        assigned_patient_ids = {patient_id for (patient_id,) in assignment_result.all()}
    
    return [
        {
            "id": a.id,
            "patient_id": a.patient.patient_id if a.patient else None,
            "patient_db_id": a.patient.id if a.patient else None,
            "patient_name": a.patient.name if a.patient else None,
            "appointment_time": a.appointment_time,
            "provider_name": a.provider_name,
            "status": a.status,
            "is_assigned": bool(a.patient and a.patient.id in assigned_patient_ids),
        }
        for a in appointments
    ]


@router.post("/{student_id}/clinic-sessions/{session_id}/select")
async def select_clinic_session(
    student_id: str,
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Select a clinic session as the current active clinic"""
    # Deselect all current sessions
    result = await db.execute(
        select(ClinicSession).where(ClinicSession.student_id == student_id)
    )
    sessions = result.scalars().all()
    for s in sessions:
        s.is_selected = 0
    
    # Select the chosen session
    result = await db.execute(
        select(ClinicSession).where(ClinicSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session:
        session.is_selected = 1
        await db.commit()
        return {"status": "selected", "session_id": session_id}
    
    raise HTTPException(status_code=404, detail="Session not found")


@router.post("/{student_id}/clinic-sessions/{session_id}/check-in")
async def check_in_to_clinic_session(
    student_id: str,
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record student check-in time for a clinic session (attendance tracking)."""
    result = await db.execute(
        select(ClinicSession).where(
            and_(
                ClinicSession.id == session_id,
                ClinicSession.student_id == student_id
            )
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Clinic session not found")
    
    if session.checked_in_at:
        raise HTTPException(status_code=400, detail="Already checked in to this session")
    
    now = datetime.utcnow()
    session.checked_in_at = now
    session.status = "Active"
    await db.commit()
    
    return {
        "status": "checked_in",
        "session_id": session_id,
        "checked_in_at": now.isoformat(),
        "clinic_name": session.clinic_name,
    }


@router.post("/{student_id}/clinic-sessions/{session_id}/check-out")
async def check_out_from_clinic_session(
    student_id: str,
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record student check-out time for a clinic session (attendance tracking)."""
    result = await db.execute(
        select(ClinicSession).where(
            and_(
                ClinicSession.id == session_id,
                ClinicSession.student_id == student_id
            )
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Clinic session not found")
    
    if not session.checked_in_at:
        raise HTTPException(status_code=400, detail="Must check in before checking out")
    
    if session.checked_out_at:
        raise HTTPException(status_code=400, detail="Already checked out from this session")
    
    now = datetime.utcnow()
    session.checked_out_at = now
    session.status = "Completed"
    
    # Calculate duration in minutes
    duration_minutes = int((now - session.checked_in_at).total_seconds() / 60)
    
    await db.commit()
    
    return {
        "status": "checked_out",
        "session_id": session_id,
        "checked_in_at": session.checked_in_at.isoformat(),
        "checked_out_at": now.isoformat(),
        "duration_minutes": duration_minutes,
        "clinic_name": session.clinic_name,
    }


@router.get("/{student_id}/attendance-calendar")
async def get_attendance_calendar(
    student_id: str,
    month: int = Query(default=None, ge=1, le=12),
    year: int = Query(default=None, ge=2020, le=2100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get student's clinic attendance for a specific month for calendar display."""
    # Default to current month if not specified
    if not month or not year:
        now = datetime.utcnow()
        month = month or now.month
        year = year or now.year
    
    # Calculate date range for the month
    from calendar import monthrange
    first_day = datetime(year, month, 1)
    last_day = datetime(year, month, monthrange(year, month)[1], 23, 59, 59)
    
    result = await db.execute(
        select(ClinicSession)
        .where(
            and_(
                ClinicSession.student_id == student_id,
                ClinicSession.date >= first_day,
                ClinicSession.date <= last_day
            )
        )
        .order_by(ClinicSession.date)
    )
    sessions = result.scalars().all()
    
    calendar_entries = []
    for s in sessions:
        duration_minutes = None
        if s.checked_in_at and s.checked_out_at:
            duration_minutes = int((s.checked_out_at - s.checked_in_at).total_seconds() / 60)
        
        calendar_entries.append({
            "id": s.id,
            "date": s.date.strftime("%Y-%m-%d"),
            "clinic_name": s.clinic_name,
            "department": s.department,
            "time_start": s.time_start,
            "time_end": s.time_end,
            "status": s.status,
            "checked_in_at": s.checked_in_at.isoformat() if s.checked_in_at else None,
            "checked_out_at": s.checked_out_at.isoformat() if s.checked_out_at else None,
            "duration_minutes": duration_minutes,
        })
    
    return {
        "month": month,
        "year": year,
        "sessions": calendar_entries,
    }


@router.get("/{student_id}/notifications")
async def get_student_notifications(
    student_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(StudentNotification)
        .where(StudentNotification.student_id == student_id)
        .order_by(StudentNotification.created_at.desc())
    )
    notifications = result.scalars().all()
    return [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "is_read": bool(n.is_read),
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifications
    ]


@router.put("/{student_id}/notifications/read")
async def mark_student_notifications_read(
    student_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all unread notifications as read for a student."""
    result = await db.execute(
        select(StudentNotification)
        .where(StudentNotification.student_id == student_id)
        .where(StudentNotification.is_read == 0)
    )
    notifications = result.scalars().all()
    count = 0
    for n in notifications:
        n.is_read = 1
        count += 1
    await db.commit()
    return {"message": f"Marked {count} notifications as read"}


@router.get("/{student_id}/previous-patients")
async def get_previous_patients(
    student_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get previously assigned patients (no longer active) for the student."""
    result = await db.execute(
        select(StudentPatientAssignment)
        .options(
            selectinload(StudentPatientAssignment.patient)
        )
        .where(
            StudentPatientAssignment.student_id == student_id,
            StudentPatientAssignment.status != "Active",
        )
    )
    assignments = result.scalars().all()

    patients = []
    for a in assignments:
        if not a.patient:
            continue
        age = None
        if a.patient.date_of_birth:
            today = date.today()
            dob = a.patient.date_of_birth
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        patients.append({
            "id": a.patient.id,
            "patient_id": a.patient.patient_id,
            "name": a.patient.name,
            "age": age,
            "gender": a.patient.gender.value if a.patient.gender else None,
            "blood_group": a.patient.blood_group,
            "photo": a.patient.photo,
            "status": a.status,
            "assigned_date": a.assigned_date.isoformat() if a.assigned_date else None,
        })
    return patients


@router.post("/{student_id}/case-records/submit")
async def submit_case_record_for_approval(
    student_id: str,
    body: dict,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a case record for faculty approval"""
    # Look up the student name for created_by
    stu_result = await db.execute(select(Student).where(Student.id == student_id))
    stu = stu_result.scalar_one_or_none()
    student_name = stu.name if stu else "Student"
    
    # Create the case record
    record = CaseRecord(
        id=str(uuid.uuid4()),
        patient_id=body.get("patient_id"),
        student_id=student_id,
        date=datetime.utcnow(),
        time=body.get("time"),
        type=body.get("procedure", "Examination"),
        procedure_name=body.get("procedure"),
        procedure_description=body.get("procedure_description"),
        description=body.get("description", ""),
        department=body.get("department"),
        findings=body.get("findings"),
        diagnosis=body.get("diagnosis"),
        icd_code=body.get("icd_code"),
        icd_description=body.get("icd_description"),
        treatment=body.get("treatment"),
        notes=body.get("notes"),
        provider=body.get("provider"),
        status="Pending",
        created_by_name=student_name,
        created_by_role="STUDENT",
        last_modified_by=student_name,
        last_modified_at=datetime.utcnow(),
    )
    db.add(record)
    await db.flush()

    # Create approval record immediately (not deferred to background task)
    # This ensures faculty can see pending approvals even if AI generation fails
    faculty_id = body.get("faculty_id")
    patient_id = body.get("patient_id")
    
    if faculty_id:
        # Validate faculty exists
        faculty_result = await db.execute(select(Faculty).where(Faculty.id == faculty_id))
        faculty = faculty_result.scalar_one_or_none()
        if not faculty:
            raise HTTPException(status_code=400, detail="Invalid faculty_id")
        
        # Get patient name for notification
        patient_result = await db.execute(select(Patient).where(Patient.id == patient_id))
        patient = patient_result.scalar_one_or_none()
        patient_name = patient.name if patient else "Patient"
        
        # Create approval record
        approval = Approval(
            id=str(uuid.uuid4()),
            approval_type=ApprovalType.CASE_RECORD,
            case_record_id=record.id,
            faculty_id=faculty_id,
            patient_id=patient_id,
            student_id=student_id,
            status=ApprovalStatus.PENDING,
        )
        db.add(approval)
        
        # Create notification for faculty
        notification = FacultyNotification(
            id=str(uuid.uuid4()),
            faculty_id=faculty_id,
            type="APPROVAL_REQUEST",
            title="New Case Record for Review",
            message=f"Case record for {patient_name} submitted by {student_name} requires your approval",
            is_read=False,
        )
        db.add(notification)

    await db.commit()
    background_tasks.add_task(
        _complete_case_record_generation,
        record_id=record.id,
        patient_id=body.get("patient_id"),
        faculty_id=faculty_id,
        student_id=student_id,
        student_name=student_name,
        form_name=body.get("form_name"),
        form_description=body.get("form_description"),
        form_values=body.get("form_values") or {},
    )
    return {"id": record.id, "status": "submitted", "summary_status": "PENDING"}


@router.post("/{student_id}/admission-requests")
async def submit_admission_request(
    student_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit an admission request for faculty approval.
    
    Student creates an admission record (status=Pending Approval)
    and an Approval record linked to it.
    """
    import uuid

    patient_id = body.get("patient_id")
    faculty_id = body.get("faculty_id")
    if not patient_id or not faculty_id:
        raise HTTPException(status_code=400, detail="patient_id and faculty_id are required")

    # Validate patient exists
    patient_result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Validate faculty exists
    faculty_result = await db.execute(select(Faculty).where(Faculty.id == faculty_id))
    faculty = faculty_result.scalar_one_or_none()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")

    # Create admission record with Pending Approval status
    admission = Admission(
        id=str(uuid.uuid4()),
        patient_id=patient_id,
        admission_date=datetime.utcnow(),
        department=body.get("department", faculty.department or "General"),
        ward=body.get("ward", ""),
        bed_number=body.get("bed_number", ""),
        attending_doctor=faculty.name,
        reason=body.get("reason", ""),
        diagnosis=body.get("diagnosis", ""),
        status="Pending Approval",
        notes=body.get("notes", ""),
        referring_doctor=body.get("referring_doctor", ""),
    )
    db.add(admission)
    await db.flush()

    # Create approval request
    approval = Approval(
        id=str(uuid.uuid4()),
        approval_type=ApprovalType.ADMISSION,
        admission_id=admission.id,
        faculty_id=faculty_id,
        patient_id=patient_id,
        student_id=student_id,
        status=ApprovalStatus.PENDING,
    )
    db.add(approval)

    # Create notification for faculty
    from app.models.faculty import FacultyNotification
    notification = FacultyNotification(
        id=str(uuid.uuid4()),
        faculty_id=faculty_id,
        type="APPROVAL_REQUEST",
        title="New Admission Request",
        message=f"Admission request for {patient.name} pending your approval",
        is_read=False,
    )
    db.add(notification)

    await db.commit()
    return {"id": admission.id, "approval_id": approval.id, "status": "submitted"}


@router.get("/{student_id}/admission-requests")
async def get_student_admission_requests(
    student_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all admission requests submitted by this student."""
    result = await db.execute(
        select(Approval)
        .options(
            selectinload(Approval.patient),
            selectinload(Approval.admission),
        )
        .where(Approval.student_id == student_id)
        .where(Approval.approval_type == ApprovalType.ADMISSION)
        .order_by(Approval.created_at.desc())
    )
    approvals = result.scalars().all()

    return [
        {
            "id": a.id,
            "status": a.status.value if a.status else "PENDING",
            "score": a.score,
            "comments": a.comments,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "processed_at": a.processed_at.isoformat() if a.processed_at else None,
            "patient": {
                "id": a.patient.id,
                "patient_id": a.patient.patient_id,
                "name": a.patient.name,
            } if a.patient else None,
            "admission": {
                "id": a.admission.id,
                "department": a.admission.department,
                "ward": a.admission.ward,
                "reason": a.admission.reason,
                "diagnosis": a.admission.diagnosis,
                "status": a.admission.status,
            } if a.admission else None,
        }
        for a in approvals
    ]


@router.post("/{student_id}/prescriptions/submit")
async def submit_prescription(
    student_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a prescription for faculty approval.
    
    Student creates a prescription (status=ACTIVE) with medications
    and an Approval record linked to it for faculty review.
    """
    import uuid

    patient_id = body.get("patient_id")
    faculty_id = body.get("faculty_id")
    if not patient_id or not faculty_id:
        raise HTTPException(status_code=400, detail="patient_id and faculty_id are required")

    # Validate patient exists
    patient_result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Validate faculty exists
    faculty_result = await db.execute(select(Faculty).where(Faculty.id == faculty_id))
    faculty = faculty_result.scalar_one_or_none()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")

    # Get student info
    student_result = await db.execute(select(Student).where(Student.id == student_id))
    student = student_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Create prescription
    rx_id = f"RX-{datetime.utcnow().strftime('%Y')}-{str(uuid.uuid4())[:4].upper()}"
    prescription = Prescription(
        id=str(uuid.uuid4()),
        prescription_id=rx_id,
        patient_id=patient_id,
        date=datetime.utcnow(),
        doctor=student.name,  # Submitted by student, awaiting faculty approval
        department=body.get("department", faculty.department or "General"),
        status=PrescriptionStatus.ACTIVE,
        notes=body.get("notes", ""),
        hospital_name="SMC Hospital",
    )
    db.add(prescription)
    await db.flush()

    # Add medications
    medications_data = body.get("medications", [])
    for med in medications_data:
        pm = PrescriptionMedication(
            id=str(uuid.uuid4()),
            prescription_id=prescription.id,
            name=med.get("name", ""),
            dosage=med.get("dosage", ""),
            frequency=med.get("frequency", ""),
            duration=med.get("duration", ""),
            instructions=med.get("instructions", ""),
            start_date=med.get("start_date", ""),
            end_date=med.get("end_date", ""),
        )
        db.add(pm)

    # Create approval request
    approval = Approval(
        id=str(uuid.uuid4()),
        approval_type=ApprovalType.PRESCRIPTION,
        prescription_id=prescription.id,
        faculty_id=faculty_id,
        patient_id=patient_id,
        student_id=student_id,
        status=ApprovalStatus.PENDING,
    )
    db.add(approval)

    # Create notification for faculty
    from app.models.faculty import FacultyNotification
    notification = FacultyNotification(
        id=str(uuid.uuid4()),
        faculty_id=faculty_id,
        type="APPROVAL_REQUEST",
        title="New Prescription for Review",
        message=f"Prescription for {patient.name} submitted by {student.name} pending your approval",
        is_read=False,
    )
    db.add(notification)

    await db.commit()
    return {"id": prescription.id, "prescription_id": rx_id, "approval_id": approval.id, "status": "submitted"}
