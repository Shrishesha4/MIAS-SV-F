from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Nurse(Base):
    __tablename__ = "nurses"

    id = Column(String, primary_key=True)
    nurse_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    photo = Column(String, nullable=True)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=True, index=True)
    
    # Hospital/Ward assignment
    hospital = Column(String, nullable=True)  # Stored clinic display name
    ward = Column(String, nullable=True)  # e.g., "ICU Ward A"
    shift = Column(String, nullable=True)  # e.g., "Morning Shift (08:00-16:00)"
    department = Column(String, nullable=True)  # e.g., "Critical Care"
    
    # First-time login flag
    has_selected_station = Column(Integer, default=0)  # 0 = needs to select, 1 = selected
    
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )

    # Relationships
    user = relationship("User", back_populates="nurse")
    clinic = relationship("Clinic")
    notifications = relationship("NurseNotification", back_populates="nurse")
    completed_orders = relationship("NurseOrder", back_populates="nurse")
    sbar_notes = relationship("SBARNote", back_populates="nurse")


class NurseNotification(Base):
    __tablename__ = "nurse_notifications"

    id = Column(String, primary_key=True)
    nurse_id = Column(String, ForeignKey("nurses.id"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, nullable=False)
    is_read = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    nurse = relationship("Nurse", back_populates="notifications")
