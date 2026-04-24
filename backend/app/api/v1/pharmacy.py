from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_role
from app.database import get_db
from app.models.case_record import Approval, ApprovalStatus
from app.models.prescription import (
    Prescription,
    PrescriptionDispensingStatus,
    PrescriptionStatus,
)
from app.models.user import User, UserRole


router = APIRouter(prefix="/pharmacy", tags=["Pharmacy"])


def _serialize_order(prescription: Prescription) -> dict:
    patient = prescription.patient
    approval = prescription.approval
    requested_by = approval.student.name if approval and approval.student else None
    requested_at = prescription.date or prescription.created_at
    notes = prescription.notes or ""

    return {
        "id": prescription.id,
        "prescription_id": prescription.prescription_id,
        "patient": {
            "id": patient.id,
            "name": patient.name,
            "patient_id": patient.patient_id,
        } if patient else None,
        "doctor": prescription.doctor,
        "department": prescription.department,
        "requested_by": requested_by,
        "requested_at": requested_at.isoformat() if requested_at else None,
        "dispensing_status": prescription.dispensing_status.value,
        "is_urgent": "urgent" in notes.lower(),
        "notes": prescription.notes,
        "prepared_at": prescription.prepared_at.isoformat() if prescription.prepared_at else None,
        "issued_at": prescription.issued_at.isoformat() if prescription.issued_at else None,
        "medications": [
            {
                "id": medication.id,
                "name": medication.name,
                "dosage": medication.dosage,
                "frequency": medication.frequency,
                "duration": medication.duration,
                "instructions": medication.instructions,
            }
            for medication in (prescription.medications or [])
        ],
    }


async def _get_pharmacy_prescription(
    db: AsyncSession,
    *,
    prescription_id: str,
) -> Prescription:
    result = await db.execute(
        select(Prescription)
        .options(
            selectinload(Prescription.patient),
            selectinload(Prescription.medications),
            selectinload(Prescription.approval).selectinload(Approval.student),
        )
        .where(Prescription.id == prescription_id)
        .where(Prescription.status == PrescriptionStatus.ACTIVE)
        .where(
            or_(
                ~Prescription.approval.has(),
                Prescription.approval.has(Approval.status == ApprovalStatus.APPROVED),
            )
        )
    )
    prescription = result.scalar_one_or_none()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return prescription


@router.get("/dashboard")
async def get_pharmacy_dashboard(
    search: Optional[str] = Query(None, description="Search by patient name, patient ID, or RX number"),
    user: User = Depends(require_role(UserRole.PHARMACY)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Prescription)
        .options(
            selectinload(Prescription.patient),
            selectinload(Prescription.medications),
            selectinload(Prescription.approval).selectinload(Approval.student),
        )
        .where(Prescription.status == PrescriptionStatus.ACTIVE)
        .where(
            or_(
                ~Prescription.approval.has(),
                Prescription.approval.has(Approval.status == ApprovalStatus.APPROVED),
            )
        )
        .order_by(Prescription.date.desc(), Prescription.created_at.desc())
    )
    prescriptions = result.scalars().all()

    if search:
        needle = search.strip().lower()
        prescriptions = [
            prescription
            for prescription in prescriptions
            if needle in (prescription.patient.name if prescription.patient else "").lower()
            or needle in (prescription.patient.patient_id if prescription.patient else "").lower()
            or needle in (prescription.prescription_id or "").lower()
        ]

    today = datetime.utcnow().date()
    in_preparation = [
        prescription
        for prescription in prescriptions
        if prescription.dispensing_status == PrescriptionDispensingStatus.PENDING_PREPARATION
    ]
    ready_for_dispatch = [
        prescription
        for prescription in prescriptions
        if prescription.dispensing_status == PrescriptionDispensingStatus.READY_FOR_DISPATCH
    ]
    issued_today = [
        prescription
        for prescription in prescriptions
        if prescription.dispensing_status == PrescriptionDispensingStatus.ISSUED
        and prescription.issued_at
        and prescription.issued_at.date() == today
    ]
    urgent_orders = [
        prescription
        for prescription in prescriptions
        if "urgent" in (prescription.notes or "").lower()
    ]

    return {
        "summary": {
            "in_preparation": len(in_preparation),
            "ready_for_dispatch": len(ready_for_dispatch),
            "issued_today": len(issued_today),
            "urgent_orders": len(urgent_orders),
        },
        "preparation_tray": [_serialize_order(prescription) for prescription in in_preparation],
        "dispatch_tray": [_serialize_order(prescription) for prescription in ready_for_dispatch],
    }


@router.post("/prescriptions/{prescription_id}/prepare")
async def mark_prescription_prepared(
    prescription_id: str,
    user: User = Depends(require_role(UserRole.PHARMACY)),
    db: AsyncSession = Depends(get_db),
):
    prescription = await _get_pharmacy_prescription(db, prescription_id=prescription_id)

    if prescription.dispensing_status == PrescriptionDispensingStatus.ISSUED:
        raise HTTPException(status_code=400, detail="Prescription has already been issued")
    if prescription.dispensing_status == PrescriptionDispensingStatus.READY_FOR_DISPATCH:
        return {"message": "Prescription already prepared", "order": _serialize_order(prescription)}

    prescription.dispensing_status = PrescriptionDispensingStatus.READY_FOR_DISPATCH
    prescription.prepared_at = datetime.utcnow()
    prescription.prepared_by = user.id
    await db.commit()
    await db.refresh(prescription)

    return {"message": "Prescription marked as prepared", "order": _serialize_order(prescription)}


@router.post("/prescriptions/{prescription_id}/issue")
async def mark_prescription_issued(
    prescription_id: str,
    user: User = Depends(require_role(UserRole.PHARMACY)),
    db: AsyncSession = Depends(get_db),
):
    prescription = await _get_pharmacy_prescription(db, prescription_id=prescription_id)

    if prescription.dispensing_status == PrescriptionDispensingStatus.ISSUED:
        return {"message": "Prescription already issued", "order": _serialize_order(prescription)}
    if prescription.dispensing_status != PrescriptionDispensingStatus.READY_FOR_DISPATCH:
        raise HTTPException(status_code=400, detail="Prepare the prescription before issuing it")

    prescription.dispensing_status = PrescriptionDispensingStatus.ISSUED
    prescription.issued_at = datetime.utcnow()
    prescription.issued_by = user.id
    await db.commit()
    await db.refresh(prescription)

    return {"message": "Prescription marked as issued", "order": _serialize_order(prescription)}