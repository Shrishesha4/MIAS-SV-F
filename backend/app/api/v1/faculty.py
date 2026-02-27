from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.faculty import Faculty, FacultyNotification
from app.models.case_record import Approval

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
        "availability": faculty.availability,
    }


@router.get("/{faculty_id}/approvals")
async def get_pending_approvals(
    faculty_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Approval)
        .options(selectinload(Approval.case_record))
        .where(Approval.faculty_id == faculty_id)
        .order_by(Approval.created_at.desc())
    )
    approvals = result.scalars().all()

    return [
        {
            "id": a.id,
            "case_record_id": a.case_record_id,
            "faculty_id": a.faculty_id,
            "status": a.status,
            "comments": a.comments,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "processed_at": a.processed_at.isoformat() if a.processed_at else None,
            "case_record": {
                "id": a.case_record.id,
                "type": a.case_record.type,
                "description": a.case_record.description,
                "student_id": a.case_record.student_id,
                "patient_id": a.case_record.patient_id,
                "date": a.case_record.date.isoformat() if a.case_record.date else None,
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

    approval.status = body.get("status", "Approved")
    approval.comments = body.get("comments")
    approval.processed_at = datetime.utcnow()

    # Also update the case record
    if approval.case_record:
        approval.case_record.status = approval.status
        approval.case_record.approved_by = (
            await db.execute(select(Faculty.name).where(Faculty.id == faculty_id))
        ).scalar_one_or_none() or faculty_id
        approval.case_record.approved_at = datetime.utcnow().isoformat()

    await db.commit()
    return {"message": "Approval processed", "status": approval.status}


@router.get("/{faculty_id}/schedule")
async def get_faculty_schedule(
    faculty_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Simplified schedule - in production, this would be a separate model
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
