from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import datetime, date
from typing import Optional
import uuid
import os

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.patient import Patient, Allergy, MedicalAlert
from app.models.faculty import Faculty, FacultyNotification, FacultySchedule
from app.models.case_record import Approval, ApprovalType, ApprovalStatus, CaseRecord
from app.models.admission import Admission
from app.models.prescription import Prescription
from app.models.student import Student

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "uploads")

router = APIRouter(prefix="/faculty", tags=["Faculty"])

CASE_RECORD_SCORE_TO_GRADE = {
    0: "F",
    1: "1",
    2: "2",
    3: "3",
    4: "4",
    5: "5",
    6: "6",
    7: "7",
    8: "8",
    9: "9",
    10: "10",
}


def resolve_case_record_grade(grade: Optional[str], score: Optional[int]) -> Optional[str]:
    if grade:
        return grade.strip().upper()
    if score is None:
        return None
    return CASE_RECORD_SCORE_TO_GRADE.get(score)


@router.get("/me")
async def get_current_faculty(
    user: User = Depends(require_role(UserRole.FACULTY)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Faculty).where(Faculty.user_id == user.id)
    )
    faculty = result.scalar_one_or_none()

    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")

    return {
        "id": faculty.id,
        "faculty_id": faculty.faculty_id,
        "name": faculty.name,
        "department": faculty.department,
        "specialty": faculty.specialty,
        "phone": faculty.phone,
        "email": faculty.email,
        "photo": faculty.photo,
        "signature_image": faculty.signature_image,
        "availability": faculty.availability,
        "availability_status": faculty.availability_status,
    }


@router.put("/me/availability-status")
async def update_availability_status(
    body: dict,
    user: User = Depends(require_role(UserRole.FACULTY)),
    db: AsyncSession = Depends(get_db),
):
    """Update the faculty member's availability status (Available/Busy/Unavailable)."""
    result = await db.execute(
        select(Faculty).where(Faculty.user_id == user.id)
    )
    faculty = result.scalar_one_or_none()

    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")

    new_status = body.get("availability_status", "Available")
    if new_status not in ("Available", "Busy", "Unavailable"):
        raise HTTPException(status_code=400, detail="Invalid status. Must be Available, Busy, or Unavailable")

    faculty.availability_status = new_status
    await db.commit()

    return {
        "availability_status": faculty.availability_status,
        "message": f"Status updated to {new_status}",
    }


@router.get("/{faculty_id}")
async def get_faculty(
    faculty_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Faculty).where(Faculty.id == faculty_id)
    )
    faculty = result.scalar_one_or_none()

    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")

    return {
        "id": faculty.id,
        "faculty_id": faculty.faculty_id,
        "name": faculty.name,
        "department": faculty.department,
        "specialty": faculty.specialty,
        "phone": faculty.phone,
        "email": faculty.email,
        "photo": faculty.photo,
        "signature_image": faculty.signature_image,
        "availability": faculty.availability,
        "availability_status": faculty.availability_status,
    }


@router.post("/me/upload-photo")
async def upload_faculty_photo(
    file: UploadFile = File(...),
    user: User = Depends(require_role(UserRole.FACULTY)),
    db: AsyncSession = Depends(get_db),
):
    """Upload faculty profile photo."""
    result = await db.execute(select(Faculty).where(Faculty.user_id == user.id))
    faculty = result.scalar_one_or_none()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")

    ext = os.path.splitext(file.filename or "photo.png")[1] or ".png"
    filename = f"{faculty.id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(UPLOADS_DIR, "photos", filename)
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    faculty.photo = f"/uploads/photos/{filename}"
    await db.commit()
    return {"photo": faculty.photo, "message": "Photo uploaded successfully"}


@router.post("/me/upload-signature")
async def upload_faculty_signature(
    file: UploadFile = File(...),
    user: User = Depends(require_role(UserRole.FACULTY)),
    db: AsyncSession = Depends(get_db),
):
    """Upload faculty signature image."""
    result = await db.execute(select(Faculty).where(Faculty.user_id == user.id))
    faculty = result.scalar_one_or_none()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")

    ext = os.path.splitext(file.filename or "signature.png")[1] or ".png"
    filename = f"sig_{faculty.id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(UPLOADS_DIR, "signatures", filename)
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    faculty.signature_image = f"/uploads/signatures/{filename}"
    await db.commit()
    return {"signature_image": faculty.signature_image, "message": "Signature uploaded successfully"}


@router.get("/{faculty_id}/approval-stats")
async def get_approval_stats(
    faculty_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get counts of pending approvals by type for faculty dashboard."""
    # Count case record approvals
    case_records = (await db.execute(
        select(func.count(Approval.id))
        .where(Approval.faculty_id == faculty_id)
        .where(Approval.approval_type == ApprovalType.CASE_RECORD)
        .where(Approval.status == ApprovalStatus.PENDING)
    )).scalar() or 0

    # Count discharge summary approvals
    discharge_summaries = (await db.execute(
        select(func.count(Approval.id))
        .where(Approval.faculty_id == faculty_id)
        .where(Approval.approval_type == ApprovalType.DISCHARGE_SUMMARY)
        .where(Approval.status == ApprovalStatus.PENDING)
    )).scalar() or 0

    # Count admission approvals
    admissions = (await db.execute(
        select(func.count(Approval.id))
        .where(Approval.faculty_id == faculty_id)
        .where(Approval.approval_type == ApprovalType.ADMISSION)
        .where(Approval.status == ApprovalStatus.PENDING)
    )).scalar() or 0

    # Count prescription approvals
    prescriptions = (await db.execute(
        select(func.count(Approval.id))
        .where(Approval.faculty_id == faculty_id)
        .where(Approval.approval_type == ApprovalType.PRESCRIPTION)
        .where(Approval.status == ApprovalStatus.PENDING)
    )).scalar() or 0

    return {
        "case_records": case_records,
        "discharge_summaries": discharge_summaries,
        "admissions": admissions,
        "prescriptions": prescriptions,
        "total": case_records + discharge_summaries + admissions + prescriptions,
    }


@router.get("/{faculty_id}/approvals")
async def get_pending_approvals(
    faculty_id: str,
    type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get pending approvals for a faculty member, optionally filtered by type."""
    query = (
        select(Approval)
        .options(
            selectinload(Approval.case_record),
            selectinload(Approval.patient).selectinload(Patient.allergies),
            selectinload(Approval.patient).selectinload(Patient.medical_alerts),
            selectinload(Approval.admission),
            selectinload(Approval.prescription).selectinload(Prescription.medications),
            selectinload(Approval.student),
        )
        .where(Approval.faculty_id == faculty_id)
    )
    
    # Filter by type if specified
    if type:
        type_map = {
            "case-records": ApprovalType.CASE_RECORD,
            "discharge": ApprovalType.DISCHARGE_SUMMARY,
            "admissions": ApprovalType.ADMISSION,
            "prescriptions": ApprovalType.PRESCRIPTION,
        }
        if type in type_map:
            query = query.where(Approval.approval_type == type_map[type])
    
    # Filter by status if specified
    if status == "PENDING":
        query = query.where(Approval.status == ApprovalStatus.PENDING)
    elif status == "APPROVED":
        query = query.where(Approval.status == ApprovalStatus.APPROVED)
    elif status == "REJECTED":
        query = query.where(Approval.status == ApprovalStatus.REJECTED)
    
    query = query.order_by(Approval.created_at.desc())
    result = await db.execute(query)
    approvals = result.scalars().all()

    return [
        {
            "id": a.id,
            "type": a.approval_type.value if a.approval_type else "CASE_RECORD",
            "case_record_id": a.case_record_id,
            "admission_id": a.admission_id,
            "prescription_id": a.prescription_id,
            "faculty_id": a.faculty_id,
            "status": a.status.value if a.status else "PENDING",
            "score": a.score,
            "comments": a.comments,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "processed_at": a.processed_at.isoformat() if a.processed_at else None,
            "patient": {
                "id": a.patient.id,
                "patient_id": a.patient.patient_id,
                "name": a.patient.name,
                "age": (date.today() - a.patient.date_of_birth).days // 365 if a.patient.date_of_birth else None,
                "gender": a.patient.gender.value if a.patient.gender else None,
                "blood_group": a.patient.blood_group,
                "photo": a.patient.photo if hasattr(a.patient, 'photo') else None,
                "allergies": [
                    {"allergen": allergy.allergen, "severity": allergy.severity}
                    for allergy in (a.patient.allergies or [])
                ],
                "primary_diagnosis": a.patient.primary_diagnosis,
                "medical_alerts": [
                    {
                        "id": alert.id,
                        "type": alert.type,
                        "severity": alert.severity,
                        "title": alert.title,
                        "description": alert.description,
                        "is_active": alert.is_active,
                    }
                    for alert in (a.patient.medical_alerts or []) if alert.is_active
                ],
            } if a.patient else None,
            "submitted_by": {
                "id": a.student.id,
                "student_id": a.student.student_id,
                "name": a.student.name,
            } if a.student else None,
            "case_record": {
                "id": a.case_record.id,
                "type": a.case_record.type,
                "description": a.case_record.description,
                "procedure_name": a.case_record.procedure_name,
                "procedure_description": a.case_record.procedure_description,
                "doctor_name": a.case_record.doctor_name or a.case_record.provider,
                "student_id": a.case_record.student_id,
                "patient_id": a.case_record.patient_id,
                "grade": a.case_record.grade,
                "date": a.case_record.date.isoformat() if a.case_record.date else None,
                "time": a.case_record.time,
            } if a.case_record else None,
            "admission": {
                "id": a.admission.id,
                "department": a.admission.department,
                "ward": a.admission.ward,
                "bed_number": a.admission.bed_number,
                "diagnosis": a.admission.diagnosis,
                "reason": a.admission.reason,
                "attending_doctor": a.admission.attending_doctor,
                "referring_doctor": a.admission.referring_doctor,
                "status": a.admission.status,
                "notes": a.admission.notes,
                "discharge_summary": a.admission.discharge_summary,
                "admission_date": a.admission.admission_date.isoformat() if a.admission.admission_date else None,
            } if a.admission else None,
            "prescription": {
                "id": a.prescription.id,
                "prescription_id": a.prescription.prescription_id,
                "doctor": a.prescription.doctor,
                "department": a.prescription.department,
                "date": a.prescription.date.isoformat() if a.prescription.date else None,
                "status": a.prescription.status.value if a.prescription.status else None,
                "notes": a.prescription.notes,
                "medications": [
                    {
                        "id": med.id,
                        "name": med.name,
                        "dosage": med.dosage,
                        "frequency": med.frequency,
                        "duration": med.duration,
                        "instructions": med.instructions,
                        "start_date": med.start_date,
                        "end_date": med.end_date,
                    }
                    for med in (a.prescription.medications or [])
                ],
            } if a.prescription else None,
        }
        for a in approvals
    ]


@router.get("/{faculty_id}/approval-history")
async def get_approval_history(
    faculty_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get processed (approved/rejected) approvals for history view."""
    result = await db.execute(
        select(Approval)
        .options(
            selectinload(Approval.case_record),
            selectinload(Approval.patient),
            selectinload(Approval.admission),
            selectinload(Approval.prescription).selectinload(Prescription.medications),
        )
        .where(Approval.faculty_id == faculty_id)
        .where(Approval.status != ApprovalStatus.PENDING)
        .order_by(Approval.processed_at.desc())
        .limit(50)
    )
    approvals = result.scalars().all()

    return [
        {
            "id": a.id,
            "type": a.approval_type.value if a.approval_type else "CASE_RECORD",
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
            "case_record": {
                "id": a.case_record.id,
                "type": a.case_record.type,
                "procedure_name": a.case_record.procedure_name,
                "description": a.case_record.description,
                "grade": a.case_record.grade,
            } if a.case_record else None,
            "admission": {
                "id": a.admission.id,
                "department": a.admission.department,
                "reason": a.admission.reason,
                "diagnosis": a.admission.diagnosis,
                "status": a.admission.status,
                "discharge_summary": a.admission.discharge_summary,
            } if a.admission else None,
            "prescription": {
                "id": a.prescription.id,
                "prescription_id": a.prescription.prescription_id,
                "doctor": a.prescription.doctor,
                "department": a.prescription.department,
                "date": a.prescription.date.isoformat() if a.prescription.date else None,
                "status": a.prescription.status.value if a.prescription.status else None,
                "notes": a.prescription.notes,
                "medications": [
                    {
                        "id": med.id,
                        "name": med.name,
                        "dosage": med.dosage,
                        "frequency": med.frequency,
                        "duration": med.duration,
                        "instructions": med.instructions,
                        "start_date": med.start_date,
                        "end_date": med.end_date,
                    }
                    for med in (a.prescription.medications or [])
                ],
            } if a.prescription else None,
        }
        for a in approvals
    ]


@router.put("/{faculty_id}/approvals/{approval_id}")
async def process_approval(
    faculty_id: str,
    approval_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Approval)
        .options(
            selectinload(Approval.case_record),
            selectinload(Approval.admission),
        )
        .where(Approval.id == approval_id)
        .where(Approval.faculty_id == faculty_id)
    )
    approval = result.scalar_one_or_none()

    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    new_status = body.get("status", "APPROVED")
    score = body.get("score")
    grade = body.get("grade")
    if approval.approval_type == ApprovalType.CASE_RECORD and score is not None:
        if not isinstance(score, int) or score < 0 or score > 10:
            raise HTTPException(status_code=400, detail="Case record score must be between F and 10")
    approval.status = ApprovalStatus.APPROVED if new_status == "APPROVED" else ApprovalStatus.REJECTED
    approval.comments = body.get("comments")
    approval.processed_at = datetime.utcnow()
    approval.score = score if approval.approval_type == ApprovalType.CASE_RECORD else None

    # Get faculty name for records
    faculty_name = (
        await db.execute(select(Faculty.name).where(Faculty.id == faculty_id))
    ).scalar_one_or_none() or faculty_id

    # Update the case record status
    if approval.case_record:
        approval.case_record.status = "Approved" if new_status == "APPROVED" else "Rejected"
        approval.case_record.approved_by = faculty_name
        approval.case_record.approved_at = datetime.utcnow().isoformat()
        approval.case_record.grade = (
            resolve_case_record_grade(grade, score)
            if new_status == "APPROVED"
            else None
        )

    # Update the admission status
    if approval.admission:
        if new_status == "APPROVED":
            approval.admission.status = "Active"
        else:
            approval.admission.status = "Rejected"

    await db.commit()
    return {"message": "Approval processed", "status": approval.status.value}


@router.get("/{faculty_id}/today-schedule")
async def get_today_schedule(
    faculty_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get today's schedule for a faculty member."""
    today = date.today()
    result = await db.execute(
        select(FacultySchedule)
        .where(FacultySchedule.faculty_id == faculty_id)
        .where(FacultySchedule.date == today)
        .order_by(FacultySchedule.time_start)
    )
    schedules = result.scalars().all()

    return [
        {
            "id": s.id,
            "time_start": s.time_start,
            "time_end": s.time_end,
            "title": s.title,
            "type": s.type,
            "location": s.location,
        }
        for s in schedules
    ]


@router.get("/{faculty_id}/schedule")
async def get_faculty_schedule(
    faculty_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Today's schedule from database
    today = date.today()
    result = await db.execute(
        select(FacultySchedule)
        .where(FacultySchedule.faculty_id == faculty_id)
        .where(FacultySchedule.date == today)
        .order_by(FacultySchedule.time_start)
    )
    schedules = result.scalars().all()
    
    if schedules:
        return {
            "faculty_id": faculty_id,
            "schedule": [
                {
                    "day": s.date.strftime("%A"),
                    "time": f"{s.time_start} - {s.time_end}",
                    "location": s.location or "TBD",
                    "title": s.title,
                }
                for s in schedules
            ],
        }

    return {
        "faculty_id": faculty_id,
        "schedule": [],
    }


@router.get("/{faculty_id}/notifications")
async def get_faculty_notifications(
    faculty_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FacultyNotification)
        .where(FacultyNotification.faculty_id == faculty_id)
        .order_by(FacultyNotification.created_at.desc())
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


@router.put("/{faculty_id}/notifications/read")
async def mark_faculty_notifications_read(
    faculty_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all unread notifications as read for a faculty member."""
    result = await db.execute(
        select(FacultyNotification)
        .where(FacultyNotification.faculty_id == faculty_id)
        .where(FacultyNotification.is_read == 0)
    )
    notifications = result.scalars().all()
    count = 0
    for n in notifications:
        n.is_read = 1
        count += 1
    await db.commit()
    return {"message": f"Marked {count} notifications as read"}


@router.post("/{faculty_id}/schedule")
async def create_schedule_item(
    faculty_id: str,
    body: dict,
    user: User = Depends(require_role(UserRole.FACULTY)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new schedule item for faculty."""
    schedule_date = body.get("date")
    if schedule_date:
        schedule_date = datetime.strptime(schedule_date, "%Y-%m-%d").date()
    else:
        schedule_date = date.today()

    item = FacultySchedule(
        id=str(uuid.uuid4()),
        faculty_id=faculty_id,
        date=schedule_date,
        time_start=body.get("time_start", "09:00"),
        time_end=body.get("time_end", "10:00"),
        title=body.get("title", ""),
        type=body.get("type", "Clinical"),
        location=body.get("location", ""),
        student_count=body.get("student_count", 0),
    )
    db.add(item)
    await db.commit()
    return {
        "id": item.id,
        "title": item.title,
        "date": item.date.isoformat(),
        "message": "Schedule item created",
    }


@router.put("/{faculty_id}/schedule/{item_id}")
async def update_schedule_item(
    faculty_id: str,
    item_id: str,
    body: dict,
    user: User = Depends(require_role(UserRole.FACULTY)),
    db: AsyncSession = Depends(get_db),
):
    """Update a schedule item."""
    result = await db.execute(
        select(FacultySchedule).where(
            FacultySchedule.id == item_id,
            FacultySchedule.faculty_id == faculty_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Schedule item not found")

    if "title" in body:
        item.title = body["title"]
    if "time_start" in body:
        item.time_start = body["time_start"]
    if "time_end" in body:
        item.time_end = body["time_end"]
    if "type" in body:
        item.type = body["type"]
    if "location" in body:
        item.location = body["location"]
    if "date" in body:
        item.date = datetime.strptime(body["date"], "%Y-%m-%d").date()

    await db.commit()
    return {"message": "Schedule item updated", "id": item.id}


@router.delete("/{faculty_id}/schedule/{item_id}")
async def delete_schedule_item(
    faculty_id: str,
    item_id: str,
    user: User = Depends(require_role(UserRole.FACULTY)),
    db: AsyncSession = Depends(get_db),
):
    """Delete a schedule item."""
    result = await db.execute(
        select(FacultySchedule).where(
            FacultySchedule.id == item_id,
            FacultySchedule.faculty_id == faculty_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Schedule item not found")

    await db.delete(item)
    await db.commit()
    return {"message": "Schedule item deleted"}


@router.get("/{faculty_id}/students")
async def get_students_list(
    faculty_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get list of students for patient assignment"""
    from app.models.student import Student, StudentPatientAssignment
    
    result = await db.execute(select(Student).order_by(Student.name))
    students = result.scalars().all()
    
    # Get assignment counts for each student
    student_counts = {}
    count_result = await db.execute(
        select(
            StudentPatientAssignment.student_id,
            func.count(StudentPatientAssignment.id)
        )
        .where(StudentPatientAssignment.status == "Active")
        .group_by(StudentPatientAssignment.student_id)
    )
    for student_id, count in count_result.all():
        student_counts[student_id] = count
    
    return [
        {
            "id": s.id,
            "student_id": s.student_id,
            "name": s.name,
            "year": s.year,
            "semester": s.semester,
            "department": s.program or "General",
            "photo": s.photo,
            "assigned_patient_count": student_counts.get(s.id, 0),
        }
        for s in students
    ]


@router.get("/{faculty_id}/patients-unassigned")
async def get_unassigned_patients(
    faculty_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get patients that are not assigned to any student"""
    from app.models.student import StudentPatientAssignment
    from app.models.patient import Patient
    from app.models.case_record import CaseRecord
    
    # Get all patient IDs that are already assigned
    assigned_result = await db.execute(
        select(StudentPatientAssignment.patient_id)
        .where(StudentPatientAssignment.status == "Active")
    )
    assigned_ids = [r[0] for r in assigned_result.all()]
    
    # Get patients not in assigned list
    query = select(Patient)
    if assigned_ids:
        query = query.where(~Patient.id.in_(assigned_ids))
    
    result = await db.execute(query.order_by(Patient.name))
    patients = result.scalars().all()
    
    # Get latest diagnosis for each patient
    patient_diagnoses = {}
    for p in patients:
        case_result = await db.execute(
            select(CaseRecord.diagnosis)
            .where(CaseRecord.patient_id == p.id)
            .where(CaseRecord.diagnosis.isnot(None))
            .order_by(CaseRecord.date.desc())
            .limit(1)
        )
        diagnosis = case_result.scalar_one_or_none()
        patient_diagnoses[p.id] = diagnosis
    
    return [
        {
            "id": p.id,
            "patient_id": p.patient_id,
            "name": p.name,
            "age": (date.today() - p.date_of_birth).days // 365 if p.date_of_birth else None,
            "gender": p.gender.value if p.gender else None,
            "blood_group": p.blood_group,
            "photo": p.photo,
            "primary_diagnosis": patient_diagnoses.get(p.id),
        }
        for p in patients
    ]


@router.post("/{faculty_id}/assign-patient")
async def assign_patient_to_student(
    faculty_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign a patient to a student"""
    from app.models.student import StudentPatientAssignment
    import uuid
    
    student_id = body.get("student_id")
    patient_id = body.get("patient_id")
    
    if not student_id or not patient_id:
        raise HTTPException(status_code=400, detail="student_id and patient_id are required")
    
    # Check if assignment already exists
    existing = await db.execute(
        select(StudentPatientAssignment)
        .where(StudentPatientAssignment.student_id == student_id)
        .where(StudentPatientAssignment.patient_id == patient_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Patient is already assigned to this student")
    
    assignment = StudentPatientAssignment(
        id=str(uuid.uuid4()),
        student_id=student_id,
        patient_id=patient_id,
        status="Active",
    )
    db.add(assignment)
    await db.commit()
    
    return {"message": "Patient assigned successfully", "id": assignment.id}


@router.delete("/{faculty_id}/assignments/{assignment_id}")
async def remove_patient_assignment(
    faculty_id: str,
    assignment_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a patient assignment from a student"""
    from app.models.student import StudentPatientAssignment
    
    result = await db.execute(
        select(StudentPatientAssignment).where(StudentPatientAssignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    await db.delete(assignment)
    await db.commit()
    
    return {"message": "Assignment removed"}

