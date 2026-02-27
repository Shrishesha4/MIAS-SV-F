from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class CaseRecord(Base):
    __tablename__ = "case_records"

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False, index=True)
    date = Column(DateTime, nullable=False)
    time = Column(String, nullable=True)
    type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    department = Column(String, nullable=True)
    findings = Column(Text, nullable=True)
    diagnosis = Column(Text, nullable=True)
    treatment = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    grade = Column(String, nullable=True)
    provider = Column(String, nullable=True)
    status = Column(String, default="Pending")  # Pending, Approved, Rejected
    approved_by = Column(String, nullable=True)
    approved_at = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    patient = relationship("Patient", back_populates="case_records")
    student = relationship("Student", back_populates="case_records")
    approval = relationship("Approval", back_populates="case_record", uselist=False)


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(String, primary_key=True)
    case_record_id = Column(String, ForeignKey("case_records.id"), nullable=False)
    faculty_id = Column(String, ForeignKey("faculty.id"), nullable=False)
    status = Column(String, default="Pending")  # Pending, Approved, Rejected
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    processed_at = Column(DateTime, nullable=True)

    case_record = relationship("CaseRecord", back_populates="approval")
    faculty = relationship("Faculty", back_populates="approvals")
