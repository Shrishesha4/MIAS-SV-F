from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.student import (
    Student, StudentPatientAssignment, StudentAttendance,
    DisciplinaryAction, ClinicSession,
)
from app.models.case_record import CaseRecord
from app.models.patient import Patient
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
        .options(selectinload(StudentPatientAssignment.patient))
        .where(StudentPatientAssignment.student_id == student_id)
    )
    assignments = result.scalars().all()

    return [
        {
            "id": a.patient.id if a.patient else a.patient_id,
            "patient_id": a.patient.patient_id if a.patient else "",
            "name": a.patient.name if a.patient else "",
            "status": a.status,
            "assigned_date": a.assigned_date.isoformat() if a.assigned_date else None,
        }
        for a in assignments
    ]


@router.get("/{student_id}/case-records")
async def get_student_case_records(
    student_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CaseRecord)
        .where(CaseRecord.student_id == student_id)
        .order_by(CaseRecord.date.desc())
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
            "treatment": r.treatment,
            "notes": r.notes,
            "grade": r.grade,
            "provider": r.provider,
            "status": r.status,
            "approved_by": r.approved_by,
            "approved_at": r.approved_at,
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
        .where(ClinicSession.student_id == student_id)
        .order_by(ClinicSession.date.desc())
    )
    sessions = result.scalars().all()
    return [
        {
            "id": s.id,
            "clinic_name": s.clinic_name,
            "department": s.department,
            "date": s.date.isoformat() if s.date else None,
            "status": s.status,
        }
        for s in sessions
    ]


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
