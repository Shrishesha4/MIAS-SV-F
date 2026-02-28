from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Index
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
    admission_date = Column(DateTime, nullable=False, index=True)
    discharge_date = Column(DateTime, nullable=True)
    department = Column(String, nullable=False)
    ward = Column(String, nullable=True)
    bed_number = Column(String, nullable=True)
    attending_doctor = Column(String, nullable=False)
    diagnosis = Column(Text, nullable=True)
    status = Column(String, default="Active", index=True)  # Active, Discharged
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    patient = relationship("Patient", back_populates="admissions")
