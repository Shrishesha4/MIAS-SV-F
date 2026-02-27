from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class RecordType(str, enum.Enum):
    CONSULTATION = "CONSULTATION"
    LABORATORY = "LABORATORY"
    PROCEDURE = "PROCEDURE"
    MEDICATION = "MEDICATION"


class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    time = Column(String, nullable=False)
    type = Column(SQLEnum(RecordType), nullable=False, index=True)
    description = Column(Text, nullable=False)
    performed_by = Column(String, nullable=False)
    supervised_by = Column(String, nullable=True)
    department = Column(String, nullable=False)
    status = Column(String, nullable=False)
    diagnosis = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)
    evaluation = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    # Relationships
    patient = relationship("Patient", back_populates="medical_records")
    findings = relationship("MedicalFinding", back_populates="medical_record", cascade="all, delete-orphan")
    images = relationship("MedicalImage", back_populates="medical_record", cascade="all, delete-orphan")


class MedicalFinding(Base):
    __tablename__ = "medical_findings"

    id = Column(String, primary_key=True)
    record_id = Column(String, ForeignKey("medical_records.id"), nullable=False)
    parameter = Column(String, nullable=False)
    value = Column(String, nullable=False)
    reference = Column(String, nullable=True)
    status = Column(String, nullable=False)

    medical_record = relationship("MedicalRecord", back_populates="findings")


class MedicalImage(Base):
    __tablename__ = "medical_images"

    id = Column(String, primary_key=True)
    record_id = Column(String, ForeignKey("medical_records.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String, nullable=False)
    type = Column(String, nullable=False)

    medical_record = relationship("MedicalRecord", back_populates="images")
