from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, date
import uuid

from app.database import get_db
from app.models.user import User, UserRole
from app.models.patient import Patient, EmergencyContact, Gender
from app.models.department import Department
from app.models.programme import Programme
from app.models.student import Clinic
from app.models.insurance_category import InsuranceClinicConfig
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
from app.services.patient_categories import get_default_patient_category_name

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


def patient_category_to_walk_in_type(patient_category: str | None) -> str | None:
    if not patient_category:
        return None
    normalized = patient_category.strip().upper().replace(" ", "_").replace("-", "_")
    if not normalized:
        return None
    if normalized.startswith("WALKIN_"):
        return normalized
    return f"WALKIN_{normalized}"


async def allocate_clinic_sequentially(
    db: AsyncSession,
    patient_category: str,
    insurance_category_id: str | None = None,
) -> str:
    """Allocate a clinic sequentially by patient type + scheme, then fallback safely."""
    clinics = []
    walk_in_type = patient_category_to_walk_in_type(patient_category)

    # Prefer active clinics configured for selected insurance + selected patient type
    if insurance_category_id:
        configured_clinics_result = await db.execute(
            select(Clinic)
            .join(InsuranceClinicConfig, InsuranceClinicConfig.clinic_id == Clinic.id)
            .where(InsuranceClinicConfig.insurance_category_id == insurance_category_id)
            .where(InsuranceClinicConfig.is_enabled == True)
            .where(InsuranceClinicConfig.walk_in_type == walk_in_type)
            .where(Clinic.is_active == True)
        )
        clinics = configured_clinics_result.scalars().all()

        # Fallback to any active clinics configured for the selected insurance
        if not clinics:
            configured_clinics_result = await db.execute(
                select(Clinic)
                .join(InsuranceClinicConfig, InsuranceClinicConfig.clinic_id == Clinic.id)
                .where(InsuranceClinicConfig.insurance_category_id == insurance_category_id)
                .where(InsuranceClinicConfig.is_enabled == True)
                .where(Clinic.is_active == True)
            )
            clinics = configured_clinics_result.scalars().all()

    # Fallback: all active clinics
    if not clinics:
        clinics_result = await db.execute(
            select(Clinic).where(Clinic.is_active == True)
        )
        clinics = clinics_result.scalars().all()
    
    if not clinics:
        return None  # No clinics available
    
    # Count patients per clinic for the given category
    clinic_counts = {}
    for clinic in clinics:
        count_result = await db.execute(
            select(func.count(Patient.id))
            .where(Patient.clinic_id == clinic.id)
            .where(Patient.category == patient_category)
        )
        clinic_counts[clinic.id] = count_result.scalar() or 0
    
    # Allocate to clinic with fewest patients in this category
    allocated_clinic_id = min(clinic_counts, key=clinic_counts.get)
    
    return allocated_clinic_id


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
    # Use provided category or default to first active category
    patient_category = request.patient_data.category if request.patient_data.category else await get_default_patient_category_name(db)
    
    # Sequential clinic allocation based on patient category
    allocated_clinic_id = await allocate_clinic_sequentially(
        db,
        patient_category,
        request.patient_data.insurance_category_id,
    )
    
    patient = Patient(
        id=patient_id,
        patient_id=generate_patient_id(),
        user_id=user_id,
        clinic_id=allocated_clinic_id,
        name=request.patient_data.name,
        date_of_birth=dob,
        gender=Gender(request.patient_data.gender),
        blood_group=request.patient_data.blood_group,
        phone=request.patient_data.phone,
        email=request.patient_data.email,
        address=request.patient_data.address or "",
        aadhaar_id=request.patient_data.aadhaar_id,
        abha_id=request.patient_data.abha_id,
        category=patient_category,
    )
    db.add(patient)

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
    
    # Get clinic name if allocated
    clinic_name = None
    if allocated_clinic_id:
        clinic_result = await db.execute(
            select(Clinic).where(Clinic.id == allocated_clinic_id)
        )
        clinic = clinic_result.scalar_one_or_none()
        if clinic:
            clinic_name = clinic.name
    
    return RegisterResponse(
        message="Registration successful",
        user_id=user_id,
        clinic_id=allocated_clinic_id,
        clinic_name=clinic_name,
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
