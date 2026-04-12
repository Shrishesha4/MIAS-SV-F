from __future__ import annotations

from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from app.models.patient_category import PatientCategoryOption


DEFAULT_PATIENT_CATEGORIES: tuple[dict[str, object], ...] = (
    {
        "name": "Classic",
        "description": "Standard hospital pricing and registration category.",
        "sort_order": 0,
    },
    {
        "name": "Prime",
        "description": "Priority services with upgraded access and benefits.",
        "sort_order": 1,
    },
    {
        "name": "Elite",
        "description": "Premium category for high-touch service workflows.",
        "sort_order": 2,
    },
    {
        "name": "Community",
        "description": "Community or subsidized patient support category.",
        "sort_order": 3,
    },
)


def normalize_patient_category_name(name: str) -> str:
    cleaned = " ".join((name or "").strip().replace("_", " ").split())
    if not cleaned:
        return ""

    if cleaned.isupper() and len(cleaned) <= 4:
        return cleaned

    return " ".join(part.capitalize() for part in cleaned.split())


async def ensure_patient_categories(db: AsyncSession) -> list[PatientCategoryOption]:
    result = await db.execute(
        select(PatientCategoryOption).order_by(PatientCategoryOption.sort_order.asc(), PatientCategoryOption.created_at.asc())
    )
    categories = list(result.scalars().all())
    existing_names = {category.name.casefold() for category in categories}

    pending_records: list[PatientCategoryOption] = []
    for index, item in enumerate(DEFAULT_PATIENT_CATEGORIES):
        name = str(item["name"])
        if name.casefold() in existing_names:
            continue
        pending_records.append(
            PatientCategoryOption(
                id=str(uuid4()),
                name=name,
                description=str(item["description"]),
                is_active=True,
                sort_order=index,
            )
        )
        existing_names.add(name.casefold())

    patient_values = await db.execute(
        select(Patient.category).distinct().where(Patient.category.is_not(None))
    )
    next_sort = len(categories) + len(pending_records)
    for raw_name in patient_values.scalars().all():
        normalized = normalize_patient_category_name(raw_name or "")
        if not normalized or normalized.casefold() in existing_names:
            continue
        pending_records.append(
            PatientCategoryOption(
                id=str(uuid4()),
                name=normalized,
                description="Imported from existing patient records.",
                is_active=True,
                sort_order=next_sort,
            )
        )
        existing_names.add(normalized.casefold())
        next_sort += 1

    if pending_records:
        db.add_all(pending_records)
        await db.flush()

    refreshed = await db.execute(
        select(PatientCategoryOption).order_by(PatientCategoryOption.sort_order.asc(), PatientCategoryOption.created_at.asc())
    )
    return list(refreshed.scalars().all())


async def get_default_patient_category_name(db: AsyncSession) -> str:
    categories = await ensure_patient_categories(db)
    first_active = next((category for category in categories if category.is_active), None)
    return first_active.name if first_active else "Classic"


async def patient_category_usage_counts(db: AsyncSession) -> dict[str, int]:
    result = await db.execute(
        select(Patient.category, func.count(Patient.id)).group_by(Patient.category)
    )
    return {normalize_patient_category_name(name or "Unknown") or "Unknown": count for name, count in result.all()}