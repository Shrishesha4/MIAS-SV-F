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
from app.models.patient import Patient, Appointment, MedicalAlert, InsurancePolicy
from app.models.vital import Vital
from app.models.prescription import (
    Prescription, PrescriptionStatus, PrescriptionMedication,
    MedicationDoseLog, MedicationDoseStatus,
    PrescriptionRequest, PrescriptionRequestStatus,
)
from app.models.medical_record import MedicalRecord
from app.models.admission import Admission
from app.models.faculty import Faculty
from app.models.report import Report
from app.models.wallet import WalletTransaction, WalletType, TransactionType
from app.models.notification import PatientNotification, ScheduledNotification
from app.models.case_record import CaseRecord
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
            selectinload(Patient.insurance_policies),
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
            selectinload(Patient.insurance_policies),
        )
        .where(Patient.id == patient_id)
    )
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    return patient


@router.put("/{patient_id}/profile")
async def update_patient_profile(
    patient_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update patient personal information."""
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if "name" in body:
        patient.name = body["name"]
    if "phone" in body:
        patient.phone = body["phone"]
    if "email" in body:
        patient.email = body["email"]
    if "address" in body:
        patient.address = body["address"]
    if "blood_group" in body:
        patient.blood_group = body["blood_group"]

    await db.commit()
    return {
        "message": "Profile updated successfully",
        "id": patient.id,
        "name": patient.name,
    }


@router.get("/{patient_id}/case-records")
async def get_patient_case_records(
    patient_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all case records for a patient (any role)."""
    result = await db.execute(
        select(CaseRecord)
        .where(CaseRecord.patient_id == patient_id)
        .order_by(CaseRecord.date.desc())
    )
    records = result.scalars().all()
    return [
        {
            "id": r.id,
            "patient_id": r.patient_id,
            "student_id": r.student_id,
            "date": r.date.isoformat() if r.date else None,
            "time": r.time,
            "type": r.type,
            "description": r.description,
            "department": r.department,
            "findings": r.findings,
            "diagnosis": r.diagnosis,
            "icd_code": r.icd_code,
            "icd_description": r.icd_description,
            "treatment": r.treatment,
            "notes": r.notes,
            "grade": r.grade,
            "provider": r.provider,
            "procedure_name": r.procedure_name,
            "status": r.status,
            "approved_by": r.approved_by,
            "approved_at": r.approved_at,
            "created_by_name": r.created_by_name,
            "created_by_role": r.created_by_role,
            "last_modified_by": r.last_modified_by,
            "last_modified_at": r.last_modified_at.isoformat() if r.last_modified_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


@router.post("/{patient_id}/case-records")
async def create_patient_case_record(
    patient_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a case record for a patient. Faculty records are auto-approved."""
    from app.models.faculty import Faculty

    is_faculty = user.role == UserRole.FACULTY

    # Resolve name of the creator
    creator_name = "Unknown"
    if is_faculty:
        fac_result = await db.execute(select(Faculty).where(Faculty.user_id == user.id))
        fac = fac_result.scalar_one_or_none()
        if fac:
            creator_name = fac.name
    else:
        from app.models.student import Student
        stu_result = await db.execute(select(Student).where(Student.user_id == user.id))
        stu = stu_result.scalar_one_or_none()
        if stu:
            creator_name = stu.name

    now = datetime.utcnow()
    record = CaseRecord(
        id=str(uuid.uuid4()),
        patient_id=patient_id,
        student_id=body.get("student_id"),  # null for faculty
        date=now,
        time=body.get("time"),
        type=body.get("procedure", "Examination"),
        procedure_name=body.get("procedure"),
        procedure_description=body.get("procedure_description"),
        description=body.get("description", ""),
        department=body.get("department"),
        findings=body.get("findings"),
        diagnosis=body.get("diagnosis"),
        icd_code=body.get("icd_code"),
        icd_description=body.get("icd_description"),
        treatment=body.get("treatment"),
        notes=body.get("notes"),
        provider=creator_name if is_faculty else body.get("provider"),
        doctor_name=creator_name if is_faculty else None,
        status="Approved" if is_faculty else "Pending",
        approved_by=creator_name if is_faculty else None,
        approved_at=now.isoformat() if is_faculty else None,
        created_by_name=creator_name,
        created_by_role=user.role.value,
        last_modified_by=creator_name,
        last_modified_at=now,
    )
    db.add(record)
    await db.commit()

    return {
        "id": record.id,
        "status": record.status,
        "created_by_name": record.created_by_name,
    }


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
            "creatinine": v.creatinine,
            "urea": v.urea,
            "sodium": v.sodium,
            "potassium": v.potassium,
            "sgot": v.sgot,
            "sgpt": v.sgpt,
            "hemoglobin": v.hemoglobin,
            "wbc": v.wbc,
            "platelet": v.platelet,
            "rbc": v.rbc,
            "hct": v.hct,
        }
        for v in vitals
    ]


@router.post("/{patient_id}/vitals")
async def create_vital(
    patient_id: str,
    vital_data: dict,
    user: User = Depends(require_role(UserRole.STUDENT, UserRole.FACULTY, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    vital = Vital(
        id=str(uuid.uuid4()),
        patient_id=patient_id,
        recorded_at=datetime.utcnow(),
        recorded_by=vital_data.get("recorded_by") or getattr(user, "username", None),
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
        creatinine=vital_data.get("creatinine"),
        urea=vital_data.get("urea"),
        sodium=vital_data.get("sodium"),
        potassium=vital_data.get("potassium"),
        sgot=vital_data.get("sgot"),
        sgpt=vital_data.get("sgpt"),
        hemoglobin=vital_data.get("hemoglobin"),
        wbc=vital_data.get("wbc"),
        platelet=vital_data.get("platelet"),
        rbc=vital_data.get("rbc"),
        hct=vital_data.get("hct"),
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

    # Get patient info for prescriptions
    patient_result = await db.execute(
        select(Patient).where(Patient.id == patient_id)
    )
    patient = patient_result.scalar_one_or_none()

    # Lookup doctor signatures for all prescriptions
    doctor_names = list(set(p.doctor for p in prescriptions if p.doctor))
    signature_map: dict = {}
    if doctor_names:
        from app.models.faculty import Faculty
        fac_result = await db.execute(
            select(Faculty).where(Faculty.name.in_(doctor_names))
        )
        for fac in fac_result.scalars().all():
            signature_map[fac.name] = fac.signature_image

    return [
        {
            "id": p.id,
            "prescription_id": p.prescription_id,
            "patient_id": p.patient_id,
            "date": p.date.isoformat() if p.date else None,
            "doctor": p.doctor,
            "doctor_license": p.doctor_license,
            "department": p.department,
            "hospital_name": p.hospital_name,
            "hospital_address": p.hospital_address,
            "hospital_contact": p.hospital_contact,
            "hospital_email": p.hospital_email,
            "hospital_website": p.hospital_website,
            "doctor_signature": p.doctor_signature or signature_map.get(p.doctor),
            "status": p.status.value if p.status else None,
            "notes": p.notes,
            "patient": {
                "name": patient.name if patient else None,
                "patient_id": patient.patient_id if patient else None,
                "date_of_birth": patient.date_of_birth.isoformat() if patient and patient.date_of_birth else None,
                "gender": patient.gender.value if patient and patient.gender else None,
                "phone": patient.phone if patient else None,
                "address": patient.address if patient else None,
            } if patient else None,
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


@router.put("/{patient_id}/prescriptions/{rx_id}")
async def update_prescription(
    patient_id: str,
    rx_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a prescription and its medications."""
    result = await db.execute(
        select(Prescription)
        .options(selectinload(Prescription.medications))
        .where(Prescription.id == rx_id)
        .where(Prescription.patient_id == patient_id)
    )
    prescription = result.scalar_one_or_none()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")

    # Update prescription fields
    if "status" in body:
        try:
            prescription.status = PrescriptionStatus(body["status"])
        except ValueError:
            pass
    if "doctor" in body:
        prescription.doctor = body["doctor"]
    if "notes" in body:
        prescription.notes = body["notes"]

    # Update medications if provided
    medications_data = body.get("medications", [])
    if medications_data:
        # Update existing medications by id, or update the first one
        for med_data in medications_data:
            med_id = med_data.get("id")
            if med_id:
                for existing_med in prescription.medications:
                    if existing_med.id == med_id:
                        if "name" in med_data:
                            existing_med.name = med_data["name"]
                        if "dosage" in med_data:
                            existing_med.dosage = med_data["dosage"]
                        if "frequency" in med_data:
                            existing_med.frequency = med_data["frequency"]
                        if "instructions" in med_data:
                            existing_med.instructions = med_data["instructions"]
                        if "start_date" in med_data:
                            existing_med.start_date = med_data["start_date"]
                        if "end_date" in med_data:
                            existing_med.end_date = med_data["end_date"]
                        break
            elif prescription.medications:
                # Update first medication if no id specified
                m = prescription.medications[0]
                if "name" in med_data:
                    m.name = med_data["name"]
                if "dosage" in med_data:
                    m.dosage = med_data["dosage"]
                if "frequency" in med_data:
                    m.frequency = med_data["frequency"]
                if "instructions" in med_data:
                    m.instructions = med_data["instructions"]
                if "start_date" in med_data:
                    m.start_date = med_data["start_date"]
                if "end_date" in med_data:
                    m.end_date = med_data["end_date"]

    await db.commit()
    return {"message": "Prescription updated", "status": prescription.status.value if prescription.status else None}


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
            "submitted_by_student_id": a.submitted_by_student_id,
            "faculty_approver_id": a.faculty_approver_id,
            "admission_date": a.admission_date.isoformat() if a.admission_date else None,
            "discharge_date": a.discharge_date.isoformat() if a.discharge_date else None,
            "department": a.department,
            "ward": a.ward,
            "bed_number": a.bed_number,
            "attending_doctor": a.attending_doctor,
            "reason": a.reason,
            "diagnosis": a.diagnosis,
            "status": a.status,
            "notes": a.notes,
            "program_duration_days": a.program_duration_days,
            # Triage
            "accompanied_by": a.accompanied_by,
            "accompanied_by_contact": a.accompanied_by_contact,
            "airway_patent": a.airway_patent,
            "breathing_adequate": a.breathing_adequate,
            "pulse_present": a.pulse_present,
            "capillary_refill_time": a.capillary_refill_time,
            # Vitals at admission
            "bp_admission": a.bp_admission,
            "heart_rate_admission": a.heart_rate_admission,
            "resp_rate_admission": a.resp_rate_admission,
            "spo2_admission": a.spo2_admission,
            "temp_admission": a.temp_admission,
            "weight_admission": a.weight_admission,
            # GCS
            "gcs_eye": a.gcs_eye,
            "gcs_verbal": a.gcs_verbal,
            "gcs_motor": a.gcs_motor,
            # Metrics
            "cbg": a.cbg,
            "pain_score": a.pain_score,
            # Clinical history
            "drug_allergy": a.drug_allergy,
            "menstrual_history": a.menstrual_history,
            "lmp": a.lmp.isoformat() if a.lmp else None,
            "identification_marks": a.identification_marks,
            "chief_complaints": a.chief_complaints,
            "history_of_present_illness": a.history_of_present_illness,
            "past_medical_history": a.past_medical_history,
            "medication_history": a.medication_history,
            "surgical_history": a.surgical_history,
            "physical_examination": a.physical_examination,
            # Assessment & plan
            "pain_score_reassessment": a.pain_score_reassessment,
            "provisional_diagnosis": a.provisional_diagnosis,
            "expected_cost": a.expected_cost,
            "proposed_plan": a.proposed_plan,
            # Misc
            "related_admission_id": a.related_admission_id,
            "transferred_from_department": a.transferred_from_department,
            "referring_doctor": a.referring_doctor,
            "discharge_summary": a.discharge_summary,
            "discharge_instructions": a.discharge_instructions,
            "follow_up_date": a.follow_up_date.isoformat() if a.follow_up_date else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in admissions
    ]


@router.post("/{patient_id}/admissions", status_code=201)
async def create_admission(
    patient_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new admission for a patient.
    - STUDENT: creates a 'Pending Approval' admission and auto-creates an Approval record
    - FACULTY/ADMIN: creates an 'Active' admission directly
    """
    from app.models.case_record import Approval, ApprovalType, ApprovalStatus
    from app.models.student import Student

    patient = (await db.execute(select(Patient).where(Patient.id == patient_id))).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    is_student = user.role == UserRole.STUDENT
    is_faculty = user.role == UserRole.FACULTY

    # Resolve attending doctor / submitted-by
    attending_doctor = body.get("attending_doctor", "")
    submitted_by_student_id = None
    faculty_approver_id = body.get("faculty_id")

    if is_student:
        stu = (await db.execute(select(Student).where(Student.user_id == user.id))).scalar_one_or_none()
        if stu:
            submitted_by_student_id = stu.id
            attending_doctor = attending_doctor or stu.name
    elif is_faculty and not attending_doctor:
        fac = (await db.execute(select(Faculty).where(Faculty.user_id == user.id))).scalar_one_or_none()
        if fac:
            attending_doctor = fac.name
            faculty_approver_id = faculty_approver_id or fac.id

    admission_date = body.get("admission_date")
    if admission_date and isinstance(admission_date, str):
        try:
            admission_date = datetime.fromisoformat(admission_date)
        except ValueError:
            admission_date = datetime.utcnow()
    else:
        admission_date = datetime.utcnow()

    # Parse LMP date
    lmp = None
    lmp_val = body.get("lmp")
    if lmp_val and isinstance(lmp_val, str):
        try:
            from datetime import date as _date
            lmp = _date.fromisoformat(lmp_val)
        except ValueError:
            pass

    status = "Pending Approval" if is_student else "Active"

    admission = Admission(
        id=str(uuid.uuid4()),
        patient_id=patient_id,
        submitted_by_student_id=submitted_by_student_id,
        faculty_approver_id=faculty_approver_id,
        admission_date=admission_date,
        department=body.get("department", ""),
        ward=body.get("ward", ""),
        bed_number=body.get("bed_number", ""),
        attending_doctor=attending_doctor,
        reason=body.get("reason"),
        diagnosis=body.get("diagnosis") or body.get("provisional_diagnosis"),
        status=status,
        notes=body.get("notes"),
        referring_doctor=body.get("referring_doctor"),
        # Triage
        accompanied_by=body.get("accompanied_by"),
        accompanied_by_contact=body.get("accompanied_by_contact"),
        airway_patent=body.get("airway_patent"),
        breathing_adequate=body.get("breathing_adequate"),
        pulse_present=body.get("pulse_present"),
        capillary_refill_time=body.get("capillary_refill_time"),
        # Admission vitals
        bp_admission=body.get("bp_admission"),
        heart_rate_admission=body.get("heart_rate_admission"),
        resp_rate_admission=body.get("resp_rate_admission"),
        spo2_admission=body.get("spo2_admission"),
        temp_admission=body.get("temp_admission"),
        weight_admission=body.get("weight_admission"),
        # GCS
        gcs_eye=body.get("gcs_eye"),
        gcs_verbal=body.get("gcs_verbal"),
        gcs_motor=body.get("gcs_motor"),
        # Metrics
        cbg=body.get("cbg"),
        pain_score=body.get("pain_score"),
        # Clinical history
        drug_allergy=body.get("drug_allergy"),
        menstrual_history=body.get("menstrual_history"),
        lmp=lmp,
        identification_marks=body.get("identification_marks"),
        chief_complaints=body.get("chief_complaints"),
        history_of_present_illness=body.get("history_of_present_illness"),
        past_medical_history=body.get("past_medical_history"),
        medication_history=body.get("medication_history"),
        surgical_history=body.get("surgical_history"),
        physical_examination=body.get("physical_examination"),
        # Assessment & plan
        pain_score_reassessment=body.get("pain_score_reassessment"),
        provisional_diagnosis=body.get("provisional_diagnosis"),
        expected_cost=body.get("expected_cost"),
        proposed_plan=body.get("proposed_plan"),
    )
    db.add(admission)
    await db.flush()

    # For student submissions: create a pending approval record
    if is_student and faculty_approver_id:
        db.add(Approval(
            id=str(uuid.uuid4()),
            approval_type=ApprovalType.ADMISSION,
            admission_id=admission.id,
            faculty_id=faculty_approver_id,
            patient_id=patient_id,
            student_id=submitted_by_student_id,
            status=ApprovalStatus.PENDING,
        ))

    await db.commit()
    await db.refresh(admission)

    return {
        "id": admission.id,
        "patient_id": admission.patient_id,
        "admission_date": admission.admission_date.isoformat(),
        "department": admission.department,
        "ward": admission.ward,
        "bed_number": admission.bed_number,
        "attending_doctor": admission.attending_doctor,
        "status": admission.status,
        "message": "Admission submitted for faculty approval" if is_student else "Patient admitted successfully",
    }


@router.put("/{patient_id}/admissions/{admission_id}")
async def update_admission(
    patient_id: str,
    admission_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an admission record."""
    admission = (
        await db.execute(
            select(Admission).where(
                Admission.id == admission_id,
                Admission.patient_id == patient_id,
            )
        )
    ).scalar_one_or_none()
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found")

    for field in ["department", "ward", "bed_number", "attending_doctor", "reason",
                  "diagnosis", "notes", "referring_doctor"]:
        if field in body:
            setattr(admission, field, body[field])

    await db.commit()
    return {"message": "Admission updated", "id": admission.id}


@router.post("/{patient_id}/admissions/{admission_id}/discharge")
async def discharge_patient(
    patient_id: str,
    admission_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Discharge a patient from an active admission."""
    admission = (
        await db.execute(
            select(Admission).where(
                Admission.id == admission_id,
                Admission.patient_id == patient_id,
            )
        )
    ).scalar_one_or_none()
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found")
    if admission.status != "Active":
        raise HTTPException(status_code=400, detail="Only active admissions can be discharged")

    admission.status = "Discharged"
    admission.discharge_date = datetime.utcnow()
    admission.discharge_summary = body.get("discharge_summary", "")
    admission.discharge_instructions = body.get("discharge_instructions", "")
    admission.diagnosis = body.get("diagnosis") or admission.diagnosis

    follow_up = body.get("follow_up_date")
    if follow_up:
        try:
            admission.follow_up_date = datetime.fromisoformat(follow_up)
        except ValueError:
            pass

    await db.commit()
    return {
        "message": "Patient discharged successfully",
        "id": admission.id,
        "discharge_date": admission.discharge_date.isoformat(),
    }


@router.post("/{patient_id}/admissions/{admission_id}/transfer")
async def transfer_patient(
    patient_id: str,
    admission_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Transfer a patient to another department."""
    old_admission = (
        await db.execute(
            select(Admission).where(
                Admission.id == admission_id,
                Admission.patient_id == patient_id,
            )
        )
    ).scalar_one_or_none()
    if not old_admission:
        raise HTTPException(status_code=404, detail="Admission not found")
    if old_admission.status != "Active":
        raise HTTPException(status_code=400, detail="Only active admissions can be transferred")

    # Mark old as Transferred
    old_admission.status = "Transferred"
    old_admission.discharge_date = datetime.utcnow()

    # Create new admission in target department
    new_admission = Admission(
        id=str(uuid.uuid4()),
        patient_id=patient_id,
        admission_date=datetime.utcnow(),
        department=body.get("department", ""),
        ward=body.get("ward", ""),
        bed_number=body.get("bed_number", ""),
        attending_doctor=body.get("attending_doctor", ""),
        reason=body.get("reason") or old_admission.reason,
        diagnosis=body.get("diagnosis") or old_admission.diagnosis,
        status="Active",
        notes=body.get("notes"),
        related_admission_id=old_admission.id,
        transferred_from_department=old_admission.department,
        referring_doctor=old_admission.attending_doctor,
    )
    db.add(new_admission)
    await db.commit()

    return {
        "message": "Patient transferred successfully",
        "old_admission_id": old_admission.id,
        "new_admission_id": new_admission.id,
        "new_department": new_admission.department,
    }


@router.get("/{patient_id}/reports")
async def get_patient_reports(
    patient_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.report import ReportFinding, ReportImage
    result = await db.execute(
        select(Report)
        .options(
            selectinload(Report.findings),
            selectinload(Report.images),
        )
        .where(Report.patient_id == patient_id)
        .order_by(Report.date.desc())
    )
    reports = result.scalars().all()
    return [
        {
            "id": r.id,
            "patient_id": r.patient_id,
            "date": r.date.isoformat() if r.date else None,
            "time": r.time,
            "title": r.title,
            "type": r.type,
            "department": r.department,
            "ordered_by": r.ordered_by,
            "performed_by": r.performed_by,
            "supervised_by": r.supervised_by,
            "status": r.status.value if r.status else None,
            "result_summary": r.result_summary,
            "notes": r.notes,
            "file_url": r.file_url,
            "findings": [
                {
                    "id": f.id,
                    "parameter": f.parameter,
                    "value": f.value,
                    "reference": f.reference,
                    "status": f.status,
                }
                for f in r.findings
            ],
            "images": [
                {
                    "id": i.id,
                    "title": i.title,
                    "description": i.description,
                    "url": i.url,
                    "type": i.type,
                }
                for i in r.images
            ],
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


@router.post("/{patient_id}/medications/{medication_id}/log-dose")
async def log_medication_dose(
    patient_id: str,
    medication_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Log a medication dose (taken, missed, or skipped) by the patient."""
    # Verify medication exists and belongs to patient
    result = await db.execute(
        select(PrescriptionMedication)
        .join(Prescription)
        .where(PrescriptionMedication.id == medication_id)
        .where(Prescription.patient_id == patient_id)
    )
    medication = result.scalar_one_or_none()
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")

    status_str = body.get("status", "TAKEN").upper()
    try:
        dose_status = MedicationDoseStatus(status_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status. Must be TAKEN, MISSED, or SKIPPED")

    dose_log = MedicationDoseLog(
        id=str(uuid.uuid4()),
        medication_id=medication_id,
        patient_id=patient_id,
        status=dose_status,
        scheduled_time=body.get("scheduled_time"),
        notes=body.get("notes"),
    )
    db.add(dose_log)

    # Create notifications for assigned student and doctor
    from app.models.student import StudentPatientAssignment, StudentNotification
    from app.models.faculty import FacultyNotification

    patient_result = await db.execute(
        select(Patient.name).where(Patient.id == patient_id)
    )
    patient_name = patient_result.scalar_one_or_none() or "Patient"

    status_text = "taken" if dose_status == MedicationDoseStatus.TAKEN else (
        "missed" if dose_status == MedicationDoseStatus.MISSED else "skipped"
    )
    notif_title = f"Medication {status_text.title()}"
    notif_message = f"{patient_name} has {status_text} {medication.name} {medication.dosage}"

    # Notify assigned students
    assignment_result = await db.execute(
        select(StudentPatientAssignment.student_id)
        .where(StudentPatientAssignment.patient_id == patient_id)
        .where(StudentPatientAssignment.status == "Active")
    )
    for (student_id,) in assignment_result.all():
        student_notif = StudentNotification(
            id=str(uuid.uuid4()),
            student_id=student_id,
            title=notif_title,
            message=notif_message,
            type="MEDICATION",
        )
        db.add(student_notif)

    # Notify prescribing doctor (look up faculty by name from prescription)
    rx_result = await db.execute(
        select(Prescription.doctor)
        .join(PrescriptionMedication)
        .where(PrescriptionMedication.id == medication_id)
    )
    doctor_name = rx_result.scalar_one_or_none()
    if doctor_name:
        from app.models.faculty import Faculty
        faculty_result = await db.execute(
            select(Faculty.id).where(Faculty.name == doctor_name)
        )
        faculty_id = faculty_result.scalar_one_or_none()
        if faculty_id:
            faculty_notif = FacultyNotification(
                id=str(uuid.uuid4()),
                faculty_id=faculty_id,
                title=notif_title,
                message=notif_message,
                type="MEDICATION",
            )
            db.add(faculty_notif)

    await db.commit()

    return {
        "id": dose_log.id,
        "status": dose_log.status.value,
        "logged_at": dose_log.logged_at.isoformat(),
        "message": f"Medication dose logged as {status_text}",
    }


@router.get("/{patient_id}/medication-history")
async def get_medication_history(
    patient_id: str,
    days: int = Query(7, ge=1, le=90),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get medication dose history for a patient."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(
        select(MedicationDoseLog)
        .options(selectinload(MedicationDoseLog.medication))
        .where(MedicationDoseLog.patient_id == patient_id)
        .where(MedicationDoseLog.logged_at >= cutoff)
        .order_by(MedicationDoseLog.logged_at.desc())
    )
    logs = result.scalars().all()

    return [
        {
            "id": log.id,
            "medication_id": log.medication_id,
            "medication_name": log.medication.name if log.medication else None,
            "medication_dosage": log.medication.dosage if log.medication else None,
            "status": log.status.value,
            "logged_at": log.logged_at.isoformat(),
            "scheduled_time": log.scheduled_time,
            "notes": log.notes,
        }
        for log in logs
    ]


@router.get("/{patient_id}/medication-adherence")
async def get_medication_adherence(
    patient_id: str,
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get medication adherence stats for a patient."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    total = await db.execute(
        select(func.count(MedicationDoseLog.id))
        .where(MedicationDoseLog.patient_id == patient_id)
        .where(MedicationDoseLog.logged_at >= cutoff)
    )
    total_count = total.scalar() or 0

    taken = await db.execute(
        select(func.count(MedicationDoseLog.id))
        .where(MedicationDoseLog.patient_id == patient_id)
        .where(MedicationDoseLog.logged_at >= cutoff)
        .where(MedicationDoseLog.status == MedicationDoseStatus.TAKEN)
    )
    taken_count = taken.scalar() or 0

    missed = await db.execute(
        select(func.count(MedicationDoseLog.id))
        .where(MedicationDoseLog.patient_id == patient_id)
        .where(MedicationDoseLog.logged_at >= cutoff)
        .where(MedicationDoseLog.status == MedicationDoseStatus.MISSED)
    )
    missed_count = missed.scalar() or 0

    skipped = await db.execute(
        select(func.count(MedicationDoseLog.id))
        .where(MedicationDoseLog.patient_id == patient_id)
        .where(MedicationDoseLog.logged_at >= cutoff)
        .where(MedicationDoseLog.status == MedicationDoseStatus.SKIPPED)
    )
    skipped_count = skipped.scalar() or 0

    adherence_rate = (taken_count / total_count * 100) if total_count > 0 else 0

    return {
        "total_doses": total_count,
        "taken": taken_count,
        "missed": missed_count,
        "skipped": skipped_count,
        "adherence_rate": round(adherence_rate, 1),
        "period_days": days,
    }


# ── Primary Diagnosis ──────────────────────────────────────────────

@router.put("/{patient_id}/primary-diagnosis")
async def update_primary_diagnosis(
    patient_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the primary diagnosis for a patient."""
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient.primary_diagnosis = body.get("diagnosis", patient.primary_diagnosis)
    patient.diagnosis_doctor = body.get("doctor", patient.diagnosis_doctor)
    patient.diagnosis_date = body.get("date", patient.diagnosis_date)
    patient.diagnosis_time = body.get("time", patient.diagnosis_time)
    await db.commit()

    return {
        "primary_diagnosis": patient.primary_diagnosis,
        "diagnosis_doctor": patient.diagnosis_doctor,
        "diagnosis_date": patient.diagnosis_date,
        "diagnosis_time": patient.diagnosis_time,
    }


# ── Medical Alerts ─────────────────────────────────────────────────

@router.post("/{patient_id}/medical-alerts")
async def add_medical_alert(
    patient_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a medical alert for a patient."""
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    alert = MedicalAlert(
        id=str(uuid.uuid4()),
        patient_id=patient_id,
        type=body.get("type", "ALERT"),
        severity=body.get("severity", "HIGH"),
        title=body.get("title", ""),
        description=body.get("description", ""),
        is_active=True,
        added_by=body.get("added_by", ""),
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    return {
        "id": alert.id,
        "title": alert.title,
        "type": alert.type,
        "severity": alert.severity,
        "is_active": alert.is_active,
        "added_by": alert.added_by,
        "added_at": alert.added_at.isoformat() if alert.added_at else None,
    }


@router.delete("/{patient_id}/medical-alerts/{alert_id}")
async def remove_medical_alert(
    patient_id: str,
    alert_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a medical alert."""
    result = await db.execute(
        select(MedicalAlert)
        .where(MedicalAlert.id == alert_id)
        .where(MedicalAlert.patient_id == patient_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_active = False
    await db.commit()
    return {"message": "Alert deactivated"}


@router.get("/{patient_id}/medical-alerts/history")
async def get_medical_alert_history(
    patient_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all medical alerts (active and inactive) for history view."""
    result = await db.execute(
        select(MedicalAlert)
        .where(MedicalAlert.patient_id == patient_id)
        .order_by(MedicalAlert.added_at.desc())
    )
    alerts = result.scalars().all()
    return [
        {
            "id": a.id,
            "title": a.title,
            "type": a.type,
            "severity": a.severity,
            "description": a.description,
            "is_active": a.is_active,
            "added_by": a.added_by,
            "added_at": a.added_at.isoformat() if a.added_at else None,
        }
        for a in alerts
    ]


# ── Prescriptions (Create) ────────────────────────────────────────

@router.post("/{patient_id}/prescriptions")
async def create_prescription(
    patient_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new prescription for a patient."""
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    rx_id = f"RX-{datetime.utcnow().strftime('%Y')}-{str(uuid.uuid4())[:4].upper()}"

    prescription = Prescription(
        id=str(uuid.uuid4()),
        prescription_id=rx_id,
        patient_id=patient_id,
        date=datetime.utcnow(),
        doctor=body.get("doctor", ""),
        department=body.get("department", ""),
        status=PrescriptionStatus.ACTIVE,
        notes=body.get("notes", ""),
        hospital_name=body.get("hospital_name", "SMC Hospital"),
    )
    db.add(prescription)

    # Add medications
    medications_data = body.get("medications", [])
    for med in medications_data:
        pm = PrescriptionMedication(
            id=str(uuid.uuid4()),
            prescription_id=prescription.id,
            name=med.get("name", ""),
            dosage=med.get("dosage", ""),
            frequency=med.get("frequency", ""),
            duration=med.get("duration", ""),
            instructions=med.get("instructions", ""),
            start_date=med.get("start_date", ""),
            end_date=med.get("end_date", ""),
        )
        db.add(pm)

    await db.commit()
    return {"id": prescription.id, "prescription_id": rx_id, "status": "created"}


# ── Prescription Requests ──────────────────────────────────────────

@router.get("/{patient_id}/prescription-requests")
async def get_prescription_requests(
    patient_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get prescription requests for a patient."""
    result = await db.execute(
        select(PrescriptionRequest)
        .where(PrescriptionRequest.patient_id == patient_id)
        .order_by(PrescriptionRequest.requested_at.desc())
    )
    requests = result.scalars().all()
    return [
        {
            "id": r.id,
            "medication": r.medication_name,
            "dosage": r.dosage,
            "notes": r.notes,
            "status": r.status.value if r.status else "PENDING",
            "requested_date": r.requested_at.strftime("%Y-%m-%d") if r.requested_at else None,
            "responded_by": r.responded_by,
            "responded_at": r.responded_at.isoformat() if r.responded_at else None,
            "response_notes": r.response_notes,
        }
        for r in requests
    ]


@router.post("/{patient_id}/prescription-requests")
async def create_prescription_request(
    patient_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Patient requests a prescription (refill or new)."""
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    req = PrescriptionRequest(
        id=str(uuid.uuid4()),
        patient_id=patient_id,
        medication_name=body.get("medication", ""),
        dosage=body.get("dosage", ""),
        notes=body.get("notes", ""),
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)

    return {
        "id": req.id,
        "medication": req.medication_name,
        "dosage": req.dosage,
        "status": req.status.value,
        "requested_date": req.requested_at.strftime("%Y-%m-%d") if req.requested_at else None,
    }


@router.put("/{patient_id}/prescription-requests/{request_id}/respond")
async def respond_to_prescription_request(
    patient_id: str,
    request_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Respond to a prescription request (approve/reject)."""
    result = await db.execute(
        select(PrescriptionRequest)
        .where(PrescriptionRequest.id == request_id)
        .where(PrescriptionRequest.patient_id == patient_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    status = body.get("status", "APPROVED").upper()
    try:
        req.status = PrescriptionRequestStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")

    req.responded_by = body.get("responded_by", "")
    req.responded_at = datetime.utcnow()
    req.response_notes = body.get("notes", "")
    await db.commit()

    return {"message": f"Request {status.lower()}", "status": req.status.value}


@router.post("/{patient_id}/prescriptions/{rx_id}/renew")
async def renew_prescription(
    patient_id: str,
    rx_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Renew a completed prescription by creating a new ACTIVE copy."""
    result = await db.execute(
        select(Prescription)
        .options(selectinload(Prescription.medications))
        .where(Prescription.id == rx_id)
        .where(Prescription.patient_id == patient_id)
    )
    old_rx = result.scalar_one_or_none()
    if not old_rx:
        raise HTTPException(status_code=404, detail="Prescription not found")

    # Count existing prescriptions for new ID
    count_result = await db.execute(
        select(func.count(Prescription.id)).where(Prescription.patient_id == patient_id)
    )
    count = count_result.scalar() or 0
    new_rx_display_id = f"RX-{datetime.utcnow().year}-{str(count + 1).zfill(4)}"

    # Look up doctor signature
    doctor_sig = old_rx.doctor_signature
    if not doctor_sig and old_rx.doctor:
        from app.models.faculty import Faculty as FacultyModel
        fac_r = await db.execute(select(FacultyModel).where(FacultyModel.name == old_rx.doctor))
        fac = fac_r.scalar_one_or_none()
        if fac:
            doctor_sig = fac.signature_image

    new_rx_id = str(uuid.uuid4())
    now = datetime.utcnow()
    new_rx = Prescription(
        id=new_rx_id,
        prescription_id=new_rx_display_id,
        patient_id=patient_id,
        date=now,
        doctor=old_rx.doctor,
        doctor_license=old_rx.doctor_license,
        department=old_rx.department,
        hospital_name=old_rx.hospital_name,
        hospital_address=old_rx.hospital_address,
        hospital_contact=old_rx.hospital_contact,
        hospital_email=old_rx.hospital_email,
        hospital_website=old_rx.hospital_website,
        doctor_signature=doctor_sig,
        status=PrescriptionStatus.ACTIVE,
        notes=f"Renewed from {old_rx.prescription_id or old_rx.id[:12]}",
    )
    db.add(new_rx)

    # Copy medications with fresh dates
    from datetime import date
    for m in old_rx.medications:
        # Parse duration to calculate end date
        duration_days = 30
        if m.duration:
            parts = m.duration.split()
            try:
                duration_days = int(parts[0])
            except (ValueError, IndexError):
                pass

        db.add(PrescriptionMedication(
            id=str(uuid.uuid4()),
            prescription_id=new_rx_id,
            name=m.name,
            dosage=m.dosage,
            frequency=m.frequency,
            duration=m.duration,
            instructions=m.instructions,
            refills_remaining=m.refills_remaining,
            start_date=date.today().isoformat(),
            end_date=(date.today() + timedelta(days=duration_days)).isoformat(),
        ))

    await db.commit()
    return {
        "id": new_rx_id,
        "prescription_id": new_rx_display_id,
        "message": "Prescription renewed successfully",
    }


# ── Insurance CRUD ──────────────────────────────────────────────
@router.post("/{patient_id}/insurance")
async def add_insurance_policy(
    patient_id: str,
    data: dict,
    user: User = Depends(require_role(UserRole.PATIENT)),
    db: AsyncSession = Depends(get_db),
):
    patient = (await db.execute(select(Patient).where(Patient.user_id == user.id))).scalar_one_or_none()
    if not patient or patient.id != patient_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    from datetime import date as d
    valid_until = None
    if data.get("valid_until"):
        try:
            valid_until = d.fromisoformat(data["valid_until"])
        except (ValueError, TypeError):
            valid_until = None

    policy = InsurancePolicy(
        id=str(uuid.uuid4()),
        patient_id=patient_id,
        provider=data["provider"],
        policy_number=data["policy_number"],
        valid_until=valid_until,
        coverage_type=data.get("coverage_type"),
    )
    db.add(policy)
    await db.commit()
    return {
        "id": policy.id,
        "provider": policy.provider,
        "policy_number": policy.policy_number,
        "valid_until": policy.valid_until.isoformat() if policy.valid_until else None,
        "coverage_type": policy.coverage_type,
    }


@router.delete("/{patient_id}/insurance/{policy_id}")
async def delete_insurance_policy(
    patient_id: str,
    policy_id: str,
    user: User = Depends(require_role(UserRole.PATIENT)),
    db: AsyncSession = Depends(get_db),
):
    patient = (await db.execute(select(Patient).where(Patient.user_id == user.id))).scalar_one_or_none()
    if not patient or patient.id != patient_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    policy = (await db.execute(
        select(InsurancePolicy).where(InsurancePolicy.id == policy_id, InsurancePolicy.patient_id == patient_id)
    )).scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Insurance policy not found")

    await db.delete(policy)
    await db.commit()
    return {"message": "Insurance policy deleted"}
