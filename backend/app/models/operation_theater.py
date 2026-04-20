from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class OTStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class OperationTheater(Base):
    __tablename__ = "operation_theaters"

    id = Column(String, primary_key=True)
    ot_id = Column(String, unique=True, nullable=False)  # e.g. OT-01
    name = Column(String, nullable=True)
    location = Column(String, nullable=True)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    bookings = relationship("OTBooking", back_populates="theater", cascade="all, delete-orphan")


class OTBooking(Base):
    __tablename__ = "ot_bookings"
    __table_args__ = (
        Index("idx_ot_booking_date_theater", "date", "theater_id"),
        Index("idx_ot_booking_patient", "patient_id"),
    )

    id = Column(String, primary_key=True)
    theater_id = Column(String, ForeignKey("operation_theaters.id"), nullable=False, index=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=True, index=True)

    date = Column(String, nullable=False)        # YYYY-MM-DD
    start_time = Column(String, nullable=False)  # HH:MM
    end_time = Column(String, nullable=False)    # HH:MM

    procedure = Column(String, nullable=False)
    doctor_name = Column(String, nullable=False)
    notes = Column(Text, nullable=True)

    status = Column(SQLEnum(OTStatus), default=OTStatus.SCHEDULED, nullable=False, index=True)
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    theater = relationship("OperationTheater", back_populates="bookings")
    patient = relationship("Patient")
    student = relationship("Student")
