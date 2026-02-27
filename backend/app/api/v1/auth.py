from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, date
import uuid

from app.database import get_db
from app.models.user import User, UserRole
from app.models.patient import Patient, EmergencyContact, Gender
from app.models.student import Student
from app.models.faculty import Faculty
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


def generate_patient_id():
    return f"PT{datetime.utcnow().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"


def generate_student_id():
    return f"ST{datetime.utcnow().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"


def generate_faculty_id():
    return f"FA{datetime.utcnow().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"


@router.post("/register", response_model=RegisterResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
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
        role=UserRole(request.role.value),
        is_active=True,
    )
    db.add(user)
    
    # Create role-specific record
    if request.role.value == "PATIENT" and request.patient_data:
        patient_id = str(uuid.uuid4())
        dob = datetime.strptime(request.patient_data.date_of_birth, "%Y-%m-%d").date()
        patient = Patient(
            id=patient_id,
            patient_id=generate_patient_id(),
            user_id=user_id,
            name=request.patient_data.name,
            date_of_birth=dob,
            gender=Gender(request.patient_data.gender),
            blood_group=request.patient_data.blood_group,
            phone=request.patient_data.phone,
            email=request.patient_data.email,
            address=request.patient_data.address or "",
            aadhaar_id=request.patient_data.aadhaar_id,
            abha_id=request.patient_data.abha_id,
        )
        db.add(patient)
        
        # Add emergency contact if provided
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
    
    elif request.role.value == "STUDENT" and request.student_data:
        student = Student(
            id=str(uuid.uuid4()),
            student_id=generate_student_id(),
            user_id=user_id,
            name=request.student_data.name,
            year=request.student_data.year,
            semester=request.student_data.semester,
            program=request.student_data.program,
            gpa=request.student_data.gpa,
            academic_advisor=request.student_data.academic_advisor,
        )
        db.add(student)
    
    elif request.role.value == "FACULTY" and request.faculty_data:
        faculty = Faculty(
            id=str(uuid.uuid4()),
            faculty_id=generate_faculty_id(),
            user_id=user_id,
            name=request.faculty_data.name,
            department=request.faculty_data.department,
            specialty=request.faculty_data.specialty,
            phone=request.faculty_data.phone,
            email=request.faculty_data.email,
        )
        db.add(faculty)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required data for role {request.role.value}",
        )
    
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
