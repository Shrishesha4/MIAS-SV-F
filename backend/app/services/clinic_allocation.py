from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.insurance_categories import generate_walk_in_type_value
from app.models.insurance_category import InsuranceCategory, InsuranceClinicConfig
from app.models.student import Clinic


async def resolve_preferred_clinic(
    db: AsyncSession,
    *,
    insurance_category_id: str | None,
    patient_category_name: str | None,
) -> Clinic | None:
    if not insurance_category_id:
        return None

    desired_walk_in_type = (
        generate_walk_in_type_value(patient_category_name)
        if patient_category_name
        else None
    )

    result = await db.execute(
        select(InsuranceClinicConfig)
        .options(selectinload(InsuranceClinicConfig.clinic))
        .where(
            InsuranceClinicConfig.insurance_category_id == insurance_category_id,
            InsuranceClinicConfig.is_enabled == True,
        )
    )
    configs = [config for config in result.scalars().all() if config.clinic and config.clinic.is_active]
    if not configs:
        return None

    def config_priority(config: InsuranceClinicConfig) -> tuple[int, float, str]:
        exact_match = int(bool(desired_walk_in_type and config.walk_in_type == desired_walk_in_type))
        clinic_name = config.clinic.name if config.clinic else ""
        return (-exact_match, config.registration_fee or 0, clinic_name.lower())

    configs.sort(key=config_priority)
    return configs[0].clinic
