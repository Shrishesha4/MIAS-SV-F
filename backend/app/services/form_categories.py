from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.form_category import FormCategoryOption
from app.models.form_definition import FormDefinition


DEFAULT_FORM_CATEGORIES: tuple[dict[str, object], ...] = (
    {"name": "CLINICAL", "sort_order": 0, "is_system": True},
    {"name": "LABORATORY", "sort_order": 1, "is_system": True},
    {"name": "ADMINISTRATIVE", "sort_order": 2, "is_system": True},
)

CLINICAL_FORM_TYPES = {
    "CLINICAL",
    "CASE_RECORD",
    "ADMISSION",
    "ADMISSION_REQUEST",
    "ADMISSION_INTAKE",
    "ADMISSION_DISCHARGE",
    "ADMISSION_TRANSFER",
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

    pending_records: list[FormCategoryOption] = []
    for item in DEFAULT_FORM_CATEGORIES:
        normalized_name = normalize_form_section_name(str(item["name"]))
        if normalized_name.casefold() in existing_names:
            continue
        pending_records.append(
            FormCategoryOption(
                id=str(uuid4()),
                name=normalized_name,
                sort_order=int(item["sort_order"]),
                is_active=True,
                is_system=bool(item["is_system"]),
            )
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
            FormCategoryOption(
                id=str(uuid4()),
                name=normalized_name,
                sort_order=next_sort,
                is_active=True,
                is_system=False,
            )
        )
        existing_names.add(normalized_name.casefold())
        next_sort += 1

    if pending_records:
        db.add_all(pending_records)
        await db.flush()

    refreshed = await db.execute(
        select(FormCategoryOption).order_by(FormCategoryOption.sort_order.asc(), FormCategoryOption.name.asc())
    )
    return list(refreshed.scalars().all())