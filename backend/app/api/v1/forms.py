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
from app.models.form_category import FormCategoryOption
from app.models.form_definition import FormDefinition
from app.models.user import User, UserRole
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


class FormCategoryPayload(BaseModel):
    name: str
    sort_order: Optional[int] = None
    is_active: bool = True


def _serialize_form_category(category: FormCategoryOption) -> dict:
    return {
        "id": category.id,
        "name": category.name,
        "sort_order": category.sort_order,
        "is_active": category.is_active,
        "is_system": category.is_system,
        "created_at": category.created_at.isoformat() if category.created_at else None,
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
    "diagnosis",
    "date",
    "file",
    "email",
    "password",
    "tel",
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
        "section": infer_form_section(form.form_type, form.section),
        "department": form.department,
        "procedure_name": form.procedure_name,
        "fields": normalized_fields,
        "sort_order": form.sort_order,
        "is_active": form.is_active,
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
