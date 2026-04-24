from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Nutritionist(Base):
    __tablename__ = "nutritionists"

    id = Column(String, primary_key=True)
    nutritionist_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(
        String, ForeignKey("users.id"), unique=True, nullable=False, index=True
    )
    clinic_id = Column(
        String, ForeignKey("clinics.id"), unique=True, nullable=False, index=True
    )
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    photo = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )

    user = relationship("User", back_populates="nutritionist")
    clinic = relationship("Clinic", back_populates="nutritionist")
    sessions = relationship("NutritionistClinicSession", back_populates="nutritionist")
    notes = relationship("NutritionistNote", back_populates="nutritionist")


class NutritionistClinicSession(Base):
    __tablename__ = "nutritionist_clinic_sessions"

    id = Column(String, primary_key=True)
    nutritionist_id = Column(
        String, ForeignKey("nutritionists.id"), nullable=False, index=True
    )
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False, index=True)
    clinic_name = Column(String, nullable=False)
    department = Column(String, nullable=False)
    date = Column(DateTime, nullable=False, index=True)
    status = Column(String, default="Active")
    checked_in_at = Column(DateTime, nullable=False)
    checked_out_at = Column(DateTime, nullable=True)

    nutritionist = relationship("Nutritionist", back_populates="sessions")
    clinic = relationship("Clinic", back_populates="nutritionist_sessions")


class NutritionistNote(Base):
    __tablename__ = "nutritionist_notes"
    __table_args__ = (
        UniqueConstraint(
            "nutritionist_id",
            "patient_id",
            "note_date",
            name="uq_nutritionist_notes_daily",
        ),
        Index("idx_nutritionist_notes_patient_date", "patient_id", "note_date"),
    )

    id = Column(String, primary_key=True)
    nutritionist_id = Column(
        String, ForeignKey("nutritionists.id"), nullable=False, index=True
    )
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False, index=True)
    note_date = Column(Date, nullable=False)
    content = Column(Text, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow(), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
        nullable=False,
    )

    nutritionist = relationship("Nutritionist", back_populates="notes")
    clinic = relationship("Clinic", back_populates="nutritionist_notes")
    patient = relationship("Patient")
