"""Admin panel API – dashboard, user management, departments, analytics."""

import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import and_, case, distinct, extract, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import invalidate_user_cache, require_role
from app.core.security import get_password_hash
from app.database import get_db
from app.models.academic import AcademicFormWeightage, AcademicGroup, AcademicTarget
from app.models.admission import Admission
from app.models.billing import Billing
from app.models.case_record import Approval, ApprovalStatus, CaseRecord
from app.models.department import Department
from app.models.faculty import Faculty
from app.models.form_definition import FormDefinition
from app.models.icd_code import ICDCode
from app.models.lab import ChargePrice
from app.models.lab_technician import LabTechnician
from app.models.medical_record import MedicalRecord
from app.models.notification import PatientNotification
from app.models.nurse import Nurse
from app.models.nutritionist import Nutritionist
from app.models.ot_manager import OTManager
from app.models.patient import Patient
from app.models.patient_category import (
    DEFAULT_PATIENT_CATEGORY_COLOR_PRIMARY,
    DEFAULT_PATIENT_CATEGORY_COLOR_SECONDARY,
    PatientCategoryOption,
    get_default_patient_category_colors,
)
from app.models.prescription import Prescription
from app.models.programme import Programme
from app.models.student import Clinic, Student
from app.models.user import User, UserRole
from app.models.vital import Vital, VitalParameter
from app.models.feedback_form import FeedbackForm, FeedbackFormResponse
from app.services.academics import (
    get_student_academic_progress,
    list_case_record_forms,
    list_student_approved_case_records,
    match_form_definition_for_record,
)
from app.services.charge_sync import sync_charge_price_categories
from app.services.id_generator import generate_patient_id as _async_generate_patient_id
from app.services.patient_categories import (
    ensure_patient_categories,
    get_default_patient_category_name,
    normalize_patient_category_name,
    patient_category_usage_counts,
)

router = APIRouter(prefix="/admin", tags=["Admin"])

# ── helpers ──────────────────────────────────────────────────────────


def _serialize_vital_parameter(param: VitalParameter) -> dict:
    return {
        "id": param.id,
        "name": param.name,
        "display_name": param.display_name,
        "category": param.category,
        "unit": param.unit,
        "min_value": param.min_value,
        "max_value": param.max_value,
        "value_style": param.value_style,
        "is_active": param.is_active,
        "sort_order": param.sort_order,
    }


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


def _serialize_academic_group(group: AcademicGroup) -> dict:
    students = list(group.students or [])
    targets = list(group.targets or [])
    return {
        "id": group.id,
        "programme_id": group.programme_id,
        "programme_name": group.programme.name
        if getattr(group, "programme", None)
        else None,
        "name": group.name,
        "description": group.description,
        "is_active": group.is_active,
        "student_count": len(students),
        "target_count": len(targets),
        "student_ids": [student.id for student in students],
        "created_at": group.created_at.isoformat() if group.created_at else None,
        "updated_at": group.updated_at.isoformat() if group.updated_at else None,
    }


def _serialize_academic_target(target: AcademicTarget) -> dict:
    group = getattr(target, "group", None)
    form_definition = getattr(target, "form_definition", None)
    return {
        "id": target.id,
        "group_id": target.group_id,
        "group_name": group.name if group else None,
        "programme_id": group.programme_id if group else None,
        "programme_name": group.programme.name
        if group and getattr(group, "programme", None)
        else None,
        "form_definition_id": target.form_definition_id,
        "form_name": form_definition.name if form_definition else None,
        "metric_name": target.metric_name,
        "metric_key": target.metric_name.strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_"),
        "category": target.category,
        "target_value": target.target_value,
        "sort_order": target.sort_order,
        "created_at": target.created_at.isoformat() if target.created_at else None,
        "updated_at": target.updated_at.isoformat() if target.updated_at else None,
    }


def _serialize_academic_weightage(weightage: AcademicFormWeightage) -> dict:
    form_definition = weightage.form_definition
    return {
        "id": weightage.id,
        "form_definition_id": weightage.form_definition_id,
        "slug": form_definition.slug if form_definition else None,
        "name": form_definition.name if form_definition else None,
        "department": form_definition.department if form_definition else None,
        "procedure_name": form_definition.procedure_name if form_definition else None,
        "section": form_definition.section if form_definition else None,
        "points": weightage.points,
        "has_weightage": True,
        "updated_at": weightage.updated_at.isoformat()
        if weightage.updated_at
        else None,
    }


def _serialize_case_record_form(
    form: FormDefinition, weightage: AcademicFormWeightage | None = None
) -> dict:
    return {
        "form_definition_id": form.id,
        "slug": form.slug,
        "name": form.name,
        "department": form.department,
        "procedure_name": form.procedure_name,
        "section": form.section,
        "points": int(weightage.points) if weightage else 0,
        "has_weightage": weightage is not None,
        "updated_at": weightage.updated_at.isoformat()
        if weightage and weightage.updated_at
        else None,
    }


def _serialize_programme(
    programme: Programme, *, student_count: int = 0, group_count: int = 0
) -> dict:
    return {
        "id": programme.id,
        "name": programme.name,
        "code": programme.code,
        "description": programme.description,
        "degree_type": programme.degree_type,
        "duration_years": programme.duration_years,
        "is_active": programme.is_active,
        "student_count": student_count,
        "group_count": group_count,
        "created_at": programme.created_at.isoformat()
        if programme.created_at
        else None,
    }


class AcademicGroupUpsert(BaseModel):
    programme_id: str
    name: str
    description: Optional[str] = None
    is_active: bool = True
    student_ids: list[str] = []


class AcademicTargetUpsert(BaseModel):
    group_id: str
    form_definition_id: Optional[str] = None
    metric_name: str
    category: Optional[str] = "ACADEMIC"
    target_value: int = 0
    sort_order: int = 0


class AcademicWeightageUpsert(BaseModel):
    points: int = 0


def _safe_iso(value) -> Optional[str]:
    return value.isoformat() if value else None


async def _load_academic_manager_context(
    db: AsyncSession,
    *,
    programme_id: Optional[str] = None,
    group_id: Optional[str] = None,
    student_id: Optional[str] = None,
    year: Optional[int] = None,
    semester: Optional[int] = None,
    search: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
):
    students_query = select(Student).options(
        selectinload(Student.academic_group),
        selectinload(Student.attendance),
    )

    if student_id:
        students_query = students_query.where(Student.id == student_id)
    if group_id:
        students_query = students_query.where(Student.academic_group_id == group_id)
    if programme_id:
        programme = (
            await db.execute(select(Programme).where(Programme.id == programme_id))
        ).scalar_one_or_none()
        if not programme:
            raise HTTPException(status_code=404, detail="Programme not found")
        students_query = students_query.where(Student.program == programme.name)
    if year is not None:
        students_query = students_query.where(Student.year == year)
    if semester is not None:
        students_query = students_query.where(Student.semester == semester)
    if search:
        pattern = f"%{search.strip()}%"
        students_query = students_query.where(
            or_(
                Student.name.ilike(pattern),
                Student.student_id.ilike(pattern),
                Student.program.ilike(pattern),
            )
        )

    students_query = students_query.order_by(Student.name.asc())
    students = list((await db.execute(students_query)).scalars().all())
    student_ids = [student.id for student in students]

    groups_query = (
        select(AcademicGroup)
        .options(
            selectinload(AcademicGroup.programme),
            selectinload(AcademicGroup.students),
            selectinload(AcademicGroup.targets).selectinload(
                AcademicTarget.form_definition
            ),
        )
        .order_by(AcademicGroup.name.asc())
    )
    if group_id:
        groups_query = groups_query.where(AcademicGroup.id == group_id)
    elif programme_id:
        groups_query = groups_query.where(AcademicGroup.programme_id == programme_id)

    groups = list((await db.execute(groups_query)).scalars().all())
    group_ids = [group.id for group in groups]

    programmes_query = select(Programme).order_by(Programme.name.asc())
    if programme_id:
        programmes_query = programmes_query.where(Programme.id == programme_id)
    programmes = list((await db.execute(programmes_query)).scalars().all())

    targets_query = (
        select(AcademicTarget)
        .options(
            selectinload(AcademicTarget.group).selectinload(AcademicGroup.programme),
            selectinload(AcademicTarget.form_definition),
        )
        .order_by(AcademicTarget.sort_order.asc(), AcademicTarget.metric_name.asc())
    )
    if group_ids:
        targets_query = targets_query.where(AcademicTarget.group_id.in_(group_ids))
    elif group_id:
        targets_query = targets_query.where(AcademicTarget.group_id == group_id)
    elif programme_id:
        targets_query = targets_query.join(
            AcademicGroup, AcademicGroup.id == AcademicTarget.group_id
        ).where(AcademicGroup.programme_id == programme_id)

    targets = list((await db.execute(targets_query)).scalars().all())

    forms = await list_case_record_forms(db)

    weightages_result = await db.execute(
        select(AcademicFormWeightage).options(
            selectinload(AcademicFormWeightage.form_definition)
        )
    )
    weightages = list(weightages_result.scalars().all())
    weightages_by_form_id = {item.form_definition_id: item for item in weightages}

    approvals: list[Approval] = []
    case_records: list[CaseRecord] = []
    approved_records_by_student: dict[str, list[CaseRecord]] = defaultdict(list)

    if student_ids:
        approvals_query = (
            select(Approval)
            .options(
                selectinload(Approval.student).selectinload(Student.academic_group),
                selectinload(Approval.faculty),
                selectinload(Approval.case_record),
            )
            .where(Approval.student_id.in_(student_ids))
            .order_by(Approval.created_at.desc())
        )
        approvals = list((await db.execute(approvals_query)).scalars().all())

        case_records_query = (
            select(CaseRecord)
            .options(
                selectinload(CaseRecord.student), selectinload(CaseRecord.approval)
            )
            .where(CaseRecord.student_id.in_(student_ids))
            .order_by(CaseRecord.created_at.desc())
        )
        if from_date:
            case_records_query = case_records_query.where(
                CaseRecord.created_at
                >= datetime.combine(from_date, datetime.min.time())
            )
        if to_date:
            case_records_query = case_records_query.where(
                CaseRecord.created_at
                < datetime.combine(to_date + timedelta(days=1), datetime.min.time())
            )
        case_records = list((await db.execute(case_records_query)).scalars().all())

        for student in students:
            approved_records_by_student[
                student.id
            ] = await list_student_approved_case_records(db, student_id=student.id)

    return {
        "students": students,
        "student_ids": student_ids,
        "groups": groups,
        "group_ids": group_ids,
        "programmes": programmes,
        "targets": targets,
        "forms": forms,
        "weightages_by_form_id": weightages_by_form_id,
        "approvals": approvals,
        "case_records": case_records,
        "approved_records_by_student": approved_records_by_student,
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
        await db.execute(
            select(func.count(Department.id)).where(Department.is_active == True)
        )
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

    total_prescriptions = (
        await db.execute(select(func.count(Prescription.id)))
    ).scalar() or 0

    pending_approvals = (
        await db.execute(
            select(func.count(Approval.id)).where(
                Approval.status == ApprovalStatus.PENDING
            )
        )
    ).scalar() or 0

    # Patient category breakdown
    category_result = await db.execute(
        select(Patient.category, func.count(Patient.id)).group_by(Patient.category)
    )
    patient_categories = {
        normalize_patient_category_name(row[0] or "UNKNOWN") or "UNKNOWN": row[1]
        for row in category_result.all()
    }

    # Recent registrations (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_registrations = (
        await db.execute(select(func.count(User.id)).where(User.created_at >= week_ago))
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
    role: Optional[str] = Query(
        None, description="Filter by role: PATIENT, STUDENT, FACULTY, ADMIN"
    ),
    search: Optional[str] = Query(None, description="Search by username or email"),
    status_filter: Optional[str] = Query(
        None, alias="status", description="active or blocked"
    ),
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
    query = (
        query.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )
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
            p = (
                await db.execute(select(Patient.name).where(Patient.user_id == u.id))
            ).scalar()
            item["name"] = p or u.username
        elif u.role == UserRole.STUDENT:
            s = (
                await db.execute(select(Student.name).where(Student.user_id == u.id))
            ).scalar()
            item["name"] = s or u.username
        elif u.role == UserRole.FACULTY:
            f = (
                await db.execute(select(Faculty.name).where(Faculty.user_id == u.id))
            ).scalar()
            item["name"] = f or u.username
        elif u.role == UserRole.LAB_TECHNICIAN:
            technician_name = (
                await db.execute(
                    select(LabTechnician.name).where(LabTechnician.user_id == u.id)
                )
            ).scalar()
            item["name"] = technician_name or u.username
        elif u.role == UserRole.NUTRITIONIST:
            nutritionist_name = (
                await db.execute(
                    select(Nutritionist.name).where(Nutritionist.user_id == u.id)
                )
            ).scalar()
            item["name"] = nutritionist_name or u.username
        elif u.role in {UserRole.NURSE, UserRole.NURSE_SUPERINTENDENT}:
            nurse_name = (
                await db.execute(select(Nurse.name).where(Nurse.user_id == u.id))
            ).scalar()
            item["name"] = nurse_name or u.username
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
    target = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="Cannot block yourself")
    target.is_active = False
    await db.commit()
    await invalidate_user_cache(user_id)
    return {"message": f"User {target.username} has been blocked", "is_active": False}


@router.put("/users/{user_id}/unblock")
async def unblock_user(
    user_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Unblock (reactivate) a user."""
    target = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    target.is_active = True
    await db.commit()
    await invalidate_user_cache(user_id)
    return {"message": f"User {target.username} has been unblocked", "is_active": True}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user and all associated profile data (patient/student/faculty/nurse)."""
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(User)
        .options(
            selectinload(User.patient),
            selectinload(User.student),
            selectinload(User.faculty),
            selectinload(User.nutritionist),
            selectinload(User.lab_technician),
            selectinload(User.nurse),
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
        if target.nutritionist:
            await db.delete(target.nutritionist)
        if target.lab_technician:
            await db.delete(target.lab_technician)
        if target.nurse:
            await db.delete(target.nurse)

        await db.delete(target)
        await db.commit()
        return {"message": f"User {target.username} has been deleted"}
    except IntegrityError as e:
        await db.rollback()
        # Check if it's a foreign key constraint error
        error_msg = str(e.orig) if hasattr(e, "orig") else str(e)
        if "foreign key" in error_msg.lower() or "violates" in error_msg.lower():
            raise HTTPException(
                status_code=409,
                detail="Cannot delete user: they have associated records (admissions, appointments, etc.). Please delete those records first or deactivate the user instead.",
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
    clinic_id: Optional[str] = None

    # NURSE fields
    hospital: Optional[str] = None
    ward: Optional[str] = None
    shift: Optional[str] = None

    # BILLING / ACCOUNTS fields
    counter_name: Optional[str] = None


def _generate_patient_id():
    # Kept as sync stub — call sites upgraded to use async generate_patient_id(db)
    import uuid
    from datetime import datetime, timezone

    return f"PT{datetime.now(timezone.utc).strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"


def _generate_student_id():
    return f"ST{datetime.utcnow().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"


def _generate_faculty_id():
    return f"FA{datetime.utcnow().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"


def _generate_nutritionist_id():
    return f"NT{datetime.utcnow().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"


def _generate_nurse_id():
    return f"NR{datetime.utcnow().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"


def _generate_nurse_superintendent_id():
    return f"NS{datetime.utcnow().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"


def _generate_lab_technician_id():
    return f"LT{datetime.utcnow().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"


def _generate_billing_id():
    return f"BL{datetime.utcnow().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"


def _generate_ot_manager_id():
    return f"OTM{datetime.utcnow().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"


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
    if (
        await db.execute(select(User).where(User.username == username))
    ).scalar_one_or_none():
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
            raise HTTPException(
                status_code=400, detail="Date of birth is required for patients"
            )

        try:
            dob = datetime.strptime(data.date_of_birth, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Date of birth must be in YYYY-MM-DD format"
            )

        from app.models.patient import Gender
        from app.services.clinic_allocation import resolve_preferred_clinic
        from app.services.clinic_intake import ensure_clinic_checkin

        resolved_category = normalize_patient_category_name(
            data.category
        ) or await get_default_patient_category_name(db)
        new_patient = Patient(
            id=str(uuid.uuid4()),
            patient_id=await _async_generate_patient_id(db),
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
            raise HTTPException(
                status_code=400,
                detail="Year, semester, and program are required for students",
            )

        db.add(
            Student(
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
            )
        )
    elif role == UserRole.FACULTY:
        if not data.department:
            raise HTTPException(
                status_code=400, detail="Department is required for faculty"
            )

        db.add(
            Faculty(
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
            )
        )
    elif role == UserRole.NUTRITIONIST:
        if not data.clinic_id:
            raise HTTPException(
                status_code=400, detail="Clinic is required for nutritionists"
            )

        clinic = (
            await db.execute(
                select(Clinic).where(
                    Clinic.id == data.clinic_id,
                    Clinic.is_active == True,
                )
            )
        ).scalar_one_or_none()
        if not clinic:
            raise HTTPException(status_code=404, detail="Assigned clinic not found")

        existing_nutritionist = (
            await db.execute(
                select(Nutritionist).where(Nutritionist.clinic_id == data.clinic_id)
            )
        ).scalar_one_or_none()
        if existing_nutritionist:
            raise HTTPException(
                status_code=400,
                detail="This clinic already has a nutritionist assigned",
            )

        db.add(
            Nutritionist(
                id=str(uuid.uuid4()),
                nutritionist_id=_generate_nutritionist_id(),
                user_id=user_id,
                clinic_id=clinic.id,
                name=name,
                phone=data.phone,
                email=email,
                photo=data.photo,
            )
        )
    elif role == UserRole.LAB_TECHNICIAN:
        db.add(
            LabTechnician(
                id=str(uuid.uuid4()),
                technician_id=_generate_lab_technician_id(),
                user_id=user_id,
                name=name,
                phone=data.phone,
                email=email,
                photo=data.photo,
                department=data.department,
                has_selected_lab=0,
            )
        )
    elif role in {UserRole.NURSE, UserRole.NURSE_SUPERINTENDENT}:
        clinic = None
        if data.clinic_id:
            clinic = (
                await db.execute(
                    select(Clinic).where(
                        Clinic.id == data.clinic_id,
                        Clinic.is_active == True,
                    )
                )
            ).scalar_one_or_none()
            if not clinic:
                raise HTTPException(status_code=404, detail="Assigned clinic not found")

        db.add(
            Nurse(
                id=str(uuid.uuid4()),
                nurse_id=_generate_nurse_superintendent_id()
                if role == UserRole.NURSE_SUPERINTENDENT
                else _generate_nurse_id(),
                user_id=user_id,
                name=name,
                phone=data.phone,
                email=email,
                photo=data.photo,
                clinic_id=clinic.id if clinic else data.clinic_id,
                hospital=clinic.name if clinic else data.hospital,
                ward=data.ward,
                shift=data.shift,
                department=data.department or (clinic.department if clinic else None),
                has_selected_station=1 if role == UserRole.NURSE_SUPERINTENDENT else 0,
            )
        )
    # ADMIN and RECEPTION roles: no extra profile record needed
    elif role in {UserRole.BILLING, UserRole.ACCOUNTS}:
        db.add(
            Billing(
                id=str(uuid.uuid4()),
                billing_id=_generate_billing_id(),
                user_id=user_id,
                name=name,
                phone=data.phone,
                email=email,
                counter_name=data.counter_name,
            )
        )
    elif role == UserRole.OT_MANAGER:
        db.add(
            OTManager(
                id=str(uuid.uuid4()),
                manager_id=_generate_ot_manager_id(),
                user_id=user_id,
                name=name,
                phone=data.phone,
                email=email,
            )
        )
    # ADMIN, RECEPTION, and MRD: no extra profile record needed

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
            rows.append(
                {k.strip().lower(): (v.strip() if v else "") for k, v in row.items()}
            )
    elif filename_lower.endswith(".xlsx") or filename_lower.endswith(".xls"):
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        headers = None
        for excel_row in ws.iter_rows(values_only=True):
            if headers is None:
                headers = [
                    str(c).strip().lower() if c is not None else "" for c in excel_row
                ]
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
            results.append(
                {
                    "row": row_num,
                    "username": username or "(empty)",
                    "status": "failed",
                    "error": "username, email, password, role are required",
                }
            )
            failed += 1
            continue

        try:
            role = UserRole(role_str)
        except ValueError:
            results.append(
                {
                    "row": row_num,
                    "username": username,
                    "status": "failed",
                    "error": f"Invalid role: {role_str}",
                }
            )
            failed += 1
            continue

        if (
            await db.execute(select(User).where(User.username == username))
        ).scalar_one_or_none():
            results.append(
                {
                    "row": row_num,
                    "username": username,
                    "status": "failed",
                    "error": "Username already exists",
                }
            )
            failed += 1
            continue
        if (
            await db.execute(select(User).where(User.email == email))
        ).scalar_one_or_none():
            results.append(
                {
                    "row": row_num,
                    "username": username,
                    "status": "failed",
                    "error": "Email already exists",
                }
            )
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
                db.add(
                    Patient(
                        id=str(uuid.uuid4()),
                        patient_id=await _async_generate_patient_id(db),
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
                        category=normalize_patient_category_name(
                            row.get("category", "")
                        )
                        or await get_default_patient_category_name(db),
                    )
                )
            elif role == UserRole.STUDENT:
                year_str = row.get("year", "").strip()
                semester_str = row.get("semester", "").strip()
                program = row.get("program", "").strip()
                if not year_str or not semester_str or not program:
                    raise ValueError("year, semester, program required for students")
                db.add(
                    Student(
                        id=str(uuid.uuid4()),
                        student_id=_generate_student_id(),
                        user_id=user_id,
                        name=display_name,
                        year=int(year_str),
                        semester=int(semester_str),
                        program=program,
                        degree=row.get("degree") or None,
                        gpa=float(row.get("gpa") or 0),
                        academic_standing=row.get("academic_standing")
                        or "Good Standing",
                        academic_advisor=row.get("academic_advisor") or None,
                    )
                )
            elif role == UserRole.FACULTY:
                department = row.get("department", "").strip()
                if not department:
                    raise ValueError("department is required for faculty")
                db.add(
                    Faculty(
                        id=str(uuid.uuid4()),
                        faculty_id=_generate_faculty_id(),
                        user_id=user_id,
                        name=display_name,
                        department=department,
                        specialty=row.get("specialty") or None,
                        phone=row.get("phone") or None,
                        email=email,
                        availability=row.get("availability") or None,
                    )
                )
            elif role == UserRole.NUTRITIONIST:
                clinic_id = row.get("clinic_id", "").strip()
                if not clinic_id:
                    raise ValueError("clinic_id is required for nutritionists")
                clinic = (
                    await db.execute(
                        select(Clinic).where(
                            Clinic.id == clinic_id,
                            Clinic.is_active == True,
                        )
                    )
                ).scalar_one_or_none()
                if not clinic:
                    raise ValueError("Assigned clinic not found")
                existing_nutritionist = (
                    await db.execute(
                        select(Nutritionist).where(Nutritionist.clinic_id == clinic_id)
                    )
                ).scalar_one_or_none()
                if existing_nutritionist:
                    raise ValueError("This clinic already has a nutritionist assigned")
                db.add(
                    Nutritionist(
                        id=str(uuid.uuid4()),
                        nutritionist_id=_generate_nutritionist_id(),
                        user_id=user_id,
                        clinic_id=clinic.id,
                        name=display_name,
                        phone=row.get("phone") or None,
                        email=email,
                    )
                )
            elif role == UserRole.LAB_TECHNICIAN:
                db.add(
                    LabTechnician(
                        id=str(uuid.uuid4()),
                        technician_id=_generate_lab_technician_id(),
                        user_id=user_id,
                        name=display_name,
                        phone=row.get("phone") or None,
                        email=email,
                        department=row.get("department") or None,
                        has_selected_lab=0,
                    )
                )
            elif role in {UserRole.NURSE, UserRole.NURSE_SUPERINTENDENT}:
                db.add(
                    Nurse(
                        id=str(uuid.uuid4()),
                        nurse_id=_generate_nurse_superintendent_id()
                        if role == UserRole.NURSE_SUPERINTENDENT
                        else _generate_nurse_id(),
                        user_id=user_id,
                        name=display_name,
                        phone=row.get("phone") or None,
                        email=email,
                        clinic_id=row.get("clinic_id") or None,
                        hospital=row.get("hospital") or None,
                        ward=row.get("ward") or None,
                        shift=row.get("shift") or None,
                        department=row.get("department") or None,
                        has_selected_station=1
                        if role == UserRole.NURSE_SUPERINTENDENT
                        else 0,
                    )
                )

            await db.flush()
            results.append({"row": row_num, "username": username, "status": "created"})
            created += 1

        except Exception as exc:
            await db.rollback()
            results.append(
                {
                    "row": row_num,
                    "username": username,
                    "status": "failed",
                    "error": str(exc),
                }
            )
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
    result = await db.execute(select(Department).order_by(Department.name))
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
                await db.execute(
                    select(Faculty.name).where(Faculty.id == dept.head_faculty_id)
                )
            ).scalar()
            head_name = head

        items.append(
            {
                "id": dept.id,
                "name": dept.name,
                "code": dept.code,
                "description": dept.description,
                "head_faculty_id": dept.head_faculty_id,
                "head_faculty_name": head_name,
                "is_active": dept.is_active,
                "faculty_count": fac_count,
                "created_at": dept.created_at.isoformat() if dept.created_at else None,
            }
        )

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
        await db.execute(
            select(Department).where(
                (Department.name == name) | (Department.code == code)
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400, detail="Department name or code already exists"
        )

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
    dept = (
        await db.execute(select(Department).where(Department.id == dept_id))
    ).scalar_one_or_none()
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
    dept = (
        await db.execute(select(Department).where(Department.id == dept_id))
    ).scalar_one_or_none()
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
        items.append(
            {
                "department": row.department,
                "faculty_count": row.faculty_count,
            }
        )
    return items


@router.get("/analytics/role-distribution")
async def role_distribution(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Count of users per role."""
    rows = (
        await db.execute(select(User.role, func.count(User.id)).group_by(User.role))
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
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """List all students."""
    q = select(Student).options(selectinload(Student.academic_group))
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
            "academic_group_id": s.academic_group_id,
            "academic_group_name": s.academic_group.name if s.academic_group else None,
        }
        for s in students
    ]


# ── Programme Management ─────────────────────────────────────────────


@router.get("/programmes")
async def list_programmes(
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """List all programmes."""
    result = await db.execute(
        select(Programme)
        .options(selectinload(Programme.academic_groups))
        .order_by(Programme.name)
    )
    programmes = result.scalars().all()

    items = []
    for p in programmes:
        student_count = (
            await db.execute(
                select(func.count(Student.id)).where(Student.program == p.name)
            )
        ).scalar() or 0
        items.append(
            _serialize_programme(
                p,
                student_count=student_count,
                group_count=len(list(p.academic_groups or [])),
            )
        )
    return items


@router.post("/programmes", status_code=201)
async def create_programme(
    body: dict,
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
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
        raise HTTPException(
            status_code=400, detail="Programme name or code already exists"
        )

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
        "group_count": 0,
        "message": "Programme created successfully",
    }


@router.put("/programmes/{prog_id}")
async def update_programme(
    prog_id: str,
    body: dict,
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Update a programme."""
    prog = (
        await db.execute(select(Programme).where(Programme.id == prog_id))
    ).scalar_one_or_none()
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
    await db.refresh(prog)
    return {
        "message": "Programme updated",
        "id": prog.id,
        "name": prog.name,
        "code": prog.code,
        "is_active": prog.is_active,
    }


@router.delete("/programmes/{prog_id}")
async def delete_programme(
    prog_id: str,
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete (deactivate) a programme."""
    prog = (
        await db.execute(select(Programme).where(Programme.id == prog_id))
    ).scalar_one_or_none()
    if not prog:
        raise HTTPException(status_code=404, detail="Programme not found")
    prog.is_active = False
    await db.commit()
    return {"message": f"Programme '{prog.name}' deactivated"}


@router.get("/programmes/academics/overview")
async def get_academics_overview(
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    programmes_result = await db.execute(
        select(Programme)
        .options(selectinload(Programme.academic_groups))
        .order_by(Programme.name.asc())
    )
    programmes = list(programmes_result.scalars().all())

    groups_result = await db.execute(
        select(AcademicGroup)
        .options(
            selectinload(AcademicGroup.programme),
            selectinload(AcademicGroup.students),
            selectinload(AcademicGroup.targets).selectinload(
                AcademicTarget.form_definition
            ),
        )
        .order_by(AcademicGroup.name.asc())
    )
    groups = list(groups_result.scalars().all())

    targets_result = await db.execute(
        select(AcademicTarget)
        .options(
            selectinload(AcademicTarget.group).selectinload(AcademicGroup.programme),
            selectinload(AcademicTarget.form_definition),
        )
        .order_by(AcademicTarget.sort_order.asc(), AcademicTarget.metric_name.asc())
    )
    targets = list(targets_result.scalars().all())

    forms_result = await db.execute(
        select(FormDefinition)
        .where(
            FormDefinition.is_active == True,
            FormDefinition.form_type == "CASE_RECORD",
        )
        .order_by(
            FormDefinition.department.asc(),
            FormDefinition.sort_order.asc(),
            FormDefinition.name.asc(),
        )
    )
    forms = list(forms_result.scalars().all())

    weightages_result = await db.execute(
        select(AcademicFormWeightage).options(
            selectinload(AcademicFormWeightage.form_definition)
        )
    )
    weightages = list(weightages_result.scalars().all())
    weightages_by_form_id = {item.form_definition_id: item for item in weightages}

    students_result = await db.execute(
        select(Student)
        .options(selectinload(Student.academic_group))
        .order_by(Student.name.asc())
    )
    students = list(students_result.scalars().all())

    programme_items = []
    for programme in programmes:
        student_count = (
            await db.execute(
                select(func.count(Student.id)).where(Student.program == programme.name)
            )
        ).scalar() or 0
        programme_items.append(
            _serialize_programme(
                programme,
                student_count=student_count,
                group_count=len(list(programme.academic_groups or [])),
            )
        )

    return {
        "programmes": programme_items,
        "groups": [_serialize_academic_group(group) for group in groups],
        "targets": [_serialize_academic_target(target) for target in targets],
        "weightages": [
            _serialize_case_record_form(form, weightages_by_form_id.get(form.id))
            for form in forms
        ],
        "students": [
            {
                "id": student.id,
                "student_id": student.student_id,
                "name": student.name,
                "year": student.year,
                "semester": student.semester,
                "program": student.program,
                "gpa": student.gpa,
                "academic_standing": student.academic_standing,
                "academic_group_id": student.academic_group_id,
                "academic_group_name": student.academic_group.name
                if student.academic_group
                else None,
            }
            for student in students
        ],
    }


@router.get("/programmes/academic-groups")
async def list_academic_groups(
    programme_id: Optional[str] = None,
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(AcademicGroup)
        .options(
            selectinload(AcademicGroup.programme),
            selectinload(AcademicGroup.students),
            selectinload(AcademicGroup.targets),
        )
        .order_by(AcademicGroup.name.asc())
    )
    if programme_id:
        query = query.where(AcademicGroup.programme_id == programme_id)

    result = await db.execute(query)
    return [_serialize_academic_group(group) for group in result.scalars().all()]


@router.post("/programmes/academic-groups", status_code=201)
async def create_academic_group(
    payload: AcademicGroupUpsert,
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    programme = (
        await db.execute(select(Programme).where(Programme.id == payload.programme_id))
    ).scalar_one_or_none()
    if not programme:
        raise HTTPException(status_code=404, detail="Programme not found")

    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Group name is required")

    existing = (
        await db.execute(
            select(AcademicGroup).where(
                AcademicGroup.programme_id == payload.programme_id,
                AcademicGroup.name == name,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Academic group name already exists for this programme",
        )

    students_result = await db.execute(
        select(Student).where(Student.id.in_(payload.student_ids or []))
    )
    students = list(students_result.scalars().all())
    for student in students:
        if student.program != programme.name:
            raise HTTPException(
                status_code=400,
                detail=f"Student '{student.name}' does not belong to programme '{programme.name}'",
            )

    group = AcademicGroup(
        id=_uid(),
        programme_id=payload.programme_id,
        name=name,
        description=(payload.description or "").strip() or None,
        is_active=payload.is_active,
    )
    db.add(group)
    await db.flush()

    for student in students:
        student.academic_group_id = group.id

    await db.commit()

    refreshed = await db.execute(
        select(AcademicGroup)
        .options(
            selectinload(AcademicGroup.programme),
            selectinload(AcademicGroup.students),
            selectinload(AcademicGroup.targets),
        )
        .where(AcademicGroup.id == group.id)
    )
    return _serialize_academic_group(refreshed.scalar_one())


@router.put("/programmes/academic-groups/{group_id}")
async def update_academic_group(
    group_id: str,
    payload: AcademicGroupUpsert,
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AcademicGroup)
        .options(
            selectinload(AcademicGroup.programme),
            selectinload(AcademicGroup.students),
            selectinload(AcademicGroup.targets),
        )
        .where(AcademicGroup.id == group_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Academic group not found")

    programme = (
        await db.execute(select(Programme).where(Programme.id == payload.programme_id))
    ).scalar_one_or_none()
    if not programme:
        raise HTTPException(status_code=404, detail="Programme not found")

    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Group name is required")

    conflict = (
        await db.execute(
            select(AcademicGroup).where(
                AcademicGroup.programme_id == payload.programme_id,
                AcademicGroup.name == name,
                AcademicGroup.id != group_id,
            )
        )
    ).scalar_one_or_none()
    if conflict:
        raise HTTPException(
            status_code=400,
            detail="Academic group name already exists for this programme",
        )

    students_result = await db.execute(
        select(Student).where(Student.id.in_(payload.student_ids or []))
    )
    students = list(students_result.scalars().all())
    selected_ids = {student.id for student in students}

    for student in students:
        if student.program != programme.name:
            raise HTTPException(
                status_code=400,
                detail=f"Student '{student.name}' does not belong to programme '{programme.name}'",
            )

    for existing_student in list(group.students or []):
        if existing_student.id not in selected_ids:
            existing_student.academic_group_id = None

    for student in students:
        student.academic_group_id = group.id

    group.programme_id = payload.programme_id
    group.name = name
    group.description = (payload.description or "").strip() or None
    group.is_active = payload.is_active

    await db.commit()

    refreshed = await db.execute(
        select(AcademicGroup)
        .options(
            selectinload(AcademicGroup.programme),
            selectinload(AcademicGroup.students),
            selectinload(AcademicGroup.targets),
        )
        .where(AcademicGroup.id == group.id)
    )
    return _serialize_academic_group(refreshed.scalar_one())


@router.delete("/programmes/academic-groups/{group_id}")
async def delete_academic_group(
    group_id: str,
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AcademicGroup)
        .options(selectinload(AcademicGroup.students))
        .where(AcademicGroup.id == group_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Academic group not found")

    for student in list(group.students or []):
        student.academic_group_id = None

    await db.delete(group)
    await db.commit()
    return {"message": "Academic group deleted successfully"}


@router.get("/programmes/academic-targets")
async def list_academic_targets(
    group_id: Optional[str] = None,
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(AcademicTarget)
        .options(
            selectinload(AcademicTarget.group).selectinload(AcademicGroup.programme),
            selectinload(AcademicTarget.form_definition),
        )
        .order_by(AcademicTarget.sort_order.asc(), AcademicTarget.metric_name.asc())
    )
    if group_id:
        query = query.where(AcademicTarget.group_id == group_id)

    result = await db.execute(query)
    return [_serialize_academic_target(item) for item in result.scalars().all()]


@router.post("/programmes/academic-targets", status_code=201)
async def create_academic_target(
    payload: AcademicTargetUpsert,
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    group = (
        await db.execute(
            select(AcademicGroup).where(AcademicGroup.id == payload.group_id)
        )
    ).scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Academic group not found")

    metric_name = payload.metric_name.strip()
    if not metric_name:
        raise HTTPException(status_code=400, detail="Metric name is required")

    form_definition = None
    if payload.form_definition_id:
        form_definition = (
            await db.execute(
                select(FormDefinition).where(
                    FormDefinition.id == payload.form_definition_id
                )
            )
        ).scalar_one_or_none()
        if not form_definition:
            raise HTTPException(status_code=404, detail="Form definition not found")

    target = AcademicTarget(
        id=_uid(),
        group_id=payload.group_id,
        form_definition_id=payload.form_definition_id,
        metric_name=metric_name,
        category=(payload.category or "ACADEMIC").strip().upper(),
        target_value=max(int(payload.target_value), 0),
        sort_order=max(int(payload.sort_order), 0),
    )
    db.add(target)
    await db.commit()

    refreshed = await db.execute(
        select(AcademicTarget)
        .options(
            selectinload(AcademicTarget.group).selectinload(AcademicGroup.programme),
            selectinload(AcademicTarget.form_definition),
        )
        .where(AcademicTarget.id == target.id)
    )
    return _serialize_academic_target(refreshed.scalar_one())


@router.put("/programmes/academic-targets/{target_id}")
async def update_academic_target(
    target_id: str,
    payload: AcademicTargetUpsert,
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    target = (
        await db.execute(select(AcademicTarget).where(AcademicTarget.id == target_id))
    ).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Academic target not found")

    group = (
        await db.execute(
            select(AcademicGroup).where(AcademicGroup.id == payload.group_id)
        )
    ).scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Academic group not found")

    if payload.form_definition_id:
        form_definition = (
            await db.execute(
                select(FormDefinition).where(
                    FormDefinition.id == payload.form_definition_id
                )
            )
        ).scalar_one_or_none()
        if not form_definition:
            raise HTTPException(status_code=404, detail="Form definition not found")

    metric_name = payload.metric_name.strip()
    if not metric_name:
        raise HTTPException(status_code=400, detail="Metric name is required")

    target.group_id = payload.group_id
    target.form_definition_id = payload.form_definition_id
    target.metric_name = metric_name
    target.category = (payload.category or "ACADEMIC").strip().upper()
    target.target_value = max(int(payload.target_value), 0)
    target.sort_order = max(int(payload.sort_order), 0)

    await db.commit()

    refreshed = await db.execute(
        select(AcademicTarget)
        .options(
            selectinload(AcademicTarget.group).selectinload(AcademicGroup.programme),
            selectinload(AcademicTarget.form_definition),
        )
        .where(AcademicTarget.id == target.id)
    )
    return _serialize_academic_target(refreshed.scalar_one())


@router.delete("/programmes/academic-targets/{target_id}")
async def delete_academic_target(
    target_id: str,
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    target = (
        await db.execute(select(AcademicTarget).where(AcademicTarget.id == target_id))
    ).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Academic target not found")

    await db.delete(target)
    await db.commit()
    return {"message": "Academic target deleted successfully"}


@router.get("/programmes/academic-weightages")
async def list_academic_weightages(
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    forms_result = await db.execute(
        select(FormDefinition)
        .where(
            FormDefinition.is_active == True,
            FormDefinition.form_type == "CASE_RECORD",
        )
        .order_by(
            FormDefinition.department.asc(),
            FormDefinition.sort_order.asc(),
            FormDefinition.name.asc(),
        )
    )
    forms = list(forms_result.scalars().all())

    weightages_result = await db.execute(
        select(AcademicFormWeightage).options(
            selectinload(AcademicFormWeightage.form_definition)
        )
    )
    weightages = list(weightages_result.scalars().all())
    weightages_by_form_id = {item.form_definition_id: item for item in weightages}

    return [
        _serialize_case_record_form(form, weightages_by_form_id.get(form.id))
        for form in forms
    ]


@router.put("/programmes/academic-weightages/{form_definition_id}")
async def upsert_academic_weightage(
    form_definition_id: str,
    payload: AcademicWeightageUpsert,
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    form_definition = (
        await db.execute(
            select(FormDefinition).where(FormDefinition.id == form_definition_id)
        )
    ).scalar_one_or_none()
    if not form_definition:
        raise HTTPException(status_code=404, detail="Form definition not found")

    weightage = (
        await db.execute(
            select(AcademicFormWeightage).where(
                AcademicFormWeightage.form_definition_id == form_definition_id
            )
        )
    ).scalar_one_or_none()

    if weightage:
        weightage.points = max(int(payload.points), 0)
    else:
        weightage = AcademicFormWeightage(
            id=_uid(),
            form_definition_id=form_definition_id,
            points=max(int(payload.points), 0),
        )
        db.add(weightage)

    await db.commit()

    refreshed = (
        await db.execute(
            select(AcademicFormWeightage)
            .options(selectinload(AcademicFormWeightage.form_definition))
            .where(AcademicFormWeightage.form_definition_id == form_definition_id)
        )
    ).scalar_one()
    return _serialize_academic_weightage(refreshed)


@router.get("/programmes/students/{student_id}/academic-progress")
async def get_student_academic_progress_endpoint(
    student_id: str,
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    progress = await get_student_academic_progress(db, student_id=student_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Student not found")
    return progress


@router.get("/programmes/academic-groups/{group_id}/summary")
async def get_academic_group_summary(
    group_id: str,
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    context = await _load_academic_manager_context(db, group_id=group_id)
    groups = context["groups"]
    if not groups:
        raise HTTPException(status_code=404, detail="Academic group not found")

    group = groups[0]
    students = [
        student
        for student in context["students"]
        if student.academic_group_id == group.id
    ]
    student_ids = {student.id for student in students}
    approvals = [
        approval
        for approval in context["approvals"]
        if approval.student_id in student_ids
    ]

    standing_breakdown: dict[str, int] = defaultdict(int)
    approved_case_records = 0
    pending_approvals = 0
    attendance_values: list[float] = []

    for student in students:
        standing_breakdown[student.academic_standing or "Unknown"] += 1
        approved_case_records += len(
            context["approved_records_by_student"].get(student.id, [])
        )
        if student.attendance and student.attendance.overall is not None:
            attendance_values.append(float(student.attendance.overall))

    for approval in approvals:
        if approval.status == ApprovalStatus.PENDING:
            pending_approvals += 1

    avg_gpa = (
        round(sum(float(student.gpa or 0) for student in students) / len(students), 2)
        if students
        else 0.0
    )
    avg_attendance = (
        round(sum(attendance_values) / len(attendance_values), 2)
        if attendance_values
        else 0.0
    )

    return {
        "group": _serialize_academic_group(group),
        "students": [
            {
                "id": student.id,
                "student_id": student.student_id,
                "name": student.name,
                "year": student.year,
                "semester": student.semester,
                "program": student.program,
                "gpa": student.gpa,
                "academic_standing": student.academic_standing,
                "attendance_overall": float(student.attendance.overall)
                if student.attendance and student.attendance.overall is not None
                else None,
            }
            for student in students
        ],
        "targets": [
            _serialize_academic_target(target)
            for target in sorted(
                group.targets or [],
                key=lambda item: (item.sort_order, item.metric_name),
            )
        ],
        "summary": {
            "student_count": len(students),
            "target_count": len(list(group.targets or [])),
            "avg_gpa": avg_gpa,
            "standing_breakdown": dict(standing_breakdown),
            "approved_case_records": approved_case_records,
            "pending_approvals": pending_approvals,
            "avg_attendance_overall": avg_attendance,
        },
    }


@router.get("/programmes/academic-performance")
async def get_academic_performance(
    programme_id: Optional[str] = Query(None),
    group_id: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    semester: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("progress"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    context = await _load_academic_manager_context(
        db,
        programme_id=programme_id,
        group_id=group_id,
        year=year,
        semester=semester,
        search=search,
    )

    items = []
    for student in context["students"]:
        progress = await get_student_academic_progress(db, student_id=student.id)
        summary = progress["summary"] if progress else {}
        approvals = [
            approval
            for approval in context["approvals"]
            if approval.student_id == student.id
        ]
        approved_scores = [
            int(approval.score)
            for approval in approvals
            if approval.status == ApprovalStatus.APPROVED and approval.score is not None
        ]
        pending_case_records = sum(
            1 for approval in approvals if approval.status == ApprovalStatus.PENDING
        )

        items.append(
            {
                "student_id": student.id,
                "student_name": student.name,
                "student_code": student.student_id,
                "programme": student.program,
                "group_id": student.academic_group_id,
                "group_name": student.academic_group.name
                if student.academic_group
                else None,
                "year": student.year,
                "semester": student.semester,
                "gpa": float(student.gpa or 0),
                "attendance_overall": float(student.attendance.overall)
                if student.attendance and student.attendance.overall is not None
                else 0.0,
                "approved_case_records": int(summary.get("approved_case_records", 0)),
                "pending_case_records": pending_case_records,
                "completed_targets": int(summary.get("completed_targets", 0)),
                "total_targets": int(summary.get("total_targets", 0)),
                "overall_percent": float(summary.get("overall_percent", 0)),
                "total_earned_points": int(summary.get("total_earned_points", 0)),
                "avg_approval_score": round(
                    sum(approved_scores) / len(approved_scores), 2
                )
                if approved_scores
                else 0.0,
                "academic_standing": student.academic_standing,
            }
        )

    sort_map = {
        "progress": lambda item: item["overall_percent"],
        "points": lambda item: item["total_earned_points"],
        "approved_records": lambda item: item["approved_case_records"],
        "gpa": lambda item: item["gpa"],
        "attendance": lambda item: item["attendance_overall"],
    }
    items.sort(key=sort_map.get(sort_by, sort_map["progress"]), reverse=True)

    total = len(items)
    start = (page - 1) * limit
    paged_items = items[start : start + limit]

    return {
        "items": paged_items,
        "total": total,
        "page": page,
        "limit": limit,
        "summary": {
            "student_count": total,
            "avg_overall_percent": round(
                sum(item["overall_percent"] for item in items) / total, 2
            )
            if total
            else 0.0,
            "avg_gpa": round(sum(item["gpa"] for item in items) / total, 2)
            if total
            else 0.0,
            "avg_attendance_overall": round(
                sum(item["attendance_overall"] for item in items) / total, 2
            )
            if total
            else 0.0,
            "total_approved_case_records": sum(
                item["approved_case_records"] for item in items
            ),
        },
    }


@router.get("/programmes/academic-feedback")
async def get_academic_feedback(
    programme_id: Optional[str] = Query(None),
    group_id: Optional[str] = Query(None),
    student_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    department: Optional[str] = Query(None),
    has_comments: bool = Query(True),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    context = await _load_academic_manager_context(
        db,
        programme_id=programme_id,
        group_id=group_id,
        student_id=student_id,
        from_date=from_date,
        to_date=to_date,
    )

    items = []
    department_breakdown: dict[str, int] = defaultdict(int)
    score_values: list[int] = []

    for approval in context["approvals"]:
        if status_filter:
            try:
                expected_status = ApprovalStatus(status_filter.upper())
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid approval status")
            if approval.status != expected_status:
                continue

        case_record = approval.case_record
        if not case_record:
            continue
        if department and (case_record.department or "") != department:
            continue
        if has_comments and not (approval.comments or "").strip():
            continue
        if from_date and approval.created_at and approval.created_at.date() < from_date:
            continue
        if to_date and approval.created_at and approval.created_at.date() > to_date:
            continue

        student = approval.student
        group = student.academic_group if student else None
        faculty = approval.faculty

        items.append(
            {
                "approval_id": approval.id,
                "student_id": student.id if student else None,
                "student_name": student.name if student else None,
                "group_id": group.id if group else None,
                "group_name": group.name if group else None,
                "case_record_id": case_record.id,
                "form_name": case_record.form_name,
                "department": case_record.department,
                "procedure_name": case_record.procedure_name,
                "status": approval.status.value,
                "score": approval.score,
                "grade": case_record.grade,
                "comments": approval.comments,
                "faculty_id": faculty.id if faculty else None,
                "faculty_name": faculty.name if faculty else None,
                "created_at": _safe_iso(approval.created_at),
                "processed_at": _safe_iso(approval.processed_at),
            }
        )

        department_breakdown[case_record.department or "General"] += 1
        if approval.score is not None:
            score_values.append(int(approval.score))

    items.sort(
        key=lambda item: item["processed_at"] or item["created_at"] or "",
        reverse=True,
    )

    total = len(items)
    start = (page - 1) * limit
    paged_items = items[start : start + limit]

    return {
        "items": paged_items,
        "total": total,
        "page": page,
        "limit": limit,
        "summary": {
            "total_feedback_items": total,
            "approved_with_comments": sum(
                1 for item in items if item["status"] == ApprovalStatus.APPROVED.value
            ),
            "rejected_with_comments": sum(
                1 for item in items if item["status"] == ApprovalStatus.REJECTED.value
            ),
            "avg_score": round(sum(score_values) / len(score_values), 2)
            if score_values
            else 0.0,
            "department_breakdown": dict(department_breakdown),
        },
    }


@router.get("/programmes/academic-activity")
async def get_academic_activity(
    programme_id: Optional[str] = Query(None),
    group_id: Optional[str] = Query(None),
    student_id: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    granularity: str = Query("day"),
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    context = await _load_academic_manager_context(
        db,
        programme_id=programme_id,
        group_id=group_id,
        student_id=student_id,
        from_date=from_date,
        to_date=to_date,
    )

    timeline: dict[str, dict] = {}
    recent_activity: list[dict] = []

    def bucket_for(dt: datetime) -> str:
        if granularity == "month":
            return dt.strftime("%Y-%m")
        if granularity == "week":
            iso_year, iso_week, _ = dt.isocalendar()
            return f"{iso_year}-W{iso_week:02d}"
        return dt.strftime("%Y-%m-%d")

    for record in context["case_records"]:
        if not record.created_at:
            continue
        bucket = bucket_for(record.created_at)
        timeline.setdefault(
            bucket,
            {
                "period": bucket,
                "case_records_created": 0,
                "approvals_processed": 0,
                "approved_count": 0,
                "rejected_count": 0,
                "earned_points": 0,
            },
        )
        timeline[bucket]["case_records_created"] += 1

        student = record.student
        group = student.academic_group if student else None
        recent_activity.append(
            {
                "type": "CASE_RECORD_SUBMITTED",
                "student_id": student.id if student else None,
                "student_name": student.name if student else None,
                "group_name": group.name if group else None,
                "case_record_id": record.id,
                "form_name": record.form_name,
                "department": record.department,
                "procedure_name": record.procedure_name,
                "score": None,
                "comments": None,
                "timestamp": _safe_iso(record.created_at),
            }
        )

    for approval in context["approvals"]:
        if not approval.processed_at:
            continue
        bucket = bucket_for(approval.processed_at)
        timeline.setdefault(
            bucket,
            {
                "period": bucket,
                "case_records_created": 0,
                "approvals_processed": 0,
                "approved_count": 0,
                "rejected_count": 0,
                "earned_points": 0,
            },
        )
        timeline[bucket]["approvals_processed"] += 1

        case_record = approval.case_record
        student = approval.student
        group = student.academic_group if student else None

        if approval.status == ApprovalStatus.APPROVED:
            timeline[bucket]["approved_count"] += 1
            matched_form = (
                match_form_definition_for_record(case_record, context["forms"])
                if case_record
                else None
            )
            if matched_form:
                weightage = context["weightages_by_form_id"].get(matched_form.id)
                if weightage:
                    timeline[bucket]["earned_points"] += int(weightage.points or 0)
        elif approval.status == ApprovalStatus.REJECTED:
            timeline[bucket]["rejected_count"] += 1

        recent_activity.append(
            {
                "type": (
                    "CASE_RECORD_APPROVED"
                    if approval.status == ApprovalStatus.APPROVED
                    else "CASE_RECORD_REJECTED"
                    if approval.status == ApprovalStatus.REJECTED
                    else "CASE_RECORD_PENDING"
                ),
                "student_id": student.id if student else None,
                "student_name": student.name if student else None,
                "group_name": group.name if group else None,
                "case_record_id": case_record.id if case_record else None,
                "form_name": case_record.form_name if case_record else None,
                "department": case_record.department if case_record else None,
                "procedure_name": case_record.procedure_name if case_record else None,
                "score": approval.score,
                "comments": approval.comments,
                "timestamp": _safe_iso(approval.processed_at),
            }
        )

    timeline_items = sorted(timeline.values(), key=lambda item: item["period"])
    recent_activity.sort(key=lambda item: item["timestamp"] or "", reverse=True)

    return {
        "timeline": timeline_items,
        "recent_activity": recent_activity[:50],
        "summary": {
            "case_records_created": sum(
                item["case_records_created"] for item in timeline_items
            ),
            "approvals_processed": sum(
                item["approvals_processed"] for item in timeline_items
            ),
            "approved_count": sum(item["approved_count"] for item in timeline_items),
            "rejected_count": sum(item["rejected_count"] for item in timeline_items),
            "earned_points": sum(item["earned_points"] for item in timeline_items),
        },
    }


@router.get("/programmes/academic-analytics")
async def get_academic_analytics(
    programme_id: Optional[str] = Query(None),
    group_id: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    semester: Optional[int] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    context = await _load_academic_manager_context(
        db,
        programme_id=programme_id,
        group_id=group_id,
        year=year,
        semester=semester,
        from_date=from_date,
        to_date=to_date,
    )

    student_count = len(context["students"])
    group_count = len(context["groups"])
    avg_gpa = (
        round(
            sum(float(student.gpa or 0) for student in context["students"])
            / student_count,
            2,
        )
        if student_count
        else 0.0
    )

    attendance_values = [
        float(student.attendance.overall)
        for student in context["students"]
        if student.attendance and student.attendance.overall is not None
    ]
    avg_attendance = (
        round(sum(attendance_values) / len(attendance_values), 2)
        if attendance_values
        else 0.0
    )

    approved_case_records = 0
    pending_approvals = 0
    total_earned_points = 0
    progress_values: list[float] = []
    department_distribution: dict[str, int] = defaultdict(int)
    form_distribution: dict[str, dict] = defaultdict(
        lambda: {"approved_count": 0, "earned_points": 0}
    )
    score_distribution: dict[str, int] = defaultdict(int)
    group_comparison: dict[str, dict] = {}
    target_completion: list[dict] = []

    for student in context["students"]:
        progress = await get_student_academic_progress(db, student_id=student.id)
        if progress:
            summary = progress["summary"]
            approved_case_records += int(summary.get("approved_case_records", 0))
            total_earned_points += int(summary.get("total_earned_points", 0))
            progress_values.append(float(summary.get("overall_percent", 0)))

            group = student.academic_group
            if group:
                group_comparison.setdefault(
                    group.id,
                    {
                        "group_id": group.id,
                        "group_name": group.name,
                        "student_count": 0,
                        "avg_progress_percent_total": 0.0,
                        "avg_gpa_total": 0.0,
                        "approved_case_records": 0,
                        "total_earned_points": 0,
                    },
                )
                group_comparison[group.id]["student_count"] += 1
                group_comparison[group.id]["avg_progress_percent_total"] += float(
                    summary.get("overall_percent", 0)
                )
                group_comparison[group.id]["avg_gpa_total"] += float(student.gpa or 0)
                group_comparison[group.id]["approved_case_records"] += int(
                    summary.get("approved_case_records", 0)
                )
                group_comparison[group.id]["total_earned_points"] += int(
                    summary.get("total_earned_points", 0)
                )

            for target in progress.get("targets", []):
                target_completion.append(
                    {
                        "target_id": target.get("id"),
                        "metric_name": target.get("metric_name"),
                        "group_id": group.id if group else None,
                        "group_name": group.name if group else None,
                        "target_value_total": target.get("target_value", 0),
                        "completed_value_total": target.get("completed_value", 0),
                        "completion_percent": target.get("percent", 0),
                    }
                )

    for approval in context["approvals"]:
        if approval.status == ApprovalStatus.PENDING:
            pending_approvals += 1
        if approval.score is not None:
            score = int(approval.score)
            if score <= 2:
                score_distribution["0-2"] += 1
            elif score <= 4:
                score_distribution["3-4"] += 1
            elif score <= 6:
                score_distribution["5-6"] += 1
            elif score <= 8:
                score_distribution["7-8"] += 1
            else:
                score_distribution["9-10"] += 1

    for record in context["case_records"]:
        if not record.approval or record.approval.status != ApprovalStatus.APPROVED:
            continue
        department_distribution[record.department or "General"] += 1
        matched_form = match_form_definition_for_record(record, context["forms"])
        form_key = (
            matched_form.name if matched_form else (record.form_name or "Unknown Form")
        )
        form_distribution[form_key]["approved_count"] += 1
        if matched_form:
            weightage = context["weightages_by_form_id"].get(matched_form.id)
            if weightage:
                form_distribution[form_key]["earned_points"] += int(
                    weightage.points or 0
                )

    group_comparison_items = []
    for item in group_comparison.values():
        count = item["student_count"] or 1
        group_comparison_items.append(
            {
                "group_id": item["group_id"],
                "group_name": item["group_name"],
                "student_count": item["student_count"],
                "avg_progress_percent": round(
                    item["avg_progress_percent_total"] / count, 2
                ),
                "avg_gpa": round(item["avg_gpa_total"] / count, 2),
                "approved_case_records": item["approved_case_records"],
                "total_earned_points": item["total_earned_points"],
            }
        )

    return {
        "overview": {
            "student_count": student_count,
            "group_count": group_count,
            "approved_case_records": approved_case_records,
            "pending_approvals": pending_approvals,
            "avg_gpa": avg_gpa,
            "avg_attendance_overall": avg_attendance,
            "avg_overall_progress_percent": round(
                sum(progress_values) / len(progress_values), 2
            )
            if progress_values
            else 0.0,
            "total_earned_points": total_earned_points,
        },
        "target_completion": target_completion,
        "department_distribution": [
            {"department": key, "approved_count": value}
            for key, value in sorted(department_distribution.items())
        ],
        "form_distribution": [
            {
                "form_name": key,
                "approved_count": value["approved_count"],
                "earned_points": value["earned_points"],
            }
            for key, value in sorted(form_distribution.items())
        ],
        "score_distribution": dict(score_distribution),
        "group_comparison": sorted(
            group_comparison_items,
            key=lambda item: item["avg_progress_percent"],
            reverse=True,
        ),
    }


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


def _serialize_patient_category(
    item: PatientCategoryOption, usage_counts: dict[str, int]
) -> dict:
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
            select(PatientCategoryOption).where(
                func.lower(PatientCategoryOption.name) == normalized_name.casefold()
            )
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
        registration_fee=data.registration_fee
        if data.registration_fee is not None
        else 100,
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
        await db.execute(
            select(PatientCategoryOption).where(PatientCategoryOption.id == category_id)
        )
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
                .where(
                    func.lower(PatientCategoryOption.name) == normalized_name.casefold()
                )
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
            text(
                "UPDATE charge_prices SET tier = :new_name WHERE lower(tier) = :old_name"
            ),
            {"new_name": normalized_name, "old_name": previous_name.casefold()},
        )
        item.name = normalized_name

    if data.description is not None:
        item.description = data.description.strip() or None
    if data.color_primary is not None:
        item.color_primary = _normalize_hex_color(
            data.color_primary, DEFAULT_PATIENT_CATEGORY_COLOR_PRIMARY
        )
    if data.color_secondary is not None:
        item.color_secondary = _normalize_hex_color(
            data.color_secondary, DEFAULT_PATIENT_CATEGORY_COLOR_SECONDARY
        )
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
        await db.execute(
            select(PatientCategoryOption).where(PatientCategoryOption.id == category_id)
        )
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Patient category not found")

    usage_count = (
        await db.execute(
            select(func.count(Patient.id)).where(Patient.category == item.name)
        )
    ).scalar() or 0
    if usage_count:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a category that is already assigned to patients",
        )

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
    search: Optional[str] = Query(
        None, description="Search by ICD code, description, or category"
    ),
    include_inactive: bool = Query(
        True, description="Include inactive codes in the result"
    ),
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
            raise HTTPException(
                status_code=400, detail=f"ICD code '{code}' already exists"
            )
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
    unit: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    value_style: Literal["single", "slash"] = "single"
    is_active: bool = True
    sort_order: int = 0


class VitalParameterUpdate(BaseModel):
    display_name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    value_style: Optional[Literal["single", "slash"]] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


@router.get("/vital-parameters")
async def list_vital_parameters(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
    active_only: bool = Query(False, description="Return only active parameters"),
):
    """List all vital parameters configurations."""
    query = select(VitalParameter).order_by(
        VitalParameter.category, VitalParameter.sort_order
    )
    if active_only:
        query = query.where(VitalParameter.is_active == True)
    result = await db.execute(query)
    parameters = result.scalars().all()
    return [_serialize_vital_parameter(p) for p in parameters]


@router.post("/vital-parameters")
async def create_vital_parameter(
    data: VitalParameterCreate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new vital parameter configuration."""
    name = data.name.strip()
    display_name = data.display_name.strip()
    if not name or not display_name:
        raise HTTPException(
            status_code=400, detail="Name and display name are required"
        )

    # Check if parameter with same name exists
    existing = (
        await db.execute(select(VitalParameter).where(VitalParameter.name == name))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400, detail=f"Parameter '{name}' already exists"
        )

    unit = data.unit.strip()
    if not unit:
        raise HTTPException(status_code=400, detail="Unit is required")

    param = VitalParameter(
        id=_uid(),
        name=name,
        display_name=display_name,
        category=data.category,
        unit=unit,
        min_value=data.min_value,
        max_value=data.max_value,
        value_style=data.value_style,
        is_active=data.is_active,
        sort_order=data.sort_order,
    )
    db.add(param)
    await db.commit()
    return _serialize_vital_parameter(param)


@router.get("/vital-parameters/{param_id}")
async def get_vital_parameter(
    param_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Get a single vital parameter by ID."""
    param = (
        await db.execute(select(VitalParameter).where(VitalParameter.id == param_id))
    ).scalar_one_or_none()
    if not param:
        raise HTTPException(status_code=404, detail="Vital parameter not found")
    return _serialize_vital_parameter(param)


@router.patch("/vital-parameters/{param_id}")
async def update_vital_parameter(
    param_id: str,
    data: VitalParameterUpdate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Update a vital parameter configuration."""
    param = (
        await db.execute(select(VitalParameter).where(VitalParameter.id == param_id))
    ).scalar_one_or_none()
    if not param:
        raise HTTPException(status_code=404, detail="Vital parameter not found")

    update_data = data.model_dump(exclude_unset=True)
    if "unit" in update_data:
        unit = (update_data["unit"] or "").strip()
        if not unit:
            raise HTTPException(status_code=400, detail="Unit is required")
        update_data["unit"] = unit
    if "display_name" in update_data and update_data["display_name"] is not None:
        display_name = update_data["display_name"].strip()
        if not display_name:
            raise HTTPException(status_code=400, detail="Display name is required")
        update_data["display_name"] = display_name
    for key, value in update_data.items():
        setattr(param, key, value)

    await db.commit()
    return _serialize_vital_parameter(param)


@router.delete("/vital-parameters/{param_id}")
async def delete_vital_parameter(
    param_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Delete a vital parameter configuration (or deactivate it)."""
    param = (
        await db.execute(select(VitalParameter).where(VitalParameter.id == param_id))
    ).scalar_one_or_none()
    if not param:
        raise HTTPException(status_code=404, detail="Vital parameter not found")

    # Soft delete by deactivating
    param.is_active = False
    await db.commit()
    return {"message": f"Vital parameter '{param.display_name}' deactivated"}


# ── Feedback Forms ────────────────────────────────────────────────────────────


class FeedbackFormCreate(BaseModel):
    target_type: Literal["STUDENT", "GROUP"]
    target_id: str
    target_name: Optional[str] = None
    recipient_type: Literal["PATIENTS", "STUDENTS", "FACULTY"] = "PATIENTS"
    questions: list[str]


def _serialize_feedback_form(form: FeedbackForm) -> dict:
    return {
        "id": form.id,
        "target_type": form.target_type,
        "target_id": form.target_id,
        "target_name": form.target_name,
        "recipient_type": form.recipient_type,
        "questions": form.questions or [],
        "is_deployed": form.is_deployed,
        "created_by": form.created_by,
        "response_count": len(form.responses) if form.responses is not None else 0,
        "created_at": _safe_iso(form.created_at),
        "updated_at": _safe_iso(form.updated_at),
    }


@router.post("/feedback-forms")
async def create_feedback_form(
    data: FeedbackFormCreate,
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    if not data.questions:
        raise HTTPException(status_code=400, detail="At least one question is required")

    form = FeedbackForm(
        id=str(uuid.uuid4()),
        target_type=data.target_type,
        target_id=data.target_id,
        target_name=data.target_name,
        recipient_type=data.recipient_type,
        questions=data.questions,
        is_deployed=False,
        created_by=user.id,
    )
    db.add(form)
    await db.commit()
    created_form = (
        await db.execute(
            select(FeedbackForm)
            .options(selectinload(FeedbackForm.responses))
            .where(FeedbackForm.id == form.id)
        )
    ).scalar_one()
    return _serialize_feedback_form(created_form)


@router.get("/feedback-forms")
async def list_feedback_forms(
    target_type: Optional[str] = Query(None),
    target_id: Optional[str] = Query(None),
    is_deployed: Optional[bool] = Query(None),
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    query = select(FeedbackForm).options(selectinload(FeedbackForm.responses))
    if target_type:
        query = query.where(FeedbackForm.target_type == target_type)
    if target_id:
        query = query.where(FeedbackForm.target_id == target_id)
    if is_deployed is not None:
        query = query.where(FeedbackForm.is_deployed == is_deployed)
    query = query.order_by(FeedbackForm.created_at.desc())
    forms = (await db.execute(query)).scalars().all()
    return [_serialize_feedback_form(f) for f in forms]


@router.post("/feedback-forms/{form_id}/deploy")
async def deploy_feedback_form(
    form_id: str,
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    form = (
        await db.execute(
            select(FeedbackForm)
            .options(selectinload(FeedbackForm.responses))
            .where(FeedbackForm.id == form_id)
        )
    ).scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=404, detail="Feedback form not found")
    if form.is_deployed:
        raise HTTPException(status_code=400, detail="Form is already deployed")
    if not form.questions:
        raise HTTPException(status_code=400, detail="Cannot deploy a form with no questions")

    form.is_deployed = True
    await db.commit()
    return {"message": "Feedback form deployed successfully", "form": _serialize_feedback_form(form)}


@router.delete("/feedback-forms/{form_id}")
async def delete_feedback_form(
    form_id: str,
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    form = (
        await db.execute(select(FeedbackForm).where(FeedbackForm.id == form_id))
    ).scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=404, detail="Feedback form not found")
    await db.delete(form)
    await db.commit()
    return {"message": "Feedback form deleted"}


class FeedbackResponseSubmit(BaseModel):
    ratings: dict[str, int]  # {question_index_str: 1-5}
    overall_satisfaction: Optional[Literal[
        "VERY_SATISFIED", "SATISFIED", "NEUTRAL", "UNSATISFIED", "VERY_UNSATISFIED"
    ]] = None
    respondent_id: Optional[str] = None


@router.post("/feedback-forms/{form_id}/respond")
async def submit_feedback_response(
    form_id: str,
    data: FeedbackResponseSubmit,
    db: AsyncSession = Depends(get_db),
):
    """Submit a response to a deployed feedback form (public endpoint for recipients)."""
    form = (
        await db.execute(
            select(FeedbackForm).where(FeedbackForm.id == form_id, FeedbackForm.is_deployed == True)  # noqa: E712
        )
    ).scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=404, detail="Feedback form not found or not deployed")

    # Validate scores
    for score in data.ratings.values():
        if not 1 <= int(score) <= 5:
            raise HTTPException(status_code=400, detail="Ratings must be between 1 and 5")

    response = FeedbackFormResponse(
        id=str(uuid.uuid4()),
        form_id=form_id,
        respondent_id=data.respondent_id,
        ratings=data.ratings,
        overall_satisfaction=data.overall_satisfaction,
    )
    db.add(response)
    await db.commit()
    return {"message": "Response submitted successfully"}


@router.get("/feedback-forms/{form_id}/analytics")
async def get_feedback_form_analytics(
    form_id: str,
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACADEMIC_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    form = (
        await db.execute(
            select(FeedbackForm)
            .options(selectinload(FeedbackForm.responses))
            .where(FeedbackForm.id == form_id)
        )
    ).scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=404, detail="Feedback form not found")

    responses = form.responses or []
    total = len(responses)

    satisfaction_counts: dict[str, int] = {
        "VERY_SATISFIED": 0,
        "SATISFIED": 0,
        "NEUTRAL": 0,
        "UNSATISFIED": 0,
        "VERY_UNSATISFIED": 0,
    }
    completed = 0
    all_scores: list[float] = []
    # Per-question score accumulation: index -> [scores]
    question_scores: dict[int, list[int]] = {i: [] for i in range(len(form.questions or []))}

    for resp in responses:
        if resp.overall_satisfaction and resp.overall_satisfaction in satisfaction_counts:
            satisfaction_counts[resp.overall_satisfaction] += 1

        ratings = resp.ratings or {}
        if ratings:
            completed += 1
            for key, score in ratings.items():
                try:
                    idx = int(key)
                    question_scores.setdefault(idx, []).append(int(score))
                    all_scores.append(int(score))
                except (ValueError, TypeError):
                    pass

    avg_rating = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0.0
    completion_rate = round((completed / total) * 100) if total > 0 else 0

    questions_list = form.questions or []
    category_breakdown = []
    for i, question_text in enumerate(questions_list):
        scores = question_scores.get(i, [])
        avg = round(sum(scores) / len(scores), 1) if scores else 0.0
        category_breakdown.append({"question": question_text, "avg_score": avg, "count": len(scores)})

    return {
        "form_id": form.id,
        "target_type": form.target_type,
        "target_id": form.target_id,
        "target_name": form.target_name,
        "recipient_type": form.recipient_type,
        "is_deployed": form.is_deployed,
        "total_responses": total,
        "completion_rate": completion_rate,
        "avg_rating": avg_rating,
        "satisfaction_distribution": satisfaction_counts,
        "category_breakdown": category_breakdown,
    }

