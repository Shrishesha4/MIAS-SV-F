from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, date
import uuid

from app.database import get_db
from app.models.insurance_category import InsuranceCategory
from app.models.user import User, UserRole
from app.models.patient import Patient, EmergencyContact, Gender, InsurancePolicy
from app.models.department import Department
from app.models.patient_category import PatientCategoryOption, get_default_patient_category_colors
from app.models.programme import Programme
from app.services.clinic_allocation import resolve_preferred_clinic
from app.schemas.auth import (
    LoginRequest, TokenResponse, RefreshRequest,
    RegisterRequest, RegisterResponse
)
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Public endpoints for registration dropdowns ─────────────────────


@router.get("/departments")
async def get_registration_departments(db: AsyncSession = Depends(get_db)):
    """Public endpoint: list active departments for registration form."""
    result = await db.execute(
        select(Department)
        .where(Department.is_active == True)
        .order_by(Department.name)
    )
    departments = result.scalars().all()
    return [{"id": d.id, "name": d.name, "code": d.code} for d in departments]


@router.get("/programmes")
async def get_registration_programmes(db: AsyncSession = Depends(get_db)):
    """Public endpoint: list active programmes for registration form."""
    result = await db.execute(
        select(Programme)
        .where(Programme.is_active == True)
        .order_by(Programme.name)
    )
    programmes = result.scalars().all()
    return [
        {"id": p.id, "name": p.name, "code": p.code, "degree_type": p.degree_type}
        for p in programmes
    ]


def generate_patient_id():
    return f"PT{datetime.utcnow().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"


@router.post("/register", response_model=RegisterResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if request.role != request.role.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public registration is available for patients only",
        )

    # Check if username exists
    result = await db.execute(
        select(User).where(User.username == request.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )
    
    # Check if email exists
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists",
        )
    
    # Create user
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        username=request.username,
        email=request.email,
        password_hash=get_password_hash(request.password),
        role=UserRole.PATIENT,
        is_active=True,
    )
    db.add(user)
    
    if not request.patient_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient registration data is required",
        )

    patient_id = str(uuid.uuid4())
    dob = datetime.strptime(request.patient_data.date_of_birth, "%Y-%m-%d").date()
    display_patient_id = generate_patient_id()

    insurance_category = None
    if request.patient_data.insurance_category_id:
        insurance_category = (
            await db.execute(
                select(InsuranceCategory)
                .options(selectinload(InsuranceCategory.patient_categories))
                .where(InsuranceCategory.id == request.patient_data.insurance_category_id)
            )
        ).scalar_one_or_none()
        if not insurance_category or not insurance_category.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected insurance category is invalid",
            )

    resolved_patient_category = None
    if request.patient_data.patient_category_id:
        resolved_patient_category = (
            await db.execute(
                select(PatientCategoryOption).where(PatientCategoryOption.id == request.patient_data.patient_category_id)
            )
        ).scalar_one_or_none()
        if not resolved_patient_category or not resolved_patient_category.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected patient category is invalid",
            )
        if insurance_category and insurance_category.patient_categories:
            allowed_ids = {category.id for category in insurance_category.patient_categories}
            if resolved_patient_category.id not in allowed_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selected patient category is not allowed for this insurance category",
                )
    elif insurance_category and insurance_category.patient_categories:
        resolved_patient_category = insurance_category.patient_categories[0]

    resolved_category_name = (
        resolved_patient_category.name
        if resolved_patient_category
        else (request.patient_data.category or "Classic")
    )
    category_color_primary, category_color_secondary = (
        (resolved_patient_category.color_primary, resolved_patient_category.color_secondary)
        if resolved_patient_category
        else get_default_patient_category_colors(resolved_category_name)
    )
    preferred_clinic = await resolve_preferred_clinic(
        db,
        insurance_category_id=insurance_category.id if insurance_category else None,
        patient_category_name=resolved_category_name,
    )

    patient = Patient(
        id=patient_id,
        patient_id=display_patient_id,
        user_id=user_id,
        name=request.patient_data.name,
        date_of_birth=dob,
        gender=Gender(request.patient_data.gender),
        blood_group=request.patient_data.blood_group,
        phone=request.patient_data.phone,
        email=request.patient_data.email,
        address=request.patient_data.address or "",
        photo=request.patient_data.photo,
        aadhaar_id=request.patient_data.aadhaar_id,
        abha_id=request.patient_data.abha_id,
        category=resolved_category_name,
        category_color_primary=category_color_primary,
        category_color_secondary=category_color_secondary,
        clinic_id=preferred_clinic.id if preferred_clinic else None,
    )
    db.add(patient)

    if insurance_category:
        db.add(
            InsurancePolicy(
                id=str(uuid.uuid4()),
                patient_id=patient_id,
                insurance_category_id=insurance_category.id,
                provider=insurance_category.name,
                policy_number=f"REG-{display_patient_id}",
                coverage_type=insurance_category.name,
                icon_key=insurance_category.icon_key,
                custom_badge_symbol=insurance_category.custom_badge_symbol,
                color_primary=insurance_category.color_primary,
                color_secondary=insurance_category.color_secondary,
            )
        )

    if request.patient_data.emergency_contact:
        ec = request.patient_data.emergency_contact
        emergency_contact = EmergencyContact(
            id=str(uuid.uuid4()),
            patient_id=patient_id,
            name=ec.name,
            relationship_=ec.relationship,
            phone=ec.phone,
        )
        db.add(emergency_contact)
    
    await db.commit()
    
    return RegisterResponse(
        message="Registration successful",
        user_id=user_id,
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.username == request.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled",
        )

    # Update last_login
    user.last_login = datetime.utcnow()
    await db.commit()

    access_token = create_access_token(
        {"sub": user.id, "role": user.role.value}
    )
    refresh_token = create_refresh_token({"sub": user.id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user_id=user.id,
        role=user.role.value,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest, db: AsyncSession = Depends(get_db)
):
    payload = decode_token(request.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    access_token = create_access_token(
        {"sub": user.id, "role": user.role.value}
    )
    new_refresh_token = create_refresh_token({"sub": user.id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        user_id=user.id,
        role=user.role.value,
    )


@router.post("/logout")
async def logout():
    return {"message": "Successfully logged out"}
