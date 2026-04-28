import json
import os
import re
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import cast, exists, select, type_coerce
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.database import get_db
from app.models.department import Department
from app.models.faculty import Faculty
from app.models.form_category import FormCategoryOption
from app.models.form_definition import FormDefinition
from app.models.lab import ChargeItem, ChargePrice, Lab
from app.models.lab_technician import LabTechnician, LabTechnicianGroup
from app.models.nurse import Nurse
from app.models.patient import Patient
from app.models.patient_category import PatientCategoryOption
from app.models.student import Clinic, Student
from app.models.user import User, UserRole
from app.services.ai_provider import AIProviderError, get_enabled_provider_settings, request_structured_completion
from app.services.charge_sync import sync_charge_sources
from app.services.form_categories import ensure_form_categories, infer_form_section, normalize_form_section_name

router = APIRouter(prefix="/forms", tags=["Forms"])
UPLOADS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "uploads",
)


class FormFieldPayload(BaseModel):
    key: Optional[str] = None
    id: Optional[str] = None
    label: str
    type: str
    required: bool = False
    placeholder: Optional[str] = None
    options: list[str] = Field(default_factory=list)
    rows: Optional[int] = None
    accept: Optional[str] = None
    multiple: bool = False
    help_text: Optional[str] = None
    condition: Optional[dict[str, Any]] = None


class FormDefinitionPayload(BaseModel):
    name: str
    description: Optional[str] = None
    form_type: Optional[str] = None
    section: Optional[str] = None
    department: Optional[str] = None
    procedure_name: Optional[str] = None
    fields: list[FormFieldPayload] = Field(default_factory=list)
    sort_order: int = 0
    is_active: bool = True
    icon: Optional[str] = None
    color: Optional[str] = None
    allowed_roles: Optional[list[str]] = None


class FormCategoryPayload(BaseModel):
    name: str
    sort_order: Optional[int] = None
    is_active: bool = True


class FormCategoryUpdatePayload(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


def _serialize_form_category(category: FormCategoryOption) -> dict:
    return {
        "id": category.id,
        "name": category.name,
        "sort_order": category.sort_order,
        "is_active": category.is_active,
        "is_system": category.is_system,
        "created_at": category.created_at.isoformat() if category.created_at else None,
    }

ALLOWED_CONDITION_OPERATORS = {
    "eq",
    "ne",
    "contains",
    "gt",
    "lt",
    "gte",
    "lte",
    "empty",
    "not_empty",
}


def _resolve_section(payload: FormDefinitionPayload, existing_section: Optional[str] = None) -> str:
    return infer_form_section(payload.form_type, payload.section or existing_section)


def _resolve_form_type(
    payload: FormDefinitionPayload,
    resolved_section: str,
    existing_form_type: Optional[str] = None,
) -> str:
    if payload.form_type:
        return payload.form_type.strip().upper()
    if existing_form_type:
        return existing_form_type.strip().upper()
    if resolved_section in {"CLINICAL", "LABORATORY", "ADMINISTRATIVE"}:
        return resolved_section
    return "CUSTOM"


ALLOWED_FIELD_TYPES = {
    "text",
    "textarea",
    "number",
    "select",
    "date",
    "file",
    "email",
    "password",
    "tel",
    "diagnosis",
    # Dynamic DB-backed select types
    "department_select",
    "faculty_select",
    "clinic_select",
}

# Maps dynamic field types to their DB source
DYNAMIC_FIELD_SOURCES = {
    "department_select": "departments",
    "faculty_select": "faculty",
    "clinic_select": "clinics",
}


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _build_slug(payload: FormDefinitionPayload, resolved_form_type: str, resolved_section: str) -> str:
    parts = [resolved_section]
    if resolved_form_type and resolved_form_type != resolved_section:
        parts.append(resolved_form_type)
    if payload.department:
        parts.append(payload.department)
    if payload.procedure_name:
        parts.append(payload.procedure_name)
    parts.append(payload.name)
    return _slugify("-".join(parts))


def _safe_upload_context(value: Optional[str]) -> str:
    cleaned = _slugify(value or "general")
    return cleaned or "general"


def _normalize_field_type(raw_type: Optional[str]) -> str:
    normalized = (raw_type or "").strip().lower()
    if normalized == "diagnosis":
        return "text"
    return normalized


def _normalize_condition(raw_condition: Any) -> Optional[dict[str, Any]]:
    if not isinstance(raw_condition, dict):
        return None

    field = str(raw_condition.get("field") or "").strip()
    operator = str(raw_condition.get("operator") or "").strip().lower()
    if not field or not operator:
        return None

    condition: dict[str, Any] = {
        "field": field,
        "operator": operator,
    }
    if "value" in raw_condition:
        condition["value"] = raw_condition.get("value")
    return condition


def _normalize_field(field: FormFieldPayload | dict) -> dict:
    field_data = field.model_dump() if isinstance(field, FormFieldPayload) else dict(field)
    label = (field_data.get("label") or "").strip()
    key = (field_data.get("key") or field_data.get("id") or _slugify(label) or "").strip()
    return {
        "key": key,
        "label": label,
        "type": _normalize_field_type(field_data.get("type")),
        "required": bool(field_data.get("required", False)),
        "placeholder": field_data.get("placeholder"),
        "options": field_data.get("options") or [],
        "rows": field_data.get("rows"),
        "accept": field_data.get("accept"),
        "multiple": bool(field_data.get("multiple", False)),
        "help_text": field_data.get("help_text"),
        "condition": _normalize_condition(field_data.get("condition")),
    }


def _serialize_form(form: FormDefinition) -> dict:
    normalized_fields = [_normalize_field(field) for field in (form.fields or [])]
    return {
        "id": form.id,
        "slug": form.slug,
        "name": form.name,
        "description": form.description,
        "form_type": form.form_type,
        "section": infer_form_section(form.form_type, form.section),
        "department": form.department,
        "procedure_name": form.procedure_name,
        "icon": form.icon,
        "color": form.color,
        "fields": normalized_fields,
        "sort_order": form.sort_order,
        "is_active": form.is_active,
        "allowed_roles": form.allowed_roles,
        "created_at": form.created_at.isoformat() if form.created_at else None,
        "updated_at": form.updated_at.isoformat() if form.updated_at else None,
    }


def _validate_payload(payload: FormDefinitionPayload, resolved_form_type: str, resolved_section: str, allowed_sections: set[str]):
    if resolved_section not in allowed_sections:
        raise HTTPException(status_code=400, detail="Unsupported section")

    if resolved_form_type == "CASE_RECORD":
        if not payload.department or not payload.procedure_name:
            raise HTTPException(status_code=400, detail="Case record forms require department and procedure name")

    if not payload.fields:
        raise HTTPException(status_code=400, detail="At least one field is required")

    seen_keys: set[str] = set()
    normalized_fields: list[dict[str, Any]] = []
    for field in payload.fields:
        normalized_field = _normalize_field(field)
        normalized_fields.append(normalized_field)
        field.key = normalized_field["key"]
        field.label = field.label.strip()
        field.type = normalized_field["type"]
        field.condition = normalized_field.get("condition")
        if not field.key or not field.label:
            raise HTTPException(status_code=400, detail="Each field requires a key and label")
        if field.key in seen_keys:
            raise HTTPException(status_code=400, detail=f"Duplicate field key: {field.key}")
        seen_keys.add(field.key)
        if field.type not in ALLOWED_FIELD_TYPES:
            raise HTTPException(status_code=400, detail=f"Unsupported field type: {field.type}")
        if field.type == "select" and not field.options:
            raise HTTPException(status_code=400, detail=f"Select field '{field.label}' requires options")

    for normalized_field in normalized_fields:
        condition = normalized_field.get("condition")
        if not condition:
            continue

        condition_field = str(condition.get("field") or "").strip()
        condition_operator = str(condition.get("operator") or "").strip().lower()
        if condition_field not in seen_keys:
            raise HTTPException(status_code=400, detail=f"Invalid condition field reference: {condition_field}")
        if condition_operator not in ALLOWED_CONDITION_OPERATORS:
            raise HTTPException(status_code=400, detail=f"Unsupported condition operator: {condition_operator}")


@router.get("/categories")
async def list_form_categories(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    categories = await ensure_form_categories(db)
    await db.commit()
    return [_serialize_form_category(category) for category in categories if category.is_active or user.role == UserRole.ADMIN]


@router.post("/categories", status_code=201)
async def create_form_category(
    payload: FormCategoryPayload,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    categories = await ensure_form_categories(db)
    normalized_name = normalize_form_section_name(payload.name)
    if not normalized_name:
        raise HTTPException(status_code=400, detail="Category name is required")

    existing = (
        await db.execute(
            select(FormCategoryOption).where(FormCategoryOption.name == normalized_name)
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Category name already exists")

    category = FormCategoryOption(
        id=str(uuid.uuid4()),
        name=normalized_name,
        sort_order=payload.sort_order if payload.sort_order is not None else len(categories),
        is_active=payload.is_active,
        is_system=False,
    )
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return _serialize_form_category(category)


@router.delete("/categories/{category_id}")
async def delete_form_category(
    category_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    category = (
        await db.execute(
            select(FormCategoryOption).where(FormCategoryOption.id == category_id)
        )
    ).scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if category.is_system:
        raise HTTPException(status_code=400, detail="System categories cannot be deleted")

    form_exists = (
        await db.execute(
            select(FormDefinition.id).where(FormDefinition.section == category.name).limit(1)
        )
    ).scalar_one_or_none()
    if form_exists:
        raise HTTPException(status_code=400, detail="Cannot delete category with existing form configurations")

    await db.delete(category)
    await db.flush()
    return {"message": "Form category deleted"}


@router.patch("/categories/{category_id}")
async def update_form_category(
    category_id: str,
    payload: FormCategoryUpdatePayload,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    category = (
        await db.execute(
            select(FormCategoryOption).where(FormCategoryOption.id == category_id)
        )
    ).scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if payload.name is not None:
        normalized_name = normalize_form_section_name(payload.name)
        if not normalized_name:
            raise HTTPException(status_code=400, detail="Category name is required")
        existing = (
            await db.execute(
                select(FormCategoryOption)
                .where(FormCategoryOption.name == normalized_name)
                .where(FormCategoryOption.id != category.id)
            )
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Category name already exists")
        if category.is_system and normalized_name != category.name:
            raise HTTPException(status_code=400, detail="System categories cannot be renamed")
        category.name = normalized_name

    if payload.sort_order is not None:
        category.sort_order = payload.sort_order

    if payload.is_active is not None:
        if category.is_system and payload.is_active is False:
            raise HTTPException(status_code=400, detail="System categories cannot be disabled")
        category.is_active = payload.is_active

    await db.flush()
    await db.refresh(category)
    return _serialize_form_category(category)


@router.get("/lookup-options/{source}")
async def get_lookup_options(
    source: str,
    department: Optional[str] = Query(None),
    lab_type: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return {value, label} options for dynamic form field types."""
    if source == "departments":
        result = await db.execute(
            select(Department).where(Department.is_active == True).order_by(Department.name)
        )
        return [{"value": d.id, "label": d.name} for d in result.scalars()]
    elif source == "faculty":
        q = select(Faculty).order_by(Faculty.name)
        if department:
            q = q.where(Faculty.department == department)
        result = await db.execute(q)
        return [{"value": f.id, "label": f"{f.name} ({f.department})"} for f in result.scalars()]
    elif source == "clinics":
        result = await db.execute(
            select(Clinic).where(Clinic.is_active == True).order_by(Clinic.name)
        )
        return [{"value": c.id, "label": f"{c.name} ({c.department})"} for c in result.scalars()]
    elif source == "labs":
        q = select(Lab).where(Lab.is_active == True).order_by(Lab.name)
        if department:
            q = q.where(Lab.department == department)
        if lab_type:
            q = q.where(Lab.lab_type == lab_type)
        result = await db.execute(q)
        return [{"value": l.id, "label": l.name} for l in result.scalars()]
    elif source == "lab_batches":
        result = await db.execute(select(LabTechnicianGroup).order_by(LabTechnicianGroup.name))
        return [{"value": g.id, "label": g.name} for g in result.scalars()]
    elif source == "patients":
        result = await db.execute(select(Patient).order_by(Patient.name))
        return [{"value": p.id, "label": f"{p.name} ({p.patient_id})"} for p in result.scalars()]
    elif source == "students":
        result = await db.execute(select(Student).order_by(Student.name))
        return [{"value": s.id, "label": f"{s.name} ({s.student_id})"} for s in result.scalars()]
    elif source == "nurses":
        result = await db.execute(select(Nurse).order_by(Nurse.name))
        return [{"value": n.id, "label": f"{n.name} ({n.nurse_id})"} for n in result.scalars()]
    elif source == "patient_categories":
        result = await db.execute(select(PatientCategoryOption).order_by(PatientCategoryOption.name))
        return [{"value": c.id, "label": c.name} for c in result.scalars()]
    else:
        raise HTTPException(status_code=400, detail=f"Unknown lookup source: {source}")


@router.get("")
async def list_forms(
    form_type: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    procedure_name: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_form_categories(db)
    query = select(FormDefinition)

    if form_type:
        query = query.where(FormDefinition.form_type == form_type)
    if section:
        query = query.where(FormDefinition.section == normalize_form_section_name(section))
    if department:
        query = query.where(FormDefinition.department == department)
    if procedure_name:
        query = query.where(FormDefinition.procedure_name == procedure_name)
    if not include_inactive or user.role != UserRole.ADMIN:
        query = query.where(FormDefinition.is_active == True)

    # Non-admin: filter by allowed_roles (null = all roles allowed)
    if user.role != UserRole.ADMIN:
        user_role_str = user.role.value if hasattr(user.role, 'value') else str(user.role)
        query = query.where(
            (FormDefinition.allowed_roles == None) |
            (cast(FormDefinition.allowed_roles, JSONB).contains([user_role_str]))
        )
        # Only show forms that have at least one configured charge price (including free / ₹0)
        has_price = exists(
            select(ChargePrice.id)
            .join(ChargeItem, ChargeItem.id == ChargePrice.item_id)
            .where(
                ChargeItem.source_type == "form_definition",
                ChargeItem.source_id == FormDefinition.id,
                ChargePrice.price >= 0,
            )
        )
        query = query.where(has_price)

    query = query.order_by(
        FormDefinition.section,
        FormDefinition.form_type,
        FormDefinition.department,
        FormDefinition.procedure_name,
        FormDefinition.sort_order,
        FormDefinition.name,
    )
    result = await db.execute(query)
    return [_serialize_form(form) for form in result.scalars().all()]


@router.post("", status_code=201)
async def create_form_definition(
    payload: FormDefinitionPayload,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    categories = await ensure_form_categories(db)
    allowed_sections = {category.name for category in categories}
    resolved_section = _resolve_section(payload)
    resolved_form_type = _resolve_form_type(payload, resolved_section)
    _validate_payload(payload, resolved_form_type, resolved_section, allowed_sections)
    slug = _build_slug(payload, resolved_form_type, resolved_section)

    existing = (
        await db.execute(select(FormDefinition).where(FormDefinition.slug == slug))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="A form with the same context and name already exists")

    form = FormDefinition(
        id=str(uuid.uuid4()),
        slug=slug,
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        form_type=resolved_form_type,
        section=resolved_section,
        department=payload.department.strip() if payload.department else None,
        procedure_name=payload.procedure_name.strip() if payload.procedure_name else None,
        fields=[_normalize_field(field) for field in payload.fields],
        sort_order=payload.sort_order,
        is_active=payload.is_active,
        icon=payload.icon or None,
        color=payload.color or None,
        allowed_roles=payload.allowed_roles,
    )
    db.add(form)
    await db.flush()
    await sync_charge_sources(db)
    await db.refresh(form)
    return _serialize_form(form)


@router.put("/{form_id}")
async def update_form_definition(
    form_id: str,
    payload: FormDefinitionPayload,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    form = (
        await db.execute(select(FormDefinition).where(FormDefinition.id == form_id))
    ).scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    categories = await ensure_form_categories(db)
    allowed_sections = {category.name for category in categories}
    resolved_section = _resolve_section(payload, form.section)
    resolved_form_type = _resolve_form_type(payload, resolved_section, form.form_type)
    _validate_payload(payload, resolved_form_type, resolved_section, allowed_sections)

    slug = _build_slug(payload, resolved_form_type, resolved_section)
    existing = (
        await db.execute(
            select(FormDefinition).where(
                FormDefinition.slug == slug,
                FormDefinition.id != form_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="A form with the same context and name already exists")

    form.slug = slug
    form.name = payload.name.strip()
    form.description = payload.description.strip() if payload.description else None
    form.form_type = resolved_form_type
    form.section = resolved_section
    form.department = payload.department.strip() if payload.department else None
    form.procedure_name = payload.procedure_name.strip() if payload.procedure_name else None
    form.fields = [_normalize_field(field) for field in payload.fields]
    form.sort_order = payload.sort_order
    form.is_active = payload.is_active
    form.icon = payload.icon or None
    form.color = payload.color or None
    form.allowed_roles = payload.allowed_roles

    await db.flush()
    await sync_charge_sources(db)
    await db.refresh(form)
    return _serialize_form(form)


@router.post("/uploads", status_code=201)
async def upload_form_file(
    file: UploadFile = File(...),
    context: Optional[str] = Form(None),
    field_key: Optional[str] = Form(None),
    user: User = Depends(get_current_user),
):
    safe_context = _safe_upload_context(context)
    safe_field_key = _safe_upload_context(field_key)
    target_dir = os.path.join(UPLOADS_DIR, "forms", safe_context)
    os.makedirs(target_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "upload.bin")[1] or ".bin"
    filename = f"{safe_field_key}_{user.id}_{uuid.uuid4().hex[:10]}{ext}"
    filepath = os.path.join(target_dir, filename)

    content = await file.read()
    with open(filepath, "wb") as handle:
        handle.write(content)

    return {
        "name": file.filename or filename,
        "url": f"/uploads/forms/{safe_context}/{filename}",
        "content_type": file.content_type,
        "size": len(content),
        "uploaded_at": datetime.utcnow().isoformat(),
    }


# ── AI form generation ───────────────────────────────────────────────────────

FORM_GENERATION_SYSTEM_PROMPT = (
    "You are a medical form builder for a dental/medical teaching hospital. "
    "Given a description of what a form is for, generate a JSON form definition.\n\n"
    "Return valid JSON only with exactly these keys:\n"
    '  "name": a short human-readable form title,\n'
    '  "description": one-sentence summary,\n'
    '  "fields": an array of field objects.\n\n'
    "Each field object MUST have:\n"
    '  "key": snake_case unique identifier,\n'
    '  "label": human-readable label,\n'
    '  "type": one of text, textarea, number, select, date, email, tel,\n'
    '  "required": boolean,\n'
    '  "placeholder": example input text or empty string,\n'
    '  "options": string array (required and non-empty ONLY if type is "select", otherwise empty array []),\n'
    '  "help_text": short guidance or empty string,\n'
    '  "condition": null OR an object with "field", "operator", and optional "value".\n\n'
    "Rules:\n"
    "- Generate 5-15 fields appropriate for the described form.\n"
    "- Use textarea for long-form text (clinical notes, findings, descriptions).\n"
    "- Use select for categorical choices (severity, status, classification).\n"
    "- Use date for any date fields.\n"
    "- Use number for numeric measurements or counts.\n"
    "- Field keys must be unique snake_case.\n"
    "- Do NOT use types: file, password, diagnosis, department_select, faculty_select, clinic_select.\n"
    "- Do NOT include patient identity fields that are already available elsewhere, especially Patient Name, Patient ID, Patient Date of Birth, or DOB.\n"
    "- Every field must collect user-entered clinical or administrative data. Never create action/button/system fields such as Generate Differential Diagnosis, Submit, Save, Print, Export, or click-to-trigger AI fields.\n"
    '- If a field should appear only after an earlier answer, set "condition" using operators: eq, ne, contains, gt, lt, gte, lte, empty, not_empty.\n'
    '- A "condition.field" must reference the key of an earlier field in the same form.\n'
    '- For operators eq, ne, contains, gt, lt, gte, and lte, include a "value". For empty and not_empty, omit "value".\n'
    '- If a field should always be visible, set "condition" to null.\n'
    "- Return ONLY the JSON object, no markdown fences or explanation."
)


class FormGeneratePayload(BaseModel):
    description: str = Field(..., min_length=3, max_length=500)
    existing_fields: list[dict[str, Any]] | None = Field(default=None, description="Current fields to refine")
    form_name: str | None = Field(default=None, description="Current form name for context")


def _build_refine_user_prompt(
    form_name: str | None,
    existing_fields: list[dict[str, Any]],
    description: str,
    *,
    delta_only: bool,
) -> str:
    existing_summary = json.dumps(
        [
            {
                "key": field.get("key"),
                "label": field.get("label"),
                "type": field.get("type"),
                "options": field.get("options") or [],
                "condition": field.get("condition"),
            }
            for field in existing_fields
        ],
        indent=2
    )
    if delta_only:
        return (
            f"Current form name: {form_name or 'Untitled'}\n"
            f"Current fields:\n{existing_summary}\n\n"
            f"User request: {description.strip()}\n\n"
            "Refine this form based on the request. Preserve all useful existing fields, preserve existing keys whenever possible, "
            "and prefer enhancing or adding fields over removing them unless the request clearly requires removal. "
            'Your JSON MUST still use the top-level keys "name", "description", and "fields". '
            'Put only the added or updated fields inside the "fields" array, and never omit the "fields" key.'
        )
    return (
        f"Current form name: {form_name or 'Untitled'}\n"
        f"Current fields:\n{existing_summary}\n\n"
        f"User request: {description.strip()}\n\n"
        "Refine this form based on the request. Preserve all useful existing fields, preserve existing keys whenever possible, "
        "and return the complete updated form definition with every field included. "
        'Your JSON MUST use the top-level keys "name", "description", and "fields".'
    )


def _extract_generated_fields(result: dict[str, Any]) -> list[dict[str, Any]] | None:
    container = _extract_generated_container(result)
    if container is None:
        return None
    result = container
    raw_fields = result.get("fields")
    if isinstance(raw_fields, list):
        return raw_fields
    for alternate_key in ("updated_fields", "new_fields", "added_fields", "modified_fields", "changes"):
        alternate_fields = result.get(alternate_key)
        if isinstance(alternate_fields, list):
            return alternate_fields
    return None


def _extract_generated_container(result: dict[str, Any] | Any) -> dict[str, Any] | None:
    if not isinstance(result, dict):
        return None
    raw_fields = result.get("fields")
    if isinstance(raw_fields, list):
        return result
    for alternate_key in ("updated_fields", "new_fields", "added_fields", "modified_fields", "changes"):
        alternate_fields = result.get(alternate_key)
        if isinstance(alternate_fields, list):
            return result
    for preferred_key in ("form", "updated_form", "updatedForm", "data", "result", "payload"):
        nested = _extract_generated_container(result.get(preferred_key))
        if nested is not None:
            return nested
    for value in result.values():
        nested = _extract_generated_container(value)
        if nested is not None:
            return nested
    return None


def _is_patient_identity_field(field: dict[str, Any]) -> bool:
    key = str(field.get("key") or "").strip().lower()
    label = re.sub(r"[^a-z0-9]+", " ", str(field.get("label") or "").strip().lower()).strip()
    return key in {
        "patient_id",
        "patient_name",
        "patient_dob",
        "patient_date_of_birth",
        "date_of_birth",
        "dob",
    } or label in {
        "patient id",
        "patient name",
        "patient dob",
        "patient date of birth",
        "date of birth",
        "dob",
    }


def _is_instructional_generated_field(field: dict[str, Any]) -> bool:
    key = str(field.get("key") or "").strip().lower()
    label = re.sub(r"[^a-z0-9]+", " ", str(field.get("label") or "").strip().lower()).strip()
    placeholder = re.sub(r"[^a-z0-9]+", " ", str(field.get("placeholder") or "").strip().lower()).strip()
    help_text = re.sub(r"[^a-z0-9]+", " ", str(field.get("help_text") or "").strip().lower()).strip()
    combined = " ".join(part for part in (label, placeholder, help_text) if part)
    if key.startswith(("generate_", "calculate_", "submit_", "save_", "print_", "export_")):
        return True
    if label.startswith(("generate ", "calculate ", "submit ", "save ", "print ", "export ")):
        return True
    return any(
        marker in combined
        for marker in {
            "clicking this will",
            "this will trigger",
            "trigger the generation",
            "generate differential diagnosis",
            "generate diagnosis",
            "ai generated",
        }
    )


@router.post("/generate")
async def generate_form_definition(
    payload: FormGeneratePayload,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Use the configured AI provider to generate a form definition from a description."""
    try:
        config = await get_enabled_provider_settings(db)
    except AIProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Build user prompt — include existing fields for refinement if provided
    if payload.existing_fields and len(payload.existing_fields) > 0:
        prompts = [
            (_build_refine_user_prompt(payload.form_name, payload.existing_fields, payload.description, delta_only=True), 2200),
            (_build_refine_user_prompt(payload.form_name, payload.existing_fields, payload.description, delta_only=False), 3600),
        ]
    else:
        prompts = [(f"Generate a medical/dental form for: {payload.description.strip()}", 4000)]

    result: dict[str, Any] | None = None
    raw_fields: list[dict[str, Any]] | None = None
    last_error: AIProviderError | None = None
    last_candidate: dict[str, Any] | None = None
    for user_prompt, max_tokens in prompts:
        try:
            candidate = await request_structured_completion(
                config,
                FORM_GENERATION_SYSTEM_PROMPT,
                user_prompt,
                max_tokens=max_tokens,
            )
        except AIProviderError as exc:
            last_error = exc
            continue

        last_candidate = candidate
        candidate_fields = _extract_generated_fields(candidate)
        if candidate_fields is None:
            last_error = AIProviderError("AI did not return any fields")
            continue

        result = candidate
        raw_fields = candidate_fields
        break

    if result is None or raw_fields is None:
        if payload.existing_fields and last_candidate is not None:
            candidate_container = _extract_generated_container(last_candidate) or last_candidate
            return {
                "name": str(candidate_container.get("name") or payload.form_name or "").strip() or "Generated Form",
                "description": str(candidate_container.get("description") or "").strip() or None,
                "fields": [],
            }
        raise HTTPException(status_code=502, detail=str(last_error or AIProviderError("AI did not return any fields")))

    result_container = _extract_generated_container(result) or result
    name = str(result_container.get("name") or result.get("name") or "").strip() or "Generated Form"
    description = str(result_container.get("description") or result.get("description") or "").strip() or None
    if payload.existing_fields and len(raw_fields) == 0:
        return {
            "name": name,
            "description": description,
            "fields": [],
        }
    if len(raw_fields) == 0:
        raise HTTPException(status_code=502, detail="AI did not return any fields")

    # Normalize and validate each field
    normalized_fields: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for raw_field in raw_fields:
        if not isinstance(raw_field, dict):
            continue
        normalized = _normalize_field(raw_field)
        key = normalized.get("key") or ""
        label = normalized.get("label") or ""
        if not key or not label:
            continue
        if _is_patient_identity_field(normalized) or _is_instructional_generated_field(normalized):
            continue
        # Deduplicate keys
        if key in seen_keys:
            continue
        # Restrict to safe types the AI should produce
        field_type = normalized.get("type", "text")
        if field_type not in ALLOWED_FIELD_TYPES:
            normalized["type"] = "text"
        # Ensure select fields have options
        if normalized["type"] == "select" and not normalized.get("options"):
            normalized["type"] = "text"
        condition = normalized.get("condition")
        if condition:
            operator = str(condition.get("operator") or "").strip().lower()
            condition_field = str(condition.get("field") or "").strip()
            requires_value = operator not in {"empty", "not_empty"}
            has_value = "value" in condition and condition.get("value") not in (None, "")
            if (
                operator not in ALLOWED_CONDITION_OPERATORS
                or condition_field not in seen_keys
                or (requires_value and not has_value)
            ):
                normalized["condition"] = None
        seen_keys.add(key)
        normalized_fields.append(normalized)

    if not normalized_fields:
        raise HTTPException(status_code=502, detail="AI response contained no valid fields")

    return {
        "name": name,
        "description": description,
        "fields": normalized_fields,
    }
