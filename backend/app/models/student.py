from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, Index, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        Index('idx_student_year_semester', 'year', 'semester'),
        Index('idx_student_name_search', 'name'),
        Index('idx_student_program', 'program'),
    )

    id = Column(String, primary_key=True)
    student_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False, index=True)
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
    __table_args__ = (
        Index('idx_assignment_student_status', 'student_id', 'status'),
        Index('idx_assignment_patient_status', 'patient_id', 'status'),
    )

    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False, index=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
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
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=True)
    clinic_name = Column(String, nullable=False)
    department = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    time_start = Column(String, nullable=True)  # e.g., "9:00 AM" (scheduled time)
    time_end = Column(String, nullable=True)    # e.g., "12:00 PM" (scheduled time)
    status = Column(String, default="Scheduled")  # Scheduled, Active, Completed
    is_selected = Column(Integer, default=0)  # 1 if this is the student's current selected clinic
    
    # Attendance tracking fields
    checked_in_at = Column(DateTime, nullable=True)  # Actual check-in time
    checked_out_at = Column(DateTime, nullable=True)  # Actual check-out time
    verified_by_faculty_id = Column(String, ForeignKey("faculty.id"), nullable=True)  # Faculty sign-off

    student = relationship("Student", back_populates="clinic_sessions")
    clinic = relationship("Clinic", back_populates="sessions")
    verified_by = relationship("Faculty", foreign_keys=[verified_by_faculty_id])


class Clinic(Base):
    """Hospital clinics where students can be assigned"""
    __tablename__ = "clinics"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    block = Column(String, nullable=True)  # e.g., "Block A", "Block B"
    clinic_type = Column(String, nullable=False, default="General")  # e.g., "General", "Specialty"
    access_mode = Column(String, nullable=False, default="WALK_IN")  # WALK_IN or APPOINTMENT_ONLY
    walk_in_type = Column(String, nullable=False, default="NO_WALK_IN")  # patient-type walk-in key
    department = Column(String, nullable=False)
    location = Column(String, nullable=True)  # e.g., "Outpatient Wing, 2nd Floor"
    faculty_id = Column(String, ForeignKey("faculty.id"), nullable=True)  # Supervising doctor
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )

    faculty = relationship("Faculty")
    sessions = relationship("ClinicSession", back_populates="clinic")
    appointments = relationship("ClinicAppointment", back_populates="clinic")
    faculty_sessions = relationship("FacultyClinicSession", back_populates="clinic")
    insurance_configs = relationship("InsuranceClinicConfig", back_populates="clinic", cascade="all, delete-orphan")


class ClinicAppointment(Base):
    """Patient appointments at a clinic for today"""
    __tablename__ = "clinic_appointments"

    id = Column(String, primary_key=True)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    appointment_date = Column(DateTime, nullable=False)
    appointment_time = Column(String, nullable=True)  # e.g., "9:15 AM"
    provider_name = Column(String, nullable=True)  # Doctor handling this appointment
    status = Column(String, default="Scheduled")  # Scheduled, Checked In, In Progress, Completed
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    clinic = relationship("Clinic", back_populates="appointments")
    patient = relationship("Patient")
