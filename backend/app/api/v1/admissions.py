"""Admissions endpoints are part of patients.py.
This module provides standalone admission queries."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.admission import Admission

router = APIRouter(prefix="/admissions", tags=["Admissions"])


@router.get("/{admission_id}")
async def get_admission(
    admission_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Admission).where(Admission.id == admission_id)
    )
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Admission not found")

    return {
        "id": a.id,
        "patient_id": a.patient_id,
        "admission_date": a.admission_date.isoformat() if a.admission_date else None,
        "discharge_date": a.discharge_date.isoformat() if a.discharge_date else None,
        "department": a.department,
        "ward": a.ward,
        "bed_number": a.bed_number,
        "attending_doctor": a.attending_doctor,
        "diagnosis": a.diagnosis,
        "status": a.status,
        "notes": a.notes,
    }
