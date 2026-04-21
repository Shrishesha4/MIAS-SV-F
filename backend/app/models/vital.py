from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Index, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


CORE_VITAL_FIELD_NAMES = (
    "systolic_bp",
    "diastolic_bp",
    "heart_rate",
    "respiratory_rate",
    "temperature",
    "oxygen_saturation",
    "weight",
    "blood_glucose",
    "cholesterol",
    "bmi",
    "creatinine",
    "urea",
    "sodium",
    "potassium",
    "sgot",
    "sgpt",
    "hemoglobin",
    "wbc",
    "platelet",
    "rbc",
    "hct",
)


class VitalParameter(Base):
    """Configuration for vital parameters that appear in the vitals form."""
    __tablename__ = "vital_parameters"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)  # e.g., "systolic_bp"
    display_name = Column(String, nullable=False)  # e.g., "Systolic BP"
    category = Column(String, nullable=False, default="Primary")  # Primary, Secondary, Biochemistry, Haematology
    unit = Column(String, nullable=True)  # e.g., "mmHg", "bpm", "°C"
    min_value = Column(Float, nullable=True)  # For validation
    max_value = Column(Float, nullable=True)  # For validation
    value_style = Column(String, nullable=False, default="single")  # single, slash
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)


class Vital(Base):
    __tablename__ = "vitals"
    __table_args__ = (
        Index('idx_vital_patient_recorded', 'patient_id', 'recorded_at'),
    )

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

    # Biochemistry
    creatinine = Column(Float, nullable=True)
    urea = Column(Float, nullable=True)
    sodium = Column(Float, nullable=True)
    potassium = Column(Float, nullable=True)
    sgot = Column(Float, nullable=True)
    sgpt = Column(Float, nullable=True)

    # Haematology
    hemoglobin = Column(Float, nullable=True)
    wbc = Column(Float, nullable=True)
    platelet = Column(Float, nullable=True)
    rbc = Column(Float, nullable=True)
    hct = Column(Float, nullable=True)
    extra_values = Column(JSON, nullable=False, default=dict)

    # Relationships
    patient = relationship("Patient", back_populates="vitals")
