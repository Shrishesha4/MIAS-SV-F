from __future__ import annotations

from datetime import date, datetime
import json
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_provider import AIProviderSettings, AIProviderType
from app.models.patient import Patient


DEFAULT_PROVIDER_MODELS: dict[AIProviderType, str] = {
    AIProviderType.OPENAI: "gpt-4.1-mini",
    AIProviderType.ANTHROPIC: "claude-3-5-sonnet-latest",
    AIProviderType.GEMINI: "gemini-2.0-flash",
    AIProviderType.OPENAI_COMPATIBLE: "gpt-4.1-mini",
}

DEFAULT_SYSTEM_PROMPT = (
    "You are assisting with a medical case record draft for a teaching hospital workflow. "
    "Use only the provided information. Do not invent patient facts. "
    "Return valid JSON only with exactly these string keys: findings, diagnosis, treatment. "
    "Keep each value concise, clinically readable, and appropriate for a case record draft. "
    "If the context is incomplete, state that clearly inside the relevant field."
)


class AIProviderError(Exception):
    pass


def _default_display_name(provider: AIProviderType, sequence: int | None = None) -> str:
    base_name = provider.value.replace('_', ' ').title()
    if not sequence or sequence <= 1:
        return base_name
    return f"{base_name} {sequence}"


def _mask_api_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:4]}{'*' * (len(api_key) - 8)}{api_key[-4:]}"


def get_default_provider_config() -> dict[str, Any]:
    return {
        "id": "",
        "display_name": _default_display_name(AIProviderType.OPENAI),
        "provider": AIProviderType.OPENAI.value,
        "model": DEFAULT_PROVIDER_MODELS[AIProviderType.OPENAI],
        "base_url": None,
        "system_prompt": DEFAULT_SYSTEM_PROMPT,
        "temperature": 0.2,
        "batch_size": 10,
        "is_enabled": False,
        "has_api_key": False,
        "masked_api_key": None,
        "last_tested_at": None,
        "last_test_status": None,
        "last_error": None,
    }


def serialize_provider_settings(config: AIProviderSettings | None) -> dict[str, Any]:
    if not config:
        return get_default_provider_config()

    return {
        "id": config.id,
        "display_name": config.display_name,
        "provider": config.provider.value,
        "model": config.model,
        "base_url": config.base_url,
        "system_prompt": config.system_prompt or DEFAULT_SYSTEM_PROMPT,
        "temperature": config.temperature,
        "batch_size": config.batch_size,
        "is_enabled": config.is_enabled,
        "has_api_key": bool(config.api_key),
        "masked_api_key": _mask_api_key(config.api_key),
        "last_tested_at": config.last_tested_at.isoformat() if config.last_tested_at else None,
        "last_test_status": config.last_test_status,
        "last_error": config.last_error,
    }


async def list_provider_settings(db: AsyncSession) -> list[AIProviderSettings]:
    result = await db.execute(
        select(AIProviderSettings)
        .order_by(AIProviderSettings.created_at.asc(), AIProviderSettings.display_name.asc())
    )
    return list(result.scalars().all())


async def get_provider_settings_record(db: AsyncSession, config_id: str) -> AIProviderSettings | None:
    result = await db.execute(select(AIProviderSettings).where(AIProviderSettings.id == config_id))
    return result.scalar_one_or_none()


async def create_provider_settings(
    db: AsyncSession,
    provider: AIProviderType = AIProviderType.OPENAI,
    display_name: str | None = None,
) -> AIProviderSettings:
    existing_count = len(await list_provider_settings(db))
    config = AIProviderSettings(
        id=str(uuid4()),
        display_name=(display_name or _default_display_name(provider, existing_count + 1)).strip(),
        provider=provider,
        model=DEFAULT_PROVIDER_MODELS[provider],
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        temperature=0.2,
        batch_size=10,
        is_enabled=False,
    )
    db.add(config)
    await db.flush()
    return config


async def set_active_provider(db: AsyncSession, config: AIProviderSettings) -> AIProviderSettings:
    await db.execute(
        update(AIProviderSettings)
        .where(AIProviderSettings.id != config.id)
        .values(is_enabled=False, updated_at=datetime.utcnow())
    )
    config.is_enabled = True
    config.updated_at = datetime.utcnow()
    await db.flush()
    return config


async def get_enabled_provider_settings(db: AsyncSession) -> AIProviderSettings:
    result = await db.execute(
        select(AIProviderSettings)
        .where(AIProviderSettings.is_enabled == True)
        .order_by(AIProviderSettings.updated_at.desc(), AIProviderSettings.created_at.desc())
    )
    config = result.scalars().first()
    if not config or not config.is_enabled:
        raise AIProviderError("No active AI provider is configured")
    if not config.api_key:
        raise AIProviderError("The active AI provider is missing an API key")
    if not config.model:
        raise AIProviderError("The active AI provider is missing a model")
    return config


def _extract_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        fragments: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if text:
                    fragments.append(str(text))
        return "\n".join(fragments)
    return str(content or "")


def _parse_json_payload(raw_text: str) -> dict[str, Any]:
    cleaned = raw_text.strip()
    if not cleaned:
        raise AIProviderError("The AI provider returned an empty response")

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(cleaned[start:end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    raise AIProviderError("The AI provider response was not valid JSON")


async def _call_openai_compatible(
    config: AIProviderSettings,
    system_prompt: str,
    user_prompt: str,
) -> str:
    default_base_url = (
        "https://api.openai.com/v1"
        if config.provider == AIProviderType.OPENAI
        else "http://localhost:11434/v1"
    )
    base_url = (config.base_url or default_base_url).rstrip("/")
    url = f"{base_url}/chat/completions"
    payload = {
        "model": config.model,
        "temperature": config.temperature,
        "max_tokens": 800,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    choices = data.get("choices") or []
    if not choices:
        raise AIProviderError("The AI provider returned no completion choices")
    message = choices[0].get("message") or {}
    return _extract_text_content(message.get("content"))


async def _call_anthropic(
    config: AIProviderSettings,
    system_prompt: str,
    user_prompt: str,
) -> str:
    base_url = (config.base_url or "https://api.anthropic.com").rstrip("/")
    url = f"{base_url}/v1/messages"
    payload = {
        "model": config.model,
        "max_tokens": 800,
        "temperature": config.temperature,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_prompt},
        ],
    }
    headers = {
        "x-api-key": config.api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    return _extract_text_content(data.get("content"))


async def _call_gemini(
    config: AIProviderSettings,
    system_prompt: str,
    user_prompt: str,
) -> str:
    base_url = (config.base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
    url = f"{base_url}/models/{config.model}:generateContent"
    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}],
        },
        "contents": [
            {
                "parts": [{"text": user_prompt}],
            }
        ],
        "generationConfig": {
            "temperature": config.temperature,
            "responseMimeType": "application/json",
        },
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(url, params={"key": config.api_key}, json=payload)
        response.raise_for_status()
        data = response.json()

    candidates = data.get("candidates") or []
    if not candidates:
        raise AIProviderError("The AI provider returned no candidates")

    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    return "\n".join(str(part.get("text", "")) for part in parts if part.get("text"))


async def request_structured_completion(
    config: AIProviderSettings,
    system_prompt: str,
    user_prompt: str,
) -> dict[str, Any]:
    try:
        if config.provider in {AIProviderType.OPENAI, AIProviderType.OPENAI_COMPATIBLE}:
            raw_text = await _call_openai_compatible(config, system_prompt, user_prompt)
        elif config.provider == AIProviderType.ANTHROPIC:
            raw_text = await _call_anthropic(config, system_prompt, user_prompt)
        elif config.provider == AIProviderType.GEMINI:
            raw_text = await _call_gemini(config, system_prompt, user_prompt)
        else:
            raise AIProviderError(f"Unsupported AI provider: {config.provider.value}")
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip() or str(exc)
        raise AIProviderError(f"Provider request failed: {detail}") from exc
    except httpx.HTTPError as exc:
        raise AIProviderError(f"Provider request failed: {exc}") from exc

    return _parse_json_payload(raw_text)


def _stringify_context(data: dict[str, Any]) -> str:
    if not data:
        return "{}"
    return json.dumps(data, ensure_ascii=True, indent=2)


def build_case_record_user_prompt(
    patient: Patient,
    department: str | None,
    procedure: str | None,
    form_name: str | None,
    form_description: str | None,
    form_values: dict[str, Any],
) -> str:
    patient_age = None
    if patient.date_of_birth:
        today = date.today()
        patient_age = today.year - patient.date_of_birth.year - (
            (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
        )

    allergies = [allergy.allergen for allergy in (patient.allergies or [])]
    alerts = [alert.title for alert in (patient.medical_alerts or []) if alert.is_active]

    context = {
        "patient": {
            "name": patient.name,
            "patient_id": patient.patient_id,
            "age": patient_age,
            "gender": patient.gender.value if patient.gender else None,
            "blood_group": patient.blood_group,
            "primary_diagnosis": patient.primary_diagnosis,
            "allergies": allergies,
            "active_medical_alerts": alerts,
        },
        "case_record": {
            "department": department,
            "procedure": procedure,
            "form_name": form_name,
            "form_description": form_description,
            "current_form_values": form_values,
        },
        "instructions": {
            "required_output": ["findings", "diagnosis", "treatment"],
            "format": "Return JSON only.",
        },
    }

    return _stringify_context(context)


async def generate_case_record_draft(
    db: AsyncSession,
    patient: Patient,
    department: str | None,
    procedure: str | None,
    form_name: str | None,
    form_description: str | None,
    form_values: dict[str, Any],
) -> dict[str, str]:
    config = await get_enabled_provider_settings(db)
    system_prompt = config.system_prompt or DEFAULT_SYSTEM_PROMPT
    user_prompt = build_case_record_user_prompt(
        patient=patient,
        department=department,
        procedure=procedure,
        form_name=form_name,
        form_description=form_description,
        form_values=form_values,
    )
    response = await request_structured_completion(config, system_prompt, user_prompt)

    findings = str(response.get("findings") or "").strip()
    diagnosis = str(response.get("diagnosis") or "").strip()
    treatment = str(response.get("treatment") or "").strip()
    if not findings or not diagnosis or not treatment:
        raise AIProviderError("The AI provider did not return all required fields")

    return {
        "findings": findings,
        "diagnosis": diagnosis,
        "treatment": treatment,
    }


async def test_provider_connection(config: AIProviderSettings) -> dict[str, str]:
    if not config.api_key:
        raise AIProviderError("Save an API key before testing the provider connection")

    payload = await request_structured_completion(
        config,
        config.system_prompt or DEFAULT_SYSTEM_PROMPT,
        "Return JSON only with findings, diagnosis, treatment for a trivial connection test. Use 'Connection successful' in all three fields.",
    )

    return {
        "findings": str(payload.get("findings") or "").strip(),
        "diagnosis": str(payload.get("diagnosis") or "").strip(),
        "treatment": str(payload.get("treatment") or "").strip(),
    }