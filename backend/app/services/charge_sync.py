from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.form_definition import FormDefinition
from app.models.lab import ChargeCategory, ChargeItem, ChargePrice, LabTest, LabTestGroup
from app.services.patient_categories import ensure_patient_categories, normalize_patient_category_name


FORM_SOURCE_TYPE = 'form_definition'
LAB_TEST_SOURCE_TYPE = 'lab_test'
LAB_GROUP_SOURCE_TYPE = 'lab_test_group'
SYNCED_SOURCE_TYPES = (FORM_SOURCE_TYPE, LAB_TEST_SOURCE_TYPE, LAB_GROUP_SOURCE_TYPE)

CLINICAL_FORM_TYPES = {
	'CLINICAL',
	'CASE_RECORD',
	'ADMISSION',
	'ADMISSION_REQUEST',
	'ADMISSION_INTAKE',
	'ADMISSION_DISCHARGE',
	'ADMISSION_TRANSFER',
	'PRESCRIPTION',
	'PRESCRIPTION_CREATE',
	'PRESCRIPTION_EDIT',
	'PRESCRIPTION_REQUEST',
	'VITAL_ENTRY',
}
LAB_FORM_TYPES = {'LABORATORY', 'LAB', 'LABS'}


def _normalize_code(prefix: str, value: str, fallback: str) -> str:
    cleaned = re.sub(r'[^A-Za-z0-9]+', '_', value or '').strip('_').upper()
    if not cleaned:
        cleaned = fallback.upper()
    return f'{prefix}_{cleaned}'


def _form_category(form: FormDefinition) -> ChargeCategory:
    form_type = (form.form_type or '').strip().upper()
    if form_type in CLINICAL_FORM_TYPES:
        return ChargeCategory.CLINICAL
    if form_type in LAB_FORM_TYPES:
        return ChargeCategory.LABS
    return ChargeCategory.ADMIN


def _form_item_code(form: FormDefinition) -> str:
    return _normalize_code('FORM', form.slug or form.name, f'FORM_{form.id[:8]}')


def _group_item_code(group: LabTestGroup) -> str:
    return _normalize_code('PANEL', group.name, f'GROUP_{group.id[:8]}')


def _base_prices(item: ChargeItem) -> dict[str, ChargePrice]:
    prices: dict[str, ChargePrice] = {}
    for price in item.prices:
        normalized_name = normalize_patient_category_name(price.tier or '')
        price_key = normalized_name.casefold()
        if not normalized_name or price_key in prices:
            continue
        if price.tier != normalized_name:
            price.tier = normalized_name
        prices[price_key] = price

    return prices


async def get_charge_price_categories(db: AsyncSession) -> list[str]:
    categories = await ensure_patient_categories(db)
    category_names: list[str] = []
    seen: set[str] = set()

    for category in categories:
        normalized_name = normalize_patient_category_name(category.name)
        category_key = normalized_name.casefold()
        if not normalized_name or category_key in seen:
            continue
        category_names.append(normalized_name)
        seen.add(category_key)

    return category_names


def _ensure_price_tiers(item: ChargeItem, db: AsyncSession, category_names: list[str]) -> None:
    existing = _base_prices(item)
    for category_name in category_names:
        category_key = category_name.casefold()
        existing_price = existing.get(category_key)
        if existing_price:
            if existing_price.tier != category_name:
                existing_price.tier = category_name
            continue
        price = ChargePrice(
            id=str(uuid.uuid4()),
            item_id=item.id,
            tier=category_name,
            price=0,
        )
        item.prices.append(price)
        db.add(price)


async def sync_charge_price_categories(
    db: AsyncSession,
    items: list[ChargeItem] | None = None,
) -> list[str]:
    category_names = await get_charge_price_categories(db)
    if items is None:
        result = await db.execute(select(ChargeItem).options(selectinload(ChargeItem.prices)))
        items = list(result.scalars().all())

    for item in items:
        _ensure_price_tiers(item, db, category_names)

    await db.flush()
    return category_names


def _upsert_charge_item(
    db: AsyncSession,
    existing_items: dict[tuple[str, str], ChargeItem],
    *,
    category_names: list[str],
    source_type: str,
    source_id: str,
    item_code: str,
    name: str,
    category: ChargeCategory,
    description: str | None,
    is_active: bool,
) -> None:
    key = (source_type, source_id)
    item = existing_items.get(key)
    if item is None:
        item = ChargeItem(
            id=str(uuid.uuid4()),
            item_code=item_code,
            name=name,
            category=category,
            description=description,
            source_type=source_type,
            source_id=source_id,
            is_active=is_active,
        )
        item.prices = []
        db.add(item)
        existing_items[key] = item
    else:
        item.item_code = item_code
        item.name = name
        item.category = category
        item.description = description
        item.is_active = is_active

    _ensure_price_tiers(item, db, category_names)


async def sync_charge_sources(db: AsyncSession) -> None:
    category_names = await get_charge_price_categories(db)
    existing_result = await db.execute(
        select(ChargeItem)
        .options(selectinload(ChargeItem.prices))
        .where(ChargeItem.source_type.in_(SYNCED_SOURCE_TYPES))
    )
    existing_items = {
        (item.source_type, item.source_id): item
        for item in existing_result.scalars().all()
        if item.source_type and item.source_id
    }
    seen_source_keys: set[tuple[str, str]] = set()

    forms_result = await db.execute(select(FormDefinition))
    for form in forms_result.scalars().all():
        seen_source_keys.add((FORM_SOURCE_TYPE, form.id))
        _upsert_charge_item(
            db,
            existing_items,
            category_names=category_names,
            source_type=FORM_SOURCE_TYPE,
            source_id=form.id,
            item_code=_form_item_code(form),
            name=form.name,
            category=_form_category(form),
            description=form.description,
            is_active=form.is_active,
        )

    tests_result = await db.execute(select(LabTest))
    for test in tests_result.scalars().all():
        seen_source_keys.add((LAB_TEST_SOURCE_TYPE, test.id))
        _upsert_charge_item(
            db,
            existing_items,
            category_names=category_names,
            source_type=LAB_TEST_SOURCE_TYPE,
            source_id=test.id,
            item_code=test.code,
            name=test.name,
            category=ChargeCategory.LABS,
            description=test.description,
            is_active=test.is_active,
        )

    groups_result = await db.execute(select(LabTestGroup))
    for group in groups_result.scalars().all():
        seen_source_keys.add((LAB_GROUP_SOURCE_TYPE, group.id))
        _upsert_charge_item(
            db,
            existing_items,
            category_names=category_names,
            source_type=LAB_GROUP_SOURCE_TYPE,
            source_id=group.id,
            item_code=_group_item_code(group),
            name=group.name,
            category=ChargeCategory.LABS,
            description=group.description,
            is_active=group.is_active,
        )

    for key, item in existing_items.items():
        if key not in seen_source_keys:
            await db.delete(item)
