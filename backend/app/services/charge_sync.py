from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.form_definition import FormDefinition
from app.models.lab import ChargeCategory, ChargeItem, ChargePrice, ChargeTier, LabTest, LabTestGroup


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


def _base_prices(item: ChargeItem) -> dict[ChargeTier, ChargePrice]:
    return {price.tier: price for price in item.prices}


def _ensure_price_tiers(item: ChargeItem, db: AsyncSession) -> None:
    existing = _base_prices(item)
    for tier in ChargeTier:
        if tier in existing:
            continue
        price = ChargePrice(
            id=str(uuid.uuid4()),
            item_id=item.id,
            tier=tier,
            price=0,
        )
        item.prices.append(price)
        db.add(price)


def _upsert_charge_item(
	db: AsyncSession,
	existing_items: dict[tuple[str, str], ChargeItem],
	*,
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
        item.description = description if description is not None else item.description
        item.is_active = is_active

    _ensure_price_tiers(item, db)


async def sync_charge_sources(db: AsyncSession) -> None:
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

    forms_result = await db.execute(select(FormDefinition))
    for form in forms_result.scalars().all():
        _upsert_charge_item(
            db,
            existing_items,
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
        _upsert_charge_item(
            db,
            existing_items,
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
        _upsert_charge_item(
            db,
            existing_items,
            source_type=LAB_GROUP_SOURCE_TYPE,
            source_id=group.id,
            item_code=_group_item_code(group),
            name=group.name,
            category=ChargeCategory.LABS,
            description=group.description,
            is_active=group.is_active,
        )
