"""Admissions endpoints are part of patients.py.
This module provides standalone admission queries."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.admission import Admission
from app.models.patient import Patient

router = APIRouter(prefix="/admissions", tags=["Admissions"])


@router.get("/")
async def list_all_admissions(
    status: Optional[str] = Query(None, description="Filter by status: Active, Discharged, Transferred"),
    department: Optional[str] = Query(None),
    user: User = Depends(require_role(UserRole.FACULTY, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """List all admissions across all patients (faculty/admin only)."""
    query = select(Admission).order_by(Admission.admission_date.desc())
    if status:
        query = query.where(Admission.status == status)
    if department:
        query = query.where(Admission.department == department)
    result = await db.execute(query)
    admissions = result.scalars().all()

    # Get patient names for display
    patient_ids = list(set(a.patient_id for a in admissions))
    patient_names = {}
    if patient_ids:
        pat_result = await db.execute(
            select(Patient.id, Patient.name, Patient.patient_id)
            .where(Patient.id.in_(patient_ids))
        )
        for pid, pname, ppid in pat_result.all():
            patient_names[pid] = {"name": pname, "patient_id": ppid}

    return [
        {
            "id": a.id,
            "patient_id": a.patient_id,
            "patient_name": patient_names.get(a.patient_id, {}).get("name", "Unknown"),
            "patient_display_id": patient_names.get(a.patient_id, {}).get("patient_id", ""),
            "admission_date": a.admission_date.isoformat() if a.admission_date else None,
            "discharge_date": a.discharge_date.isoformat() if a.discharge_date else None,
            "department": a.department,
            "ward": a.ward,
            "bed_number": a.bed_number,
            "attending_doctor": a.attending_doctor,
            "reason": a.reason,
            "diagnosis": a.diagnosis,
            "status": a.status,
            "notes": a.notes,
            "program_duration_days": a.program_duration_days,
            "related_admission_id": a.related_admission_id,
            "transferred_from_department": a.transferred_from_department,
            "referring_doctor": a.referring_doctor,
            "discharge_summary": a.discharge_summary,
            "discharge_instructions": a.discharge_instructions,
            "follow_up_date": a.follow_up_date.isoformat() if a.follow_up_date else None,
        }
        for a in admissions
    ]


@router.get("/patients/search")
async def search_patients_for_admission(
    q: str = Query("", description="Search by name or patient ID"),
    user: User = Depends(require_role(UserRole.FACULTY, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Search patients by name or ID for admission form (faculty/admin)."""
    query = select(Patient).order_by(Patient.name)
    if q:
        query = query.where(
            (Patient.name.ilike(f"%{q}%")) | (Patient.patient_id.ilike(f"%{q}%"))
        )
    result = await db.execute(query.limit(50))
    patients = result.scalars().all()
    return [
        {
            "id": p.id,
            "patient_id": p.patient_id,
            "name": p.name,
            "gender": p.gender.value if p.gender else None,
            "blood_group": p.blood_group,
        }
        for p in patients
    ]


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
