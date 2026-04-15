"""Autocomplete endpoints for ICD-10 codes, medicines, and other reference data."""
from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, case, or_
from typing import Optional

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.icd_code import ICDCode
from app.models.case_record import CaseRecord
from app.models.patient import Patient
from app.models.prescription import PrescriptionMedication
from app.utils.reference_data import (
    search_medicines, FREQUENCIES, DURATIONS, DOSAGE_FORMS,
)

router = APIRouter(prefix="/autocomplete", tags=["Autocomplete"])


async def _search_icd_catalog(db: AsyncSession, query: str, limit: int = 20) -> list[ICDCode]:
    cleaned_query = query.strip()
    statement = select(ICDCode).where(ICDCode.is_active == True)

    if not cleaned_query:
        statement = statement.order_by(ICDCode.code).limit(limit)
    else:
        like = f"%{cleaned_query}%"
        prefix = f"{cleaned_query}%"
        statement = (
            statement.where(
                or_(
                    ICDCode.code.ilike(like),
                    ICDCode.description.ilike(like),
                    ICDCode.category.ilike(like),
                )
            )
            .order_by(
                case(
                    (ICDCode.code.ilike(prefix), 0),
                    (ICDCode.description.ilike(prefix), 1),
                    (ICDCode.category.ilike(prefix), 2),
                    else_=3,
                ),
                ICDCode.code,
            )
            .limit(limit)
        )

    return (await db.execute(statement)).scalars().all()


@router.get("/icd10")
async def autocomplete_icd10(
    q: str = Query("", description="Search query for ICD-10 codes"),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search ICD-10 codes by code or description."""
    results = await _search_icd_catalog(db, q, limit)
    return [
        {
            "code": item.code,
            "description": item.description,
            "category": item.category,
        }
        for item in results
    ]


@router.get("/medicines")
async def autocomplete_medicines(
    q: str = Query("", description="Search query for medicines"),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search medicines from reference database + previously entered ones."""
    # Get results from reference database
    ref_results = search_medicines(q, limit)
    
    # Also search from previously entered medication names in the system
    existing_meds = []
    if q and len(q) >= 2:
        result = await db.execute(
            select(
                PrescriptionMedication.name,
                PrescriptionMedication.dosage,
                PrescriptionMedication.frequency,
            )
            .where(PrescriptionMedication.name.ilike(f"%{q}%"))
            .group_by(
                PrescriptionMedication.name,
                PrescriptionMedication.dosage,
                PrescriptionMedication.frequency,
            )
            .limit(10)
        )
        for row in result.all():
            existing_meds.append({
                "name": row[0],
                "dosage": row[1],
                "frequency": row[2],
                "source": "existing",
            })
    
    # Merge: reference results first, then existing (deduplicated)
    ref_names = {r["name"].lower() for r in ref_results}
    for med in existing_meds:
        if med["name"].lower() not in ref_names:
            ref_results.append({
                "name": med["name"],
                "generic": med["name"],
                "category": "Previously Used",
                "common_dosages": [med["dosage"]] if med["dosage"] else [],
                "common_frequencies": [med["frequency"]] if med["frequency"] else [],
                "form": "Tablet",
            })
    
    return ref_results[:limit]


@router.get("/medicine-details/{medicine_name}")
async def get_medicine_details(
    medicine_name: str,
    user: User = Depends(get_current_user),
):
    """Get detailed info for a specific medicine (dosages, frequencies, etc.)."""
    results = search_medicines(medicine_name, 1)
    if results and results[0]["name"].lower() == medicine_name.lower():
        return results[0]
    
    # Partial match
    if results:
        return results[0]
    
    return {"name": medicine_name, "generic": medicine_name, "category": "Unknown",
            "common_dosages": [], "common_frequencies": [], "form": "Tablet"}


@router.get("/frequencies")
async def get_frequencies(
    user: User = Depends(get_current_user),
):
    """Get common medication frequencies."""
    return FREQUENCIES


@router.get("/durations")
async def get_durations(
    user: User = Depends(get_current_user),
):
    """Get common medication durations."""
    return DURATIONS


@router.get("/dosage-forms")
async def get_dosage_forms(
    user: User = Depends(get_current_user),
):
    """Get common dosage forms."""
    return DOSAGE_FORMS


@router.get("/diagnoses")
async def autocomplete_diagnoses(
    q: str = Query("", description="Search query for diagnoses"),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search for diagnoses from previously entered data + ICD-10."""
    results = []

    icd_results = await _search_icd_catalog(db, q, limit)
    for icd in icd_results:
        results.append({
            "text": f"{icd.code} - {icd.description}",
            "icd_code": icd.code,
            "icd_description": icd.description,
            "category": icd.category,
        })

    if q and len(q) >= 2:
        existing_case_records = await db.execute(
            select(CaseRecord.diagnosis)
            .where(CaseRecord.diagnosis.ilike(f"%{q}%"))
            .where(CaseRecord.diagnosis.isnot(None))
            .group_by(CaseRecord.diagnosis)
            .limit(10)
        )
        existing_patient_diagnoses = await db.execute(
            select(Patient.primary_diagnosis)
            .where(Patient.primary_diagnosis.ilike(f"%{q}%"))
            .where(Patient.primary_diagnosis.isnot(None))
            .group_by(Patient.primary_diagnosis)
            .limit(10)
        )
        existing_diagnoses = [row[0] for row in existing_case_records.all()] + [row[0] for row in existing_patient_diagnoses.all()]
        existing_texts = {r["text"].lower() for r in results}
        for diag in existing_diagnoses:
            normalized = diag.strip().lower()
            if normalized and normalized not in existing_texts:
                results.append({
                    "text": diag,
                    "icd_code": None,
                    "icd_description": None,
                    "category": "Previously Used",
                })
    
    return results[:limit]
