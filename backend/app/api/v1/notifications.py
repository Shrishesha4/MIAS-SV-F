"""Notifications endpoints — provides general notification counts."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.notification import PatientNotification
from app.models.student import StudentNotification, Student
from app.models.faculty import Faculty, FacultyNotification
from app.models.patient import Patient

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/unread-count")
async def get_unread_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get unread notification count for the current user based on their role."""
    count = 0

    if user.role == UserRole.PATIENT:
        patient = (await db.execute(
            select(Patient.id).where(Patient.user_id == user.id)
        )).scalar_one_or_none()
        if patient:
            count = (await db.execute(
                select(func.count(PatientNotification.id))
                .where(PatientNotification.patient_id == patient)
                .where(PatientNotification.is_read == 0)
            )).scalar() or 0

    elif user.role == UserRole.STUDENT:
        student = (await db.execute(
            select(Student.id).where(Student.user_id == user.id)
        )).scalar_one_or_none()
        if student:
            count = (await db.execute(
                select(func.count(StudentNotification.id))
                .where(StudentNotification.student_id == student)
                .where(StudentNotification.is_read == 0)
            )).scalar() or 0

    elif user.role == UserRole.FACULTY:
        faculty = (await db.execute(
            select(Faculty.id).where(Faculty.user_id == user.id)
        )).scalar_one_or_none()
        if faculty:
            count = (await db.execute(
                select(func.count(FacultyNotification.id))
                .where(FacultyNotification.faculty_id == faculty)
                .where(FacultyNotification.is_read == 0)
            )).scalar() or 0

    return {"count": count}
