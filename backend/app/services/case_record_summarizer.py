"""Background service: auto-summarize case records missing findings/diagnosis/treatment."""
from __future__ import annotations

import asyncio
from datetime import datetime

from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.case_record import CaseRecord
from app.models.patient import Patient, PatientDiagnosisEntry, MedicalAlert, Allergy
from app.services.ai_provider import (
    AIProviderError,
    generate_case_record_draft,
    get_enabled_provider_settings,
)


def _is_empty(val: str | None) -> bool:
    return not val or not val.strip() or val.strip() in {"—", "-", "N/A", "n/a", ""}


async def _fetch_prior_records(db, patient_id: str, exclude_id: str, limit: int = 5) -> list[dict]:
    """Return the most recent summarized records for context."""
    result = await db.execute(
        select(CaseRecord)
        .where(
            and_(
                CaseRecord.patient_id == patient_id,
                CaseRecord.id != exclude_id,
                or_(
                    CaseRecord.findings.isnot(None),
                    CaseRecord.diagnosis.isnot(None),
                ),
            )
        )
        .order_by(CaseRecord.date.desc())
        .limit(limit)
    )
    records = result.scalars().all()
    out = []
    for r in records:
        entry: dict = {
            "date": r.date.strftime("%Y-%m-%d") if r.date else None,
            "procedure": r.procedure_name,
            "department": r.department,
            "description": r.description,
        }
        if r.findings and not _is_empty(r.findings):
            entry["findings"] = r.findings
        if r.diagnosis and not _is_empty(r.diagnosis):
            entry["diagnosis"] = r.diagnosis
        if r.treatment and not _is_empty(r.treatment):
            entry["treatment"] = r.treatment
        out.append(entry)
    return out


async def _fetch_diagnosis_history(db, patient_id: str) -> list[dict]:
    result = await db.execute(
        select(PatientDiagnosisEntry)
        .where(PatientDiagnosisEntry.patient_id == patient_id)
        .order_by(PatientDiagnosisEntry.added_at.desc())
        .limit(10)
    )
    entries = result.scalars().all()
    return [
        {
            "diagnosis": e.diagnosis,
            "icd_code": e.icd_code,
            "icd_description": e.icd_description,
            "is_active": e.is_active,
            "added_at": e.added_at.strftime("%Y-%m-%d") if e.added_at else None,
        }
        for e in entries
    ]


async def summarize_pending_case_records() -> int:
    """Find case records with empty findings/diagnosis/treatment and fill them via AI."""
    async with AsyncSessionLocal() as db:
        # Check AI is configured before querying
        try:
            await get_enabled_provider_settings(db)
        except AIProviderError:
            return 0

        # Fetch records missing all three fields
        result = await db.execute(
            select(CaseRecord)
            .where(
                and_(
                    or_(CaseRecord.findings.is_(None), CaseRecord.findings == ""),
                    or_(CaseRecord.diagnosis.is_(None), CaseRecord.diagnosis == ""),
                    or_(CaseRecord.treatment.is_(None), CaseRecord.treatment == ""),
                )
            )
            .options(
                selectinload(CaseRecord.patient).selectinload(Patient.allergies),
                selectinload(CaseRecord.patient).selectinload(Patient.medical_alerts),
            )
            .order_by(CaseRecord.date.asc())
            .limit(10)  # Process up to 10 per cycle
        )
        records = result.scalars().all()

        count = 0
        for record in records:
            patient = record.patient
            if not patient:
                continue

            try:
                prior = await _fetch_prior_records(db, patient.id, record.id)
                history = await _fetch_diagnosis_history(db, patient.id)

                result_draft = await generate_case_record_draft(
                    db=db,
                    patient=patient,
                    department=record.department,
                    procedure=record.procedure_name,
                    form_name=record.form_name,
                    form_description=record.form_description,
                    form_values=record.form_values or {},
                    prior_records=prior if prior else None,
                    diagnosis_history=history if history else None,
                )

                record.findings = result_draft["findings"]
                record.diagnosis = result_draft["diagnosis"]
                record.treatment = result_draft["treatment"]
                record.last_modified_at = datetime.utcnow()
                record.last_modified_by = "AI (auto)"
                count += 1

            except AIProviderError as exc:
                print(f"[AI Summarizer] Skipped record {record.id}: {exc}")
            except Exception as exc:
                print(f"[AI Summarizer] Error on record {record.id}: {exc}")

        if count:
            await db.commit()

        return count
