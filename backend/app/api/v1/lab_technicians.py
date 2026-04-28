from datetime import datetime
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_role
from app.core.exceptions import NotFoundException
from app.database import get_db
from app.models.lab import Lab, LabTestParameter
from app.models.lab_technician import LabTechnician, LabTechnicianGroup
from app.models.report import Report, ReportFinding, ReportStatus
from app.models.user import User, UserRole
from app.services.daily_checkins import ensure_daily_checkin


router = APIRouter(prefix="/lab-technicians", tags=["Lab Technicians"])


class ActiveLabSelectionRequest(BaseModel):
    lab_id: str


class TechnicianGroupUpsertRequest(BaseModel):
    name: str
    description: Optional[str] = None
    technician_ids: List[str] = Field(default_factory=list)
    lab_ids: List[str] = Field(default_factory=list)
    is_active: bool = True


class ReportFindingInput(BaseModel):
    parameter: str
    value: str
    reference: Optional[str] = None
    status: str = "Normal"


class ReportResultRequest(BaseModel):
    findings: List[ReportFindingInput] = Field(default_factory=list)
    status: str
    result_summary: Optional[str] = None
    notes: Optional[str] = None
    supervised_by: Optional[str] = None


def _serialize_lab(lab: Lab) -> dict:
    return {
        "id": lab.id,
        "name": lab.name,
        "department": lab.department,
        "lab_type": lab.lab_type,
        "location": lab.location,
        "is_active": lab.is_active,
    }


def _permitted_labs(technician: LabTechnician, *, active_only: bool) -> list[Lab]:
    group = technician.group
    if not group or not group.is_active:
        return []
    labs = list(group.labs or [])
    if active_only:
        return [lab for lab in labs if lab.is_active]
    return labs


def _serialize_group(group: LabTechnicianGroup) -> dict:
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "is_active": group.is_active,
        "technician_count": len(group.technicians or []),
        "technician_ids": [technician.id for technician in group.technicians or []],
        "technicians": [
            {
                "id": technician.id,
                "technician_id": technician.technician_id,
                "name": technician.name,
            }
            for technician in group.technicians or []
        ],
        "lab_ids": [lab.id for lab in group.labs or []],
        "labs": [_serialize_lab(lab) for lab in group.labs or []],
    }


def _serialize_technician(technician: LabTechnician) -> dict:
    permitted_labs = _permitted_labs(technician, active_only=True)
    permitted_lab_map = {lab.id: lab for lab in permitted_labs}
    active_lab = permitted_lab_map.get(technician.active_lab_id or "")

    return {
        "id": technician.id,
        "technician_id": technician.technician_id,
        "user_id": technician.user_id,
        "name": technician.name,
        "phone": technician.phone,
        "email": technician.email,
        "photo": technician.photo,
        "department": technician.department,
        "group_id": technician.group_id,
        "group_name": technician.group.name if technician.group else None,
        "has_selected_lab": 1 if active_lab else 0,
        "active_lab": _serialize_lab(active_lab) if active_lab else None,
        "last_checked_in_at": technician.last_checked_in_at.isoformat() if technician.last_checked_in_at else None,
        "permitted_labs": [_serialize_lab(lab) for lab in permitted_labs],
    }


def _compute_finding_status(
    value_str: str,
    low,
    critically_low,
    high,
    critically_high,
) -> str:
    try:
        v = float(value_str)
    except (ValueError, TypeError):
        return "Normal"
    if critically_low is not None and v <= float(critically_low):
        return "Critically Low"
    if critically_high is not None and v >= float(critically_high):
        return "Critically High"
    if low is not None and v < float(low):
        return "Low"
    if high is not None and v > float(high):
        return "High"
    return "Normal"


def _serialize_report_item(
    report: Report,
    *,
    viewer_user_id: str,
    test_parameters: list[dict] | None = None,
) -> dict:
    workflow_status = "COMPLETED"
    if report.status == ReportStatus.PENDING and not report.accepted_by_user_id:
        workflow_status = "NEW"
    elif report.status == ReportStatus.PENDING:
        workflow_status = "IN_PROGRESS"

    return {
        "id": report.id,
        "lab_id": report.lab_id,
        "patient_id": report.patient_id,
        "patient_name": report.patient.name if report.patient else "Unknown Patient",
        "patient_code": report.patient.patient_id if report.patient else None,
        "title": report.title,
        "type": report.type,
        "department": report.department,
        "ordered_by": report.ordered_by,
        "ordered_at": report.date.isoformat() if report.date else None,
        "time": report.time,
        "status": report.status.value if report.status else None,
        "workflow_status": workflow_status,
        "accepted_by_user_id": report.accepted_by_user_id,
        "accepted_at": report.accepted_at.isoformat() if report.accepted_at else None,
        "accepted_by_name": report.performed_by,
        "accepted_by_me": report.accepted_by_user_id == viewer_user_id,
        "performed_by": report.performed_by,
        "supervised_by": report.supervised_by,
        "result_summary": report.result_summary,
        "notes": report.notes,
        "findings": [
            {
                "id": finding.id,
                "parameter": finding.parameter,
                "value": finding.value,
                "reference": finding.reference,
                "status": finding.status,
            }
            for finding in report.findings or []
        ],
        "lab_test_id": report.lab_test_id,
        "test_parameters": test_parameters,
    }


async def _get_technician_or_404(db: AsyncSession, *, user_id: str) -> LabTechnician:
    result = await db.execute(
        select(LabTechnician)
        .options(
            selectinload(LabTechnician.group).selectinload(LabTechnicianGroup.labs),
            selectinload(LabTechnician.active_lab),
        )
        .where(LabTechnician.user_id == user_id)
    )
    technician = result.scalar_one_or_none()
    if not technician:
        raise HTTPException(status_code=404, detail="Lab technician profile not found")
    return technician


async def _get_permitted_report(
    db: AsyncSession,
    *,
    report_id: str,
    technician: LabTechnician,
) -> Report:
    permitted_lab_ids = {lab.id for lab in _permitted_labs(technician, active_only=True)}
    result = await db.execute(
        select(Report)
        .options(selectinload(Report.patient), selectinload(Report.findings))
        .where(Report.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise NotFoundException("Report not found")
    if not report.lab_id or report.lab_id not in permitted_lab_ids:
        raise HTTPException(status_code=403, detail="You do not have access to this lab order")
    return report


def _sync_technician_active_lab(technician: LabTechnician, allowed_lab_ids: set[str]) -> None:
    if technician.active_lab_id and technician.active_lab_id not in allowed_lab_ids:
        technician.active_lab_id = None
        technician.has_selected_lab = 0


async def _resolve_group_inputs(
    db: AsyncSession,
    *,
    technician_ids: list[str],
    lab_ids: list[str],
) -> tuple[list[LabTechnician], list[Lab]]:
    technicians_result = await db.execute(
        select(LabTechnician).where(LabTechnician.id.in_(technician_ids or ["__none__"]))
    )
    technicians = technicians_result.scalars().all()
    if len(technicians) != len(set(technician_ids)):
        raise HTTPException(status_code=400, detail="One or more technicians are invalid")

    labs_result = await db.execute(
        select(Lab).where(Lab.id.in_(lab_ids or ["__none__"]))
    )
    labs = labs_result.scalars().all()
    if len(labs) != len(set(lab_ids)):
        raise HTTPException(status_code=400, detail="One or more labs are invalid")

    return technicians, labs


@router.get("")
async def list_lab_technicians(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LabTechnician)
        .options(
            selectinload(LabTechnician.group).selectinload(LabTechnicianGroup.labs),
            selectinload(LabTechnician.active_lab),
        )
        .order_by(LabTechnician.name.asc())
    )
    return [_serialize_technician(technician) for technician in result.scalars().all()]


@router.get("/groups")
async def list_lab_technician_groups(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LabTechnicianGroup)
        .options(
            selectinload(LabTechnicianGroup.labs),
            selectinload(LabTechnicianGroup.technicians),
        )
        .order_by(LabTechnicianGroup.name.asc())
    )
    return [_serialize_group(group) for group in result.scalars().all()]


@router.post("/groups")
async def create_lab_technician_group(
    data: TechnicianGroupUpsertRequest,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Group name is required")

    existing = await db.execute(select(LabTechnicianGroup).where(LabTechnicianGroup.name == name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A technician batch with this name already exists")

    technicians, labs = await _resolve_group_inputs(
        db,
        technician_ids=data.technician_ids,
        lab_ids=data.lab_ids,
    )

    group = LabTechnicianGroup(
        id=str(uuid.uuid4()),
        name=name,
        description=data.description.strip() if data.description else None,
        is_active=data.is_active,
    )
    group.labs = labs
    db.add(group)
    await db.flush()

    allowed_lab_ids = {lab.id for lab in labs}
    for technician in technicians:
        technician.group_id = group.id
        _sync_technician_active_lab(technician, allowed_lab_ids)

    await db.commit()
    result = await db.execute(
        select(LabTechnicianGroup)
        .options(
            selectinload(LabTechnicianGroup.labs),
            selectinload(LabTechnicianGroup.technicians),
        )
        .where(LabTechnicianGroup.id == group.id)
    )
    return _serialize_group(result.scalar_one())


@router.put("/groups/{group_id}")
async def update_lab_technician_group(
    group_id: str,
    data: TechnicianGroupUpsertRequest,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LabTechnicianGroup)
        .options(
            selectinload(LabTechnicianGroup.labs),
            selectinload(LabTechnicianGroup.technicians),
        )
        .where(LabTechnicianGroup.id == group_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise NotFoundException("Technician batch not found")

    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Group name is required")

    name_conflict = await db.execute(
        select(LabTechnicianGroup)
        .where(LabTechnicianGroup.name == name, LabTechnicianGroup.id != group_id)
    )
    if name_conflict.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A technician batch with this name already exists")

    technicians, labs = await _resolve_group_inputs(
        db,
        technician_ids=data.technician_ids,
        lab_ids=data.lab_ids,
    )

    group.name = name
    group.description = data.description.strip() if data.description else None
    group.is_active = data.is_active
    group.labs = labs

    selected_ids = {technician.id for technician in technicians}
    allowed_lab_ids = {lab.id for lab in labs}
    for technician in list(group.technicians or []):
        if technician.id not in selected_ids:
            technician.group_id = None
            technician.active_lab_id = None
            technician.has_selected_lab = 0

    for technician in technicians:
        technician.group_id = group.id
        _sync_technician_active_lab(technician, allowed_lab_ids)

    await db.commit()
    refreshed = await db.execute(
        select(LabTechnicianGroup)
        .options(
            selectinload(LabTechnicianGroup.labs),
            selectinload(LabTechnicianGroup.technicians),
        )
        .where(LabTechnicianGroup.id == group.id)
    )
    return _serialize_group(refreshed.scalar_one())


@router.delete("/groups/{group_id}")
async def delete_lab_technician_group(
    group_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LabTechnicianGroup)
        .options(selectinload(LabTechnicianGroup.technicians))
        .where(LabTechnicianGroup.id == group_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise NotFoundException("Technician batch not found")

    for technician in list(group.technicians or []):
        technician.group_id = None
        technician.active_lab_id = None
        technician.has_selected_lab = 0

    await db.delete(group)
    await db.commit()
    return {"message": "Technician batch deleted successfully"}


@router.get("/me")
async def get_current_lab_technician(
    user: User = Depends(require_role(UserRole.LAB_TECHNICIAN)),
    db: AsyncSession = Depends(get_db),
):
    technician = await _get_technician_or_404(db, user_id=user.id)
    return _serialize_technician(technician)


@router.put("/me/lab")
async def select_active_lab(
    data: ActiveLabSelectionRequest,
    user: User = Depends(require_role(UserRole.LAB_TECHNICIAN)),
    db: AsyncSession = Depends(get_db),
):
    technician = await _get_technician_or_404(db, user_id=user.id)
    permitted_lab_map = {lab.id: lab for lab in _permitted_labs(technician, active_only=True)}
    lab = permitted_lab_map.get(data.lab_id)
    if not lab:
        raise HTTPException(status_code=403, detail="This technician is not permitted to check in to that lab")

    technician.active_lab_id = lab.id
    technician.has_selected_lab = 1
    technician.last_checked_in_at = datetime.utcnow()
    await ensure_daily_checkin(db, user_id=user.id, role=user.role)

    await db.commit()
    refreshed = await _get_technician_or_404(db, user_id=user.id)
    return _serialize_technician(refreshed)


@router.get("/me/dashboard")
async def get_lab_dashboard(
    user: User = Depends(require_role(UserRole.LAB_TECHNICIAN)),
    db: AsyncSession = Depends(get_db),
):
    technician = await _get_technician_or_404(db, user_id=user.id)
    serialized_technician = _serialize_technician(technician)
    active_lab = technician.active_lab if serialized_technician["active_lab"] else None
    if not active_lab:
        return {
            "technician": serialized_technician,
            "new_orders": [],
            "in_progress_orders": [],
            "completed_reports": [],
        }

    result = await db.execute(
        select(Report)
        .options(selectinload(Report.patient), selectinload(Report.findings))
        .where(Report.lab_id == active_lab.id)
        .order_by(Report.date.desc(), Report.created_at.desc())
    )
    reports = result.scalars().all()

    return {
        "technician": serialized_technician,
        "new_orders": [
            _serialize_report_item(report, viewer_user_id=user.id)
            for report in reports
            if report.status == ReportStatus.PENDING and not report.accepted_by_user_id
        ],
        "in_progress_orders": [
            _serialize_report_item(report, viewer_user_id=user.id)
            for report in reports
            if report.status == ReportStatus.PENDING and report.accepted_by_user_id
        ],
        "completed_reports": [
            _serialize_report_item(report, viewer_user_id=user.id)
            for report in reports
            if report.status != ReportStatus.PENDING
        ][:50],
    }


@router.get("/reports/{report_id}")
async def get_lab_report_detail(
    report_id: str,
    user: User = Depends(require_role(UserRole.LAB_TECHNICIAN)),
    db: AsyncSession = Depends(get_db),
):
    technician = await _get_technician_or_404(db, user_id=user.id)
    report = await _get_permitted_report(db, report_id=report_id, technician=technician)
    test_parameters = None
    if report.lab_test_id:
        params_result = await db.execute(
            select(LabTestParameter)
            .where(LabTestParameter.test_id == report.lab_test_id, LabTestParameter.is_active == True)
            .order_by(LabTestParameter.sort_order, LabTestParameter.name)
        )
        params = params_result.scalars().all()
        if params:
            test_parameters = [
                {
                    "id": p.id,
                    "name": p.name,
                    "unit": p.unit,
                    "reference_required": p.reference_required,
                    "normal_range": p.normal_range,
                    "low": float(p.low) if p.low is not None else None,
                    "critically_low": float(p.critically_low) if p.critically_low is not None else None,
                    "high": float(p.high) if p.high is not None else None,
                    "critically_high": float(p.critically_high) if p.critically_high is not None else None,
                }
                for p in params
            ]
    return _serialize_report_item(report, viewer_user_id=user.id, test_parameters=test_parameters)


@router.post("/reports/{report_id}/accept")
async def accept_lab_report(
    report_id: str,
    user: User = Depends(require_role(UserRole.LAB_TECHNICIAN)),
    db: AsyncSession = Depends(get_db),
):
    technician = await _get_technician_or_404(db, user_id=user.id)
    report = await _get_permitted_report(db, report_id=report_id, technician=technician)
    if report.status != ReportStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only pending lab orders can be accepted")
    if report.accepted_by_user_id and report.accepted_by_user_id != user.id:
        raise HTTPException(status_code=409, detail="This lab order has already been accepted by another technician")

    report.accepted_by_user_id = user.id
    report.accepted_at = report.accepted_at or datetime.utcnow()
    report.performed_by = technician.name
    await db.commit()
    return {"message": "Lab order accepted successfully"}


@router.put("/reports/{report_id}/results")
async def save_lab_report_results(
    report_id: str,
    data: ReportResultRequest,
    user: User = Depends(require_role(UserRole.LAB_TECHNICIAN)),
    db: AsyncSession = Depends(get_db),
):
    technician = await _get_technician_or_404(db, user_id=user.id)
    report = await _get_permitted_report(db, report_id=report_id, technician=technician)
    if report.status != ReportStatus.PENDING:
        raise HTTPException(status_code=400, detail="Results can only be entered for pending lab orders")
    if report.accepted_by_user_id and report.accepted_by_user_id != user.id:
        raise HTTPException(status_code=409, detail="This lab order is assigned to another technician")

    try:
        resolved_status = ReportStatus(data.status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Status must be NORMAL, ABNORMAL, or CRITICAL")

    if resolved_status == ReportStatus.PENDING:
        raise HTTPException(status_code=400, detail="Completed lab results cannot remain pending")
    if not data.result_summary and not data.findings:
        raise HTTPException(status_code=400, detail="Add either a summary or at least one result row")

    report.accepted_by_user_id = user.id
    report.accepted_at = report.accepted_at or datetime.utcnow()
    report.performed_by = technician.name
    report.supervised_by = data.supervised_by.strip() if data.supervised_by else None
    if data.result_summary is not None:
        report.result_summary = data.result_summary.strip() or None
    if data.notes is not None:
        report.notes = data.notes.strip() or None
    report.status = resolved_status

    # Build a parameter lookup map for auto-computing status if test_parameters are defined
    param_map: dict[str, LabTestParameter] = {}
    if report.lab_test_id:
        params_result = await db.execute(
            select(LabTestParameter)
            .where(LabTestParameter.test_id == report.lab_test_id, LabTestParameter.is_active == True)
        )
        for p in params_result.scalars().all():
            param_map[p.name.strip().lower()] = p

    report.findings = [
        ReportFinding(
            id=str(uuid.uuid4()),
            parameter=finding.parameter.strip(),
            value=finding.value.strip(),
            reference=finding.reference.strip() if finding.reference else None,
            status=(
                _compute_finding_status(
                    finding.value.strip(),
                    p.low, p.critically_low, p.high, p.critically_high,
                )
                if (p := param_map.get(finding.parameter.strip().lower())) and p.reference_required
                else finding.status.strip() or "Normal"
            ),
        )
        for finding in data.findings
        if finding.parameter.strip() and finding.value.strip()
    ]

    await db.commit()
    refreshed = await _get_permitted_report(db, report_id=report_id, technician=technician)
    return _serialize_report_item(refreshed, viewer_user_id=user.id)