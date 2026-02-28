from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class PatientNotification(Base):
    __tablename__ = "patient_notifications"

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, nullable=False)  # APPOINTMENT, REPORT, PRESCRIPTION, SYSTEM, MEDICATION_REMINDER
    is_read = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    patient = relationship("Patient", back_populates="notifications")


class ScheduledNotification(Base):
    """Configurable notification schedules for automatic reminders."""
    __tablename__ = "scheduled_notifications"

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=True, index=True)
    target_role = Column(String, nullable=False)  # PATIENT, STUDENT, FACULTY
    target_id = Column(String, nullable=True)  # Specific user target (student_id or faculty_id)
    notification_type = Column(String, nullable=False)  # MEDICATION_REMINDER, APPOINTMENT_REMINDER, FOLLOW_UP, VITAL_CHECK
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    frequency = Column(String, nullable=False)  # DAILY, TWICE_DAILY, WEEKLY, ONCE, CUSTOM
    time_of_day = Column(String, nullable=True)  # e.g. "08:00", "14:00", "20:00"
    next_run_at = Column(DateTime, nullable=True, index=True)
    last_run_at = Column(DateTime, nullable=True)
    is_active = Column(Integer, default=1)
    reference_id = Column(String, nullable=True)  # Link to prescription_id, appointment_id, etc.
    reference_type = Column(String, nullable=True)  # PRESCRIPTION, APPOINTMENT, etc.
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
