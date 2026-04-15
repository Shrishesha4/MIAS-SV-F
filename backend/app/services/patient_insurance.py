from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.insurance_category import InsuranceCategory
from app.models.patient import InsurancePolicy, Patient


async def sync_patient_insurance_category(
    db: AsyncSession,
    patient: Patient,
    insurance_category_id: str | None,
    *,
    policy_prefix: str,
) -> InsuranceCategory | None:
    if not insurance_category_id:
        return None

    insurance_category = (
        await db.execute(
            select(InsuranceCategory).where(InsuranceCategory.id == insurance_category_id)
        )
    ).scalar_one_or_none()
    if not insurance_category or not insurance_category.is_active:
        raise HTTPException(status_code=400, detail="Selected insurance category is invalid")

    existing_policies = (
        await db.execute(
            select(InsurancePolicy)
            .where(InsurancePolicy.patient_id == patient.id)
            .order_by(InsurancePolicy.id)
        )
    ).scalars().all()

    target_policy = next(
        (
            policy
            for policy in existing_policies
            if policy.insurance_category_id == insurance_category.id
        ),
        None,
    )

    if target_policy is None:
        if len(existing_policies) == 1:
            target_policy = existing_policies[0]
        else:
            suffix = f"-{len(existing_policies) + 1}" if existing_policies else ""
            target_policy = InsurancePolicy(
                id=str(uuid.uuid4()),
                patient_id=patient.id,
                policy_number=f"{policy_prefix}-{patient.patient_id}{suffix}",
            )
            db.add(target_policy)

    if not target_policy.policy_number:
        target_policy.policy_number = f"{policy_prefix}-{patient.patient_id}"

    target_policy.insurance_category_id = insurance_category.id
    target_policy.provider = insurance_category.name
    target_policy.coverage_type = insurance_category.name
    target_policy.icon_key = insurance_category.icon_key
    target_policy.custom_badge_symbol = insurance_category.custom_badge_symbol
    target_policy.color_primary = insurance_category.color_primary
    target_policy.color_secondary = insurance_category.color_secondary

    return insurance_category