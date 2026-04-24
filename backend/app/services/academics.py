from __future__ import annotations

from collections import defaultdict
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academic import AcademicFormWeightage, AcademicGroup, AcademicTarget
from app.models.case_record import Approval, ApprovalStatus, CaseRecord
from app.models.form_definition import FormDefinition
from app.models.student import Student


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


def normalize_metric_key(value: Any) -> str:
    normalized = normalize_text(value)
    if not normalized:
        return ""
    return normalized.replace(" ", "_").replace("-", "_")


def metric_label_to_key(value: Any) -> str:
    return normalize_metric_key(value)


def build_form_metric_keys(form: Optional[FormDefinition]) -> set[str]:
    if form is None:
        return set()

    form_name = normalize_text(getattr(form, "name", None))
    form_slug = normalize_text(getattr(form, "slug", None))
    form_procedure = normalize_text(getattr(form, "procedure_name", None))
    form_department = normalize_text(getattr(form, "department", None))

    keys = {
        normalize_metric_key(form_name),
        normalize_metric_key(form_slug),
        normalize_metric_key(form_procedure),
        normalize_metric_key(form_department),
    }

    if form_department and form_procedure:
        keys.add(normalize_metric_key(f"{form_department}_{form_procedure}"))
        keys.add(normalize_metric_key(f"{form_department} {form_procedure}"))

    return {key for key in keys if key}


def record_signature(record: Optional[CaseRecord]) -> tuple[str, str, str]:
    if record is None:
        return ("", "", "")

    return (
        normalize_text(getattr(record, "form_name", None)),
        normalize_text(getattr(record, "department", None)),
        normalize_text(getattr(record, "procedure_name", None)),
    )


def score_record_against_form(record: CaseRecord, form: FormDefinition) -> int:
    record_form_name, record_department, record_procedure = record_signature(record)
    score = 0

    form_name = normalize_text(getattr(form, "name", None))
    form_department = normalize_text(getattr(form, "department", None))
    form_procedure = normalize_text(getattr(form, "procedure_name", None))

    if record_form_name and form_name and record_form_name == form_name:
        score += 10

    if record_department and form_department and record_department == form_department:
        score += 4

    if record_procedure and form_procedure and record_procedure == form_procedure:
        score += 5

    if record_form_name and form_procedure and record_form_name == form_procedure:
        score += 3

    if record_procedure and form_name and record_procedure == form_name:
        score += 2

    return score


def match_form_definition_for_record(
    record: CaseRecord,
    forms: list[FormDefinition],
) -> Optional[FormDefinition]:
    best_form: Optional[FormDefinition] = None
    best_score = 0

    for form in forms:
        score = score_record_against_form(record, form)
        if score > best_score:
            best_score = score
            best_form = form

    return best_form if best_score > 0 else None


async def list_case_record_forms(db: AsyncSession) -> list[FormDefinition]:
    result = await db.execute(
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
    return list(result.scalars().all())


async def get_student_with_academics(
    db: AsyncSession,
    *,
    student_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Optional[Student]:
    query = select(Student).options(
        selectinload(Student.attendance),
        selectinload(Student.academic_group)
        .selectinload(AcademicGroup.targets)
        .selectinload(AcademicTarget.form_definition),
    )

    if student_id:
        query = query.where(Student.id == student_id)
    elif user_id:
        query = query.where(Student.user_id == user_id)
    else:
        raise ValueError("student_id or user_id is required")

    result = await db.execute(query)
    return result.scalar_one_or_none()


async def list_programme_groups(
    db: AsyncSession,
    *,
    programme_id: str,
    include_inactive: bool = True,
) -> list[AcademicGroup]:
    query = (
        select(AcademicGroup)
        .options(
            selectinload(AcademicGroup.students),
            selectinload(AcademicGroup.targets).selectinload(
                AcademicTarget.form_definition
            ),
        )
        .where(AcademicGroup.programme_id == programme_id)
        .order_by(AcademicGroup.name.asc())
    )
    if not include_inactive:
        query = query.where(AcademicGroup.is_active == True)

    result = await db.execute(query)
    return list(result.scalars().all())


async def list_academic_weightages(
    db: AsyncSession,
) -> dict[str, AcademicFormWeightage]:
    result = await db.execute(
        select(AcademicFormWeightage).options(
            selectinload(AcademicFormWeightage.form_definition)
        )
    )
    items = list(result.scalars().all())
    return {
        str(getattr(item, "form_definition_id", "")): item
        for item in items
        if getattr(item, "form_definition_id", None)
    }


async def list_student_approved_case_records(
    db: AsyncSession,
    *,
    student_id: str,
) -> list[CaseRecord]:
    result = await db.execute(
        select(CaseRecord)
        .join(Approval, Approval.case_record_id == CaseRecord.id)
        .where(
            CaseRecord.student_id == student_id,
            Approval.status == ApprovalStatus.APPROVED,
        )
        .options(selectinload(CaseRecord.approval))
        .order_by(CaseRecord.date.desc(), CaseRecord.created_at.desc())
    )
    return list(result.scalars().all())


async def build_student_academic_progress_context(
    db: AsyncSession,
    *,
    student: Student,
) -> dict[str, Any]:
    forms = await list_case_record_forms(db)
    weightages = await list_academic_weightages(db)
    approved_records = await list_student_approved_case_records(
        db,
        student_id=str(getattr(student, "id")),
    )

    group = getattr(student, "academic_group", None)
    targets = list(getattr(group, "targets", []) or []) if group is not None else []

    return {
        "student": student,
        "group": group,
        "forms": forms,
        "targets": targets,
        "weightages": weightages,
        "approved_records": approved_records,
    }


def compute_target_progress(
    *,
    targets: list[AcademicTarget],
    forms: list[FormDefinition],
    approved_records: list[CaseRecord],
) -> list[dict[str, Any]]:
    record_counts_by_form_id: dict[str, int] = defaultdict(int)

    for record in approved_records:
        matched_form = match_form_definition_for_record(record, forms)
        if matched_form is not None:
            matched_form_id = str(getattr(matched_form, "id", ""))
            if matched_form_id:
                record_counts_by_form_id[matched_form_id] += 1

    target_items: list[dict[str, Any]] = []

    def _target_sort_key(item: AcademicTarget) -> tuple[int, str, str]:
        raw_sort_order = getattr(item, "sort_order", 0)
        raw_metric_name = getattr(item, "metric_name", "") or ""
        raw_id = getattr(item, "id", "") or ""
        return (int(raw_sort_order or 0), str(raw_metric_name).lower(), str(raw_id))

    for index, target in enumerate(sorted(targets, key=_target_sort_key)):
        metric_name = str(getattr(target, "metric_name", "") or "")
        metric_keys = {metric_label_to_key(metric_name)}

        form_definition = getattr(target, "form_definition", None)
        if form_definition is not None:
            metric_keys |= build_form_metric_keys(form_definition)

        completed_value = 0
        matched_form_id = getattr(target, "form_definition_id", None)

        if matched_form_id:
            completed_value = record_counts_by_form_id.get(str(matched_form_id), 0)
        else:
            for form in forms:
                if build_form_metric_keys(form) & metric_keys:
                    form_id = str(getattr(form, "id", ""))
                    if form_id:
                        completed_value += record_counts_by_form_id.get(form_id, 0)

        target_value = max(int(getattr(target, "target_value", 0) or 0), 0)
        percent = (
            100.0
            if target_value == 0
            else min((completed_value / target_value) * 100.0, 100.0)
        )

        target_items.append(
            {
                "id": getattr(target, "id", None),
                "sort_order": int(getattr(target, "sort_order", index) or index),
                "metric_name": metric_name,
                "metric_key": metric_label_to_key(metric_name),
                "category": getattr(target, "category", None),
                "target_value": target_value,
                "completed_value": completed_value,
                "remaining_value": max(target_value - completed_value, 0),
                "percent": round(percent, 2),
                "is_complete": completed_value >= target_value
                if target_value > 0
                else True,
                "form_definition_id": getattr(target, "form_definition_id", None),
                "form_name": getattr(form_definition, "name", None)
                if form_definition is not None
                else None,
            }
        )

    return target_items


def compute_weighted_form_progress(
    *,
    forms: list[FormDefinition],
    weightages: dict[str, AcademicFormWeightage],
    approved_records: list[CaseRecord],
) -> dict[str, Any]:
    approved_counts_by_form_id: dict[str, int] = defaultdict(int)
    unmatched_records: list[dict[str, Any]] = []

    for record in approved_records:
        matched_form = match_form_definition_for_record(record, forms)
        if matched_form is not None:
            matched_form_id = str(getattr(matched_form, "id", ""))
            if matched_form_id:
                approved_counts_by_form_id[matched_form_id] += 1
        else:
            record_date = getattr(record, "date", None)
            unmatched_records.append(
                {
                    "id": getattr(record, "id", None),
                    "form_name": getattr(record, "form_name", None),
                    "department": getattr(record, "department", None),
                    "procedure_name": getattr(record, "procedure_name", None),
                    "date": record_date.isoformat()
                    if record_date is not None
                    else None,
                    "status": getattr(record, "status", None),
                }
            )

    configured_forms: list[dict[str, Any]] = []
    total_possible_points = 0
    total_earned_points = 0
    total_approved_forms = 0

    def _form_sort_key(form: FormDefinition) -> tuple[int, str, str]:
        raw_sort_order = getattr(form, "sort_order", 0)
        raw_name = getattr(form, "name", "") or ""
        raw_id = getattr(form, "id", "") or ""
        return (int(raw_sort_order or 0), str(raw_name).lower(), str(raw_id))

    sorted_forms = sorted(forms, key=_form_sort_key)
    for form in sorted_forms:
        form_id = str(getattr(form, "id", ""))
        weightage = weightages.get(form_id)
        points = (
            int(getattr(weightage, "points", 0) or 0) if weightage is not None else 0
        )
        approved_count = approved_counts_by_form_id.get(form_id, 0)
        earned_points = approved_count * points

        total_possible_points += points
        total_earned_points += earned_points
        total_approved_forms += approved_count

        configured_forms.append(
            {
                "form_definition_id": getattr(form, "id", None),
                "slug": getattr(form, "slug", None),
                "name": getattr(form, "name", None),
                "department": getattr(form, "department", None),
                "procedure_name": getattr(form, "procedure_name", None),
                "section": getattr(form, "section", None),
                "points": points,
                "approved_count": approved_count,
                "earned_points": earned_points,
                "has_weightage": weightage is not None,
            }
        )

    average_points = (
        round(total_earned_points / total_approved_forms, 2)
        if total_approved_forms > 0
        else 0.0
    )

    return {
        "total_approved_forms": total_approved_forms,
        "total_configured_forms": len(forms),
        "total_possible_points": total_possible_points,
        "total_earned_points": total_earned_points,
        "average_points_per_approved_form": average_points,
        "items": configured_forms,
        "unmatched_records": unmatched_records,
    }


def build_student_academic_progress_payload(
    *,
    student: Student,
    group: Optional[AcademicGroup],
    forms: list[FormDefinition],
    targets: list[AcademicTarget],
    weightages: dict[str, AcademicFormWeightage],
    approved_records: list[CaseRecord],
) -> dict[str, Any]:
    target_progress = compute_target_progress(
        targets=targets,
        forms=forms,
        approved_records=approved_records,
    )
    weighted_progress = compute_weighted_form_progress(
        forms=forms,
        weightages=weightages,
        approved_records=approved_records,
    )

    if target_progress:
        overall_percent = round(
            sum(item["percent"] for item in target_progress) / len(target_progress),
            2,
        )
    else:
        overall_percent = 0.0

    completed_targets = sum(1 for item in target_progress if item["is_complete"])
    total_targets = len(target_progress)

    return {
        "student_id": getattr(student, "id", None),
        "student_name": getattr(student, "name", None),
        "programme_name": getattr(student, "program", None),
        "academic_group": {
            "id": getattr(group, "id", None),
            "name": getattr(group, "name", None),
            "description": getattr(group, "description", None),
            "is_active": getattr(group, "is_active", None),
            "programme_id": getattr(group, "programme_id", None),
        }
        if group is not None
        else None,
        "summary": {
            "overall_percent": overall_percent,
            "completed_targets": completed_targets,
            "total_targets": total_targets,
            "approved_case_records": len(approved_records),
            "total_earned_points": weighted_progress["total_earned_points"],
            "total_possible_points": weighted_progress["total_possible_points"],
        },
        "targets": target_progress,
        "weightages": weighted_progress,
    }


async def get_student_academic_progress(
    db: AsyncSession,
    *,
    student_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    student = await get_student_with_academics(
        db,
        student_id=student_id,
        user_id=user_id,
    )
    if student is None:
        return None

    context = await build_student_academic_progress_context(db, student=student)
    return build_student_academic_progress_payload(
        student=context["student"],
        group=context["group"],
        forms=context["forms"],
        targets=context["targets"],
        weightages=context["weightages"],
        approved_records=context["approved_records"],
    )
