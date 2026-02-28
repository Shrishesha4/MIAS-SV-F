from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List
from datetime import datetime, timedelta
import uuid

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.patient import Patient, Appointment
from app.models.vital import Vital
from app.models.prescription import Prescription, PrescriptionStatus
from app.models.medical_record import MedicalRecord
from app.models.admission import Admission
from app.models.report import Report
from app.models.wallet import WalletTransaction, WalletType, TransactionType
from app.models.notification import PatientNotification
from app.schemas.patient import PatientResponse, PatientDetailResponse

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.get("/me", response_model=PatientDetailResponse)
async def get_current_patient(
    user: User = Depends(require_role(UserRole.PATIENT)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Patient)
        .options(
            selectinload(Patient.emergency_contact),
            selectinload(Patient.allergies),
            selectinload(Patient.medical_alerts),
        )
        .where(Patient.user_id == user.id)
    )
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    return patient


@router.get("/{patient_id}", response_model=PatientDetailResponse)
async def get_patient(
    patient_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Patient)
        .options(
            selectinload(Patient.emergency_contact),
            selectinload(Patient.allergies),
            selectinload(Patient.medical_alerts),
        )
        .where(Patient.id == patient_id)
    )
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    return patient


@router.get("/{patient_id}/vitals")
async def get_patient_vitals(
    patient_id: str,
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(Vital)
        .where(Vital.patient_id == patient_id)
        .where(Vital.recorded_at >= cutoff_date)
        .order_by(Vital.recorded_at.desc())
    )

    vitals = result.scalars().all()
    return [
        {
            "id": v.id,
            "patient_id": v.patient_id,
            "recorded_at": v.recorded_at.isoformat() if v.recorded_at else None,
            "recorded_by": v.recorded_by,
            "systolic_bp": v.systolic_bp,
            "diastolic_bp": v.diastolic_bp,
            "heart_rate": v.heart_rate,
            "respiratory_rate": v.respiratory_rate,
            "temperature": v.temperature,
            "oxygen_saturation": v.oxygen_saturation,
            "weight": v.weight,
            "blood_glucose": v.blood_glucose,
            "cholesterol": v.cholesterol,
            "bmi": v.bmi,
        }
        for v in vitals
    ]


@router.post("/{patient_id}/vitals")
async def create_vital(
    patient_id: str,
    vital_data: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vital = Vital(
        id=str(uuid.uuid4()),
        patient_id=patient_id,
        recorded_at=datetime.utcnow(),
        recorded_by=vital_data.get("recorded_by"),
        systolic_bp=vital_data.get("systolic_bp"),
        diastolic_bp=vital_data.get("diastolic_bp"),
        heart_rate=vital_data.get("heart_rate"),
        respiratory_rate=vital_data.get("respiratory_rate"),
        temperature=vital_data.get("temperature"),
        oxygen_saturation=vital_data.get("oxygen_saturation"),
        weight=vital_data.get("weight"),
        blood_glucose=vital_data.get("blood_glucose"),
        cholesterol=vital_data.get("cholesterol"),
        bmi=vital_data.get("bmi"),
    )

    db.add(vital)
    await db.commit()
    await db.refresh(vital)

    return {"id": vital.id, "patient_id": vital.patient_id, "recorded_at": vital.recorded_at.isoformat()}


@router.get("/{patient_id}/records")
async def get_patient_records(
    patient_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MedicalRecord)
        .options(
            selectinload(MedicalRecord.findings),
            selectinload(MedicalRecord.images),
        )
        .where(MedicalRecord.patient_id == patient_id)
        .order_by(MedicalRecord.date.desc())
    )
    records = result.scalars().all()
    return [
        {
            "id": r.id,
            "patient_id": r.patient_id,
            "date": r.date.isoformat() if r.date else None,
            "time": r.time,
            "type": r.type.value if r.type else None,
            "description": r.description,
            "performed_by": r.performed_by,
            "supervised_by": r.supervised_by,
            "department": r.department,
            "status": r.status,
            "diagnosis": r.diagnosis,
            "recommendations": r.recommendations,
            "findings": [
                {
                    "id": f.id, "parameter": f.parameter,
                    "value": f.value, "reference": f.reference, "status": f.status,
                }
                for f in r.findings
            ],
            "images": [
                {
                    "id": i.id, "title": i.title,
                    "description": i.description, "url": i.url, "type": i.type,
                }
                for i in r.images
            ],
        }
        for r in records
    ]


@router.get("/{patient_id}/prescriptions")
async def get_patient_prescriptions(
    patient_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Prescription)
        .options(selectinload(Prescription.medications))
        .where(Prescription.patient_id == patient_id)
        .order_by(Prescription.date.desc())
    )
    prescriptions = result.scalars().all()
    return [
        {
            "id": p.id,
            "patient_id": p.patient_id,
            "date": p.date.isoformat() if p.date else None,
            "doctor": p.doctor,
            "department": p.department,
            "status": p.status.value if p.status else None,
            "medications": [
                {
                    "id": m.id, "name": m.name, "dosage": m.dosage,
                    "frequency": m.frequency, "duration": m.duration,
                    "instructions": m.instructions,
                    "refills_remaining": m.refills_remaining,
                    "start_date": m.start_date, "end_date": m.end_date,
                }
                for m in p.medications
            ],
        }
        for p in prescriptions
    ]


@router.put("/{patient_id}/prescriptions/{rx_id}/status")
async def update_prescription_status(
    patient_id: str,
    rx_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Prescription)
        .where(Prescription.id == rx_id)
        .where(Prescription.patient_id == patient_id)
    )
    prescription = result.scalar_one_or_none()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")

    prescription.status = body.get("status", prescription.status)
    await db.commit()
    return {"message": "Status updated"}


@router.get("/{patient_id}/admissions")
async def get_patient_admissions(
    patient_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Admission)
        .where(Admission.patient_id == patient_id)
        .order_by(Admission.admission_date.desc())
    )
    admissions = result.scalars().all()
    return [
        {
            "id": a.id,
            "patient_id": a.patient_id,
            "admission_date": a.admission_date.isoformat() if a.admission_date else None,
            "discharge_date": a.discharge_date.isoformat() if a.discharge_date else None,
            "department": a.department,
            "ward": a.ward,
            "bed_number": a.bed_number,
            "attending_doctor": a.attending_doctor,
            "diagnosis": a.diagnosis,
            "status": a.status,
            "notes": a.notes,
        }
        for a in admissions
    ]


@router.get("/{patient_id}/reports")
async def get_patient_reports(
    patient_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Report)
        .where(Report.patient_id == patient_id)
        .order_by(Report.date.desc())
    )
    reports = result.scalars().all()
    return [
        {
            "id": r.id,
            "patient_id": r.patient_id,
            "date": r.date.isoformat() if r.date else None,
            "title": r.title,
            "type": r.type,
            "department": r.department,
            "ordered_by": r.ordered_by,
            "status": r.status.value if r.status else None,
            "result_summary": r.result_summary,
            "notes": r.notes,
            "file_url": r.file_url,
        }
        for r in reports
    ]


@router.get("/{patient_id}/wallet/{wallet_type}/transactions")
async def get_wallet_transactions(
    patient_id: str,
    wallet_type: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    wt = WalletType.HOSPITAL if wallet_type.upper() == "HOSPITAL" else WalletType.PHARMACY

    result = await db.execute(
        select(WalletTransaction)
        .where(WalletTransaction.patient_id == patient_id)
        .where(WalletTransaction.wallet_type == wt)
        .order_by(WalletTransaction.date.desc())
    )
    txns = result.scalars().all()
    return [
        {
            "id": t.id,
            "patient_id": t.patient_id,
            "wallet_type": t.wallet_type.value if t.wallet_type else None,
            "date": t.date.isoformat() if t.date else None,
            "time": t.time,
            "description": t.description,
            "amount": float(t.amount) if t.amount else 0,
            "type": t.type.value if t.type else None,
            "payment_method": t.payment_method,
            "reference_number": t.reference_number,
            "invoice_number": t.invoice_number,
            "department": t.department,
            "provider": t.provider,
        }
        for t in txns
    ]


@router.get("/{patient_id}/notifications")
async def get_patient_notifications(
    patient_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PatientNotification)
        .where(PatientNotification.patient_id == patient_id)
        .order_by(PatientNotification.created_at.desc())
    )
    notifications = result.scalars().all()
    return [
        {
            "id": n.id,
            "patient_id": n.patient_id,
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "is_read": bool(n.is_read),
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifications
    ]


@router.put("/{patient_id}/notifications/read")
async def mark_notifications_read(
    patient_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PatientNotification)
        .where(PatientNotification.patient_id == patient_id)
        .where(PatientNotification.is_read == 0)
    )
    notifications = result.scalars().all()
    for n in notifications:
        n.is_read = 1
    await db.commit()
    return {"message": f"Marked {len(notifications)} notifications as read"}


@router.get("/{patient_id}/appointments")
async def get_patient_appointments(
    patient_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Appointment)
        .where(Appointment.patient_id == patient_id)
        .order_by(Appointment.date.desc())
    )
    appointments = result.scalars().all()
    return [
        {
            "id": a.id,
            "patient_id": a.patient_id,
            "date": a.date.isoformat() if a.date else None,
            "time": a.time,
            "doctor": a.doctor,
            "department": a.department,
            "status": a.status,
            "notes": a.notes,
        }
        for a in appointments
    ]


@router.get("/{patient_id}/next-appointment")
async def get_next_appointment(
    patient_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()
    result = await db.execute(
        select(Appointment)
        .where(Appointment.patient_id == patient_id)
        .where(Appointment.date >= now)
        .where(Appointment.status == "Scheduled")
        .order_by(Appointment.date.asc())
        .limit(1)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        return None
    return {
        "id": appointment.id,
        "date": appointment.date.isoformat() if appointment.date else None,
        "time": appointment.time,
        "doctor": appointment.doctor,
        "department": appointment.department,
        "status": appointment.status,
    }


@router.get("/{patient_id}/active-medications")
async def get_active_medications(
    patient_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get active medications for medication reminder."""
    result = await db.execute(
        select(Prescription)
        .options(selectinload(Prescription.medications))
        .where(Prescription.patient_id == patient_id)
        .where(Prescription.status == PrescriptionStatus.ACTIVE)
        .order_by(Prescription.date.desc())
    )
    prescriptions = result.scalars().all()
    
    # Flatten medications from active prescriptions
    medications = []
    for p in prescriptions:
        for m in p.medications:
            medications.append({
                "id": m.id,
                "prescription_id": p.id,
                "name": m.name,
                "dosage": m.dosage,
                "frequency": m.frequency,
                "instructions": m.instructions,
                "doctor": p.doctor,
            })
    return medications


@router.get("/{patient_id}/dashboard")
async def get_patient_dashboard(
    patient_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all dashboard data for patient home screen."""
    # Get next appointment
    now = datetime.utcnow()
    appt_result = await db.execute(
        select(Appointment)
        .where(Appointment.patient_id == patient_id)
        .where(Appointment.date >= now)
        .where(Appointment.status == "Scheduled")
        .order_by(Appointment.date.asc())
        .limit(1)
    )
    next_appointment = appt_result.scalar_one_or_none()
    
    # Get active medications
    rx_result = await db.execute(
        select(Prescription)
        .options(selectinload(Prescription.medications))
        .where(Prescription.patient_id == patient_id)
        .where(Prescription.status == PrescriptionStatus.ACTIVE)
        .limit(3)
    )
    active_prescriptions = rx_result.scalars().all()
    
    medications = []
    for p in active_prescriptions:
        for m in p.medications:
            medications.append({
                "id": m.id,
                "prescription_id": p.id,
                "name": m.name,
                "dosage": m.dosage,
                "frequency": m.frequency,
                "instructions": m.instructions,
            })
    
    # Get wallet balances
    for wt in [WalletType.HOSPITAL, WalletType.PHARMACY]:
        credit_result = await db.execute(
            select(func.coalesce(func.sum(WalletTransaction.amount), 0))
            .where(WalletTransaction.patient_id == patient_id)
            .where(WalletTransaction.wallet_type == wt)
            .where(WalletTransaction.type == TransactionType.CREDIT)
        )
        debit_result = await db.execute(
            select(func.coalesce(func.sum(WalletTransaction.amount), 0))
            .where(WalletTransaction.patient_id == patient_id)
            .where(WalletTransaction.wallet_type == wt)
            .where(WalletTransaction.type == TransactionType.DEBIT)
        )
        if wt == WalletType.HOSPITAL:
            hospital_balance = float(credit_result.scalar() or 0) - float(debit_result.scalar() or 0)
        else:
            pharmacy_balance = float(credit_result.scalar() or 0) - float(debit_result.scalar() or 0)
    
    # Get last visit date (most recent admission or record)
    last_visit = None
    admission_result = await db.execute(
        select(Admission.admission_date)
        .where(Admission.patient_id == patient_id)
        .order_by(Admission.admission_date.desc())
        .limit(1)
    )
    last_admission = admission_result.scalar_one_or_none()
    if last_admission:
        last_visit = last_admission.isoformat()
    
    return {
        "next_appointment": {
            "id": next_appointment.id,
            "date": next_appointment.date.isoformat() if next_appointment.date else None,
            "time": next_appointment.time,
            "doctor": next_appointment.doctor,
            "department": next_appointment.department,
        } if next_appointment else None,
        "active_medications": medications[:3],  # Limit to 3
        "hospital_balance": hospital_balance,
        "pharmacy_balance": pharmacy_balance,
        "last_visit": last_visit,
    }
