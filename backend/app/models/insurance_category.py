"""Insurance category models for patient registration."""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer, Float, ForeignKey, Table
from sqlalchemy.orm import relationship

from app.database import Base


class InsuranceCategory(Base):
    """Insurance/payment categories that determine patient access and pricing."""
    __tablename__ = "insurance_categories"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    is_default = Column(Boolean, nullable=False, default=False)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )

    # Relationship to clinic configurations
    clinic_configs = relationship("InsuranceClinicConfig", back_populates="insurance_category", cascade="all, delete-orphan")


class InsuranceClinicConfig(Base):
    """Configuration linking insurance categories to clinics with pricing and walk-in settings."""
    __tablename__ = "insurance_clinic_configs"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    insurance_category_id = Column(String, ForeignKey("insurance_categories.id"), nullable=False, index=True)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False, index=True)
    
    # Walk-in type for this category-clinic combination
    walk_in_type = Column(
        String, 
        nullable=False, 
        default="NO_WALK_IN",
        comment="Options: NO_WALK_IN, WALKIN_PRIME, WALKIN_CLASSIC, WALKIN_CAMP, WALKIN_ELITE"
    )
    
    # Registration fee for this category at this clinic
    registration_fee = Column(Float, nullable=False, default=100.0)
    
    # Whether this clinic is available for this insurance category
    is_enabled = Column(Boolean, nullable=False, default=True)
    
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )

    # Relationships
    insurance_category = relationship("InsuranceCategory", back_populates="clinic_configs")
    clinic = relationship("Clinic", back_populates="insurance_configs")
