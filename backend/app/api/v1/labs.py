from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional, List
import uuid

from app.api.deps import get_db, get_current_user, require_role
from app.models.user import User, UserRole
from app.models.lab import Lab, LabTest, LabTestGroup, ChargeItem, ChargePrice, ChargeCategory, ChargeTier
from app.core.exceptions import NotFoundException
from app.services.charge_sync import sync_charge_sources

router = APIRouter(prefix="/labs", tags=["Labs"])


class LabInfo(BaseModel):
    id: str
    name: str
    block: Optional[str]
    lab_type: str
    department: str
    location: Optional[str]
    contact_phone: Optional[str]
    operating_hours: Optional[str]
    is_active: bool


class CreateLabRequest(BaseModel):
    name: str
    block: Optional[str] = None
    lab_type: str = "General"
    department: str
    location: Optional[str] = None
    contact_phone: Optional[str] = None
    operating_hours: Optional[str] = None
    is_active: bool = True


class UpdateLabRequest(BaseModel):
    name: Optional[str] = None
    block: Optional[str] = None
    lab_type: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    contact_phone: Optional[str] = None
    operating_hours: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("")
async def list_labs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all labs with test and group counts"""
    result = await db.execute(
        select(Lab)
        .options(selectinload(Lab.tests), selectinload(Lab.test_groups))
        .order_by(Lab.created_at.desc())
    )
    labs = result.scalars().all()
    return [
        {
            "id": lab.id,
            "name": lab.name,
            "block": lab.block,
            "lab_type": lab.lab_type,
            "department": lab.department,
            "location": lab.location,
            "contact_phone": lab.contact_phone,
            "operating_hours": lab.operating_hours,
            "is_active": lab.is_active,
            "test_count": len(lab.tests) if lab.tests else 0,
            "group_count": len(lab.test_groups) if lab.test_groups else 0,
        }
        for lab in labs
    ]


@router.post("")
async def create_lab(
    data: CreateLabRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Create a new lab (admin only)"""
    lab = Lab(
        id=str(uuid.uuid4()),
        name=data.name,
        block=data.block,
        lab_type=data.lab_type,
        department=data.department,
        location=data.location,
        contact_phone=data.contact_phone,
        operating_hours=data.operating_hours,
        is_active=data.is_active,
    )
    db.add(lab)
    await db.commit()
    await db.refresh(lab)
    return {
        "id": lab.id,
        "name": lab.name,
        "block": lab.block,
        "lab_type": lab.lab_type,
        "department": lab.department,
        "location": lab.location,
        "contact_phone": lab.contact_phone,
        "operating_hours": lab.operating_hours,
        "is_active": lab.is_active,
    }


@router.get("/{id}")
async def get_lab(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific lab by ID"""
    result = await db.execute(select(Lab).where(Lab.id == id))
    lab = result.scalar_one_or_none()
    if not lab:
        raise NotFoundException("Lab not found")
    return {
        "id": lab.id,
        "name": lab.name,
        "block": lab.block,
        "lab_type": lab.lab_type,
        "department": lab.department,
        "location": lab.location,
        "contact_phone": lab.contact_phone,
        "operating_hours": lab.operating_hours,
        "is_active": lab.is_active,
    }


@router.put("/{id}")
async def update_lab(
    id: str,
    data: UpdateLabRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Update an existing lab (admin only)"""
    result = await db.execute(select(Lab).where(Lab.id == id))
    lab = result.scalar_one_or_none()
    if not lab:
        raise NotFoundException("Lab not found")

    # Update only provided fields
    if data.name is not None:
        lab.name = data.name
    if data.block is not None:
        lab.block = data.block
    if data.lab_type is not None:
        lab.lab_type = data.lab_type
    if data.department is not None:
        lab.department = data.department
    if data.location is not None:
        lab.location = data.location
    if data.contact_phone is not None:
        lab.contact_phone = data.contact_phone
    if data.operating_hours is not None:
        lab.operating_hours = data.operating_hours
    if data.is_active is not None:
        lab.is_active = data.is_active

    await db.commit()
    await db.refresh(lab)
    return {
        "id": lab.id,
        "name": lab.name,
        "block": lab.block,
        "lab_type": lab.lab_type,
        "department": lab.department,
        "location": lab.location,
        "contact_phone": lab.contact_phone,
        "operating_hours": lab.operating_hours,
        "is_active": lab.is_active,
    }


@router.delete("/{id}")
async def delete_lab(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Delete a lab (admin only)"""
    result = await db.execute(select(Lab).where(Lab.id == id))
    lab = result.scalar_one_or_none()
    if not lab:
        raise NotFoundException("Lab not found")

    await db.delete(lab)
    await db.commit()
    return {"message": "Lab deleted successfully"}


# ============ Lab Tests ============

class CreateLabTestRequest(BaseModel):
    name: str
    code: str
    category: str
    description: Optional[str] = None
    sample_type: Optional[str] = None
    turnaround_time: Optional[str] = None
    is_active: bool = True


class UpdateLabTestRequest(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    sample_type: Optional[str] = None
    turnaround_time: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/{lab_id}/tests")
async def list_lab_tests(
    lab_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all tests for a lab"""
    result = await db.execute(
        select(LabTest)
        .where(LabTest.lab_id == lab_id)
        .order_by(LabTest.category, LabTest.name)
    )
    tests = result.scalars().all()
    return [
        {
            "id": t.id,
            "lab_id": t.lab_id,
            "name": t.name,
            "code": t.code,
            "category": t.category,
            "description": t.description,
            "sample_type": t.sample_type,
            "turnaround_time": t.turnaround_time,
            "is_active": t.is_active,
        }
        for t in tests
    ]


@router.post("/{lab_id}/tests")
async def create_lab_test(
    lab_id: str,
    data: CreateLabTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Create a new lab test (admin only)"""
    # Verify lab exists
    result = await db.execute(select(Lab).where(Lab.id == lab_id))
    if not result.scalar_one_or_none():
        raise NotFoundException("Lab not found")

    test = LabTest(
        id=str(uuid.uuid4()),
        lab_id=lab_id,
        name=data.name,
        code=data.code,
        category=data.category,
        description=data.description,
        sample_type=data.sample_type,
        turnaround_time=data.turnaround_time,
        is_active=data.is_active,
    )
    db.add(test)
    await db.commit()
    await db.refresh(test)
    return {
        "id": test.id,
        "lab_id": test.lab_id,
        "name": test.name,
        "code": test.code,
        "category": test.category,
        "description": test.description,
        "sample_type": test.sample_type,
        "turnaround_time": test.turnaround_time,
        "is_active": test.is_active,
    }


@router.put("/{lab_id}/tests/{test_id}")
async def update_lab_test(
    lab_id: str,
    test_id: str,
    data: UpdateLabTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Update a lab test (admin only)"""
    result = await db.execute(
        select(LabTest).where(LabTest.id == test_id, LabTest.lab_id == lab_id)
    )
    test = result.scalar_one_or_none()
    if not test:
        raise NotFoundException("Lab test not found")

    if data.name is not None:
        test.name = data.name
    if data.code is not None:
        test.code = data.code
    if data.category is not None:
        test.category = data.category
    if data.description is not None:
        test.description = data.description
    if data.sample_type is not None:
        test.sample_type = data.sample_type
    if data.turnaround_time is not None:
        test.turnaround_time = data.turnaround_time
    if data.is_active is not None:
        test.is_active = data.is_active

    await db.commit()
    await db.refresh(test)
    return {
        "id": test.id,
        "lab_id": test.lab_id,
        "name": test.name,
        "code": test.code,
        "category": test.category,
        "description": test.description,
        "sample_type": test.sample_type,
        "turnaround_time": test.turnaround_time,
        "is_active": test.is_active,
    }


@router.delete("/{lab_id}/tests/{test_id}")
async def delete_lab_test(
    lab_id: str,
    test_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Delete a lab test (admin only)"""
    result = await db.execute(
        select(LabTest).where(LabTest.id == test_id, LabTest.lab_id == lab_id)
    )
    test = result.scalar_one_or_none()
    if not test:
        raise NotFoundException("Lab test not found")

    await db.delete(test)
    await db.commit()
    return {"message": "Lab test deleted successfully"}


# ============ Lab Test Groups ============

class CreateLabTestGroupRequest(BaseModel):
    name: str
    description: Optional[str] = None
    test_ids: List[str] = []
    is_active: bool = True


class UpdateLabTestGroupRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    test_ids: Optional[List[str]] = None
    is_active: Optional[bool] = None


@router.get("/{lab_id}/groups")
async def list_lab_test_groups(
    lab_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all test groups for a lab"""
    result = await db.execute(
        select(LabTestGroup)
        .options(selectinload(LabTestGroup.tests))
        .where(LabTestGroup.lab_id == lab_id)
        .order_by(LabTestGroup.name)
    )
    groups = result.scalars().all()
    return [
        {
            "id": g.id,
            "lab_id": g.lab_id,
            "name": g.name,
            "description": g.description,
            "is_active": g.is_active,
            "tests": [
                {"id": t.id, "name": t.name, "code": t.code, "category": t.category}
                for t in g.tests
            ],
        }
        for g in groups
    ]


@router.post("/{lab_id}/groups")
async def create_lab_test_group(
    lab_id: str,
    data: CreateLabTestGroupRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Create a new test group (admin only)"""
    # Verify lab exists
    result = await db.execute(select(Lab).where(Lab.id == lab_id))
    if not result.scalar_one_or_none():
        raise NotFoundException("Lab not found")

    group_id = str(uuid.uuid4())
    group = LabTestGroup(
        id=group_id,
        lab_id=lab_id,
        name=data.name,
        description=data.description,
        is_active=data.is_active,
    )
    db.add(group)
    await db.commit()
    
    # Now add tests to the committed group
    if data.test_ids:
        # Reload group with selectinload to avoid lazy loading
        result = await db.execute(
            select(LabTestGroup)
            .options(selectinload(LabTestGroup.tests))
            .where(LabTestGroup.id == group_id)
        )
        group = result.scalar_one()
        
        # Fetch the tests
        result = await db.execute(
            select(LabTest).where(LabTest.id.in_(data.test_ids))
        )
        tests = result.scalars().all()
        group.tests = list(tests)
        await db.commit()
    
    # Reload with tests for response
    result = await db.execute(
        select(LabTestGroup)
        .options(selectinload(LabTestGroup.tests))
        .where(LabTestGroup.id == group_id)
    )
    group = result.scalar_one()
    
    return {
        "id": group.id,
        "lab_id": group.lab_id,
        "name": group.name,
        "description": group.description,
        "is_active": group.is_active,
        "tests": [
            {"id": t.id, "name": t.name, "code": t.code, "category": t.category}
            for t in group.tests
        ],
    }


@router.put("/{lab_id}/groups/{group_id}")
async def update_lab_test_group(
    lab_id: str,
    group_id: str,
    data: UpdateLabTestGroupRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Update a test group (admin only)"""
    result = await db.execute(
        select(LabTestGroup)
        .options(selectinload(LabTestGroup.tests))
        .where(LabTestGroup.id == group_id, LabTestGroup.lab_id == lab_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise NotFoundException("Test group not found")

    if data.name is not None:
        group.name = data.name
    if data.description is not None:
        group.description = data.description
    if data.is_active is not None:
        group.is_active = data.is_active
    if data.test_ids is not None:
        result = await db.execute(
            select(LabTest).where(LabTest.id.in_(data.test_ids))
        )
        tests = result.scalars().all()
        group.tests = list(tests)

    group_id = group.id  # Store ID before commit
    await db.commit()
    
    # Reload with tests
    result = await db.execute(
        select(LabTestGroup)
        .options(selectinload(LabTestGroup.tests))
        .where(LabTestGroup.id == group_id)
    )
    group = result.scalar_one()
    
    return {
        "id": group.id,
        "lab_id": group.lab_id,
        "name": group.name,
        "description": group.description,
        "is_active": group.is_active,
        "tests": [
            {"id": t.id, "name": t.name, "code": t.code, "category": t.category}
            for t in group.tests
        ],
    }


@router.delete("/{lab_id}/groups/{group_id}")
async def delete_lab_test_group(
    lab_id: str,
    group_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Delete a test group (admin only)"""
    result = await db.execute(
        select(LabTestGroup).where(LabTestGroup.id == group_id, LabTestGroup.lab_id == lab_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise NotFoundException("Test group not found")

    await db.delete(group)
    await db.commit()
    return {"message": "Test group deleted successfully"}


# ============ Charge Master ============

class CreateChargeItemRequest(BaseModel):
    item_code: str
    name: str
    category: str  # "CLINICAL", "LABS", "ADMIN"
    description: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    prices: dict = {}  # {"CLASSIC": 500, "PRIME": 800, ...}
    is_active: bool = True


class UpdateChargeItemRequest(BaseModel):
    item_code: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    prices: Optional[dict] = None
    is_active: Optional[bool] = None


charge_router = APIRouter(prefix="/charges", tags=["Charge Master"])


@charge_router.get("")
async def list_charge_items(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all charge items, optionally filtered by category"""
    await sync_charge_sources(db)

    query = select(ChargeItem).options(selectinload(ChargeItem.prices))
    if category:
        query = query.where(ChargeItem.category == ChargeCategory(category))
    query = query.order_by(ChargeItem.category, ChargeItem.name)
    
    result = await db.execute(query)
    items = result.scalars().all()
    return [
        {
            "id": item.id,
            "item_code": item.item_code,
            "name": item.name,
            "category": item.category.value,
            "description": item.description,
            "source_type": item.source_type,
            "source_id": item.source_id,
            "is_active": item.is_active,
            "prices": {p.tier.value: float(p.price) for p in item.prices},
        }
        for item in items
    ]


@charge_router.post("")
async def create_charge_item(
    data: CreateChargeItemRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Create a new charge item (admin only)"""
    item = ChargeItem(
        id=str(uuid.uuid4()),
        item_code=data.item_code,
        name=data.name,
        category=ChargeCategory(data.category),
        description=data.description,
        source_type=data.source_type,
        source_id=data.source_id,
        is_active=data.is_active,
    )
    db.add(item)
    
    # Add prices for each tier
    for tier_name, price in data.prices.items():
        price_obj = ChargePrice(
            id=str(uuid.uuid4()),
            item_id=item.id,
            tier=ChargeTier(tier_name),
            price=price,
        )
        db.add(price_obj)
    
    item_id = item.id  # Store ID before commit
    await db.commit()
    
    # Reload with prices
    result = await db.execute(
        select(ChargeItem)
        .options(selectinload(ChargeItem.prices))
        .where(ChargeItem.id == item_id)
    )
    item = result.scalar_one()
    
    return {
        "id": item.id,
        "item_code": item.item_code,
        "name": item.name,
        "category": item.category.value,
        "description": item.description,
        "source_type": item.source_type,
        "source_id": item.source_id,
        "is_active": item.is_active,
        "prices": {p.tier.value: float(p.price) for p in item.prices},
    }


@charge_router.put("/{item_id}")
async def update_charge_item(
    item_id: str,
    data: UpdateChargeItemRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Update a charge item (admin only)"""
    result = await db.execute(
        select(ChargeItem)
        .options(selectinload(ChargeItem.prices))
        .where(ChargeItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise NotFoundException("Charge item not found")

    if data.item_code is not None:
        item.item_code = data.item_code
    if data.name is not None:
        item.name = data.name
    if data.category is not None:
        item.category = ChargeCategory(data.category)
    if data.description is not None:
        item.description = data.description
    if data.source_type is not None:
        item.source_type = data.source_type
    if data.source_id is not None:
        item.source_id = data.source_id
    if data.is_active is not None:
        item.is_active = data.is_active
    
    if data.prices is not None:
        # Update or create prices
        existing_prices = {p.tier.value: p for p in item.prices}
        for tier_name, price in data.prices.items():
            if tier_name in existing_prices:
                existing_prices[tier_name].price = price
            else:
                price_obj = ChargePrice(
                    id=str(uuid.uuid4()),
                    item_id=item.id,
                    tier=ChargeTier(tier_name),
                    price=price,
                )
                db.add(price_obj)

    item_id = item.id  # Store ID before commit
    await db.commit()
    
    # Reload with prices
    result = await db.execute(
        select(ChargeItem)
        .options(selectinload(ChargeItem.prices))
        .where(ChargeItem.id == item_id)
    )
    item = result.scalar_one()
    
    return {
        "id": item.id,
        "item_code": item.item_code,
        "name": item.name,
        "category": item.category.value,
        "description": item.description,
        "source_type": item.source_type,
        "source_id": item.source_id,
        "is_active": item.is_active,
        "prices": {p.tier.value: float(p.price) for p in item.prices},
    }


@charge_router.delete("/{item_id}")
async def delete_charge_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Delete a charge item (admin only)"""
    result = await db.execute(select(ChargeItem).where(ChargeItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise NotFoundException("Charge item not found")

    await db.delete(item)
    await db.commit()
    return {"message": "Charge item deleted successfully"}
