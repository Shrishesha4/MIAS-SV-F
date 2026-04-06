"""Admin panel API – dashboard, user management, departments, analytics."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, text, and_, distinct, extract
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, date
from typing import Optional
from pydantic import BaseModel, EmailStr
import uuid

from app.database import get_db
from app.api.deps import require_role
from app.models.user import User, UserRole
from app.models.patient import Patient, PatientCategory
from app.models.student import Student
from app.models.faculty import Faculty
from app.models.department import Department
from app.models.programme import Programme
from app.models.admission import Admission
from app.models.prescription import Prescription
from app.models.vital import Vital
from app.models.medical_record import MedicalRecord
from app.models.case_record import CaseRecord, Approval, ApprovalStatus
from app.models.notification import PatientNotification
from app.core.security import get_password_hash

router = APIRouter(prefix="/admin", tags=["Admin"])

# ── helpers ──────────────────────────────────────────────────────────


def _uid() -> str:
    return str(uuid.uuid4())


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
    patient_categories = {str(row[0].value) if row[0] else "UNKNOWN": row[1] for row in category_result.all()}

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
    """Delete a user entirely."""
    target = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    await db.delete(target)
    await db.commit()
    return {"message": f"User {target.username} has been deleted"}


# ── Create User (Admin) ──────────────────────────────────────────────


class AdminCreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str
    # PATIENT fields
    name: Optional[str] = None
    date_of_birth: Optional[str] = None  # YYYY-MM-DD
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    phone: Optional[str] = None
    # STUDENT fields
    year: Optional[int] = None
    semester: Optional[int] = None
    program: Optional[str] = None
    # FACULTY fields
    department: Optional[str] = None
    specialty: Optional[str] = None


def _generate_patient_id():
    return f"PT{datetime.utcnow().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"

def _generate_student_id():
    return f"ST{datetime.utcnow().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"

def _generate_faculty_id():
    return f"FA{datetime.utcnow().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"


@router.post("/users", status_code=201)
async def admin_create_user(
    data: AdminCreateUserRequest,
    admin: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Admin creates a new user directly (no email verification required)."""
    # Check uniqueness
    if (await db.execute(select(User).where(User.username == data.username))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")
    if (await db.execute(select(User).where(User.email == data.email))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already exists")

    try:
        role = UserRole(data.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {data.role}")

    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        username=data.username,
        email=data.email,
        password_hash=get_password_hash(data.password),
        role=role,
        is_active=True,
    )
    db.add(user)

    name = data.name or data.username

    if role == UserRole.PATIENT:
        dob = datetime.strptime(data.date_of_birth, "%Y-%m-%d").date() if data.date_of_birth else date.today()
        from app.models.patient import Gender
        db.add(Patient(
            id=str(uuid.uuid4()),
            patient_id=_generate_patient_id(),
            user_id=user_id,
            name=name,
            date_of_birth=dob,
            gender=Gender(data.gender) if data.gender else Gender.OTHER,
            blood_group=data.blood_group or "Unknown",
            phone=data.phone or "",
            email=data.email,
            address="",
        ))
    elif role == UserRole.STUDENT:
        db.add(Student(
            id=str(uuid.uuid4()),
            student_id=_generate_student_id(),
            user_id=user_id,
            name=name,
            year=data.year or 1,
            semester=data.semester or 1,
            program=data.program or "",
            gpa=0.0,
            academic_advisor="",
        ))
    elif role == UserRole.FACULTY:
        db.add(Faculty(
            id=str(uuid.uuid4()),
            faculty_id=_generate_faculty_id(),
            user_id=user_id,
            name=name,
            department=data.department or "",
            specialty=data.specialty or "",
            phone=data.phone or "",
            email=data.email,
        ))
    # ADMIN role: no extra profile record needed

    await db.commit()
    return {"message": f"User {data.username} created successfully", "user_id": user_id}


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
