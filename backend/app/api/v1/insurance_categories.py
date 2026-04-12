"""Insurance categories and clinic configuration endpoints."""
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.insurance_category import InsuranceCategory, InsuranceClinicConfig
from app.models.student import Clinic

router = APIRouter(prefix="/insurance-categories", tags=["Insurance Categories"])

# Valid walk-in types
WALK_IN_TYPES = {
    "NO_WALK_IN": "No Walk In",
    "WALKIN_PRIME": "Walkin Prime",
    "WALKIN_CLASSIC": "Walkin Classic",
    "WALKIN_CAMP": "Walkin Camp",
    "WALKIN_ELITE": "Walk in Elite",
}


def _uid() -> str:
    return str(uuid4())


# ── Pydantic Schemas ────────────────────────────────────────────────

class WalkInTypeInfo(BaseModel):
    value: str
    label: str


class ClinicConfigResponse(BaseModel):
    id: str
    clinic_id: str
    clinic_name: str
    walk_in_type: str
    walk_in_label: str
    registration_fee: float
    is_enabled: bool


class InsuranceCategoryResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    is_active: bool
    is_default: bool
    sort_order: int
    clinic_configs: List[ClinicConfigResponse]


class InsuranceCategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True
    is_default: bool = False
    sort_order: Optional[int] = None


class InsuranceCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    sort_order: Optional[int] = None


class ClinicConfigUpdate(BaseModel):
    walk_in_type: Optional[str] = None
    registration_fee: Optional[float] = None
    is_enabled: Optional[bool] = None


# ── Walk-in Type Endpoint ──────────────────────────────────────────

@router.get("/walk-in-types")
async def list_walk_in_types(
    user: User = Depends(get_current_user),
):
    """List all available walk-in types for clinic configuration."""
    return [
        WalkInTypeInfo(value=k, label=v)
        for k, v in WALK_IN_TYPES.items()
    ]


# ── Insurance Category CRUD ───────────────────────────────────────

async def ensure_default_insurance_category(db: AsyncSession) -> InsuranceCategory:
    """Ensure at least one default insurance category exists."""
    result = await db.execute(
        select(InsuranceCategory).where(InsuranceCategory.is_default == True)
    )
    default = result.scalar_one_or_none()
    
    if not default:
        # Check if any categories exist
        result = await db.execute(select(InsuranceCategory))
        categories = result.scalars().all()
        
        if not categories:
            # Create default categories
            default_categories = [
                InsuranceCategory(
                    id=_uid(),
                    name="CM Scheme",
                    description="Chief Minister Health Scheme",
                    is_active=True,
                    is_default=True,
                    sort_order=0,
                ),
                InsuranceCategory(
                    id=_uid(),
                    name="Private Insurance",
                    description="Private health insurance policies",
                    is_active=True,
                    is_default=False,
                    sort_order=1,
                ),
                InsuranceCategory(
                    id=_uid(),
                    name="Self Pay",
                    description="Direct payment by patient",
                    is_active=True,
                    is_default=False,
                    sort_order=2,
                ),
            ]
            for cat in default_categories:
                db.add(cat)
            await db.commit()
            
            # Create clinic configs for each category
            for cat in default_categories:
                await _create_default_clinic_configs(db, cat.id)
            await db.commit()
            
            return default_categories[0]
        else:
            # Make first category default
            first = categories[0]
            first.is_default = True
            await db.commit()
            return first
    
    return default


async def _create_default_clinic_configs(db: AsyncSession, category_id: str):
    """Create default clinic configurations for a new insurance category."""
    clinics_result = await db.execute(select(Clinic))
    clinics = clinics_result.scalars().all()
    
    for clinic in clinics:
        config = InsuranceClinicConfig(
            id=_uid(),
            insurance_category_id=category_id,
            clinic_id=clinic.id,
            walk_in_type="WALKIN_CLASSIC" if clinic.access_mode == "WALK_IN" else "NO_WALK_IN",
            registration_fee=100.0,
            is_enabled=True,
        )
        db.add(config)


@router.get("")
async def list_insurance_categories(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all insurance categories with their clinic configurations."""
    await ensure_default_insurance_category(db)
    
    result = await db.execute(
        select(InsuranceCategory)
        .options(selectinload(InsuranceCategory.clinic_configs).selectinload(InsuranceClinicConfig.clinic))
        .order_by(InsuranceCategory.sort_order, InsuranceCategory.name)
    )
    categories = result.scalars().all()
    
    response = []
    for cat in categories:
        clinic_configs = []
        for config in cat.clinic_configs:
            clinic_configs.append(ClinicConfigResponse(
                id=config.id,
                clinic_id=config.clinic_id,
                clinic_name=config.clinic.name if config.clinic else "Unknown",
                walk_in_type=config.walk_in_type,
                walk_in_label=WALK_IN_TYPES.get(config.walk_in_type, config.walk_in_type),
                registration_fee=config.registration_fee,
                is_enabled=config.is_enabled,
            ))
        
        response.append(InsuranceCategoryResponse(
            id=cat.id,
            name=cat.name,
            description=cat.description,
            is_active=cat.is_active,
            is_default=cat.is_default,
            sort_order=cat.sort_order,
            clinic_configs=clinic_configs,
        ))
    
    return response


@router.post("", status_code=201)
async def create_insurance_category(
    data: InsuranceCategoryCreate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new insurance category (admin only)."""
    # Check for duplicate name
    existing = await db.execute(
        select(InsuranceCategory).where(func.lower(InsuranceCategory.name) == data.name.lower())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Insurance category name already exists")
    
    # If setting as default, clear other defaults
    if data.is_default:
        await db.execute(
            select(InsuranceCategory).where(InsuranceCategory.is_default == True)
        )
        await db.execute(
            update(InsuranceCategory).where(InsuranceCategory.is_default == True).values(is_default=False)
        )
    
    category = InsuranceCategory(
        id=_uid(),
        name=data.name,
        description=data.description,
        is_active=data.is_active,
        is_default=data.is_default,
        sort_order=data.sort_order or 0,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    
    # Create default clinic configs
    await _create_default_clinic_configs(db, category.id)
    await db.commit()
    
    return {
        "id": category.id,
        "name": category.name,
        "description": category.description,
        "is_active": category.is_active,
        "is_default": category.is_default,
        "sort_order": category.sort_order,
        "message": "Insurance category created successfully",
    }


@router.patch("/{category_id}")
async def update_insurance_category(
    category_id: str,
    data: InsuranceCategoryUpdate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Update an insurance category (admin only)."""
    result = await db.execute(
        select(InsuranceCategory).where(InsuranceCategory.id == category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Insurance category not found")
    
    if data.name is not None and data.name != category.name:
        existing = await db.execute(
            select(InsuranceCategory)
            .where(func.lower(InsuranceCategory.name) == data.name.lower())
            .where(InsuranceCategory.id != category_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Insurance category name already exists")
        category.name = data.name
    
    if data.description is not None:
        category.description = data.description
    if data.is_active is not None:
        category.is_active = data.is_active
    if data.sort_order is not None:
        category.sort_order = data.sort_order
    
    # Handle default status change
    if data.is_default is True:
        await db.execute(
            select(InsuranceCategory).where(
                and_(InsuranceCategory.is_default == True, InsuranceCategory.id != category_id)
            )
        )
        await db.execute(
            update(InsuranceCategory)
            .where(InsuranceCategory.is_default == True)
            .where(InsuranceCategory.id != category_id)
            .values(is_default=False)
        )
        category.is_default = True
    
    await db.commit()
    await db.refresh(category)
    
    return {
        "id": category.id,
        "name": category.name,
        "description": category.description,
        "is_active": category.is_active,
        "is_default": category.is_default,
        "sort_order": category.sort_order,
        "message": "Insurance category updated successfully",
    }


@router.delete("/{category_id}")
async def delete_insurance_category(
    category_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Delete an insurance category (admin only)."""
    result = await db.execute(
        select(InsuranceCategory).where(InsuranceCategory.id == category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Insurance category not found")
    
    await db.delete(category)
    await db.commit()
    
    return {"message": f"Insurance category '{category.name}' deleted successfully"}


# ── Clinic Configuration Endpoints ─────────────────────────────────

@router.patch("/{category_id}/clinics/{config_id}")
async def update_clinic_config(
    category_id: str,
    config_id: str,
    data: ClinicConfigUpdate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Update a clinic configuration for an insurance category (admin only)."""
    result = await db.execute(
        select(InsuranceClinicConfig)
        .where(InsuranceClinicConfig.id == config_id)
        .where(InsuranceClinicConfig.insurance_category_id == category_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Clinic configuration not found")
    
    if data.walk_in_type is not None:
        if data.walk_in_type not in WALK_IN_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid walk-in type. Must be one of: {', '.join(WALK_IN_TYPES.keys())}")
        config.walk_in_type = data.walk_in_type
    
    if data.registration_fee is not None:
        if data.registration_fee < 0:
            raise HTTPException(status_code=400, detail="Registration fee cannot be negative")
        config.registration_fee = data.registration_fee
    
    if data.is_enabled is not None:
        config.is_enabled = data.is_enabled
    
    await db.commit()
    await db.refresh(config)
    
    # Get clinic name for response
    clinic_result = await db.execute(select(Clinic).where(Clinic.id == config.clinic_id))
    clinic = clinic_result.scalar_one_or_none()
    
    return {
        "id": config.id,
        "clinic_id": config.clinic_id,
        "clinic_name": clinic.name if clinic else "Unknown",
        "walk_in_type": config.walk_in_type,
        "walk_in_label": WALK_IN_TYPES.get(config.walk_in_type, config.walk_in_type),
        "registration_fee": config.registration_fee,
        "is_enabled": config.is_enabled,
        "message": "Clinic configuration updated successfully",
    }


# ── Public Endpoints for Registration ───────────────────────────────

@router.get("/public/list")
async def list_public_insurance_categories(
    db: AsyncSession = Depends(get_db),
):
    """List active insurance categories for public registration (no auth required)."""
    await ensure_default_insurance_category(db)
    
    result = await db.execute(
        select(InsuranceCategory)
        .where(InsuranceCategory.is_active == True)
        .order_by(InsuranceCategory.sort_order, InsuranceCategory.name)
    )
    categories = result.scalars().all()
    
    return [
        {
            "id": cat.id,
            "name": cat.name,
            "description": cat.description,
            "is_default": cat.is_default,
        }
        for cat in categories
    ]


@router.get("/public/{category_id}/clinics")
async def get_category_clinics(
    category_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get available clinics for a specific insurance category (no auth required)."""
    result = await db.execute(
        select(InsuranceClinicConfig)
        .options(selectinload(InsuranceClinicConfig.clinic))
        .where(InsuranceClinicConfig.insurance_category_id == category_id)
        .where(InsuranceClinicConfig.is_enabled == True)
        .join(Clinic, InsuranceClinicConfig.clinic_id == Clinic.id)
        .where(Clinic.is_active == True)
    )
    configs = result.scalars().all()
    
    return [
        {
            "config_id": config.id,
            "clinic_id": config.clinic_id,
            "clinic_name": config.clinic.name if config.clinic else "Unknown",
            "clinic_type": config.clinic.clinic_type if config.clinic else None,
            "department": config.clinic.department if config.clinic else None,
            "location": config.clinic.location if config.clinic else None,
            "walk_in_type": config.walk_in_type,
            "walk_in_label": WALK_IN_TYPES.get(config.walk_in_type, config.walk_in_type),
            "registration_fee": config.registration_fee,
        }
        for config in configs
    ]
