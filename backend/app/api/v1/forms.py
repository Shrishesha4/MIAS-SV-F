import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.database import get_db
from app.models.form_definition import FormDefinition
from app.models.user import User, UserRole

router = APIRouter(prefix="/forms", tags=["Forms"])


class FormFieldPayload(BaseModel):
    key: str
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
    form_type: str = "CASE_RECORD"
    department: Optional[str] = None
    procedure_name: Optional[str] = None
    fields: list[FormFieldPayload] = Field(default_factory=list)
    sort_order: int = 0
    is_active: bool = True


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


def _build_slug(payload: FormDefinitionPayload) -> str:
    parts = [payload.form_type]
    if payload.department:
        parts.append(payload.department)
    if payload.procedure_name:
        parts.append(payload.procedure_name)
    parts.append(payload.name)
    return _slugify("-".join(parts))


def _serialize_form(form: FormDefinition) -> dict:
    return {
        "id": form.id,
        "slug": form.slug,
        "name": form.name,
        "description": form.description,
        "form_type": form.form_type,
        "department": form.department,
        "procedure_name": form.procedure_name,
        "fields": form.fields or [],
        "sort_order": form.sort_order,
        "is_active": form.is_active,
        "created_at": form.created_at.isoformat() if form.created_at else None,
        "updated_at": form.updated_at.isoformat() if form.updated_at else None,
    }


def _validate_payload(payload: FormDefinitionPayload):
    if payload.form_type == "CASE_RECORD":
        if not payload.department or not payload.procedure_name:
            raise HTTPException(status_code=400, detail="Case record forms require department and procedure name")

    if not payload.fields:
        raise HTTPException(status_code=400, detail="At least one field is required")

    seen_keys: set[str] = set()
    for field in payload.fields:
        field.key = field.key.strip()
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
    return [_serialize_form(form) for form in result.scalars().all()]


@router.post("", status_code=201)
async def create_form_definition(
    payload: FormDefinitionPayload,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    _validate_payload(payload)
    slug = _build_slug(payload)

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
        form_type=payload.form_type,
        department=payload.department.strip() if payload.department else None,
        procedure_name=payload.procedure_name.strip() if payload.procedure_name else None,
        fields=[field.model_dump() for field in payload.fields],
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
    _validate_payload(payload)
    form = (
        await db.execute(select(FormDefinition).where(FormDefinition.id == form_id))
    ).scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    slug = _build_slug(payload)
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
    form.form_type = payload.form_type
    form.department = payload.department.strip() if payload.department else None
    form.procedure_name = payload.procedure_name.strip() if payload.procedure_name else None
    form.fields = [field.model_dump() for field in payload.fields]
    form.sort_order = payload.sort_order
    form.is_active = payload.is_active

    await db.flush()
    await db.refresh(form)
    return _serialize_form(form)
