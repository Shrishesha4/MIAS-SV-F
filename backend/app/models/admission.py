from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Index, Integer, Float, Boolean, Date
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Admission(Base):
    __tablename__ = "admissions"
    __table_args__ = (
        Index('idx_admission_status_date', 'status', 'admission_date'),
        Index('idx_admission_patient_status', 'patient_id', 'status'),
    )

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    submitted_by_student_id = Column(String, ForeignKey("students.id"), nullable=True, index=True)
    faculty_approver_id = Column(String, ForeignKey("faculty.id"), nullable=True)
    admission_date = Column(DateTime, nullable=False, index=True)
    discharge_date = Column(DateTime, nullable=True)
    department = Column(String, nullable=False)
    ward = Column(String, nullable=True)
    bed_number = Column(String, nullable=True)
    attending_doctor = Column(String, nullable=False)
    reason = Column(Text, nullable=True)
    diagnosis = Column(Text, nullable=True)
    status = Column(String, default="Active", index=True)  # Active, Discharged, Transferred, Pending Approval
    notes = Column(Text, nullable=True)
    program_duration_days = Column(Integer, nullable=True)

    # ── Triage / Primary Survey ──────────────────────────────────────
    accompanied_by = Column(String, nullable=True)
    accompanied_by_contact = Column(String, nullable=True)
    airway_patent = Column(Boolean, nullable=True)
    breathing_adequate = Column(Boolean, nullable=True)
    pulse_present = Column(Boolean, nullable=True)
    capillary_refill_time = Column(Float, nullable=True)  # seconds

    # ── Admission Vitals ─────────────────────────────────────────────
    bp_admission = Column(String, nullable=True)       # e.g. "120/80"
    heart_rate_admission = Column(String, nullable=True)
    resp_rate_admission = Column(String, nullable=True)
    spo2_admission = Column(String, nullable=True)
    temp_admission = Column(String, nullable=True)
    weight_admission = Column(String, nullable=True)

    # ── GCS ─────────────────────────────────────────────────────────
    gcs_eye = Column(Integer, nullable=True)    # 1-4
    gcs_verbal = Column(Integer, nullable=True)  # 1-5
    gcs_motor = Column(Integer, nullable=True)   # 1-6

    # ── Additional Clinical Metrics ──────────────────────────────────
    cbg = Column(String, nullable=True)         # mg/dL
    pain_score = Column(Integer, nullable=True)  # 0-10

    # ── Clinical History ─────────────────────────────────────────────
    drug_allergy = Column(Text, nullable=True)
    menstrual_history = Column(Text, nullable=True)
    lmp = Column(Date, nullable=True)             # Last Menstrual Period
    identification_marks = Column(Text, nullable=True)
    chief_complaints = Column(Text, nullable=True)
    history_of_present_illness = Column(Text, nullable=True)
    past_medical_history = Column(Text, nullable=True)
    medication_history = Column(Text, nullable=True)
    surgical_history = Column(Text, nullable=True)
    physical_examination = Column(Text, nullable=True)

    # ── Assessment & Plan ────────────────────────────────────────────
    pain_score_reassessment = Column(Integer, nullable=True)
    provisional_diagnosis = Column(Text, nullable=True)
    expected_cost = Column(Float, nullable=True)   # INR
    proposed_plan = Column(Text, nullable=True)
    attached_document = Column(String, nullable=True)  # file path

    # ── Related/transferred admission info ───────────────────────────
    related_admission_id = Column(String, ForeignKey("admissions.id"), nullable=True)
    transferred_from_department = Column(String, nullable=True)
    referring_doctor = Column(String, nullable=True)

    # ── Discharge summary fields ─────────────────────────────────────
    discharge_summary = Column(Text, nullable=True)
    discharge_instructions = Column(Text, nullable=True)
    follow_up_date = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    # Relationships
    patient = relationship("Patient", back_populates="admissions")
    submitted_by_student = relationship("Student", foreign_keys=[submitted_by_student_id])
    faculty_approver = relationship("Faculty", foreign_keys=[faculty_approver_id])
    related_admission = relationship("Admission", remote_side=[id], backref="child_admissions")
    approval = relationship("Approval", back_populates="admission", uselist=False)
    io_events = relationship("IOEvent", back_populates="admission", cascade="all, delete-orphan")
    soap_notes = relationship("SOAPNote", back_populates="admission", cascade="all, delete-orphan")
    equipment = relationship("AdmissionEquipment", back_populates="admission", cascade="all, delete-orphan")
