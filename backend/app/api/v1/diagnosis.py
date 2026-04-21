from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.database import get_db
from app.models.prescription import Prescription
from app.models.user import User, UserRole
from app.models.patient import Patient
from app.services.ai_provider import (
    get_diagnosis_suggestions,
    AIProviderError,
)

router = APIRouter(prefix="/ai", tags=["AI Diagnostics"])


class DiagnosisSuggestionResponse(BaseModel):
    disease: str
    confidence: float
    reasoning: str
    icd_code: str


class DiagnosisRequest(BaseModel):
    patient_id: str
    department: str | None = None
    form_name: str | None = None
    form_values: dict[str, Any]
    prior_diagnoses: list[dict[str, Any]] | None = None
    top_n: int = Field(default=5, ge=1, le=20)


@router.post("/diagnose", response_model=list[DiagnosisSuggestionResponse])
async def diagnose_patient(
    request: DiagnosisRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get AI-assisted diagnosis suggestions based on form data and patient history."""
    # Fetch patient
    result = await db.execute(
        select(Patient)
        .options(
            selectinload(Patient.allergies),
            selectinload(Patient.medical_alerts),
            selectinload(Patient.diagnosis_entries),
            selectinload(Patient.admissions),
            selectinload(Patient.case_records),
            selectinload(Patient.vitals),
            selectinload(Patient.prescriptions).selectinload(Prescription.medications),
        )
        .where(Patient.id == request.patient_id)
    )
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Permission check: patient can only request for themselves, students/faculty need appropriate access
    if user.role == UserRole.PATIENT and patient.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        suggestions = await get_diagnosis_suggestions(
            db=db,
            patient=patient,
            department=request.department,
            form_name=request.form_name,
            form_values=request.form_values,
            prior_diagnoses=request.prior_diagnoses,
            top_n=request.top_n,
        )
        return [DiagnosisSuggestionResponse(**s) for s in suggestions]
    except AIProviderError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
