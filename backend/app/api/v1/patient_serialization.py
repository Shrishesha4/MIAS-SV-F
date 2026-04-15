from __future__ import annotations

from app.models.patient import InsurancePolicy, Patient


def serialize_insurance_policy(policy: InsurancePolicy) -> dict:
    return {
        "id": policy.id,
        "provider": policy.provider,
        "policy_number": policy.policy_number,
        "valid_until": policy.valid_until.isoformat() if policy.valid_until else None,
        "coverage_type": policy.coverage_type,
        "insurance_category_id": policy.insurance_category_id,
        "icon_key": policy.icon_key,
        "custom_badge_symbol": policy.custom_badge_symbol,
        "color_primary": policy.color_primary,
        "color_secondary": policy.color_secondary,
    }


def serialize_patient_insurance(patient: Patient | None) -> list[dict]:
    if not patient or not patient.insurance_policies:
        return []

    return [serialize_insurance_policy(policy) for policy in patient.insurance_policies]


def serialize_patient_badge_context(patient: Patient | None) -> dict:
    if not patient:
        return {
            "category": None,
            "category_color_primary": None,
            "category_color_secondary": None,
        }

    return {
        "category": patient.category,
        "category_color_primary": patient.category_color_primary,
        "category_color_secondary": patient.category_color_secondary,
    }