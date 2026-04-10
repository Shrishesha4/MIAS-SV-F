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
    get_or_create_provider_settings,
    serialize_provider_settings,
    test_provider_connection,
)

router = APIRouter(prefix="/admin/ai-provider", tags=["Admin AI"])


class AIProviderSettingsPayload(BaseModel):
    provider: AIProviderType
    model: str
    api_key: str | None = None
    base_url: str | None = None
    system_prompt: str | None = None
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    is_enabled: bool = False


@router.get("")
async def get_ai_provider_settings(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    config = await get_or_create_provider_settings(db)
    await db.commit()
    response = serialize_provider_settings(config)
    response["provider_defaults"] = {
        provider.value: DEFAULT_PROVIDER_MODELS[provider]
        for provider in AIProviderType
    }
    return response


@router.put("")
async def update_ai_provider_settings(
    payload: AIProviderSettingsPayload,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    config = await get_or_create_provider_settings(db)

    config.provider = payload.provider
    config.model = payload.model.strip() or DEFAULT_PROVIDER_MODELS[payload.provider]
    config.base_url = payload.base_url.strip() if payload.base_url else None
    config.system_prompt = payload.system_prompt.strip() if payload.system_prompt else DEFAULT_SYSTEM_PROMPT
    config.temperature = payload.temperature
    config.is_enabled = payload.is_enabled
    config.updated_at = datetime.utcnow()

    if payload.api_key is not None and payload.api_key.strip():
        config.api_key = payload.api_key.strip()

    if config.is_enabled and not config.api_key:
        raise HTTPException(status_code=400, detail="Enablement requires a saved API key")

    await db.commit()
    response = serialize_provider_settings(config)
    response["provider_defaults"] = {
        provider.value: DEFAULT_PROVIDER_MODELS[provider]
        for provider in AIProviderType
    }
    response["message"] = "AI provider settings saved"
    return response


@router.post("/test")
async def run_ai_provider_test(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    config = await get_or_create_provider_settings(db)
    try:
        result = await test_provider_connection(db)
        config.last_tested_at = datetime.utcnow()
        config.last_test_status = "SUCCESS"
        config.last_error = None
        await db.commit()
        return {
            "message": "AI provider connection successful",
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