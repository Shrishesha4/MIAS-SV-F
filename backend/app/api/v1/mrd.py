"""MRD (Medical Records Department) read-only API endpoints.

All queries run against the analytics/snapshot database.
Audit rows are written to OLTP.
"""

import time
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_role
from app.core.mrd_governance import (
    MrdGovernance,
    get_cached_response,
    set_cached_response,
    write_audit,
)
from app.database import get_analytics_db, get_db
from app.models.admission import Admission
from app.models.medical_record import MedicalFinding, MedicalImage, MedicalRecord, RecordType
from app.models.operation_theater import OTBooking, OTStatus
from app.models.patient import Patient
from app.models.prescription import Prescription, PrescriptionMedication
from app.models.report import Report, ReportFinding, ReportImage
from app.models.student import ClinicAppointment, Clinic
from app.models.user import User, UserRole

router = APIRouter(prefix="/mrd", tags=["MRD"])

_MAX_TIME_SPAN_DAYS = 366
_DEFAULT_PAGE_SIZE = 50
_MAX_PAGE_SIZE = 200


# ── Pydantic models ─────────────────────────────────────────────────


class TimeWindowParams(BaseModel):
    from_date: date
    to_date: date

    @field_validator("to_date")
    @classmethod
    def validate_window(cls, v, info):
        from_date = info.data.get("from_date")
        if from_date and v:
            if v < from_date:
                raise ValueError("to_date must be >= from_date")
            span = (v - from_date).days
            if span > _MAX_TIME_SPAN_DAYS:
                raise ValueError(
                    f"Time window cannot exceed {_MAX_TIME_SPAN_DAYS} days"
                )
        return v


class CursorPage(BaseModel):
    """Keyset cursor: base64 of 'created_at|id'. Opaque to clients."""

    cursor: Optional[str] = None
    page_size: int = _DEFAULT_PAGE_SIZE

    @field_validator("page_size")
    @classmethod
    def clamp_page_size(cls, v):
        return max(1, min(v, _MAX_PAGE_SIZE))


class MrdHealthResponse(BaseModel):
    status: str
    snapshot_age_hours: Optional[float] = None
    snapshot_timestamp: Optional[str] = None
    analytics_db_connected: bool


def _parse_cursor(cursor: Optional[str]) -> tuple[Optional[datetime], Optional[str]]:
    """Decode keyset cursor → (created_at, id)."""
    if not cursor:
        return None, None
    import base64

    try:
        decoded = base64.urlsafe_b64decode(cursor).decode()
        ts_str, row_id = decoded.split("|", 1)
        return datetime.fromisoformat(ts_str), row_id
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid cursor",
        )


def _encode_cursor(created_at: datetime, row_id: str) -> str:
    import base64

    raw = f"{created_at.isoformat()}|{row_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


# ── Helpers ──────────────────────────────────────────────────────────


async def _governed_query(
    user: User,
    gov: MrdGovernance,
    analytics_db: AsyncSession,
    oltp_db: AsyncSession,
    route: str,
    filters: dict,
    query_fn,
):
    """Run a governed query: cache check, semaphore, audit, cache set."""
    cached = await get_cached_response(route, user.id, filters)
    if cached is not None:
        await gov.release()
        return cached

    start = time.monotonic()
    audit_status = "ok"
    rows_returned = 0
    try:
        result = await query_fn(analytics_db)
        rows_returned = result.get("total", len(result.get("items", [])))
        await set_cached_response(route, user.id, filters, result)
        return result
    except Exception as exc:
        audit_status = f"error: {type(exc).__name__}"
        raise
    finally:
        duration_ms = int((time.monotonic() - start) * 1000)
        await gov.release()
        try:
            await write_audit(
                oltp_db, user.id, route, filters, rows_returned, duration_ms, audit_status
            )
        except Exception:
            pass  # Audit failure must not break the request


# ── Health ───────────────────────────────────────────────────────────


@router.get("/health", response_model=MrdHealthResponse)
async def mrd_health(
    user: User = Depends(require_role(UserRole.MRD)),
    analytics_db: AsyncSession = Depends(get_analytics_db),
):
    """Report snapshot age and analytics DB connectivity."""
    try:
        result = await analytics_db.execute(text("SELECT NOW()"))
        db_now = result.scalar()
        # Try to read snapshot metadata table (created by snapshot pipeline)
        try:
            meta = await analytics_db.execute(
                text("SELECT snapshot_timestamp FROM mrd_snapshot_meta ORDER BY snapshot_timestamp DESC LIMIT 1")
            )
            snapshot_ts = meta.scalar()
        except Exception:
            snapshot_ts = None

        age_hours = None
        ts_str = None
        if snapshot_ts:
            age_hours = round((db_now - snapshot_ts).total_seconds() / 3600, 1)
            ts_str = snapshot_ts.isoformat()

        stale = age_hours is not None and age_hours > 36
        return MrdHealthResponse(
            status="stale" if stale else "ok",
            snapshot_age_hours=age_hours,
            snapshot_timestamp=ts_str,
            analytics_db_connected=True,
        )
    except Exception:
        return MrdHealthResponse(
            status="unavailable",
            analytics_db_connected=False,
        )


# ── Census Dashboard ─────────────────────────────────────────────────


def _date_to_dt_range(from_date: date, to_date: date):
    """Convert date pair to datetime range for queries."""
    return (
        datetime.combine(from_date, datetime.min.time()),
        datetime.combine(to_date, datetime.max.time()),
    )


@router.get("/census", summary="Census counts for MRD dashboard")
async def get_census(
    from_date: date = Query(...),
    to_date: date = Query(...),
    user: User = Depends(require_role(UserRole.MRD)),
    gov: MrdGovernance = Depends(MrdGovernance()),
    analytics_db: AsyncSession = Depends(get_analytics_db),
    oltp_db: AsyncSession = Depends(get_db),
):
    """Return aggregate counts: OP, IP, OT, births, deaths, investigations, discharges."""
    if (to_date - from_date).days > _MAX_TIME_SPAN_DAYS:
        raise HTTPException(400, "Date range exceeds 366 days")

    filters = {"from_date": str(from_date), "to_date": str(to_date)}
    from_dt, to_dt = _date_to_dt_range(from_date, to_date)

    async def query(db):
        # OP COUNT — completed clinic appointments
        op_res = await db.execute(
            select(func.count(ClinicAppointment.id)).where(
                ClinicAppointment.appointment_date.between(from_dt, to_dt),
                ClinicAppointment.status == "Completed",
            )
        )
        op_count = op_res.scalar() or 0

        # IP COUNT — admissions in range (active or discharged during range)
        ip_res = await db.execute(
            select(func.count(Admission.id)).where(
                Admission.admission_date.between(from_dt, to_dt),
                Admission.status.in_(["Active", "Discharged", "Transferred"]),
            )
        )
        ip_count = ip_res.scalar() or 0

        # OT PROCEDURES — completed OT bookings
        ot_res = await db.execute(
            select(func.count(OTBooking.id)).where(
                OTBooking.date.between(str(from_date), str(to_date)),
                OTBooking.status == OTStatus.COMPLETED,
            )
        )
        ot_count = ot_res.scalar() or 0

        # BIRTHS — admissions with birth-related diagnosis
        birth_res = await db.execute(
            select(func.count(Admission.id)).where(
                Admission.admission_date.between(from_dt, to_dt),
                func.lower(Admission.diagnosis).op("SIMILAR TO")(
                    "%(birth|deliver|lscs|caesarean|c-section|newborn|neonatal)%"
                ),
            )
        )
        births = birth_res.scalar() or 0

        # DEATHS — discharged with death-related summary
        death_res = await db.execute(
            select(func.count(Admission.id)).where(
                Admission.discharge_date.between(from_dt, to_dt),
                Admission.status == "Discharged",
                func.lower(func.coalesce(Admission.discharge_summary, "")).op("SIMILAR TO")(
                    "%(death|expired|demise|brought dead|doa)%"
                ),
            )
        )
        deaths = death_res.scalar() or 0

        # INVESTIGATIONS — reports (non-pending)
        inv_res = await db.execute(
            select(func.count(Report.id)).where(
                Report.date.between(from_dt, to_dt),
            )
        )
        investigations = inv_res.scalar() or 0

        # DISCHARGES — admissions discharged in date range
        dis_res = await db.execute(
            select(func.count(Admission.id)).where(
                Admission.discharge_date.between(from_dt, to_dt),
                Admission.status == "Discharged",
            )
        )
        discharges = dis_res.scalar() or 0

        return {
            "from_date": str(from_date),
            "to_date": str(to_date),
            "op_count": op_count,
            "ip_count": ip_count,
            "ot_procedures": ot_count,
            "births": births,
            "deaths": deaths,
            "investigations": investigations,
            "discharges": discharges,
            "total": op_count + ip_count + ot_count + births + deaths + investigations + discharges,
        }

    return await _governed_query(
        user, gov, analytics_db, oltp_db, "/mrd/census", filters, query
    )


def _empty_dept_row(dept: str) -> dict:
    return {
        "department": dept,
        "op": 0, "ip": 0, "ot": 0,
        "inv_total": 0, "discharges": 0,
    }


@router.get("/census/department-breakdown", summary="Department-wise activity breakdown")
async def get_department_breakdown(
    from_date: date = Query(...),
    to_date: date = Query(...),
    user: User = Depends(require_role(UserRole.MRD)),
    gov: MrdGovernance = Depends(MrdGovernance()),
    analytics_db: AsyncSession = Depends(get_analytics_db),
    oltp_db: AsyncSession = Depends(get_db),
):
    """Hospital-wide activity breakdown by department."""
    if (to_date - from_date).days > _MAX_TIME_SPAN_DAYS:
        raise HTTPException(400, "Date range exceeds 366 days")

    from_dt, to_dt = _date_to_dt_range(from_date, to_date)
    filters = {"from_date": str(from_date), "to_date": str(to_date)}

    async def query(db):
        # OP by department (clinic department)
        op_stmt = (
            select(Clinic.department, func.count(ClinicAppointment.id))
            .join(Clinic, ClinicAppointment.clinic_id == Clinic.id)
            .where(
                ClinicAppointment.appointment_date.between(from_dt, to_dt),
                ClinicAppointment.status == "Completed",
            )
            .group_by(Clinic.department)
        )
        op_rows = (await db.execute(op_stmt)).all()

        # IP by department
        ip_stmt = (
            select(Admission.department, func.count(Admission.id))
            .where(
                Admission.admission_date.between(from_dt, to_dt),
                Admission.status.in_(["Active", "Discharged", "Transferred"]),
            )
            .group_by(Admission.department)
        )
        ip_rows = (await db.execute(ip_stmt)).all()

        # Investigations by department
        inv_stmt = (
            select(Report.department, func.count(Report.id))
            .where(Report.date.between(from_dt, to_dt))
            .group_by(Report.department)
        )
        inv_rows = (await db.execute(inv_stmt)).all()

        # Discharges by department
        dis_stmt = (
            select(Admission.department, func.count(Admission.id))
            .where(
                Admission.discharge_date.between(from_dt, to_dt),
                Admission.status == "Discharged",
            )
            .group_by(Admission.department)
        )
        dis_rows = (await db.execute(dis_stmt)).all()

        # Merge into department map
        depts: dict[str, dict] = {}
        for dept, count in op_rows:
            depts.setdefault(dept, _empty_dept_row(dept))["op"] = count
        for dept, count in ip_rows:
            depts.setdefault(dept, _empty_dept_row(dept))["ip"] = count
        for dept, count in inv_rows:
            depts.setdefault(dept, _empty_dept_row(dept))["inv_total"] = count
        for dept, count in dis_rows:
            depts.setdefault(dept, _empty_dept_row(dept))["discharges"] = count

        # Calculate grand totals
        rows = sorted(depts.values(), key=lambda r: r["department"])
        grand = _empty_dept_row("Grand Total")
        for r in rows:
            for k in grand:
                if k != "department" and isinstance(grand[k], int):
                    grand[k] += r.get(k, 0)
        rows.append(grand)

        return {"departments": rows, "total": len(rows) - 1}

    return await _governed_query(
        user, gov, analytics_db, oltp_db, "/mrd/census/department-breakdown", filters, query
    )


@router.get("/census/{category}/patients", summary="Patient list for a census category")
async def get_census_patients(
    category: str,
    from_date: date = Query(...),
    to_date: date = Query(...),
    department: Optional[str] = Query(None),
    cursor: Optional[str] = None,
    page_size: int = Query(50, ge=1, le=200),
    user: User = Depends(require_role(UserRole.MRD)),
    gov: MrdGovernance = Depends(MrdGovernance()),
    analytics_db: AsyncSession = Depends(get_analytics_db),
    oltp_db: AsyncSession = Depends(get_db),
):
    """Return patient records for a specific census category."""
    valid_categories = {"op", "ip", "ot", "births", "deaths", "investigations", "discharges"}
    if category not in valid_categories:
        raise HTTPException(400, f"Invalid category. Must be one of: {valid_categories}")
    if (to_date - from_date).days > _MAX_TIME_SPAN_DAYS:
        raise HTTPException(400, "Date range exceeds 366 days")

    from_dt, to_dt = _date_to_dt_range(from_date, to_date)
    filters = {
        "category": category, "from_date": str(from_date), "to_date": str(to_date),
        "department": department, "cursor": cursor, "page_size": page_size,
    }

    async def query(db):
        items = []

        if category == "op":
            stmt = (
                select(ClinicAppointment, Patient, Clinic)
                .join(Patient, ClinicAppointment.patient_id == Patient.id)
                .join(Clinic, ClinicAppointment.clinic_id == Clinic.id)
                .where(
                    ClinicAppointment.appointment_date.between(from_dt, to_dt),
                    ClinicAppointment.status == "Completed",
                )
            )
            if department:
                stmt = stmt.where(Clinic.department == department)
            stmt = stmt.order_by(ClinicAppointment.appointment_date.desc()).limit(page_size)
            result = await db.execute(stmt)
            for appt, pat, clinic in result.all():
                items.append({
                    "id": pat.id,
                    "patient_id": pat.patient_id,
                    "name": pat.name,
                    "age": _calc_age(pat.date_of_birth),
                    "diagnosis": pat.primary_diagnosis or "",
                    "department": clinic.department,
                    "date": str(appt.appointment_date),
                    "time": appt.appointment_time or "",
                })

        elif category == "ip":
            stmt = (
                select(Admission, Patient)
                .join(Patient, Admission.patient_id == Patient.id)
                .where(
                    Admission.admission_date.between(from_dt, to_dt),
                    Admission.status.in_(["Active", "Discharged", "Transferred"]),
                )
            )
            if department:
                stmt = stmt.where(Admission.department == department)
            stmt = stmt.order_by(Admission.admission_date.desc()).limit(page_size)
            result = await db.execute(stmt)
            for adm, pat in result.all():
                items.append({
                    "id": pat.id,
                    "patient_id": pat.patient_id,
                    "name": pat.name,
                    "age": _calc_age(pat.date_of_birth),
                    "diagnosis": adm.diagnosis or "",
                    "department": adm.department,
                    "date": str(adm.admission_date),
                    "time": "",
                    "status": adm.status,
                })

        elif category == "ot":
            stmt = (
                select(OTBooking, Patient)
                .join(Patient, OTBooking.patient_id == Patient.id)
                .where(
                    OTBooking.date.between(str(from_date), str(to_date)),
                    OTBooking.status == OTStatus.COMPLETED,
                )
            )
            stmt = stmt.order_by(OTBooking.date.desc()).limit(page_size)
            result = await db.execute(stmt)
            for booking, pat in result.all():
                items.append({
                    "id": pat.id,
                    "patient_id": pat.patient_id,
                    "name": pat.name,
                    "age": _calc_age(pat.date_of_birth),
                    "diagnosis": booking.procedure,
                    "department": "",
                    "date": booking.date,
                    "time": booking.start_time,
                })

        elif category == "births":
            stmt = (
                select(Admission, Patient)
                .join(Patient, Admission.patient_id == Patient.id)
                .where(
                    Admission.admission_date.between(from_dt, to_dt),
                    func.lower(Admission.diagnosis).op("SIMILAR TO")(
                        "%(birth|deliver|lscs|caesarean|c-section|newborn|neonatal)%"
                    ),
                )
            )
            if department:
                stmt = stmt.where(Admission.department == department)
            stmt = stmt.order_by(Admission.admission_date.desc()).limit(page_size)
            result = await db.execute(stmt)
            for adm, pat in result.all():
                items.append({
                    "id": pat.id,
                    "patient_id": pat.patient_id,
                    "name": pat.name,
                    "age": _calc_age(pat.date_of_birth),
                    "diagnosis": adm.diagnosis or "",
                    "department": adm.department,
                    "date": str(adm.admission_date),
                    "time": "",
                })

        elif category == "deaths":
            stmt = (
                select(Admission, Patient)
                .join(Patient, Admission.patient_id == Patient.id)
                .where(
                    Admission.discharge_date.between(from_dt, to_dt),
                    Admission.status == "Discharged",
                    func.lower(func.coalesce(Admission.discharge_summary, "")).op("SIMILAR TO")(
                        "%(death|expired|demise|brought dead|doa)%"
                    ),
                )
            )
            if department:
                stmt = stmt.where(Admission.department == department)
            stmt = stmt.order_by(Admission.discharge_date.desc()).limit(page_size)
            result = await db.execute(stmt)
            for adm, pat in result.all():
                items.append({
                    "id": pat.id,
                    "patient_id": pat.patient_id,
                    "name": pat.name,
                    "age": _calc_age(pat.date_of_birth),
                    "diagnosis": adm.diagnosis or "",
                    "department": adm.department,
                    "date": str(adm.discharge_date),
                    "time": "",
                })

        elif category == "investigations":
            stmt = (
                select(Report, Patient)
                .join(Patient, Report.patient_id == Patient.id)
                .where(Report.date.between(from_dt, to_dt))
            )
            if department:
                stmt = stmt.where(Report.department == department)
            stmt = stmt.order_by(Report.date.desc()).limit(page_size)
            result = await db.execute(stmt)
            for rpt, pat in result.all():
                items.append({
                    "id": pat.id,
                    "patient_id": pat.patient_id,
                    "name": pat.name,
                    "age": _calc_age(pat.date_of_birth),
                    "diagnosis": f"{rpt.title} - {rpt.department}",
                    "department": rpt.department,
                    "date": str(rpt.date),
                    "time": rpt.time or "",
                    "status": rpt.status.value if rpt.status else "",
                })

        elif category == "discharges":
            stmt = (
                select(Admission, Patient)
                .join(Patient, Admission.patient_id == Patient.id)
                .where(
                    Admission.discharge_date.between(from_dt, to_dt),
                    Admission.status == "Discharged",
                )
            )
            if department:
                stmt = stmt.where(Admission.department == department)
            stmt = stmt.order_by(Admission.discharge_date.desc()).limit(page_size)
            result = await db.execute(stmt)
            for adm, pat in result.all():
                items.append({
                    "id": pat.id,
                    "patient_id": pat.patient_id,
                    "name": pat.name,
                    "age": _calc_age(pat.date_of_birth),
                    "diagnosis": adm.diagnosis or "",
                    "department": adm.department,
                    "date": str(adm.discharge_date),
                    "time": "",
                })

        return {"items": items, "total": len(items), "category": category}

    return await _governed_query(
        user, gov, analytics_db, oltp_db, f"/mrd/census/{category}/patients", filters, query
    )


def _calc_age(dob) -> int:
    """Calculate age from date of birth."""
    if not dob:
        return 0
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))



# ── Patient Search ───────────────────────────────────────────────────


@router.get("/patients/search")
async def search_patients(
    user: User = Depends(require_role(UserRole.MRD)),
    gov: MrdGovernance = Depends(MrdGovernance()),
    analytics_db: AsyncSession = Depends(get_analytics_db),
    oltp_db: AsyncSession = Depends(get_db),
    name: Optional[str] = Query(None, min_length=1, max_length=200),
    patient_id: Optional[str] = Query(None, max_length=50),
    phone: Optional[str] = Query(None, max_length=20),
    dob_from: Optional[date] = None,
    dob_to: Optional[date] = None,
    cursor: Optional[str] = None,
    page_size: int = Query(_DEFAULT_PAGE_SIZE, ge=1, le=_MAX_PAGE_SIZE),
):
    filters = {
        "name": name,
        "patient_id": patient_id,
        "phone": phone,
        "dob_from": str(dob_from) if dob_from else None,
        "dob_to": str(dob_to) if dob_to else None,
        "cursor": cursor,
        "page_size": page_size,
    }

    async def query(db):
        stmt = select(Patient)
        if name:
            stmt = stmt.where(Patient.name.ilike(f"%{name}%"))
        if patient_id:
            stmt = stmt.where(Patient.patient_id == patient_id)
        if phone:
            stmt = stmt.where(Patient.phone == phone)
        if dob_from:
            stmt = stmt.where(Patient.date_of_birth >= dob_from)
        if dob_to:
            stmt = stmt.where(Patient.date_of_birth <= dob_to)

        # Keyset pagination on (created_at DESC, id DESC)
        cursor_ts, cursor_id = _parse_cursor(cursor)
        if cursor_ts and cursor_id:
            stmt = stmt.where(
                (Patient.created_at < cursor_ts)
                | ((Patient.created_at == cursor_ts) & (Patient.id < cursor_id))
            )
        stmt = stmt.order_by(Patient.created_at.desc(), Patient.id.desc())
        stmt = stmt.limit(page_size + 1)

        result = await db.execute(stmt)
        rows = result.scalars().all()

        has_more = len(rows) > page_size
        items = rows[:page_size]
        next_cursor = None
        if has_more and items:
            last = items[-1]
            next_cursor = _encode_cursor(last.created_at, last.id)

        return {
            "items": [
                {
                    "id": p.id,
                    "patient_id": p.patient_id,
                    "name": p.name,
                    "date_of_birth": str(p.date_of_birth),
                    "gender": p.gender.value if p.gender else None,
                    "phone": p.phone,
                    "category": p.category,
                }
                for p in items
            ],
            "next_cursor": next_cursor,
            "total": len(items),
        }

    return await _governed_query(
        user, gov, analytics_db, oltp_db, "/mrd/patients/search", filters, query
    )


# ── Medical Records ──────────────────────────────────────────────────


@router.get("/records")
async def list_records(
    user: User = Depends(require_role(UserRole.MRD)),
    gov: MrdGovernance = Depends(MrdGovernance()),
    analytics_db: AsyncSession = Depends(get_analytics_db),
    oltp_db: AsyncSession = Depends(get_db),
    from_date: date = Query(..., description="Start date (required)"),
    to_date: date = Query(..., description="End date (required)"),
    record_type: Optional[str] = Query(None, description="CONSULTATION|LABORATORY|PROCEDURE|MEDICATION"),
    department: Optional[str] = None,
    patient_id: Optional[str] = None,
    performed_by: Optional[str] = None,
    cursor: Optional[str] = None,
    page_size: int = Query(_DEFAULT_PAGE_SIZE, ge=1, le=_MAX_PAGE_SIZE),
):
    # Validate time window
    tw = TimeWindowParams(from_date=from_date, to_date=to_date)

    filters = {
        "from_date": str(from_date),
        "to_date": str(to_date),
        "record_type": record_type,
        "department": department,
        "patient_id": patient_id,
        "performed_by": performed_by,
        "cursor": cursor,
        "page_size": page_size,
    }

    async def query(db):
        from_dt = datetime.combine(from_date, datetime.min.time())
        to_dt = datetime.combine(to_date, datetime.max.time())

        stmt = select(MedicalRecord).where(
            MedicalRecord.date.between(from_dt, to_dt)
        )
        if record_type:
            stmt = stmt.where(MedicalRecord.type == record_type)
        if department:
            stmt = stmt.where(MedicalRecord.department == department)
        if patient_id:
            stmt = stmt.where(MedicalRecord.patient_id == patient_id)
        if performed_by:
            stmt = stmt.where(MedicalRecord.performed_by.ilike(f"%{performed_by}%"))

        cursor_ts, cursor_id = _parse_cursor(cursor)
        if cursor_ts and cursor_id:
            stmt = stmt.where(
                (MedicalRecord.date < cursor_ts)
                | ((MedicalRecord.date == cursor_ts) & (MedicalRecord.id < cursor_id))
            )
        stmt = stmt.order_by(MedicalRecord.date.desc(), MedicalRecord.id.desc())
        stmt = stmt.limit(page_size + 1)

        result = await db.execute(stmt)
        rows = result.scalars().all()

        has_more = len(rows) > page_size
        items = rows[:page_size]
        next_cursor = None
        if has_more and items:
            last = items[-1]
            next_cursor = _encode_cursor(last.date, last.id)

        return {
            "items": [
                {
                    "id": r.id,
                    "patient_id": r.patient_id,
                    "date": str(r.date),
                    "time": r.time,
                    "type": r.type.value if r.type else None,
                    "description": r.description,
                    "performed_by": r.performed_by,
                    "department": r.department,
                    "status": r.status,
                    "diagnosis": r.diagnosis,
                }
                for r in items
            ],
            "next_cursor": next_cursor,
            "total": len(items),
        }

    return await _governed_query(
        user, gov, analytics_db, oltp_db, "/mrd/records", filters, query
    )


@router.get("/records/{record_id}")
async def get_record(
    record_id: str,
    user: User = Depends(require_role(UserRole.MRD)),
    gov: MrdGovernance = Depends(MrdGovernance()),
    analytics_db: AsyncSession = Depends(get_analytics_db),
    oltp_db: AsyncSession = Depends(get_db),
):
    filters = {"record_id": record_id}

    async def query(db):
        stmt = (
            select(MedicalRecord)
            .options(
                selectinload(MedicalRecord.findings),
                selectinload(MedicalRecord.images),
            )
            .where(MedicalRecord.id == record_id)
        )
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")

        return {
            "id": record.id,
            "patient_id": record.patient_id,
            "date": str(record.date),
            "time": record.time,
            "type": record.type.value if record.type else None,
            "description": record.description,
            "performed_by": record.performed_by,
            "supervised_by": record.supervised_by,
            "department": record.department,
            "status": record.status,
            "diagnosis": record.diagnosis,
            "recommendations": record.recommendations,
            "findings": [
                {
                    "id": f.id,
                    "parameter": f.parameter,
                    "value": f.value,
                    "reference": f.reference,
                    "status": f.status,
                }
                for f in record.findings
            ],
            "images": [
                {
                    "id": img.id,
                    "title": img.title,
                    "description": img.description,
                    "url": img.url,
                    "type": img.type,
                }
                for img in record.images
            ],
            "total": 1,
        }

    return await _governed_query(
        user, gov, analytics_db, oltp_db, "/mrd/records/{id}", filters, query
    )


# ── Prescriptions ────────────────────────────────────────────────────


@router.get("/prescriptions")
async def list_prescriptions(
    user: User = Depends(require_role(UserRole.MRD)),
    gov: MrdGovernance = Depends(MrdGovernance()),
    analytics_db: AsyncSession = Depends(get_analytics_db),
    oltp_db: AsyncSession = Depends(get_db),
    from_date: date = Query(...),
    to_date: date = Query(...),
    patient_id: Optional[str] = None,
    department: Optional[str] = None,
    doctor: Optional[str] = None,
    cursor: Optional[str] = None,
    page_size: int = Query(_DEFAULT_PAGE_SIZE, ge=1, le=_MAX_PAGE_SIZE),
):
    tw = TimeWindowParams(from_date=from_date, to_date=to_date)
    filters = {
        "from_date": str(from_date),
        "to_date": str(to_date),
        "patient_id": patient_id,
        "department": department,
        "doctor": doctor,
        "cursor": cursor,
        "page_size": page_size,
    }

    async def query(db):
        from_dt = datetime.combine(from_date, datetime.min.time())
        to_dt = datetime.combine(to_date, datetime.max.time())

        stmt = select(Prescription).where(
            Prescription.date.between(from_dt, to_dt)
        )
        if patient_id:
            stmt = stmt.where(Prescription.patient_id == patient_id)
        if department:
            stmt = stmt.where(Prescription.department == department)
        if doctor:
            stmt = stmt.where(Prescription.doctor.ilike(f"%{doctor}%"))

        cursor_ts, cursor_id = _parse_cursor(cursor)
        if cursor_ts and cursor_id:
            stmt = stmt.where(
                (Prescription.date < cursor_ts)
                | ((Prescription.date == cursor_ts) & (Prescription.id < cursor_id))
            )
        stmt = stmt.order_by(Prescription.date.desc(), Prescription.id.desc())
        stmt = stmt.limit(page_size + 1)

        result = await db.execute(stmt)
        rows = result.scalars().all()

        has_more = len(rows) > page_size
        items = rows[:page_size]
        next_cursor = None
        if has_more and items:
            last = items[-1]
            next_cursor = _encode_cursor(last.date, last.id)

        return {
            "items": [
                {
                    "id": p.id,
                    "prescription_id": p.prescription_id,
                    "patient_id": p.patient_id,
                    "date": str(p.date),
                    "doctor": p.doctor,
                    "department": p.department,
                    "status": p.status.value if p.status else None,
                    "notes": p.notes,
                }
                for p in items
            ],
            "next_cursor": next_cursor,
            "total": len(items),
        }

    return await _governed_query(
        user, gov, analytics_db, oltp_db, "/mrd/prescriptions", filters, query
    )


# ── Reports ──────────────────────────────────────────────────────────


@router.get("/reports")
async def list_reports(
    user: User = Depends(require_role(UserRole.MRD)),
    gov: MrdGovernance = Depends(MrdGovernance()),
    analytics_db: AsyncSession = Depends(get_analytics_db),
    oltp_db: AsyncSession = Depends(get_db),
    from_date: date = Query(...),
    to_date: date = Query(...),
    patient_id: Optional[str] = None,
    department: Optional[str] = None,
    report_type: Optional[str] = None,
    report_status: Optional[str] = None,
    cursor: Optional[str] = None,
    page_size: int = Query(_DEFAULT_PAGE_SIZE, ge=1, le=_MAX_PAGE_SIZE),
):
    tw = TimeWindowParams(from_date=from_date, to_date=to_date)
    filters = {
        "from_date": str(from_date),
        "to_date": str(to_date),
        "patient_id": patient_id,
        "department": department,
        "report_type": report_type,
        "report_status": report_status,
        "cursor": cursor,
        "page_size": page_size,
    }

    async def query(db):
        from_dt = datetime.combine(from_date, datetime.min.time())
        to_dt = datetime.combine(to_date, datetime.max.time())

        stmt = select(Report).where(Report.date.between(from_dt, to_dt))
        if patient_id:
            stmt = stmt.where(Report.patient_id == patient_id)
        if department:
            stmt = stmt.where(Report.department == department)
        if report_type:
            stmt = stmt.where(Report.type == report_type)
        if report_status:
            stmt = stmt.where(Report.status == report_status)

        cursor_ts, cursor_id = _parse_cursor(cursor)
        if cursor_ts and cursor_id:
            stmt = stmt.where(
                (Report.date < cursor_ts)
                | ((Report.date == cursor_ts) & (Report.id < cursor_id))
            )
        stmt = stmt.order_by(Report.date.desc(), Report.id.desc())
        stmt = stmt.limit(page_size + 1)

        result = await db.execute(stmt)
        rows = result.scalars().all()

        has_more = len(rows) > page_size
        items = rows[:page_size]
        next_cursor = None
        if has_more and items:
            last = items[-1]
            next_cursor = _encode_cursor(last.date, last.id)

        return {
            "items": [
                {
                    "id": r.id,
                    "patient_id": r.patient_id,
                    "date": str(r.date),
                    "title": r.title,
                    "type": r.type,
                    "department": r.department,
                    "ordered_by": r.ordered_by,
                    "status": r.status.value if r.status else None,
                    "result_summary": r.result_summary,
                }
                for r in items
            ],
            "next_cursor": next_cursor,
            "total": len(items),
        }

    return await _governed_query(
        user, gov, analytics_db, oltp_db, "/mrd/reports", filters, query
    )


# ── Admissions ───────────────────────────────────────────────────────


@router.get("/admissions")
async def list_admissions(
    user: User = Depends(require_role(UserRole.MRD)),
    gov: MrdGovernance = Depends(MrdGovernance()),
    analytics_db: AsyncSession = Depends(get_analytics_db),
    oltp_db: AsyncSession = Depends(get_db),
    from_date: date = Query(...),
    to_date: date = Query(...),
    patient_id: Optional[str] = None,
    department: Optional[str] = None,
    admission_status: Optional[str] = None,
    cursor: Optional[str] = None,
    page_size: int = Query(_DEFAULT_PAGE_SIZE, ge=1, le=_MAX_PAGE_SIZE),
):
    tw = TimeWindowParams(from_date=from_date, to_date=to_date)
    filters = {
        "from_date": str(from_date),
        "to_date": str(to_date),
        "patient_id": patient_id,
        "department": department,
        "admission_status": admission_status,
        "cursor": cursor,
        "page_size": page_size,
    }

    async def query(db):
        from_dt = datetime.combine(from_date, datetime.min.time())
        to_dt = datetime.combine(to_date, datetime.max.time())

        stmt = select(Admission).where(
            Admission.admission_date.between(from_dt, to_dt)
        )
        if patient_id:
            stmt = stmt.where(Admission.patient_id == patient_id)
        if department:
            stmt = stmt.where(Admission.department == department)
        if admission_status:
            stmt = stmt.where(Admission.status == admission_status)

        cursor_ts, cursor_id = _parse_cursor(cursor)
        if cursor_ts and cursor_id:
            stmt = stmt.where(
                (Admission.admission_date < cursor_ts)
                | (
                    (Admission.admission_date == cursor_ts)
                    & (Admission.id < cursor_id)
                )
            )
        stmt = stmt.order_by(
            Admission.admission_date.desc(), Admission.id.desc()
        )
        stmt = stmt.limit(page_size + 1)

        result = await db.execute(stmt)
        rows = result.scalars().all()

        has_more = len(rows) > page_size
        items = rows[:page_size]
        next_cursor = None
        if has_more and items:
            last = items[-1]
            next_cursor = _encode_cursor(last.admission_date, last.id)

        return {
            "items": [
                {
                    "id": a.id,
                    "patient_id": a.patient_id,
                    "admission_date": str(a.admission_date),
                    "discharge_date": str(a.discharge_date) if a.discharge_date else None,
                    "department": a.department,
                    "ward": a.ward,
                    "bed_number": a.bed_number,
                    "attending_doctor": a.attending_doctor,
                    "status": a.status,
                    "diagnosis": a.diagnosis,
                }
                for a in items
            ],
            "next_cursor": next_cursor,
            "total": len(items),
        }

    return await _governed_query(
        user, gov, analytics_db, oltp_db, "/mrd/admissions", filters, query
    )


# ── Export endpoints ──────────────────────────────────────────


class ExportRequest(BaseModel):
    export_type: str
    from_date: date
    to_date: date

    @field_validator("export_type")
    @classmethod
    def valid_type(cls, v):
        allowed = {"records", "prescriptions", "admissions"}
        if v not in allowed:
            raise ValueError(f"export_type must be one of {allowed}")
        return v

    @field_validator("to_date")
    @classmethod
    def bounded_window(cls, v, info):
        fd = info.data.get("from_date")
        if fd and v:
            if v < fd:
                raise ValueError("to_date must be >= from_date")
            if (v - fd).days > 366:
                raise ValueError("Export window cannot exceed 366 days")
        return v


@router.post(
    "/exports",
    summary="Enqueue an export job",
    dependencies=[Depends(MrdGovernance)],
)
async def create_export(
    body: ExportRequest,
    user: User = Depends(require_role(UserRole.MRD)),
):
    from app.services.mrd_export import enqueue_export

    filters = {
        "from_date": body.from_date.isoformat(),
        "to_date": body.to_date.isoformat(),
    }
    job_id = await enqueue_export(
        user_id=user.id,
        export_type=body.export_type,
        filters=filters,
    )
    return {"job_id": job_id, "status": "queued"}


@router.get(
    "/exports",
    summary="List export jobs for current user",
    dependencies=[Depends(MrdGovernance)],
)
async def list_exports(
    user: User = Depends(require_role(UserRole.MRD)),
):
    from app.services.mrd_export import list_user_jobs

    jobs = await list_user_jobs(user.id)
    return {"jobs": jobs}


@router.get(
    "/exports/{job_id}",
    summary="Get export job status",
    dependencies=[Depends(MrdGovernance)],
)
async def get_export(
    job_id: str,
    user: User = Depends(require_role(UserRole.MRD)),
):
    from app.services.mrd_export import get_job_status

    job = await get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")
    if job.get("user_id") != user.id:
        raise HTTPException(status_code=403, detail="Not your export job")
    return job
