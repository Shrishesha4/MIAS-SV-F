from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum as SQLEnum, Integer, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class PrescriptionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    BOUGHT = "BOUGHT"
    RECEIVE = "RECEIVE"
    COMPLETED = "COMPLETED"


class MedicationDoseStatus(str, enum.Enum):
    TAKEN = "TAKEN"
    MISSED = "MISSED"
    SKIPPED = "SKIPPED"


class Prescription(Base):
    __tablename__ = "prescriptions"
    __table_args__ = (
        Index('idx_prescription_status_date', 'status', 'date'),
        Index('idx_prescription_patient_status', 'patient_id', 'status'),
    )

    id = Column(String, primary_key=True)
    prescription_id = Column(String, nullable=True)  # Display ID like RX-2023-0056
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    doctor = Column(String, nullable=False)
    doctor_license = Column(String, nullable=True)  # License number
    department = Column(String, nullable=False)
    hospital_name = Column(String, nullable=True)
    hospital_address = Column(String, nullable=True)
    hospital_contact = Column(String, nullable=True)
    hospital_email = Column(String, nullable=True)
    hospital_website = Column(String, nullable=True)
    doctor_signature = Column(String, nullable=True)  # URL to doctor's signature image
    status = Column(SQLEnum(PrescriptionStatus), default=PrescriptionStatus.ACTIVE, index=True)
    notes = Column(Text, nullable=True)  # Additional notes
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    # Relationships
    patient = relationship("Patient", back_populates="prescriptions")
    medications = relationship("PrescriptionMedication", back_populates="prescription", cascade="all, delete-orphan")
    approval = relationship("Approval", back_populates="prescription", uselist=False)


class PrescriptionMedication(Base):
    __tablename__ = "prescription_medications"

    id = Column(String, primary_key=True)
    prescription_id = Column(String, ForeignKey("prescriptions.id"), nullable=False)
    name = Column(String, nullable=False)
    dosage = Column(String, nullable=False)
    frequency = Column(String, nullable=False)
    duration = Column(String, nullable=False)
    instructions = Column(Text, nullable=True)
    refills_remaining = Column(Integer, default=0)
    start_date = Column(String, nullable=False)
    end_date = Column(String, nullable=False)

    prescription = relationship("Prescription", back_populates="medications")
    dose_logs = relationship("MedicationDoseLog", back_populates="medication", cascade="all, delete-orphan")


class MedicationDoseLog(Base):
    """Tracks when a patient reports taking, missing, or skipping a dose."""
    __tablename__ = "medication_dose_logs"
    __table_args__ = (
        Index('idx_dose_log_med_date', 'medication_id', 'logged_at'),
        Index('idx_dose_log_patient_date', 'patient_id', 'logged_at'),
    )

    id = Column(String, primary_key=True)
    medication_id = Column(String, ForeignKey("prescription_medications.id"), nullable=False, index=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    status = Column(SQLEnum(MedicationDoseStatus), nullable=False, default=MedicationDoseStatus.TAKEN)
    logged_at = Column(DateTime, default=lambda: datetime.utcnow(), nullable=False)
    scheduled_time = Column(String, nullable=True)  # e.g. "Morning", "Afternoon", "Night"
    notes = Column(Text, nullable=True)

    medication = relationship("PrescriptionMedication", back_populates="dose_logs")
    patient = relationship("Patient")


class PrescriptionRequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class PrescriptionRequest(Base):
    """Patient requests for prescription refills or new prescriptions."""
    __tablename__ = "prescription_requests"

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    medication_name = Column(String, nullable=False)
    dosage = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(SQLEnum(PrescriptionRequestStatus), default=PrescriptionRequestStatus.PENDING)
    requested_at = Column(DateTime, default=lambda: datetime.utcnow())
    responded_by = Column(String, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    response_notes = Column(Text, nullable=True)

    patient = relationship("Patient")
