import os
import re
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.database import get_db
from app.models.form_definition import FormDefinition
from app.models.user import User, UserRole

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


FORM_SECTIONS = {"CLINICAL", "LABORATORY", "ADMINISTRATIVE"}


def _resolve_section(form_type: Optional[str]) -> str:
    normalized = (form_type or "").upper()
    if normalized in {"CLINICAL", "CASE_RECORD", "ADMISSION", "ADMISSION_REQUEST", "ADMISSION_INTAKE", "ADMISSION_DISCHARGE", "ADMISSION_TRANSFER", "PRESCRIPTION", "PRESCRIPTION_CREATE", "PRESCRIPTION_EDIT", "PRESCRIPTION_REQUEST", "VITAL_ENTRY"}:
        return "CLINICAL"
    if normalized in {"LABORATORY", "LAB", "LABS"}:
        return "LABORATORY"
    return "ADMINISTRATIVE"


def _resolve_form_type(payload: FormDefinitionPayload, existing_form_type: Optional[str] = None) -> str:
    if payload.form_type:
        return payload.form_type.strip().upper()
    if payload.section:
        return payload.section.strip().upper()
    if existing_form_type:
        return existing_form_type.strip().upper()
    return "ADMINISTRATIVE"


ALLOWED_FIELD_TYPES = {
    "text",
    "textarea",
    "number",
    "select",
    "diagnosis",
    "date",
    "file",
    "email",
    "password",
    "tel",
}


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _build_slug(payload: FormDefinitionPayload, resolved_form_type: str) -> str:
    parts = [resolved_form_type]
    if payload.department:
        parts.append(payload.department)
    if payload.procedure_name:
        parts.append(payload.procedure_name)
    parts.append(payload.name)
    return _slugify("-".join(parts))


def _safe_upload_context(value: Optional[str]) -> str:
    cleaned = _slugify(value or "general")
    return cleaned or "general"


def _normalize_field(field: FormFieldPayload | dict) -> dict:
    field_data = field.model_dump() if isinstance(field, FormFieldPayload) else dict(field)
    label = (field_data.get("label") or "").strip()
    key = (field_data.get("key") or field_data.get("id") or _slugify(label) or "").strip()
    return {
        "key": key,
        "label": label,
        "type": field_data.get("type"),
        "required": bool(field_data.get("required", False)),
        "placeholder": field_data.get("placeholder"),
        "options": field_data.get("options") or [],
        "rows": field_data.get("rows"),
        "accept": field_data.get("accept"),
        "multiple": bool(field_data.get("multiple", False)),
        "help_text": field_data.get("help_text"),
    }


def _serialize_form(form: FormDefinition) -> dict:
    normalized_fields = [_normalize_field(field) for field in (form.fields or [])]
    return {
        "id": form.id,
        "slug": form.slug,
        "name": form.name,
        "description": form.description,
        "form_type": form.form_type,
        "section": _resolve_section(form.form_type),
        "department": form.department,
        "procedure_name": form.procedure_name,
        "fields": normalized_fields,
        "sort_order": form.sort_order,
        "is_active": form.is_active,
        "created_at": form.created_at.isoformat() if form.created_at else None,
        "updated_at": form.updated_at.isoformat() if form.updated_at else None,
    }


def _validate_payload(payload: FormDefinitionPayload, resolved_form_type: str):
    if payload.section and payload.section.strip().upper() not in FORM_SECTIONS:
        raise HTTPException(status_code=400, detail="Unsupported section")

    if resolved_form_type == "CASE_RECORD":
        if not payload.department or not payload.procedure_name:
            raise HTTPException(status_code=400, detail="Case record forms require department and procedure name")

    if not payload.fields:
        raise HTTPException(status_code=400, detail="At least one field is required")

    seen_keys: set[str] = set()
    for field in payload.fields:
        normalized_field = _normalize_field(field)
        field.key = normalized_field["key"]
        field.label = field.label.strip()
        if not field.key or not field.label:
            raise HTTPException(status_code=400, detail="Each field requires a key and label")
        if field.key in seen_keys:
            raise HTTPException(status_code=400, detail=f"Duplicate field key: {field.key}")
        seen_keys.add(field.key)
        if field.type not in ALLOWED_FIELD_TYPES:
            raise HTTPException(status_code=400, detail=f"Unsupported field type: {field.type}")
        if field.type == "select" and not field.options:
            raise HTTPException(status_code=400, detail=f"Select field '{field.label}' requires options")


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
    query = select(FormDefinition)

    if form_type:
        query = query.where(FormDefinition.form_type == form_type)
    if department:
        query = query.where(FormDefinition.department == department)
    if procedure_name:
        query = query.where(FormDefinition.procedure_name == procedure_name)
    if not include_inactive or user.role != UserRole.ADMIN:
        query = query.where(FormDefinition.is_active == True)

    query = query.order_by(
        FormDefinition.form_type,
        FormDefinition.department,
        FormDefinition.procedure_name,
        FormDefinition.sort_order,
        FormDefinition.name,
    )
    result = await db.execute(query)
    forms = [_serialize_form(form) for form in result.scalars().all()]
    if section:
        target_section = section.strip().upper()
        forms = [form for form in forms if form["section"] == target_section]
    return forms


@router.post("", status_code=201)
async def create_form_definition(
    payload: FormDefinitionPayload,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    resolved_form_type = _resolve_form_type(payload)
    _validate_payload(payload, resolved_form_type)
    slug = _build_slug(payload, resolved_form_type)

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
        department=payload.department.strip() if payload.department else None,
        procedure_name=payload.procedure_name.strip() if payload.procedure_name else None,
        fields=[_normalize_field(field) for field in payload.fields],
        sort_order=payload.sort_order,
        is_active=payload.is_active,
    )
    db.add(form)
    await db.flush()
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

    resolved_form_type = _resolve_form_type(payload, form.form_type)
    _validate_payload(payload, resolved_form_type)

    slug = _build_slug(payload, resolved_form_type)
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
    form.department = payload.department.strip() if payload.department else None
    form.procedure_name = payload.procedure_name.strip() if payload.procedure_name else None
    form.fields = [_normalize_field(field) for field in payload.fields]
    form.sort_order = payload.sort_order
    form.is_active = payload.is_active

    await db.flush()
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
