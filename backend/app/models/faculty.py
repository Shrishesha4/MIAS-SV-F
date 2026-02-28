from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Date
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Faculty(Base):
    __tablename__ = "faculty"

    id = Column(String, primary_key=True)
    faculty_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String, nullable=False)
    department = Column(String, nullable=False, index=True)
    specialty = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    photo = Column(String, nullable=True)
    availability = Column(String, nullable=True)  # e.g., "On-call 24/7", "Available 8AM-8PM"
    availability_status = Column(String, default="Available")  # Available, Busy, Unavailable
    is_emergency_contact = Column(Integer, default=0)  # 1 if this faculty is an emergency contact
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )

    # Relationships
    user = relationship("User", back_populates="faculty")
    approvals = relationship("Approval", back_populates="faculty")
    notifications = relationship("FacultyNotification", back_populates="faculty")
    schedules = relationship("FacultySchedule", back_populates="faculty")


class FacultyNotification(Base):
    __tablename__ = "faculty_notifications"

    id = Column(String, primary_key=True)
    faculty_id = Column(String, ForeignKey("faculty.id"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, nullable=False)
    is_read = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    faculty = relationship("Faculty", back_populates="notifications")


class FacultySchedule(Base):
    __tablename__ = "faculty_schedules"

    id = Column(String, primary_key=True)
    faculty_id = Column(String, ForeignKey("faculty.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    time_start = Column(String, nullable=False)  # e.g., "9:00 AM"
    time_end = Column(String, nullable=False)    # e.g., "11:00 AM"
    title = Column(String, nullable=False)
    type = Column(String, nullable=False)  # consultation, meeting, review
    location = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    faculty = relationship("Faculty", back_populates="schedules")
