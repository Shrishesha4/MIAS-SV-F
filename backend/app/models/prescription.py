from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum as SQLEnum, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class PrescriptionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    BOUGHT = "BOUGHT"
    RECEIVE = "RECEIVE"
    COMPLETED = "COMPLETED"


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    date = Column(DateTime, nullable=False)
    doctor = Column(String, nullable=False)
    department = Column(String, nullable=False)
    status = Column(SQLEnum(PrescriptionStatus), default=PrescriptionStatus.ACTIVE)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    # Relationships
    patient = relationship("Patient", back_populates="prescriptions")
    medications = relationship("PrescriptionMedication", back_populates="prescription", cascade="all, delete-orphan")


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
