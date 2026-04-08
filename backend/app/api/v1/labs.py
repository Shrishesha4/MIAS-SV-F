from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import uuid

from app.api.deps import get_db, get_current_user, require_role
from app.models.user import User, UserRole
from app.models.lab import Lab
from app.core.exceptions import NotFoundException

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
    """List all labs"""
    result = await db.execute(select(Lab).order_by(Lab.created_at.desc()))
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
