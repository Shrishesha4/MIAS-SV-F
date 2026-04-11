from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import require_role
from app.database import get_db
from app.models.ai_provider import AIProviderType
from app.models.user import User, UserRole
from app.services.ai_provider import (
    AIProviderError,
    DEFAULT_PROVIDER_MODELS,
    DEFAULT_SYSTEM_PROMPT,
    create_provider_settings,
    get_provider_settings_record,
    list_provider_settings,
    serialize_provider_settings,
    set_active_provider,
    test_provider_connection,
)

router = APIRouter(prefix="/admin/ai-provider", tags=["Admin AI"])


class AIProviderSettingsPayload(BaseModel):
    display_name: str | None = None
    provider: AIProviderType = AIProviderType.OPENAI
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    system_prompt: str | None = None
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    batch_size: int = Field(default=10, ge=1, le=500)
    is_enabled: bool = False


class AIProviderSettingsUpdatePayload(BaseModel):
    display_name: str | None = None
    provider: AIProviderType | None = None
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    system_prompt: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    batch_size: int | None = Field(default=None, ge=1, le=500)
    is_enabled: bool | None = None


@router.get("")
async def get_ai_provider_settings(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    configs = await list_provider_settings(db)
    return {
        "items": [serialize_provider_settings(config) for config in configs],
        "provider_defaults": {
            provider.value: DEFAULT_PROVIDER_MODELS[provider]
            for provider in AIProviderType
        },
    }


@router.post("", status_code=201)
async def create_ai_provider_settings(
    payload: AIProviderSettingsPayload,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    config = await create_provider_settings(
        db,
        provider=payload.provider,
        display_name=(payload.display_name or "").strip() or None,
    )
    config.model = (payload.model or "").strip() or DEFAULT_PROVIDER_MODELS[payload.provider]
    config.base_url = payload.base_url.strip() if payload.base_url else None
    config.system_prompt = payload.system_prompt.strip() if payload.system_prompt else DEFAULT_SYSTEM_PROMPT
    config.temperature = payload.temperature
    config.batch_size = payload.batch_size
    config.is_enabled = payload.is_enabled
    config.updated_at = datetime.utcnow()

    if payload.api_key is not None and payload.api_key.strip():
        config.api_key = payload.api_key.strip()

    if config.is_enabled and not config.api_key:
        raise HTTPException(status_code=400, detail="Enablement requires a saved API key")
    if config.is_enabled:
        await set_active_provider(db, config)

    await db.commit()
    response = serialize_provider_settings(config)
    response["message"] = "AI provider settings saved"
    return response


@router.patch("/{config_id}")
async def update_ai_provider_settings(
    config_id: str,
    payload: AIProviderSettingsUpdatePayload,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    config = await get_provider_settings_record(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="AI provider config not found")

    if payload.provider is not None:
        config.provider = payload.provider
    if payload.display_name is not None:
        config.display_name = payload.display_name.strip() or config.provider.value.replace('_', ' ').title()
    if payload.model is not None:
        config.model = payload.model.strip() or DEFAULT_PROVIDER_MODELS[config.provider]
    if payload.base_url is not None:
        config.base_url = payload.base_url.strip() or None
    if payload.system_prompt is not None:
        config.system_prompt = payload.system_prompt.strip() or DEFAULT_SYSTEM_PROMPT
    if payload.temperature is not None:
        config.temperature = payload.temperature
    if payload.batch_size is not None:
        config.batch_size = payload.batch_size
    if payload.is_enabled is not None:
        config.is_enabled = payload.is_enabled
    if payload.api_key is not None and payload.api_key.strip():
        config.api_key = payload.api_key.strip()

    config.updated_at = datetime.utcnow()

    if config.is_enabled and not config.api_key:
        raise HTTPException(status_code=400, detail="Enablement requires a saved API key")
    if config.is_enabled:
        await set_active_provider(db, config)

    await db.commit()
    response = serialize_provider_settings(config)
    response["message"] = "AI provider settings saved"
    return response


@router.post("/{config_id}/activate")
async def activate_ai_provider(
    config_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    config = await get_provider_settings_record(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="AI provider config not found")
    if not config.api_key:
        raise HTTPException(status_code=400, detail="Save an API key before activating this provider")

    await set_active_provider(db, config)
    await db.commit()
    response = serialize_provider_settings(config)
    response["message"] = f"{config.display_name} is now the active AI provider"
    return response


@router.delete("/{config_id}")
async def delete_ai_provider(
    config_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    config = await get_provider_settings_record(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="AI provider config not found")

    await db.delete(config)
    await db.commit()
    return {"message": f"AI provider '{config.display_name}' deleted"}


@router.post("/{config_id}/test")
async def run_ai_provider_test(
    config_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    config = await get_provider_settings_record(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="AI provider config not found")

    try:
        result = await test_provider_connection(config)
        config.last_tested_at = datetime.utcnow()
        config.last_test_status = "SUCCESS"
        config.last_error = None
        await db.commit()
        return {
            "message": "AI provider connection successful",
            "id": config.id,
            "provider": config.provider.value,
            "model": config.model,
            "preview": result,
        }
    except AIProviderError as exc:
        config.last_tested_at = datetime.utcnow()
        config.last_test_status = "ERROR"
        config.last_error = str(exc)
        await db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc