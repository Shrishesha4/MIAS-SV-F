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
from app.api.v1.patient_serialization import serialize_patient_badge_context, serialize_patient_insurance

router = APIRouter(prefix="/admissions", tags=["Admissions"])


@router.get("/")
async def list_all_admissions(
    status: Optional[str] = Query(None, description="Filter by status: Active, Discharged, Transferred"),
    department: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    user: User = Depends(require_role(UserRole.FACULTY, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """List admissions with pagination (faculty/admin only)."""
    query = select(Admission).order_by(Admission.admission_date.desc())
    if status:
        query = query.where(Admission.status == status)
    if department:
        query = query.where(Admission.department == department)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0
    
    # Apply pagination
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    admissions = result.scalars().all()

    # Get patient names for display
    patient_ids = list(set(a.patient_id for a in admissions))
    patient_names = {}
    if patient_ids:
        pat_result = await db.execute(
            select(Patient)
            .options(selectinload(Patient.insurance_policies))
            .where(Patient.id.in_(patient_ids))
        )
        for patient in pat_result.scalars().all():
            patient_names[patient.id] = {
                "name": patient.name,
                "patient_id": patient.patient_id,
                **serialize_patient_badge_context(patient),
                "insurance_policies": serialize_patient_insurance(patient),
            }

    items = [
        {
            "id": a.id,
            "patient_id": a.patient_id,
            "patient_name": patient_names.get(a.patient_id, {}).get("name", "Unknown"),
            "patient_display_id": patient_names.get(a.patient_id, {}).get("patient_id", ""),
            "category": patient_names.get(a.patient_id, {}).get("category"),
            "category_color_primary": patient_names.get(a.patient_id, {}).get("category_color_primary"),
            "category_color_secondary": patient_names.get(a.patient_id, {}).get("category_color_secondary"),
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
            "insurance_policies": patient_names.get(a.patient_id, {}).get("insurance_policies", []),
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
    
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/patients/search")
async def search_patients_for_admission(
    q: str = Query("", description="Search by name or patient ID"),
    user: User = Depends(require_role(UserRole.FACULTY, UserRole.ADMIN, UserRole.STUDENT)),
    db: AsyncSession = Depends(get_db),
):
    """Search patients by name or ID for admission form (faculty/admin/student)."""
    query = select(Patient).order_by(Patient.name)
    if q:
        query = query.where(
            (Patient.name.ilike(f"%{q}%")) | (Patient.patient_id.ilike(f"%{q}%"))
        )
    result = await db.execute(
        query.options(selectinload(Patient.insurance_policies)).limit(50)
    )
    patients = result.scalars().all()
    return [
        {
            "id": p.id,
            "patient_id": p.patient_id,
            "name": p.name,
            "gender": p.gender.value if p.gender else None,
            "blood_group": p.blood_group,
            "insurance_policies": serialize_patient_insurance(p),
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
