from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from datetime import datetime, date

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.student import (
    Student, StudentPatientAssignment, StudentAttendance,
    DisciplinaryAction, ClinicSession, Clinic, ClinicAppointment,
)
from app.models.case_record import CaseRecord, Approval, ApprovalType, ApprovalStatus
from app.models.patient import Patient, Allergy
from app.models.faculty import Faculty
from app.models.notification import PatientNotification
from app.models.student import StudentNotification

router = APIRouter(prefix="/students", tags=["Students"])


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
async def get_procedures():
    """Get available procedures organized by department"""
    return {
        "Internal Medicine": [
            "Blood Pressure Monitoring",
            "Physical Examination",
            "ECG Recording",
            "Medication Review",
        ],
        "Pediatrics": [
            "Growth Assessment",
            "Developmental Screening",
            "Vaccination",
            "Well-child Checkup",
        ],
        "Surgery": [
            "Wound Care",
            "Suture Removal",
            "Pre-operative Assessment",
            "Post-operative Follow-up",
        ],
        "OB/GYN": [
            "Prenatal Checkup",
            "Pap Smear",
            "Breast Examination",
            "Fetal Monitoring",
        ],
        "Psychiatry": [
            "Mental Status Examination",
            "Counseling Session",
            "Medication Management",
            "Risk Assessment",
        ],
        "Emergency Medicine": [
            "Triage Assessment",
            "Trauma Care",
            "Resuscitation",
            "Emergency Stabilization",
        ],
    }


@router.get("/departments")
async def get_departments():
    """Get list of departments"""
    return [
        "Internal Medicine",
        "Pediatrics",
        "Surgery",
        "OB/GYN",
        "Psychiatry",
        "Emergency Medicine",
    ]


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
    
    return [
        {
            "id": a.id,
            "patient_id": a.patient.patient_id if a.patient else None,
            "patient_name": a.patient.name if a.patient else None,
            "appointment_time": a.appointment_time,
            "provider_name": a.provider_name,
            "status": a.status,
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


@router.post("/{student_id}/case-records/submit")
async def submit_case_record_for_approval(
    student_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a case record for faculty approval"""
    import uuid

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
    
    # Create an approval request
    faculty_id = body.get("faculty_id")
    if faculty_id:
        approval = Approval(
            id=str(uuid.uuid4()),
            approval_type=ApprovalType.CASE_RECORD,
            case_record_id=record.id,
            faculty_id=faculty_id,
            patient_id=body.get("patient_id"),
            student_id=student_id,
            status=ApprovalStatus.PENDING,
        )
        db.add(approval)
    
    await db.commit()
    return {"id": record.id, "status": "submitted"}
