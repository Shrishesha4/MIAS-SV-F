"""Insurance categories and clinic configuration endpoints."""
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.insurance_category import (
    DEFAULT_INSURANCE_COLOR_PRIMARY,
    DEFAULT_INSURANCE_COLOR_SECONDARY,
    DEFAULT_INSURANCE_ICON_KEY,
    VALID_INSURANCE_ICON_KEYS,
    InsuranceCategory,
    InsuranceClinicConfig,
)
from app.models.patient import InsurancePolicy
from app.models.patient_category import PatientCategoryOption
from app.models.student import Clinic

router = APIRouter(prefix="/insurance-categories", tags=["Insurance Categories"])

# Default walk-in types - will be combined with dynamic types from insurance categories
DEFAULT_WALK_IN_TYPES = {
    "NO_WALK_IN": "No Walk In",
}

def generate_walk_in_type_value(category_name: str) -> str:
    """Generate a walk-in type value from category name."""
    return f"WALKIN_{category_name.upper().replace(' ', '_').replace('-', '_')}"

def generate_walk_in_type_label(category_name: str) -> str:
    """Generate a walk-in type label from category name."""
    return f"Walkin {category_name}"

async def get_walk_in_type_label(db: AsyncSession, walk_in_type: str) -> str:
    """Get the label for a walk-in type (dynamic lookup)."""
    if walk_in_type == "NO_WALK_IN":
        return "No Walk In"
    
    # Try to find matching patient category first
    if walk_in_type.startswith("WALKIN_"):
        category_part = walk_in_type[7:]  # Remove "WALKIN_" prefix
        patient_result = await db.execute(
            select(PatientCategoryOption).where(
                func.lower(PatientCategoryOption.name) == category_part.lower().replace("_", " ")
            )
        )
        patient_category = patient_result.scalar_one_or_none()
        if patient_category:
            return f"Walkin {patient_category.name}"

        # Legacy fallback: match insurance category names
        result = await db.execute(
            select(InsuranceCategory).where(
                func.lower(InsuranceCategory.name) == category_part.lower().replace("_", " ")
            )
        )
        cat = result.scalar_one_or_none()
        if cat:
            return f"Walkin {cat.name}"
    
    # Fallback to the raw value
    return walk_in_type


async def is_valid_walk_in_type(db: AsyncSession, walk_in_type: str) -> bool:
    if walk_in_type == "NO_WALK_IN":
        return True

    if not walk_in_type or not walk_in_type.startswith("WALKIN_"):
        return False

    normalized_name = walk_in_type.replace("WALKIN_", "").replace("_", " ").strip().lower()
    if not normalized_name:
        return False

    patient_category_result = await db.execute(
        select(PatientCategoryOption).where(func.lower(PatientCategoryOption.name) == normalized_name)
    )
    if patient_category_result.scalar_one_or_none():
        return True

    insurance_category_result = await db.execute(
        select(InsuranceCategory).where(func.lower(InsuranceCategory.name) == normalized_name)
    )
    return insurance_category_result.scalar_one_or_none() is not None


def _uid() -> str:
    return str(uuid4())


def _normalize_hex_color(value: Optional[str], default: str) -> str:
    normalized = str(value or default).strip().upper()
    if not normalized.startswith("#"):
        normalized = f"#{normalized}"
    if len(normalized) != 7 or any(ch not in "#0123456789ABCDEF" for ch in normalized):
        raise HTTPException(status_code=400, detail=f"Invalid hex color: {value}")
    return normalized


def _normalize_icon_key(value: Optional[str]) -> str:
    icon_key = str(value or DEFAULT_INSURANCE_ICON_KEY).strip().lower()
    if icon_key not in VALID_INSURANCE_ICON_KEYS:
        raise HTTPException(status_code=400, detail=f"Unsupported insurance icon: {value}")
    return icon_key


def _normalize_custom_badge_symbol(value: Optional[str]) -> Optional[str]:
    normalized = str(value or "").strip().upper()
    if not normalized:
        return None
    if len(normalized) > 3:
        raise HTTPException(status_code=400, detail="Custom badge symbol must be 1-3 characters")
    return normalized


# ── Pydantic Schemas ────────────────────────────────────────────────

class WalkInTypeInfo(BaseModel):
    value: str
    label: str


class ClinicConfigResponse(BaseModel):
    id: str
    clinic_id: str
    clinic_name: str
    clinic_walk_in_types: List[str]  # walk_in_types array from the clinic
    walk_in_type: str
    walk_in_label: str
    registration_fee: float
    is_enabled: bool


class PatientCategoryResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    is_active: bool


class InsuranceCategoryResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    icon_key: str
    custom_badge_symbol: Optional[str]
    color_primary: str
    color_secondary: str
    is_active: bool
    sort_order: int
    patient_categories: List[PatientCategoryResponse]
    clinic_configs: List[ClinicConfigResponse]


class InsuranceCategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon_key: Optional[str] = DEFAULT_INSURANCE_ICON_KEY
    custom_badge_symbol: Optional[str] = None
    color_primary: Optional[str] = DEFAULT_INSURANCE_COLOR_PRIMARY
    color_secondary: Optional[str] = DEFAULT_INSURANCE_COLOR_SECONDARY
    is_active: bool = True
    sort_order: Optional[int] = None
    patient_category_ids: Optional[List[str]] = None


class InsuranceCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon_key: Optional[str] = None
    custom_badge_symbol: Optional[str] = None
    color_primary: Optional[str] = None
    color_secondary: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    patient_category_ids: Optional[List[str]] = None


class ClinicConfigUpdate(BaseModel):
    walk_in_type: Optional[str] = None
    registration_fee: Optional[float] = None
    is_enabled: Optional[bool] = None


# ── Walk-in Type Endpoint ──────────────────────────────────────────

@router.get("/walk-in-types")
async def list_walk_in_types(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all available walk-in types dynamically from patient categories."""
    # Get all active patient categories
    result = await db.execute(
        select(PatientCategoryOption)
        .where(PatientCategoryOption.is_active == True)
        .order_by(PatientCategoryOption.sort_order, PatientCategoryOption.name)
    )
    categories = result.scalars().all()
    
    # Build dynamic walk-in types from categories
    walk_in_types = []
    
    # Always include NO_WALK_IN option
    walk_in_types.append(WalkInTypeInfo(value="NO_WALK_IN", label="No Walk In"))
    
    # Generate walk-in types from each patient category
    for cat in categories:
        value = generate_walk_in_type_value(cat.name)
        label = generate_walk_in_type_label(cat.name)
        walk_in_types.append(WalkInTypeInfo(value=value, label=label))
    
    return walk_in_types


# ── Insurance Category CRUD ───────────────────────────────────────

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
    """List all insurance categories with their clinic configurations and patient categories."""
    result = await db.execute(
        select(InsuranceCategory)
        .options(
            selectinload(InsuranceCategory.clinic_configs).selectinload(InsuranceClinicConfig.clinic),
            selectinload(InsuranceCategory.patient_categories)
        )
        .order_by(InsuranceCategory.sort_order, InsuranceCategory.name)
    )
    categories = result.scalars().all()
    
    response = []
    for cat in categories:
        clinic_configs = []
        for config in cat.clinic_configs:
            clinic_walk_in_types = []
            if config.clinic:
                clinic_walk_in_types = config.clinic.walk_in_types or []
            clinic_configs.append(ClinicConfigResponse(
                id=config.id,
                clinic_id=config.clinic_id,
                clinic_name=config.clinic.name if config.clinic else "Unknown",
                clinic_walk_in_types=clinic_walk_in_types,
                walk_in_type=config.walk_in_type,
                walk_in_label=await get_walk_in_type_label(db, config.walk_in_type),
                registration_fee=config.registration_fee,
                is_enabled=config.is_enabled,
            ))
        
        patient_categories = [
            PatientCategoryResponse(id=pc.id, name=pc.name, description=pc.description, is_active=pc.is_active)
            for pc in cat.patient_categories
        ]
        
        response.append(InsuranceCategoryResponse(
            id=cat.id,
            name=cat.name,
            description=cat.description,
            icon_key=cat.icon_key,
            custom_badge_symbol=cat.custom_badge_symbol,
            color_primary=cat.color_primary,
            color_secondary=cat.color_secondary,
            is_active=cat.is_active,
            sort_order=cat.sort_order,
            patient_categories=patient_categories,
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
    
    category = InsuranceCategory(
        id=_uid(),
        name=data.name,
        description=data.description,
        icon_key=_normalize_icon_key(data.icon_key),
        custom_badge_symbol=_normalize_custom_badge_symbol(data.custom_badge_symbol),
        color_primary=_normalize_hex_color(data.color_primary, DEFAULT_INSURANCE_COLOR_PRIMARY),
        color_secondary=_normalize_hex_color(data.color_secondary, DEFAULT_INSURANCE_COLOR_SECONDARY),
        is_active=data.is_active,
        sort_order=data.sort_order or 0,
    )
    db.add(category)
    await db.flush()  # get the ID without committing

    assigned_patient_category_ids: List[str] = []

    # Add patient categories if provided
    if data.patient_category_ids:
        for pc_id in data.patient_category_ids:
            patient_category = await db.execute(
                select(PatientCategoryOption).where(PatientCategoryOption.id == pc_id)
            )
            pc = patient_category.scalar_one_or_none()
            if pc:
                # Use explicit association insert to avoid lazy-loading the relationship
                from sqlalchemy import text as _text
                await db.execute(
                    _text("INSERT INTO insurance_patient_category_association (insurance_category_id, patient_category_id) VALUES (:iid, :pid) ON CONFLICT DO NOTHING"),
                    {"iid": category.id, "pid": pc.id},
                )
                assigned_patient_category_ids.append(pc.id)
    
    await db.commit()

    # Create default clinic configs
    await _create_default_clinic_configs(db, category.id)
    await db.commit()
    
    return {
        "id": category.id,
        "name": category.name,
        "description": category.description,
        "icon_key": category.icon_key,
        "custom_badge_symbol": category.custom_badge_symbol,
        "color_primary": category.color_primary,
        "color_secondary": category.color_secondary,
        "is_active": category.is_active,
        "sort_order": category.sort_order,
        "patient_category_ids": assigned_patient_category_ids,
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
        select(InsuranceCategory)
        .options(selectinload(InsuranceCategory.patient_categories))
        .where(InsuranceCategory.id == category_id)
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
    if data.icon_key is not None:
        category.icon_key = _normalize_icon_key(data.icon_key)
    if data.custom_badge_symbol is not None:
        category.custom_badge_symbol = _normalize_custom_badge_symbol(data.custom_badge_symbol)
    if data.color_primary is not None:
        category.color_primary = _normalize_hex_color(data.color_primary, DEFAULT_INSURANCE_COLOR_PRIMARY)
    if data.color_secondary is not None:
        category.color_secondary = _normalize_hex_color(data.color_secondary, DEFAULT_INSURANCE_COLOR_SECONDARY)
    if data.is_active is not None:
        category.is_active = data.is_active
        # When an insurance category is deactivated, disable all its clinic configs
        # so no walk-in slots are offered under this category.
        if not data.is_active:
            await db.execute(
                update(InsuranceClinicConfig)
                .where(InsuranceClinicConfig.insurance_category_id == category_id)
                .values(is_enabled=False)
            )
    if data.sort_order is not None:
        category.sort_order = data.sort_order
    
    patient_category_ids: List[str] = [pc.id for pc in category.patient_categories]

    # Handle patient categories update
    if data.patient_category_ids is not None:
        # Clear existing patient categories
        category.patient_categories.clear()
        patient_category_ids = []
        # Add new patient categories
        for pc_id in data.patient_category_ids:
            patient_category = await db.execute(
                select(PatientCategoryOption).where(PatientCategoryOption.id == pc_id)
            )
            pc = patient_category.scalar_one_or_none()
            if pc:
                category.patient_categories.append(pc)
                patient_category_ids.append(pc.id)

    await db.execute(
        update(InsurancePolicy)
        .where(InsurancePolicy.insurance_category_id == category_id)
        .values(
            provider=category.name,
            coverage_type=category.name,
            icon_key=category.icon_key,
            custom_badge_symbol=category.custom_badge_symbol,
            color_primary=category.color_primary,
            color_secondary=category.color_secondary,
        )
    )
    
    await db.commit()
    
    return {
        "id": category.id,
        "name": category.name,
        "description": category.description,
        "icon_key": category.icon_key,
        "custom_badge_symbol": category.custom_badge_symbol,
        "color_primary": category.color_primary,
        "color_secondary": category.color_secondary,
        "is_active": category.is_active,
        "sort_order": category.sort_order,
        "patient_category_ids": patient_category_ids,
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
        if not await is_valid_walk_in_type(db, data.walk_in_type):
            raise HTTPException(status_code=400, detail=f"Invalid walk-in type: {data.walk_in_type}")
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
        "walk_in_label": await get_walk_in_type_label(db, config.walk_in_type),
        "registration_fee": config.registration_fee,
        "is_enabled": config.is_enabled,
        "message": "Clinic configuration updated successfully",
    }


# ── Public Endpoints for Registration ───────────────────────────────

@router.get("/public")
async def list_public_insurance_categories(
    db: AsyncSession = Depends(get_db),
):
    """List active insurance categories with their patient categories for public registration (no auth required)."""
    result = await db.execute(
        select(InsuranceCategory)
        .options(selectinload(InsuranceCategory.patient_categories))
        .where(InsuranceCategory.is_active == True)
        .order_by(InsuranceCategory.sort_order, InsuranceCategory.name)
    )
    categories = result.scalars().all()
    
    return [
        {
            "id": cat.id,
            "name": cat.name,
            "description": cat.description,
            "icon_key": cat.icon_key,
            "custom_badge_symbol": cat.custom_badge_symbol,
            "color_primary": cat.color_primary,
            "color_secondary": cat.color_secondary,
            "patient_categories": [
                {
                    "id": pc.id,
                    "name": pc.name,
                    "description": pc.description,
                    "is_active": pc.is_active,
                }
                for pc in cat.patient_categories
            ]
        }
        for cat in categories
    ]


@router.get("/clinic-config/by-clinic")
@router.get("/clinic-config")
async def get_clinic_config_by_clinic(
    category_id: str = Query(...),
    clinic_id: str = Query(...),
    walk_in_type: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get clinic configuration by category ID and clinic ID (for admin panel)."""
    query = (
        select(InsuranceClinicConfig)
        .where(InsuranceClinicConfig.insurance_category_id == category_id)
        .where(InsuranceClinicConfig.clinic_id == clinic_id)
    )
    if walk_in_type:
        query = query.where(InsuranceClinicConfig.walk_in_type == walk_in_type)

    result = await db.execute(query)
    config = result.scalar_one_or_none()
    
    if not config:
        # Get clinic and category names for response
        clinic_result = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
        clinic = clinic_result.scalar_one_or_none()
        
        cat_result = await db.execute(select(InsuranceCategory).where(InsuranceCategory.id == category_id))
        category = cat_result.scalar_one_or_none()
        
        # Return a default config (not yet saved)
        return {
            "id": None,
            "insurance_category_id": category_id,
            "clinic_id": clinic_id,
            "clinic_name": clinic.name if clinic else "Unknown",
            "walk_in_type": walk_in_type or (generate_walk_in_type_value(category.name) if category else "WALKIN_CLASSIC"),
            "walk_in_label": await get_walk_in_type_label(db, walk_in_type or (generate_walk_in_type_value(category.name) if category else "WALKIN_CLASSIC")),
            "registration_fee": 100,
            "is_enabled": True,
            "exists": False,
        }
    
    clinic_result = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = clinic_result.scalar_one_or_none()
    
    return {
        "id": config.id,
        "insurance_category_id": config.insurance_category_id,
        "clinic_id": config.clinic_id,
        "clinic_name": clinic.name if clinic else "Unknown",
        "walk_in_type": config.walk_in_type,
        "walk_in_label": await get_walk_in_type_label(db, config.walk_in_type),
        "registration_fee": config.registration_fee,
        "is_enabled": config.is_enabled,
        "exists": True,
    }


@router.patch("/clinic-config/by-clinic")
@router.patch("/clinic-config")
async def update_clinic_config_by_clinic(
    data: ClinicConfigUpdate,
    category_id: str = Query(...),
    clinic_id: str = Query(...),
    walk_in_type: Optional[str] = Query(None),
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Update or create clinic configuration by category ID and clinic ID."""
    resolved_walk_in_type = walk_in_type or data.walk_in_type
    query = (
        select(InsuranceClinicConfig)
        .where(InsuranceClinicConfig.insurance_category_id == category_id)
        .where(InsuranceClinicConfig.clinic_id == clinic_id)
    )
    if resolved_walk_in_type:
        query = query.where(InsuranceClinicConfig.walk_in_type == resolved_walk_in_type)

    result = await db.execute(query)
    config = result.scalar_one_or_none()
    
    if not config:
        # Create new config
        config = InsuranceClinicConfig(
            id=_uid(),
            insurance_category_id=category_id,
            clinic_id=clinic_id,
            walk_in_type=resolved_walk_in_type or "WALKIN_CLASSIC",
            registration_fee=data.registration_fee if data.registration_fee is not None else 100,
            is_enabled=data.is_enabled if data.is_enabled is not None else True,
        )
        db.add(config)
    else:
        # Update existing
        if data.walk_in_type is not None:
            if not await is_valid_walk_in_type(db, data.walk_in_type):
                raise HTTPException(status_code=400, detail=f"Invalid walk-in type: {data.walk_in_type}")
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
    clinic_result = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = clinic_result.scalar_one_or_none()
    
    return {
        "id": config.id,
        "insurance_category_id": config.insurance_category_id,
        "clinic_id": config.clinic_id,
        "clinic_name": clinic.name if clinic else "Unknown",
        "walk_in_type": config.walk_in_type,
        "walk_in_label": await get_walk_in_type_label(db, config.walk_in_type),
        "registration_fee": config.registration_fee,
        "is_enabled": config.is_enabled,
        "message": "Clinic configuration saved successfully",
    }


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
            "walk_in_label": await get_walk_in_type_label(db, config.walk_in_type),
            "registration_fee": config.registration_fee,
        }
        for config in configs
    ]
