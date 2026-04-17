"""Admin panel API – dashboard, user management, departments, analytics."""
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, text, and_, or_, distinct, extract
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, date
from typing import Optional
from pydantic import BaseModel, EmailStr
import uuid

from app.database import get_db
from app.api.deps import require_role
from app.models.user import User, UserRole
from app.models.patient import Patient
from app.models.patient_category import PatientCategoryOption
from app.models.patient_category import (
    DEFAULT_PATIENT_CATEGORY_COLOR_PRIMARY,
    DEFAULT_PATIENT_CATEGORY_COLOR_SECONDARY,
    get_default_patient_category_colors,
)
from app.models.student import Student
from app.models.faculty import Faculty
from app.models.department import Department
from app.models.programme import Programme
from app.models.admission import Admission
from app.models.prescription import Prescription
from app.models.vital import Vital, VitalParameter
from app.models.icd_code import ICDCode
from app.models.medical_record import MedicalRecord
from app.models.case_record import CaseRecord, Approval, ApprovalStatus
from app.models.notification import PatientNotification
from app.models.nurse import Nurse
from app.models.billing import Billing
from app.core.security import get_password_hash
from app.models.lab import ChargePrice
from app.services.charge_sync import sync_charge_price_categories
from app.services.patient_categories import (
    ensure_patient_categories,
    get_default_patient_category_name,
    normalize_patient_category_name,
    patient_category_usage_counts,
)

router = APIRouter(prefix="/admin", tags=["Admin"])

# ── helpers ──────────────────────────────────────────────────────────


def _uid() -> str:
    return str(uuid.uuid4())


def _normalize_hex_color(value: Optional[str], default: str) -> str:
    normalized = str(value or default).strip().upper()
    if not normalized.startswith("#"):
        normalized = f"#{normalized}"
    if len(normalized) != 7 or any(ch not in "#0123456789ABCDEF" for ch in normalized):
        raise HTTPException(status_code=400, detail=f"Invalid hex color: {value}")
    return normalized


def _normalize_required_text(value: Optional[str], field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise HTTPException(status_code=400, detail=f"{field_name} is required")
    return normalized


def _normalize_icd_code(value: Optional[str]) -> str:
    normalized = _normalize_required_text(value, "ICD code").upper()
    if len(normalized) > 32:
        raise HTTPException(status_code=400, detail="ICD code is too long")
    return normalized


def _serialize_icd_code(item: ICDCode) -> dict:
    return {
        "id": item.id,
        "code": item.code,
        "description": item.description,
        "category": item.category,
        "is_active": item.is_active,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


# ── Dashboard Overview ───────────────────────────────────────────────


@router.get("/dashboard")
async def admin_dashboard(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Return high-level counts and recent activity for the admin dashboard."""
    total_patients = (await db.execute(select(func.count(Patient.id)))).scalar() or 0
    total_students = (await db.execute(select(func.count(Student.id)))).scalar() or 0
    total_faculty = (await db.execute(select(func.count(Faculty.id)))).scalar() or 0
    total_departments = (
        await db.execute(select(func.count(Department.id)).where(Department.is_active == True))
    ).scalar() or 0

    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    active_users = (
        await db.execute(select(func.count(User.id)).where(User.is_active == True))
    ).scalar() or 0
    blocked_users = total_users - active_users

    active_admissions = (
        await db.execute(
            select(func.count(Admission.id)).where(Admission.status == "Active")
        )
    ).scalar() or 0

    total_prescriptions = (await db.execute(select(func.count(Prescription.id)))).scalar() or 0

    pending_approvals = (
        await db.execute(
            select(func.count(Approval.id)).where(Approval.status == ApprovalStatus.PENDING)
        )
    ).scalar() or 0

    # Patient category breakdown
    category_result = await db.execute(
        select(Patient.category, func.count(Patient.id)).group_by(Patient.category)
    )
    patient_categories = {normalize_patient_category_name(row[0] or "UNKNOWN") or "UNKNOWN": row[1] for row in category_result.all()}

    # Recent registrations (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_registrations = (
        await db.execute(
            select(func.count(User.id)).where(User.created_at >= week_ago)
        )
    ).scalar() or 0

    return {
        "total_patients": total_patients,
        "total_students": total_students,
        "total_faculty": total_faculty,
        "total_departments": total_departments,
        "total_users": total_users,
        "active_users": active_users,
        "blocked_users": blocked_users,
        "active_admissions": active_admissions,
        "total_prescriptions": total_prescriptions,
        "pending_approvals": pending_approvals,
        "patient_categories": patient_categories,
        "recent_registrations": recent_registrations,
    }


# ── User Management ─────────────────────────────────────────────────


@router.get("/users")
async def list_users(
    role: Optional[str] = Query(None, description="Filter by role: PATIENT, STUDENT, FACULTY, ADMIN"),
    search: Optional[str] = Query(None, description="Search by username or email"),
    status_filter: Optional[str] = Query(None, alias="status", description="active or blocked"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """List all users with filtering, search and pagination."""
    query = select(User)

    if role:
        query = query.where(User.role == UserRole(role))
    if search:
        query = query.where(
            (User.username.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%"))
        )
    if status_filter == "active":
        query = query.where(User.is_active == True)
    elif status_filter == "blocked":
        query = query.where(User.is_active == False)

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    query = query.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    items = []
    for u in users:
        item = {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role.value,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "last_login": u.last_login.isoformat() if u.last_login else None,
        }
        # Attach name from role-specific table
        if u.role == UserRole.PATIENT:
            p = (await db.execute(select(Patient.name).where(Patient.user_id == u.id))).scalar()
            item["name"] = p or u.username
        elif u.role == UserRole.STUDENT:
            s = (await db.execute(select(Student.name).where(Student.user_id == u.id))).scalar()
            item["name"] = s or u.username
        elif u.role == UserRole.FACULTY:
            f = (await db.execute(select(Faculty.name).where(Faculty.user_id == u.id))).scalar()
            item["name"] = f or u.username
        else:
            item["name"] = u.username
        items.append(item)

    return {"items": items, "total": total, "page": page, "limit": limit}


@router.put("/users/{user_id}/block")
async def block_user(
    user_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Block (deactivate) a user."""
    target = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="Cannot block yourself")
    target.is_active = False
    await db.commit()
    return {"message": f"User {target.username} has been blocked", "is_active": False}


@router.put("/users/{user_id}/unblock")
async def unblock_user(
    user_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Unblock (reactivate) a user."""
    target = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    target.is_active = True
    await db.commit()
    return {"message": f"User {target.username} has been unblocked", "is_active": True}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user and all associated profile data (patient/student/faculty/nurse)."""
    from sqlalchemy.orm import selectinload
    from sqlalchemy.exc import IntegrityError
    
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.patient),
            selectinload(User.student),
            selectinload(User.faculty),
            selectinload(User.nurse)
        )
        .where(User.id == user_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    try:
        # Delete associated profile records first (foreign key constraints)
        if target.patient:
            await db.delete(target.patient)
        if target.student:
            await db.delete(target.student)
        if target.faculty:
            await db.delete(target.faculty)
        if target.nurse:
            await db.delete(target.nurse)
        
        await db.delete(target)
        await db.commit()
        return {"message": f"User {target.username} has been deleted"}
    except IntegrityError as e:
        await db.rollback()
        # Check if it's a foreign key constraint error
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        if "foreign key" in error_msg.lower() or "violates" in error_msg.lower():
            raise HTTPException(
                status_code=409,
                detail="Cannot delete user: they have associated records (admissions, appointments, etc.). Please delete those records first or deactivate the user instead."
            )
        raise HTTPException(status_code=500, detail=f"Database error: {error_msg}")


# ── Create User (Admin) ──────────────────────────────────────────────


class AdminCreateUserRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str
    name: Optional[str] = None
    photo: Optional[str] = None

    # PATIENT fields
    date_of_birth: Optional[str] = None  # YYYY-MM-DD
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    category: Optional[str] = None
    aadhaar_id: Optional[str] = None
    abha_id: Optional[str] = None
    primary_diagnosis: Optional[str] = None
    diagnosis_doctor: Optional[str] = None
    diagnosis_date: Optional[str] = None
    diagnosis_time: Optional[str] = None

    # STUDENT fields
    year: Optional[int] = None
    semester: Optional[int] = None
    program: Optional[str] = None
    degree: Optional[str] = None
    gpa: Optional[float] = None
    academic_standing: Optional[str] = None
    academic_advisor: Optional[str] = None

    # FACULTY / NURSE fields
    department: Optional[str] = None
    specialty: Optional[str] = None
    availability: Optional[str] = None

    # NURSE fields
    hospital: Optional[str] = None
    ward: Optional[str] = None
    shift: Optional[str] = None

    # BILLING fields
    counter_name: Optional[str] = None


def _generate_patient_id():
    return f"PT{datetime.utcnow().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"

def _generate_student_id():
    return f"ST{datetime.utcnow().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"

def _generate_faculty_id():
    return f"FA{datetime.utcnow().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"

def _generate_nurse_id():
    return f"NR{datetime.utcnow().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"

def _generate_billing_id():
    return f"BL{datetime.utcnow().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"


@router.post("/users", status_code=201)
async def admin_create_user(
    data: AdminCreateUserRequest,
    admin: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Admin creates a new user directly (no email verification required)."""
    username = data.username.strip()
    email = str(data.email).strip()

    # Check uniqueness
    if (await db.execute(select(User).where(User.username == username))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")
    if (await db.execute(select(User).where(User.email == email))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already exists")

    try:
        role = UserRole(data.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {data.role}")

    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        username=username,
        email=email,
        password_hash=get_password_hash(data.password),
        role=role,
        is_active=True,
    )
    db.add(user)

    name = (data.name or data.username).strip()

    if role == UserRole.PATIENT:
        if not data.date_of_birth:
            raise HTTPException(status_code=400, detail="Date of birth is required for patients")

        try:
            dob = datetime.strptime(data.date_of_birth, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Date of birth must be in YYYY-MM-DD format")

        from app.models.patient import Gender
        from app.services.clinic_allocation import resolve_preferred_clinic
        from app.services.clinic_intake import ensure_clinic_checkin

        resolved_category = normalize_patient_category_name(data.category) or await get_default_patient_category_name(db)
        new_patient = Patient(
            id=str(uuid.uuid4()),
            patient_id=_generate_patient_id(),
            user_id=user_id,
            name=name,
            date_of_birth=dob,
            gender=Gender(data.gender) if data.gender else Gender.OTHER,
            blood_group=data.blood_group or "Unknown",
            phone=data.phone or "",
            email=email,
            address=data.address or "",
            photo=data.photo,
            aadhaar_id=data.aadhaar_id,
            abha_id=data.abha_id,
            primary_diagnosis=data.primary_diagnosis,
            diagnosis_doctor=data.diagnosis_doctor,
            diagnosis_date=data.diagnosis_date,
            diagnosis_time=data.diagnosis_time,
            category=resolved_category,
        )
        db.add(new_patient)

        preferred_clinic = await resolve_preferred_clinic(
            db,
            insurance_category_id=None,
            patient_category_name=resolved_category,
        )
        if not preferred_clinic:
            from app.models.student import Clinic
            clinic_result = await db.execute(
                select(Clinic).where(Clinic.is_active == True).limit(1)
            )
            preferred_clinic = clinic_result.scalar_one_or_none()
        if preferred_clinic:
            await ensure_clinic_checkin(
                db,
                patient=new_patient,
                clinic=preferred_clinic,
                appointment_datetime=datetime.utcnow(),
                status="Scheduled",
            )
    elif role == UserRole.STUDENT:
        if data.year is None or data.semester is None or not data.program:
            raise HTTPException(status_code=400, detail="Year, semester, and program are required for students")

        db.add(Student(
            id=str(uuid.uuid4()),
            student_id=_generate_student_id(),
            user_id=user_id,
            name=name,
            year=data.year,
            semester=data.semester,
            program=data.program,
            degree=data.degree,
            photo=data.photo,
            gpa=data.gpa if data.gpa is not None else 0.0,
            academic_standing=data.academic_standing or "Good Standing",
            academic_advisor=data.academic_advisor,
        ))
    elif role == UserRole.FACULTY:
        if not data.department:
            raise HTTPException(status_code=400, detail="Department is required for faculty")

        db.add(Faculty(
            id=str(uuid.uuid4()),
            faculty_id=_generate_faculty_id(),
            user_id=user_id,
            name=name,
            department=data.department,
            specialty=data.specialty,
            phone=data.phone,
            email=email,
            photo=data.photo,
            availability=data.availability,
        ))
    elif role == UserRole.NURSE:
        db.add(Nurse(
            id=str(uuid.uuid4()),
            nurse_id=_generate_nurse_id(),
            user_id=user_id,
            name=name,
            phone=data.phone,
            email=email,
            photo=data.photo,
            hospital=data.hospital,
            ward=data.ward,
            shift=data.shift,
            department=data.department,
            has_selected_station=0,
        ))
    # ADMIN and RECEPTION roles: no extra profile record needed
    elif role == UserRole.BILLING:
        db.add(Billing(
            id=str(uuid.uuid4()),
            billing_id=_generate_billing_id(),
            user_id=user_id,
            name=name,
            phone=data.phone,
            email=email,
            counter_name=data.counter_name,
        ))
    # ADMIN and RECEPTION: no extra profile record needed

    await db.commit()
    return {"message": f"User {data.username} created successfully", "user_id": user_id}


# ── Bulk Import Users ─────────────────────────────────────────────────


@router.post("/users/bulk-import", status_code=200)
async def bulk_import_users(
    file: UploadFile = File(...),
    admin: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Bulk import users from a CSV or Excel (.xlsx) file."""
    import csv
    import io
    import openpyxl

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    filename_lower = file.filename.lower()
    content = await file.read()

    rows: list[dict] = []

    if filename_lower.endswith(".csv"):
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            rows.append({k.strip().lower(): (v.strip() if v else "") for k, v in row.items()})
    elif filename_lower.endswith(".xlsx") or filename_lower.endswith(".xls"):
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        headers = None
        for excel_row in ws.iter_rows(values_only=True):
            if headers is None:
                headers = [str(c).strip().lower() if c is not None else "" for c in excel_row]
                continue
            row_dict = {}
            for h, v in zip(headers, excel_row):
                row_dict[h] = str(v).strip() if v is not None else ""
            rows.append(row_dict)
        wb.close()
    else:
        raise HTTPException(status_code=400, detail="File must be .csv or .xlsx")

    results = []
    created = 0
    failed = 0

    for idx, row in enumerate(rows, start=2):
        row_num = idx
        username = row.get("username", "").strip()
        email = row.get("email", "").strip()
        password = row.get("password", "").strip()
        role_str = row.get("role", "").strip().upper()
        name = row.get("name", "").strip()

        if not username or not email or not password or not role_str:
            results.append({"row": row_num, "username": username or "(empty)", "status": "failed", "error": "username, email, password, role are required"})
            failed += 1
            continue

        try:
            role = UserRole(role_str)
        except ValueError:
            results.append({"row": row_num, "username": username, "status": "failed", "error": f"Invalid role: {role_str}"})
            failed += 1
            continue

        if (await db.execute(select(User).where(User.username == username))).scalar_one_or_none():
            results.append({"row": row_num, "username": username, "status": "failed", "error": "Username already exists"})
            failed += 1
            continue
        if (await db.execute(select(User).where(User.email == email))).scalar_one_or_none():
            results.append({"row": row_num, "username": username, "status": "failed", "error": "Email already exists"})
            failed += 1
            continue

        try:
            user_id = str(uuid.uuid4())
            new_user = User(
                id=user_id,
                username=username,
                email=email,
                password_hash=get_password_hash(password),
                role=role,
                is_active=True,
            )
            db.add(new_user)

            display_name = name or username

            if role == UserRole.PATIENT:
                dob_str = row.get("date_of_birth", "").strip()
                if not dob_str:
                    raise ValueError("date_of_birth is required for patients")
                try:
                    dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
                except ValueError:
                    raise ValueError("date_of_birth must be YYYY-MM-DD")
                from app.models.patient import Gender
                gender_str = row.get("gender", "OTHER").strip().upper()
                try:
                    gender = Gender(gender_str)
                except ValueError:
                    gender = Gender.OTHER
                db.add(Patient(
                    id=str(uuid.uuid4()),
                    patient_id=_generate_patient_id(),
                    user_id=user_id,
                    name=display_name,
                    date_of_birth=dob,
                    gender=gender,
                    blood_group=row.get("blood_group", "") or "Unknown",
                    phone=row.get("phone", "") or "",
                    email=email,
                    address=row.get("address", "") or "",
                    aadhaar_id=row.get("aadhaar_id") or None,
                    abha_id=row.get("abha_id") or None,
                    primary_diagnosis=row.get("primary_diagnosis") or None,
                    category=normalize_patient_category_name(row.get("category", "")) or await get_default_patient_category_name(db),
                ))
            elif role == UserRole.STUDENT:
                year_str = row.get("year", "").strip()
                semester_str = row.get("semester", "").strip()
                program = row.get("program", "").strip()
                if not year_str or not semester_str or not program:
                    raise ValueError("year, semester, program required for students")
                db.add(Student(
                    id=str(uuid.uuid4()),
                    student_id=_generate_student_id(),
                    user_id=user_id,
                    name=display_name,
                    year=int(year_str),
                    semester=int(semester_str),
                    program=program,
                    degree=row.get("degree") or None,
                    gpa=float(row.get("gpa") or 0),
                    academic_standing=row.get("academic_standing") or "Good Standing",
                    academic_advisor=row.get("academic_advisor") or None,
                ))
            elif role == UserRole.FACULTY:
                department = row.get("department", "").strip()
                if not department:
                    raise ValueError("department is required for faculty")
                db.add(Faculty(
                    id=str(uuid.uuid4()),
                    faculty_id=_generate_faculty_id(),
                    user_id=user_id,
                    name=display_name,
                    department=department,
                    specialty=row.get("specialty") or None,
                    phone=row.get("phone") or None,
                    email=email,
                    availability=row.get("availability") or None,
                ))
            elif role == UserRole.NURSE:
                db.add(Nurse(
                    id=str(uuid.uuid4()),
                    nurse_id=_generate_nurse_id(),
                    user_id=user_id,
                    name=display_name,
                    phone=row.get("phone") or None,
                    email=email,
                    hospital=row.get("hospital") or None,
                    ward=row.get("ward") or None,
                    shift=row.get("shift") or None,
                    department=row.get("department") or None,
                    has_selected_station=0,
                ))

            await db.flush()
            results.append({"row": row_num, "username": username, "status": "created"})
            created += 1

        except Exception as exc:
            await db.rollback()
            results.append({"row": row_num, "username": username, "status": "failed", "error": str(exc)})
            failed += 1
            continue

    await db.commit()
    return {
        "created": created,
        "failed": failed,
        "total": len(rows),
        "results": results,
    }


# ── Department Management ────────────────────────────────────────────


@router.get("/departments")
async def list_departments(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """List all departments with faculty counts."""
    result = await db.execute(
        select(Department).order_by(Department.name)
    )
    departments = result.scalars().all()

    items = []
    for dept in departments:
        # count faculty in this department
        fac_count = (
            await db.execute(
                select(func.count(Faculty.id)).where(Faculty.department == dept.name)
            )
        ).scalar() or 0

        # get head name
        head_name = None
        if dept.head_faculty_id:
            head = (
                await db.execute(select(Faculty.name).where(Faculty.id == dept.head_faculty_id))
            ).scalar()
            head_name = head

        items.append({
            "id": dept.id,
            "name": dept.name,
            "code": dept.code,
            "description": dept.description,
            "head_faculty_id": dept.head_faculty_id,
            "head_faculty_name": head_name,
            "is_active": dept.is_active,
            "faculty_count": fac_count,
            "created_at": dept.created_at.isoformat() if dept.created_at else None,
        })

    return items


@router.post("/departments", status_code=201)
async def create_department(
    body: dict,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new department."""
    name = body.get("name", "").strip()
    code = body.get("code", "").strip().upper()
    if not name or not code:
        raise HTTPException(status_code=400, detail="name and code are required")

    # uniqueness
    existing = (
        await db.execute(select(Department).where((Department.name == name) | (Department.code == code)))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Department name or code already exists")

    dept = Department(
        id=_uid(),
        name=name,
        code=code,
        description=body.get("description"),
        head_faculty_id=body.get("head_faculty_id"),
    )
    db.add(dept)
    await db.commit()
    await db.refresh(dept)

    return {
        "id": dept.id,
        "name": dept.name,
        "code": dept.code,
        "description": dept.description,
        "is_active": dept.is_active,
        "message": "Department created successfully",
    }


@router.put("/departments/{dept_id}")
async def update_department(
    dept_id: str,
    body: dict,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Update a department."""
    dept = (await db.execute(select(Department).where(Department.id == dept_id))).scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    if "name" in body:
        dept.name = body["name"]
    if "code" in body:
        dept.code = body["code"].upper()
    if "description" in body:
        dept.description = body["description"]
    if "head_faculty_id" in body:
        dept.head_faculty_id = body["head_faculty_id"]
    if "is_active" in body:
        dept.is_active = body["is_active"]

    await db.commit()
    return {"message": "Department updated", "id": dept.id, "name": dept.name}


@router.delete("/departments/{dept_id}")
async def delete_department(
    dept_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete (deactivate) a department."""
    dept = (await db.execute(select(Department).where(Department.id == dept_id))).scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    dept.is_active = False
    await db.commit()
    return {"message": f"Department '{dept.name}' deactivated"}


# ── Analytics / Trends ───────────────────────────────────────────────


@router.get("/analytics/trends")
async def analytics_trends(
    days: int = Query(30, ge=7, le=365),
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Return daily counts for patient registrations, admissions,
    prescriptions, and vitals over the last N days.
    """
    start = datetime.utcnow() - timedelta(days=days)

    async def daily_counts(model, date_col):
        rows = (
            await db.execute(
                select(
                    func.date(date_col).label("day"),
                    func.count().label("count"),
                )
                .where(date_col >= start)
                .group_by(func.date(date_col))
                .order_by(func.date(date_col))
            )
        ).all()
        return [{"date": str(r.day), "count": r.count} for r in rows]

    registrations = await daily_counts(Patient, Patient.created_at)
    admissions = await daily_counts(Admission, Admission.admission_date)
    prescriptions = await daily_counts(Prescription, Prescription.created_at)
    vitals = await daily_counts(Vital, Vital.recorded_at)

    return {
        "period_days": days,
        "registrations": registrations,
        "admissions": admissions,
        "prescriptions": prescriptions,
        "vitals": vitals,
    }


@router.get("/analytics/department-stats")
async def department_stats(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Faculty count and admission count per department."""
    # Get all unique departments from faculty
    dept_rows = (
        await db.execute(
            select(Faculty.department, func.count(Faculty.id).label("faculty_count"))
            .group_by(Faculty.department)
            .order_by(Faculty.department)
        )
    ).all()

    items = []
    for row in dept_rows:
        items.append({
            "department": row.department,
            "faculty_count": row.faculty_count,
        })
    return items


@router.get("/analytics/role-distribution")
async def role_distribution(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Count of users per role."""
    rows = (
        await db.execute(
            select(User.role, func.count(User.id)).group_by(User.role)
        )
    ).all()
    return {str(r[0].value): r[1] for r in rows}


# ── Faculty listing for admin ────────────────────────────────────────


@router.get("/faculty")
async def list_faculty(
    department: Optional[str] = None,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """List all faculty members (for assignment etc.)."""
    q = select(Faculty)
    if department:
        q = q.where(Faculty.department == department)
    q = q.order_by(Faculty.name)
    result = await db.execute(q)
    faculty_list = result.scalars().all()

    return [
        {
            "id": f.id,
            "faculty_id": f.faculty_id,
            "name": f.name,
            "department": f.department,
            "specialty": f.specialty,
            "availability_status": f.availability_status,
        }
        for f in faculty_list
    ]


# ── Students listing for admin ───────────────────────────────────────


@router.get("/students")
async def list_students(
    year: Optional[int] = None,
    program: Optional[str] = None,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """List all students."""
    q = select(Student)
    if year:
        q = q.where(Student.year == year)
    if program:
        q = q.where(Student.program == program)
    q = q.order_by(Student.name)
    result = await db.execute(q)
    students = result.scalars().all()

    return [
        {
            "id": s.id,
            "student_id": s.student_id,
            "name": s.name,
            "year": s.year,
            "semester": s.semester,
            "program": s.program,
            "gpa": s.gpa,
            "academic_standing": s.academic_standing,
        }
        for s in students
    ]


# ── Programme Management ─────────────────────────────────────────────


@router.get("/programmes")
async def list_programmes(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """List all programmes."""
    result = await db.execute(select(Programme).order_by(Programme.name))
    programmes = result.scalars().all()

    # Count students per programme
    items = []
    for p in programmes:
        student_count = (
            await db.execute(
                select(func.count(Student.id)).where(Student.program == p.name)
            )
        ).scalar() or 0
        items.append({
            "id": p.id,
            "name": p.name,
            "code": p.code,
            "description": p.description,
            "degree_type": p.degree_type,
            "duration_years": p.duration_years,
            "is_active": p.is_active,
            "student_count": student_count,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })
    return items


@router.post("/programmes", status_code=201)
async def create_programme(
    body: dict,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new programme."""
    name = body.get("name", "").strip()
    code = body.get("code", "").strip().upper()
    if not name or not code:
        raise HTTPException(status_code=400, detail="name and code are required")

    existing = (
        await db.execute(
            select(Programme).where((Programme.name == name) | (Programme.code == code))
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Programme name or code already exists")

    prog = Programme(
        id=_uid(),
        name=name,
        code=code,
        description=body.get("description"),
        degree_type=body.get("degree_type"),
        duration_years=body.get("duration_years"),
    )
    db.add(prog)
    await db.commit()
    await db.refresh(prog)

    return {
        "id": prog.id,
        "name": prog.name,
        "code": prog.code,
        "message": "Programme created successfully",
    }


@router.put("/programmes/{prog_id}")
async def update_programme(
    prog_id: str,
    body: dict,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Update a programme."""
    prog = (await db.execute(select(Programme).where(Programme.id == prog_id))).scalar_one_or_none()
    if not prog:
        raise HTTPException(status_code=404, detail="Programme not found")

    if "name" in body:
        prog.name = body["name"]
    if "code" in body:
        prog.code = body["code"].upper()
    if "description" in body:
        prog.description = body["description"]
    if "degree_type" in body:
        prog.degree_type = body["degree_type"]
    if "duration_years" in body:
        prog.duration_years = body["duration_years"]
    if "is_active" in body:
        prog.is_active = body["is_active"]

    await db.commit()
    return {"message": "Programme updated", "id": prog.id, "name": prog.name}


@router.delete("/programmes/{prog_id}")
async def delete_programme(
    prog_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete (deactivate) a programme."""
    prog = (await db.execute(select(Programme).where(Programme.id == prog_id))).scalar_one_or_none()
    if not prog:
        raise HTTPException(status_code=404, detail="Programme not found")
    prog.is_active = False
    await db.commit()
    return {"message": f"Programme '{prog.name}' deactivated"}


# ── System info ──────────────────────────────────────────────────────


@router.get("/system-info")
async def system_info(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Return system metadata."""
    return {
        "version": "1.0.0",
        "api": "MIAS-MP API",
        "database": "PostgreSQL 15",
        "status": "operational",
    }


class PatientCategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color_primary: Optional[str] = None
    color_secondary: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    registration_fee: Optional[int] = None


class PatientCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color_primary: Optional[str] = None
    color_secondary: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    registration_fee: Optional[int] = None


def _serialize_patient_category(item: PatientCategoryOption, usage_counts: dict[str, int]) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "color_primary": item.color_primary,
        "color_secondary": item.color_secondary,
        "is_active": item.is_active,
        "sort_order": item.sort_order,
        "registration_fee": item.registration_fee,
        "patient_count": usage_counts.get(item.name, 0),
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


@router.get("/patient-categories")
async def list_patient_categories(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    categories = await ensure_patient_categories(db)
    await db.commit()
    usage_counts = await patient_category_usage_counts(db)
    return [_serialize_patient_category(item, usage_counts) for item in categories]


@router.get("/patient-categories/public")
async def list_public_patient_categories(
    db: AsyncSession = Depends(get_db),
):
    """List active patient categories with pricing for public registration (no auth required)."""
    categories = await ensure_patient_categories(db)
    await db.commit()
    return [
        {
            "id": cat.id,
            "name": cat.name,
            "description": cat.description,
            "color_primary": cat.color_primary,
            "color_secondary": cat.color_secondary,
            "registration_fee": cat.registration_fee,
        }
        for cat in categories
        if cat.is_active
    ]


@router.post("/patient-categories", status_code=201)
async def create_patient_category(
    data: PatientCategoryCreate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    categories = await ensure_patient_categories(db)
    normalized_name = normalize_patient_category_name(data.name)
    if not normalized_name:
        raise HTTPException(status_code=400, detail="Category name is required")

    existing = (
        await db.execute(
            select(PatientCategoryOption).where(func.lower(PatientCategoryOption.name) == normalized_name.casefold())
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Category name already exists")

    item = PatientCategoryOption(
        id=_uid(),
        name=normalized_name,
        description=(data.description or "").strip() or None,
        color_primary=_normalize_hex_color(
            data.color_primary,
            get_default_patient_category_colors(normalized_name)[0],
        ),
        color_secondary=_normalize_hex_color(
            data.color_secondary,
            get_default_patient_category_colors(normalized_name)[1],
        ),
        is_active=data.is_active,
        sort_order=data.sort_order if data.sort_order is not None else len(categories),
        registration_fee=data.registration_fee if data.registration_fee is not None else 100,
    )
    db.add(item)
    await db.flush()
    await sync_charge_price_categories(db)
    await db.commit()
    usage_counts = await patient_category_usage_counts(db)
    return _serialize_patient_category(item, usage_counts)


@router.patch("/patient-categories/{category_id}")
async def update_patient_category(
    category_id: str,
    data: PatientCategoryUpdate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    item = (
        await db.execute(select(PatientCategoryOption).where(PatientCategoryOption.id == category_id))
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Patient category not found")

    if data.name is not None:
        previous_name = item.name
        normalized_name = normalize_patient_category_name(data.name)
        if not normalized_name:
            raise HTTPException(status_code=400, detail="Category name is required")

        existing = (
            await db.execute(
                select(PatientCategoryOption)
                .where(func.lower(PatientCategoryOption.name) == normalized_name.casefold())
                .where(PatientCategoryOption.id != item.id)
            )
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Category name already exists")

        await db.execute(
            text("UPDATE patients SET category = :new_name WHERE category = :old_name"),
            {"new_name": normalized_name, "old_name": item.name},
        )
        await db.execute(
            text("UPDATE charge_prices SET tier = :new_name WHERE lower(tier) = :old_name"),
            {"new_name": normalized_name, "old_name": previous_name.casefold()},
        )
        item.name = normalized_name

    if data.description is not None:
        item.description = data.description.strip() or None
    if data.color_primary is not None:
        item.color_primary = _normalize_hex_color(data.color_primary, DEFAULT_PATIENT_CATEGORY_COLOR_PRIMARY)
    if data.color_secondary is not None:
        item.color_secondary = _normalize_hex_color(data.color_secondary, DEFAULT_PATIENT_CATEGORY_COLOR_SECONDARY)
    if data.is_active is not None:
        item.is_active = data.is_active
    if data.sort_order is not None:
        item.sort_order = data.sort_order
    if data.registration_fee is not None:
        item.registration_fee = data.registration_fee

    await db.execute(
        text(
            "UPDATE patients SET category_color_primary = :color_primary, category_color_secondary = :color_secondary WHERE category = :category_name"
        ),
        {
            "category_name": item.name,
            "color_primary": item.color_primary,
            "color_secondary": item.color_secondary,
        },
    )

    await sync_charge_price_categories(db)
    await db.commit()
    usage_counts = await patient_category_usage_counts(db)
    return _serialize_patient_category(item, usage_counts)


@router.delete("/patient-categories/{category_id}")
async def delete_patient_category(
    category_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    item = (
        await db.execute(select(PatientCategoryOption).where(PatientCategoryOption.id == category_id))
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Patient category not found")

    usage_count = (
        await db.execute(select(func.count(Patient.id)).where(Patient.category == item.name))
    ).scalar() or 0
    if usage_count:
        raise HTTPException(status_code=409, detail="Cannot delete a category that is already assigned to patients")

    await db.execute(
        text("DELETE FROM charge_prices WHERE lower(tier) = :category_name"),
        {"category_name": item.name.casefold()},
    )
    await db.delete(item)
    await sync_charge_price_categories(db)
    await db.commit()
    return {"message": f"Patient category '{item.name}' deleted"}


# ── ICD Code Catalog ────────────────────────────────────────────────


class ICDCodeCreate(BaseModel):
    code: str
    description: str
    category: Optional[str] = "General"
    is_active: bool = True


class ICDCodeUpdate(BaseModel):
    code: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/icd-codes")
async def list_icd_codes(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = Query(None, description="Search by ICD code, description, or category"),
    include_inactive: bool = Query(True, description="Include inactive codes in the result"),
):
    query = select(ICDCode)
    if not include_inactive:
        query = query.where(ICDCode.is_active == True)

    if search:
        search_term = search.strip()
        like = f"%{search_term}%"
        prefix = f"{search_term}%"
        query = query.where(
            or_(
                ICDCode.code.ilike(like),
                ICDCode.description.ilike(like),
                ICDCode.category.ilike(like),
            )
        ).order_by(
            case(
                (ICDCode.code.ilike(prefix), 0),
                (ICDCode.description.ilike(prefix), 1),
                (ICDCode.category.ilike(prefix), 2),
                else_=3,
            ),
            ICDCode.code,
        )
    else:
        query = query.order_by(ICDCode.code)

    items = (await db.execute(query)).scalars().all()
    return [_serialize_icd_code(item) for item in items]


@router.post("/icd-codes", status_code=201)
async def create_icd_code(
    data: ICDCodeCreate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    code = _normalize_icd_code(data.code)
    description = _normalize_required_text(data.description, "Description")
    category = _normalize_required_text(data.category or "General", "Category")

    existing = (
        await db.execute(select(ICDCode).where(ICDCode.code == code))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail=f"ICD code '{code}' already exists")

    item = ICDCode(
        id=_uid(),
        code=code,
        description=description,
        category=category,
        is_active=data.is_active,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _serialize_icd_code(item)


@router.patch("/icd-codes/{icd_id}")
async def update_icd_code(
    icd_id: str,
    data: ICDCodeUpdate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    item = (
        await db.execute(select(ICDCode).where(ICDCode.id == icd_id))
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="ICD code not found")

    if data.code is not None:
        code = _normalize_icd_code(data.code)
        existing = (
            await db.execute(
                select(ICDCode).where(ICDCode.code == code).where(ICDCode.id != item.id)
            )
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail=f"ICD code '{code}' already exists")
        item.code = code

    if data.description is not None:
        item.description = _normalize_required_text(data.description, "Description")
    if data.category is not None:
        item.category = _normalize_required_text(data.category, "Category")
    if data.is_active is not None:
        item.is_active = data.is_active

    await db.commit()
    await db.refresh(item)
    return _serialize_icd_code(item)


@router.delete("/icd-codes/{icd_id}")
async def delete_icd_code(
    icd_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    item = (
        await db.execute(select(ICDCode).where(ICDCode.id == icd_id))
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="ICD code not found")

    code = item.code
    await db.delete(item)
    await db.commit()
    return {"message": f"ICD code '{code}' deleted"}


# ── Vital Parameters Management ──────────────────────────────────────


class VitalParameterCreate(BaseModel):
    name: str
    display_name: str
    category: str = "Primary"
    unit: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    is_active: bool = True
    sort_order: int = 0


class VitalParameterUpdate(BaseModel):
    display_name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


@router.get("/vital-parameters")
async def list_vital_parameters(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
    active_only: bool = Query(False, description="Return only active parameters"),
):
    """List all vital parameters configurations."""
    query = select(VitalParameter).order_by(VitalParameter.category, VitalParameter.sort_order)
    if active_only:
        query = query.where(VitalParameter.is_active == True)
    result = await db.execute(query)
    parameters = result.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "display_name": p.display_name,
            "category": p.category,
            "unit": p.unit,
            "min_value": p.min_value,
            "max_value": p.max_value,
            "is_active": p.is_active,
            "sort_order": p.sort_order,
        }
        for p in parameters
    ]


@router.post("/vital-parameters")
async def create_vital_parameter(
    data: VitalParameterCreate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new vital parameter configuration."""
    # Check if parameter with same name exists
    existing = (await db.execute(
        select(VitalParameter).where(VitalParameter.name == data.name)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail=f"Parameter '{data.name}' already exists")

    param = VitalParameter(
        id=_uid(),
        name=data.name,
        display_name=data.display_name,
        category=data.category,
        unit=data.unit,
        min_value=data.min_value,
        max_value=data.max_value,
        is_active=data.is_active,
        sort_order=data.sort_order,
    )
    db.add(param)
    await db.commit()
    return {
        "id": param.id,
        "name": param.name,
        "display_name": param.display_name,
        "category": param.category,
        "unit": param.unit,
        "min_value": param.min_value,
        "max_value": param.max_value,
        "is_active": param.is_active,
        "sort_order": param.sort_order,
    }


@router.get("/vital-parameters/{param_id}")
async def get_vital_parameter(
    param_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Get a single vital parameter by ID."""
    param = (await db.execute(
        select(VitalParameter).where(VitalParameter.id == param_id)
    )).scalar_one_or_none()
    if not param:
        raise HTTPException(status_code=404, detail="Vital parameter not found")
    return {
        "id": param.id,
        "name": param.name,
        "display_name": param.display_name,
        "category": param.category,
        "unit": param.unit,
        "min_value": param.min_value,
        "max_value": param.max_value,
        "is_active": param.is_active,
        "sort_order": param.sort_order,
    }


@router.patch("/vital-parameters/{param_id}")
async def update_vital_parameter(
    param_id: str,
    data: VitalParameterUpdate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Update a vital parameter configuration."""
    param = (await db.execute(
        select(VitalParameter).where(VitalParameter.id == param_id)
    )).scalar_one_or_none()
    if not param:
        raise HTTPException(status_code=404, detail="Vital parameter not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(param, key, value)

    await db.commit()
    return {
        "id": param.id,
        "name": param.name,
        "display_name": param.display_name,
        "category": param.category,
        "unit": param.unit,
        "min_value": param.min_value,
        "max_value": param.max_value,
        "is_active": param.is_active,
        "sort_order": param.sort_order,
    }


@router.delete("/vital-parameters/{param_id}")
async def delete_vital_parameter(
    param_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Delete a vital parameter configuration (or deactivate it)."""
    param = (await db.execute(
        select(VitalParameter).where(VitalParameter.id == param_id)
    )).scalar_one_or_none()
    if not param:
        raise HTTPException(status_code=404, detail="Vital parameter not found")

    # Soft delete by deactivating
    param.is_active = False
    await db.commit()
    return {"message": f"Vital parameter '{param.display_name}' deactivated"}
