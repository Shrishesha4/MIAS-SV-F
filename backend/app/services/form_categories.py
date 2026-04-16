from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.form_category import FormCategoryOption
from app.models.form_definition import FormDefinition


DEFAULT_FORM_CATEGORIES: tuple[dict[str, object], ...] = (
    {"name": "ADMISSION", "sort_order": 0, "is_system": True},
    {"name": "CLINICAL", "sort_order": 1, "is_system": True},
    {"name": "LABORATORY", "sort_order": 2, "is_system": True},
    {"name": "ADMINISTRATIVE", "sort_order": 3, "is_system": True},
)

ADMISSION_FORM_TYPES = {
    "ADMISSION",
    "ADMISSION_REQUEST",
    "ADMISSION_INTAKE",
    "ADMISSION_DISCHARGE",
    "ADMISSION_TRANSFER",
}

CLINICAL_FORM_TYPES = {
    "CLINICAL",
    "CASE_RECORD",
    "PRESCRIPTION",
    "PRESCRIPTION_CREATE",
    "PRESCRIPTION_EDIT",
    "PRESCRIPTION_REQUEST",
    "VITAL_ENTRY",
}
LAB_FORM_TYPES = {"LABORATORY", "LAB", "LABS"}
ADMIN_FORM_TYPES = {"ADMINISTRATIVE", "PROFILE", "PROFILE_EDIT", "CUSTOM"}


def normalize_form_section_name(name: str | None) -> str:
    cleaned = " ".join((name or "").strip().replace("_", " ").split())
    return cleaned.upper() if cleaned else ""


def infer_form_section(form_type: str | None, section: str | None = None) -> str:
    normalized_section = normalize_form_section_name(section)
    if normalized_section:
        return normalized_section

    normalized_type = normalize_form_section_name(form_type)
    if normalized_type in ADMISSION_FORM_TYPES:
        return "ADMISSION"
    if normalized_type in CLINICAL_FORM_TYPES:
        return "CLINICAL"
    if normalized_type in LAB_FORM_TYPES:
        return "LABORATORY"
    if normalized_type in ADMIN_FORM_TYPES or not normalized_type:
        return "ADMINISTRATIVE"
    return normalized_type


async def ensure_form_categories(db: AsyncSession) -> list[FormCategoryOption]:
    result = await db.execute(
        select(FormCategoryOption).order_by(FormCategoryOption.sort_order.asc(), FormCategoryOption.name.asc())
    )
    categories = list(result.scalars().all())
    existing_names = {category.name.casefold() for category in categories}

    pending_records: list[dict[str, object]] = []
    for item in DEFAULT_FORM_CATEGORIES:
        normalized_name = normalize_form_section_name(str(item["name"]))
        if normalized_name.casefold() in existing_names:
            continue
        pending_records.append(
            {
                "id": str(uuid4()),
                "name": normalized_name,
                "sort_order": int(item["sort_order"]),
                "is_active": True,
                "is_system": bool(item["is_system"]),
            }
        )
        existing_names.add(normalized_name.casefold())

    section_values = await db.execute(
        select(FormDefinition.section, FormDefinition.form_type).distinct()
    )
    next_sort = len(categories) + len(pending_records)
    for section, form_type in section_values.all():
        normalized_name = infer_form_section(form_type, section)
        if not normalized_name or normalized_name.casefold() in existing_names:
            continue
        pending_records.append(
            {
                "id": str(uuid4()),
                "name": normalized_name,
                "sort_order": next_sort,
                "is_active": True,
                "is_system": False,
            }
        )
        existing_names.add(normalized_name.casefold())
        next_sort += 1

    if pending_records:
        timestamp = datetime.utcnow()
        rows = [
            {
                **record,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
            for record in pending_records
        ]
        await db.execute(
            pg_insert(FormCategoryOption)
            .values(rows)
            .on_conflict_do_nothing(index_elements=[FormCategoryOption.name])
        )
        await db.flush()

    refreshed = await db.execute(
        select(FormCategoryOption).order_by(FormCategoryOption.sort_order.asc(), FormCategoryOption.name.asc())
    )
    return list(refreshed.scalars().all())
