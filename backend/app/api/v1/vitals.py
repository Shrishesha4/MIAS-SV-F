"""Vitals routes - additional standalone endpoints beyond patient-scoped ones."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.vital import Vital

router = APIRouter(prefix="/vitals", tags=["Vitals"])


@router.get("/latest/{patient_id}")
async def get_latest_vitals(
    patient_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Vital)
        .where(Vital.patient_id == patient_id)
        .order_by(Vital.recorded_at.desc())
        .limit(1)
    )
    vital = result.scalar_one_or_none()

    if not vital:
        return None

    return {
        "id": vital.id,
        "patient_id": vital.patient_id,
        "recorded_at": vital.recorded_at.isoformat() if vital.recorded_at else None,
        "systolic_bp": vital.systolic_bp,
        "diastolic_bp": vital.diastolic_bp,
        "heart_rate": vital.heart_rate,
        "respiratory_rate": vital.respiratory_rate,
        "temperature": vital.temperature,
        "oxygen_saturation": vital.oxygen_saturation,
        "weight": vital.weight,
        "blood_glucose": vital.blood_glucose,
        "cholesterol": vital.cholesterol,
        "bmi": vital.bmi,
    }
