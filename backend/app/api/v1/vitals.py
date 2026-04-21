"""Vitals routes - additional standalone endpoints beyond patient-scoped ones."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.vital import CORE_VITAL_FIELD_NAMES, Vital, VitalParameter

router = APIRouter(prefix="/vitals", tags=["Vitals"])


def _serialize_vital(vital: Vital) -> dict:
    payload = {
        "id": vital.id,
        "patient_id": vital.patient_id,
        "recorded_at": vital.recorded_at.isoformat() if vital.recorded_at else None,
        "recorded_by": vital.recorded_by,
        "extra_values": vital.extra_values or {},
    }
    for field_name in CORE_VITAL_FIELD_NAMES:
        payload[field_name] = getattr(vital, field_name)
    payload.update(vital.extra_values or {})
    return payload


@router.get("/parameters")
async def get_active_vital_parameters(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all active vital parameters for use in forms."""
    result = await db.execute(
        select(VitalParameter)
        .where(VitalParameter.is_active == True)
        .order_by(VitalParameter.category, VitalParameter.sort_order)
    )
    parameters = result.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "display_name": p.display_name,
            "category": p.category,
            "unit": p.unit,
            "min_value": p.min_value,
            "max_value": p.max_value,
            "value_style": p.value_style,
            "is_active": p.is_active,
            "sort_order": p.sort_order,
        }
        for p in parameters
    ]


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

    return _serialize_vital(vital)
