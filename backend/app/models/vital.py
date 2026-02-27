from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Vital(Base):
    __tablename__ = "vitals"

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    recorded_at = Column(DateTime, default=lambda: datetime.utcnow(), index=True)
    recorded_by = Column(String, nullable=True)

    # Primary Vitals
    systolic_bp = Column(Integer, nullable=True)
    diastolic_bp = Column(Integer, nullable=True)
    heart_rate = Column(Integer, nullable=True)
    respiratory_rate = Column(Integer, nullable=True)
    temperature = Column(Float, nullable=True)
    oxygen_saturation = Column(Integer, nullable=True)

    # Secondary Vitals
    weight = Column(Float, nullable=True)
    blood_glucose = Column(Integer, nullable=True)
    cholesterol = Column(Integer, nullable=True)
    bmi = Column(Float, nullable=True)

    # Relationships
    patient = relationship("Patient", back_populates="vitals")
