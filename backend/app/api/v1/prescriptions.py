"""Standalone prescriptions routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.prescription import Prescription

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])


@router.get("/{prescription_id}")
async def get_prescription(
    prescription_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Prescription)
        .options(selectinload(Prescription.medications))
        .where(Prescription.id == prescription_id)
    )
    prescription = result.scalar_one_or_none()

    if not prescription:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Prescription not found")

    return {
        "id": prescription.id,
        "patient_id": prescription.patient_id,
        "date": prescription.date.isoformat() if prescription.date else None,
        "doctor": prescription.doctor,
        "department": prescription.department,
        "status": prescription.status.value if prescription.status else None,
        "medications": [
            {
                "id": m.id, "name": m.name, "dosage": m.dosage,
                "frequency": m.frequency, "duration": m.duration,
                "instructions": m.instructions,
                "refills_remaining": m.refills_remaining,
                "start_date": m.start_date, "end_date": m.end_date,
            }
            for m in prescription.medications
        ],
    }
