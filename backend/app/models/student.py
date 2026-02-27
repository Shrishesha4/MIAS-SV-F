from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(String, primary_key=True)
    student_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    semester = Column(Integer, nullable=False)
    program = Column(String, nullable=False)
    degree = Column(String, nullable=True)
    photo = Column(String, nullable=True)
    gpa = Column(Float, nullable=False)
    academic_standing = Column(String, default="Good Standing")
    academic_advisor = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )

    # Relationships
    user = relationship("User", back_populates="student")
    emergency_contact = relationship(
        "EmergencyContact", back_populates="student", uselist=False,
        foreign_keys="EmergencyContact.student_id",
    )
    attendance = relationship("StudentAttendance", back_populates="student", uselist=False)
    disciplinary_actions = relationship("DisciplinaryAction", back_populates="student")
    assigned_patients = relationship("StudentPatientAssignment", back_populates="student")
    case_records = relationship("CaseRecord", back_populates="student")
    notifications = relationship("StudentNotification", back_populates="student")
    clinic_sessions = relationship("ClinicSession", back_populates="student")


class StudentAttendance(Base):
    __tablename__ = "student_attendance"

    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), unique=True, nullable=False)
    overall = Column(Float, default=0)
    clinical = Column(Float, default=0)
    lecture = Column(Float, default=0)
    lab = Column(Float, default=0)

    student = relationship("Student", back_populates="attendance")


class DisciplinaryAction(Base):
    __tablename__ = "disciplinary_actions"

    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    date = Column(String, nullable=False)
    status = Column(String, nullable=False)  # Resolved, Active, Pending
    details = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)

    student = relationship("Student", back_populates="disciplinary_actions")


class StudentPatientAssignment(Base):
    __tablename__ = "student_patient_assignments"

    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    assigned_date = Column(DateTime, default=lambda: datetime.utcnow())
    status = Column(String, default="Active")

    student = relationship("Student", back_populates="assigned_patients")
    patient = relationship("Patient", back_populates="assigned_students")


class StudentNotification(Base):
    __tablename__ = "student_notifications"

    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, nullable=False)
    is_read = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    student = relationship("Student", back_populates="notifications")


class ClinicSession(Base):
    __tablename__ = "clinic_sessions"

    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    clinic_name = Column(String, nullable=False)
    department = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    status = Column(String, default="Scheduled")

    student = relationship("Student", back_populates="clinic_sessions")
