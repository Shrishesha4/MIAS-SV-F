"""Student department/procedure permission model."""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class StudentPermission(Base):
    __tablename__ = "student_permissions"

    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False, index=True)
    department = Column(String, nullable=False)
    granted_by_faculty_id = Column(String, ForeignKey("faculty.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    granted_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)

    student = relationship("Student", backref="permissions")
    granted_by = relationship("Faculty", backref="granted_permissions")
