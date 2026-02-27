"""Standalone reports routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.report import Report

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Report).where(Report.id == report_id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "id": report.id,
        "patient_id": report.patient_id,
        "date": report.date.isoformat() if report.date else None,
        "title": report.title,
        "type": report.type,
        "department": report.department,
        "ordered_by": report.ordered_by,
        "status": report.status.value if report.status else None,
        "result_summary": report.result_summary,
        "notes": report.notes,
        "file_url": report.file_url,
    }
