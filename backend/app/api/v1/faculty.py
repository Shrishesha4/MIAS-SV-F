from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import datetime, date
from typing import Optional

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.patient import Patient, Allergy
from app.models.faculty import Faculty, FacultyNotification, FacultySchedule
from app.models.case_record import Approval, ApprovalType, ApprovalStatus, CaseRecord
from app.models.admission import Admission
from app.models.prescription import Prescription

router = APIRouter(prefix="/faculty", tags=["Faculty"])


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
        "availability": faculty.availability,
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
        "availability": faculty.availability,
    }


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
            selectinload(Approval.admission),
            selectinload(Approval.prescription),
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
                "primary_diagnosis": None,  # Could be fetched from medical records
            } if a.patient else None,
            "case_record": {
                "id": a.case_record.id,
                "type": a.case_record.type,
                "description": a.case_record.description,
                "procedure_name": a.case_record.procedure_name,
                "procedure_description": a.case_record.procedure_description,
                "doctor_name": a.case_record.doctor_name or a.case_record.provider,
                "student_id": a.case_record.student_id,
                "patient_id": a.case_record.patient_id,
                "date": a.case_record.date.isoformat() if a.case_record.date else None,
                "time": a.case_record.time,
            } if a.case_record else None,
            "admission": {
                "id": a.admission.id,
                "department": a.admission.department,
                "ward": a.admission.ward,
                "diagnosis": a.admission.diagnosis,
                "admission_date": a.admission.admission_date.isoformat() if a.admission.admission_date else None,
            } if a.admission else None,
            "prescription": {
                "id": a.prescription.id,
                "prescription_id": a.prescription.prescription_id,
                "doctor": a.prescription.doctor,
                "department": a.prescription.department,
                "date": a.prescription.date.isoformat() if a.prescription.date else None,
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
            selectinload(Approval.prescription),
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
            } if a.case_record else None,
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
        .options(selectinload(Approval.case_record))
        .where(Approval.id == approval_id)
        .where(Approval.faculty_id == faculty_id)
    )
    approval = result.scalar_one_or_none()

    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    new_status = body.get("status", "APPROVED")
    approval.status = ApprovalStatus.APPROVED if new_status == "APPROVED" else ApprovalStatus.REJECTED
    approval.score = body.get("score")
    approval.comments = body.get("comments")
    approval.processed_at = datetime.utcnow()

    # Also update the case record
    if approval.case_record:
        approval.case_record.status = "Approved" if new_status == "APPROVED" else "Rejected"
        approval.case_record.approved_by = (
            await db.execute(select(Faculty.name).where(Faculty.id == faculty_id))
        ).scalar_one_or_none() or faculty_id
        approval.case_record.approved_at = datetime.utcnow().isoformat()

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
    
    # Fallback to static schedule for demo
    return {
        "faculty_id": faculty_id,
        "schedule": [
            {"day": "Monday", "time": "9:00 AM - 1:00 PM", "location": "OPD Block A"},
            {"day": "Wednesday", "time": "10:00 AM - 2:00 PM", "location": "OPD Block B"},
            {"day": "Friday", "time": "9:00 AM - 12:00 PM", "location": "Ward 3"},
        ],
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
