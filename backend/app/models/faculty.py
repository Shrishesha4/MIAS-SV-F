from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer
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
    availability = Column(String, nullable=True)
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
