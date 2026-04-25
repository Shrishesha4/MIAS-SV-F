from __future__ import annotations

import re
from collections.abc import Iterable

from app.services.patient_categories import normalize_patient_category_name


def normalize_charge_tier_spacing(value: str | None) -> str:
    cleaned = " ".join((value or "").strip().replace("_", " ").split())
    return re.sub(r"\s*-\s*", " - ", cleaned)


def build_mapped_charge_tier_key(insurance_name: str, patient_category_name: str) -> str:
    return normalize_charge_tier_spacing(f"{insurance_name} - {patient_category_name}")


def normalize_charge_tier_name(value: str | None) -> str:
    cleaned = normalize_charge_tier_spacing(value)
    if not cleaned:
        return ""

    if " - " in cleaned:
        insurance_name, patient_category_name = cleaned.split(" - ", 1)
        normalized_insurance = normalize_charge_tier_spacing(insurance_name)
        normalized_category = normalize_patient_category_name(patient_category_name)
        if normalized_insurance and normalized_category:
            return build_mapped_charge_tier_key(normalized_insurance, normalized_category)
        return cleaned

    return normalize_patient_category_name(cleaned)


def normalize_charge_tier_key(value: str | None) -> str:
    return normalize_charge_tier_name(value).casefold()


def build_all_mapped_charge_tiers(
    insurance_names_and_categories: Iterable[tuple[str, Iterable[str]]]
) -> list[str]:
    tiers: list[str] = []
    seen: set[str] = set()

    for insurance_name, category_names in insurance_names_and_categories:
        normalized_insurance = normalize_charge_tier_spacing(insurance_name)
        if not normalized_insurance:
            continue

        for category_name in category_names:
            normalized_category = normalize_patient_category_name(category_name)
            if not normalized_category:
                continue

            tier_name = build_mapped_charge_tier_key(normalized_insurance, normalized_category)
            tier_key = tier_name.casefold()
            if tier_key in seen:
                continue

            tiers.append(tier_name)
            seen.add(tier_key)

    return tiers
