from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Admission(Base):
    __tablename__ = "admissions"

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    admission_date = Column(DateTime, nullable=False)
    discharge_date = Column(DateTime, nullable=True)
    department = Column(String, nullable=False)
    ward = Column(String, nullable=True)
    bed_number = Column(String, nullable=True)
    attending_doctor = Column(String, nullable=False)
    diagnosis = Column(Text, nullable=True)
    status = Column(String, default="Active")  # Active, Discharged
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    patient = relationship("Patient", back_populates="admissions")
