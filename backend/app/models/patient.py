from sqlalchemy import (
    Column, String, Date, DateTime, Enum as SQLEnum, ForeignKey, Boolean, Text, Index,
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class Gender(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (
        Index('idx_patient_category_created', 'category', 'created_at'),
        Index('idx_patient_name_search', 'name'),
        Index('idx_patient_phone', 'phone'),
    )

    id = Column(String, primary_key=True)
    patient_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(SQLEnum(Gender), nullable=False)
    blood_group = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String, nullable=True)
    address = Column(String, nullable=False)
    photo = Column(String, nullable=True)
    aadhaar_id = Column(String, nullable=True)
    abha_id = Column(String, nullable=True)
    primary_diagnosis = Column(Text, nullable=True)
    diagnosis_doctor = Column(String, nullable=True)
    diagnosis_date = Column(String, nullable=True)
    diagnosis_time = Column(String, nullable=True)
    category = Column(String, nullable=False, default="Classic")
    category_color_primary = Column(String, nullable=False, default="#60A5FA")
    category_color_secondary = Column(String, nullable=False, default="#1D4ED8")
    is_deceased = Column(Boolean, default=False, nullable=False)
    mother_patient_id = Column(String, ForeignKey("patients.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )

    # Relationships
    user = relationship("User", back_populates="patient")
    mother = relationship("Patient", remote_side="Patient.id", foreign_keys="Patient.mother_patient_id", backref="children")
    emergency_contact = relationship("EmergencyContact", back_populates="patient", uselist=False,
                                     foreign_keys="EmergencyContact.patient_id")
    insurance_policies = relationship("InsurancePolicy", back_populates="patient")
    allergies = relationship("Allergy", back_populates="patient")
    medical_alerts = relationship("MedicalAlert", back_populates="patient")
    diagnosis_entries = relationship(
        "PatientDiagnosisEntry",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="desc(PatientDiagnosisEntry.added_at)",
    )
    admissions = relationship("Admission", back_populates="patient")
    medical_records = relationship("MedicalRecord", back_populates="patient")
    prescriptions = relationship("Prescription", back_populates="patient")
    reports = relationship("Report", back_populates="patient")
    vitals = relationship("Vital", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient")
    notifications = relationship("PatientNotification", back_populates="patient")
    wallet_transactions = relationship("WalletTransaction", back_populates="patient")
    wallets = relationship("PatientWallet", back_populates="patient")
    assigned_students = relationship("StudentPatientAssignment", back_populates="patient")
    case_records = relationship("CaseRecord", back_populates="patient")
    nurse_orders = relationship("NurseOrder", back_populates="patient")
    sbar_notes = relationship("SBARNote", back_populates="patient")


class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=True)
    name = Column(String, nullable=False)
    relationship_ = Column("relationship", String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String, nullable=True)
    address = Column(String, nullable=True)

    patient = relationship("Patient", back_populates="emergency_contact",
                           foreign_keys=[patient_id])
    student = relationship("Student", back_populates="emergency_contact",
                           foreign_keys=[student_id])


class InsurancePolicy(Base):
    __tablename__ = "insurance_policies"

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    insurance_category_id = Column(String, nullable=True, index=True)
    provider = Column(String, nullable=False)
    policy_number = Column(String, nullable=False)
    valid_until = Column(Date, nullable=True)
    coverage_type = Column(String, nullable=True)
    icon_key = Column(String, nullable=True)
    custom_badge_symbol = Column(String, nullable=True)
    color_primary = Column(String, nullable=True)
    color_secondary = Column(String, nullable=True)

    patient = relationship("Patient", back_populates="insurance_policies")


class Allergy(Base):
    __tablename__ = "allergies"

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    allergen = Column(String, nullable=False)
    severity = Column(String, nullable=False)  # HIGH, MEDIUM, LOW
    reaction = Column(String, nullable=True)

    patient = relationship("Patient", back_populates="allergies")


class MedicalAlert(Base):
    __tablename__ = "medical_alerts"

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    symptoms = Column(Text, nullable=True)  # stored as JSON string
    is_active = Column(Boolean, default=True)
    added_by = Column(String, nullable=True)
    added_at = Column(DateTime, default=lambda: datetime.utcnow())

    patient = relationship("Patient", back_populates="medical_alerts")


class PatientDiagnosisEntry(Base):
    __tablename__ = "patient_diagnosis_entries"
    __table_args__ = (
        Index("idx_patient_diagnosis_patient_active", "patient_id", "is_active"),
        Index("idx_patient_diagnosis_added_at", "added_at"),
    )

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    diagnosis = Column(Text, nullable=False)
    icd_code = Column(String, nullable=True)
    icd_description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    added_by = Column(String, nullable=True)
    added_at = Column(DateTime, default=lambda: datetime.utcnow(), nullable=False)
    removed_by = Column(String, nullable=True)
    removed_at = Column(DateTime, nullable=True)

    patient = relationship("Patient", back_populates="diagnosis_entries")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    time = Column(String, nullable=False)
    doctor = Column(String, nullable=False)
    department = Column(String, nullable=False)
    status = Column(String, default="Scheduled")
    notes = Column(Text, nullable=True)

    patient = relationship("Patient", back_populates="appointments")
