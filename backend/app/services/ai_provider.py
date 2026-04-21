from __future__ import annotations

from datetime import date, datetime
import json
import logging
import re
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_provider import AIProviderSettings, AIProviderType
from app.models.patient import Patient

logger = logging.getLogger(__name__)


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
        logger.error("AI provider returned empty response")
        raise AIProviderError("The AI provider returned an empty response")

    logger.debug("Raw AI response (first 500 chars): %s", cleaned[:500])

    # Strip markdown code fences that models often add despite being told not to
    fence_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?\s*```", cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()
        logger.debug("Stripped markdown fences, result (first 500 chars): %s", cleaned[:500])

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError as e:
        logger.warning("Initial JSON parse failed: %s", e)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(cleaned[start:end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError as e:
            logger.warning("Fallback JSON parse failed: %s", e)

    for start_index, char in enumerate(cleaned):
        if char != "{":
            continue
        depth = 0
        in_string = False
        escape_next = False
        for end_index in range(start_index, len(cleaned)):
            current = cleaned[end_index]
            if escape_next:
                escape_next = False
                continue
            if current == "\\":
                escape_next = True
                continue
            if current == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if current == "{":
                depth += 1
            elif current == "}":
                depth -= 1
                if depth == 0:
                    candidate = cleaned[start_index:end_index + 1]
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        break

    logger.error("Failed to parse AI response as JSON. Full response: %s", raw_text[:2000])
    raise AIProviderError("The AI provider response was not valid JSON")


async def _call_openai_compatible(
    config: AIProviderSettings,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int | None = None,
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
        "max_tokens": max_tokens or 800,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if (
        config.provider == AIProviderType.OPENAI
        or "api.openai.com" in base_url
        or "openrouter.ai" in base_url
    ):
        payload["response_format"] = {"type": "json_object"}
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
    max_tokens: int | None = None,
) -> str:
    base_url = (config.base_url or "https://api.anthropic.com").rstrip("/")
    url = f"{base_url}/v1/messages"
    payload = {
        "model": config.model,
        "max_tokens": max_tokens or 800,
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
    max_tokens: int | None = None,
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
            "maxOutputTokens": max_tokens or 800,
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
    max_tokens: int | None = None,
) -> dict[str, Any]:
    try:
        if config.provider in {AIProviderType.OPENAI, AIProviderType.OPENAI_COMPATIBLE}:
            raw_text = await _call_openai_compatible(config, system_prompt, user_prompt, max_tokens=max_tokens)
        elif config.provider == AIProviderType.ANTHROPIC:
            raw_text = await _call_anthropic(config, system_prompt, user_prompt, max_tokens=max_tokens)
        elif config.provider == AIProviderType.GEMINI:
            raw_text = await _call_gemini(config, system_prompt, user_prompt, max_tokens=max_tokens)
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
    prior_records: list[dict[str, Any]] | None = None,
    diagnosis_history: list[dict[str, Any]] | None = None,
) -> str:
    patient_age = None
    if patient.date_of_birth:
        today = date.today()
        patient_age = today.year - patient.date_of_birth.year - (
            (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
        )

    allergies = [allergy.allergen for allergy in (patient.allergies or [])]
    alerts = [
        {"title": alert.title, "severity": alert.severity}
        for alert in (patient.medical_alerts or [])
        if alert.is_active
    ]

    context: dict[str, Any] = {
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

    if diagnosis_history:
        context["diagnosis_history"] = diagnosis_history

    if prior_records:
        context["prior_case_records"] = prior_records

    return _stringify_context(context)


async def generate_case_record_draft(
    db: AsyncSession,
    patient: Patient,
    department: str | None,
    procedure: str | None,
    form_name: str | None,
    form_description: str | None,
    form_values: dict[str, Any],
    prior_records: list[dict[str, Any]] | None = None,
    diagnosis_history: list[dict[str, Any]] | None = None,
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
        prior_records=prior_records,
        diagnosis_history=diagnosis_history,
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


# ─── Diagnosis Suggestion Service ─────────────────────────────────────────────

DIAGNOSIS_SYSTEM_PROMPT = (
    "You are a medical diagnostic assistant for a teaching hospital. "
    "Based on the patient information and current form data provided, "
    "analyze the symptoms and clinical findings to suggest the top N primary diagnosis diseases. "
    "Return valid JSON only with exactly this structure: "
    "'suggestions': array of objects, each with 'disease' (string), 'confidence' (number 0-100), "
    "'reasoning' (string explaining why), and 'icd_code' (string if available). "
    "Return exactly the requested number of suggestions ranked by confidence (highest first). "
    "Only include diseases that are clinically plausible given the data. "
    "If the context is insufficient, note that in the reasoning."
)


def _isoformat(value: date | datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _serialize_recent_diagnosis_entries(patient: Patient, limit: int = 5) -> list[dict[str, Any]]:
    entries = [entry for entry in (patient.diagnosis_entries or []) if entry.is_active]
    return [
        {
            "diagnosis": entry.diagnosis,
            "icd_code": entry.icd_code,
            "icd_description": entry.icd_description,
            "added_at": _isoformat(entry.added_at),
        }
        for entry in entries[:limit]
    ]


def _serialize_recent_admissions(patient: Patient, limit: int = 3) -> list[dict[str, Any]]:
    admissions = sorted(
        patient.admissions or [],
        key=lambda admission: admission.admission_date or datetime.min,
        reverse=True,
    )
    return [
        {
            "admission_date": _isoformat(admission.admission_date),
            "discharge_date": _isoformat(admission.discharge_date),
            "status": admission.status,
            "department": admission.department,
            "ward": admission.ward,
            "attending_doctor": admission.attending_doctor,
            "reason": admission.reason,
            "diagnosis": admission.diagnosis,
            "chief_complaints": admission.chief_complaints,
            "history_of_present_illness": admission.history_of_present_illness,
            "past_medical_history": admission.past_medical_history,
            "provisional_diagnosis": admission.provisional_diagnosis,
            "physical_examination": admission.physical_examination,
            "discharge_summary": admission.discharge_summary,
        }
        for admission in admissions[:limit]
    ]


def _serialize_recent_case_records(patient: Patient, limit: int = 3) -> list[dict[str, Any]]:
    records = sorted(
        patient.case_records or [],
        key=lambda record: record.date or record.created_at or datetime.min,
        reverse=True,
    )
    return [
        {
            "date": _isoformat(record.date),
            "type": record.type,
            "department": record.department,
            "form_name": record.form_name,
            "procedure_name": record.procedure_name,
            "description": record.description,
            "findings": record.findings,
            "diagnosis": record.diagnosis,
            "treatment": record.treatment,
        }
        for record in records[:limit]
    ]


def _serialize_recent_prescriptions(patient: Patient, limit: int = 3) -> list[dict[str, Any]]:
    prescriptions = sorted(
        patient.prescriptions or [],
        key=lambda prescription: prescription.date or prescription.created_at or datetime.min,
        reverse=True,
    )
    return [
        {
            "date": _isoformat(prescription.date),
            "department": prescription.department,
            "doctor": prescription.doctor,
            "status": prescription.status.value if hasattr(prescription.status, "value") else prescription.status,
            "notes": prescription.notes,
            "medications": [
                {
                    "name": medication.name,
                    "dosage": medication.dosage,
                    "frequency": medication.frequency,
                    "duration": medication.duration,
                    "instructions": medication.instructions,
                }
                for medication in (prescription.medications or [])[:5]
            ],
        }
        for prescription in prescriptions[:limit]
    ]


def _serialize_latest_vitals(patient: Patient) -> dict[str, Any] | None:
    latest_vital = max(
        patient.vitals or [],
        key=lambda vital: vital.recorded_at or datetime.min,
        default=None,
    )
    if latest_vital is None:
        return None

    vitals = {
        "recorded_at": _isoformat(latest_vital.recorded_at),
        "systolic_bp": latest_vital.systolic_bp,
        "diastolic_bp": latest_vital.diastolic_bp,
        "heart_rate": latest_vital.heart_rate,
        "respiratory_rate": latest_vital.respiratory_rate,
        "temperature": latest_vital.temperature,
        "oxygen_saturation": latest_vital.oxygen_saturation,
        "weight": latest_vital.weight,
        "blood_glucose": latest_vital.blood_glucose,
        "cholesterol": latest_vital.cholesterol,
        "bmi": latest_vital.bmi,
        "extra_values": latest_vital.extra_values,
    }
    return {key: value for key, value in vitals.items() if value is not None and value != {}}


def build_diagnosis_user_prompt(
    patient: Patient,
    department: str | None,
    form_name: str | None,
    form_values: dict[str, Any],
    prior_diagnoses: list[dict[str, Any]] | None = None,
    top_n: int = 5,
) -> str:
    patient_age = None
    if patient.date_of_birth:
        today = date.today()
        patient_age = today.year - patient.date_of_birth.year - (
            (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
        )

    allergies = [allergy.allergen for allergy in (patient.allergies or [])]
    alerts = [
        {"title": alert.title, "severity": alert.severity}
        for alert in (patient.medical_alerts or [])
        if alert.is_active
    ]

    context: dict[str, Any] = {
        "patient_demographics": {
            "name": patient.name,
            "patient_id": patient.patient_id,
            "age": patient_age,
            "gender": patient.gender.value if patient.gender else None,
            "blood_group": patient.blood_group,
            "category": patient.category,
        },
        "patient_history": {
            "primary_diagnosis": patient.primary_diagnosis,
            "allergies": allergies,
            "active_medical_alerts": alerts,
            "recent_diagnosis_entries": _serialize_recent_diagnosis_entries(patient),
            "recent_admissions": _serialize_recent_admissions(patient),
            "recent_case_records": _serialize_recent_case_records(patient),
            "recent_prescriptions": _serialize_recent_prescriptions(patient),
            "latest_vitals": _serialize_latest_vitals(patient),
        },
        "current_form": {
            "department": department,
            "form_name": form_name,
            "form_values": form_values,
        },
        "instructions": {
            "required_output": "suggestions array with disease, confidence, reasoning, icd_code",
            "count": top_n,
            "format": "Return JSON only.",
        },
    }

    if prior_diagnoses:
        context["prior_diagnoses"] = prior_diagnoses

    return _stringify_context(context)


async def get_diagnosis_suggestions(
    db: AsyncSession,
    patient: Patient,
    department: str | None,
    form_name: str | None,
    form_values: dict[str, Any],
    prior_diagnoses: list[dict[str, Any]] | None = None,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    config = await get_enabled_provider_settings(db)
    system_prompt = DIAGNOSIS_SYSTEM_PROMPT
    user_prompt = build_diagnosis_user_prompt(
        patient=patient,
        department=department,
        form_name=form_name,
        form_values=form_values,
        prior_diagnoses=prior_diagnoses,
        top_n=top_n,
    )
    response = await request_structured_completion(config, system_prompt, user_prompt)

    suggestions = response.get("suggestions")
    if not suggestions or not isinstance(suggestions, list):
        raise AIProviderError("The AI provider did not return diagnosis suggestions")

    # Validate and normalize suggestions
    validated = []
    for s in suggestions[:top_n]:
        if isinstance(s, dict):
            validated.append({
                "disease": str(s.get("disease") or "").strip(),
                "confidence": min(max(float(s.get("confidence") or 0), 0), 100),
                "reasoning": str(s.get("reasoning") or "").strip(),
                "icd_code": str(s.get("icd_code") or "").strip(),
            })

    if not validated:
        raise AIProviderError("No valid diagnosis suggestions returned")

    return validated
