from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Index, Integer, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class ApprovalType(enum.Enum):
    CASE_RECORD = "CASE_RECORD"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    ADMISSION = "ADMISSION"
    PRESCRIPTION = "PRESCRIPTION"


class ApprovalStatus(enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class CaseRecord(Base):
    __tablename__ = "case_records"
    __table_args__ = (
        Index('idx_case_record_status_date', 'status', 'date'),
        Index('idx_case_record_student_date', 'student_id', 'date'),
    )

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=True, index=True)
    date = Column(DateTime, nullable=False, index=True)
    time = Column(String, nullable=True)
    type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    procedure_name = Column(String, nullable=True)
    procedure_description = Column(Text, nullable=True)
    department = Column(String, nullable=True)
    findings = Column(Text, nullable=True)
    diagnosis = Column(Text, nullable=True)
    icd_code = Column(String, nullable=True)  # ICD-10 code
    icd_description = Column(String, nullable=True)  # ICD-10 description
    treatment = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    grade = Column(String, nullable=True)
    provider = Column(String, nullable=True)
    doctor_name = Column(String, nullable=True)
    status = Column(String, default="Pending", index=True)  # Pending, Approved, Rejected
    approved_by = Column(String, nullable=True)
    approved_at = Column(String, nullable=True)
    created_by_name = Column(String, nullable=True)  # Name of who created this record
    created_by_role = Column(String, nullable=True)  # STUDENT or FACULTY
    last_modified_by = Column(String, nullable=True)  # Name of last person to modify
    last_modified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    patient = relationship("Patient", back_populates="case_records")
    student = relationship("Student", back_populates="case_records")
    approval = relationship("Approval", back_populates="case_record", uselist=False)


class Approval(Base):
    __tablename__ = "approvals"
    __table_args__ = (
        Index('idx_approval_faculty_status', 'faculty_id', 'status'),
        Index('idx_approval_type_status', 'approval_type', 'status'),
    )

    id = Column(String, primary_key=True)
    approval_type = Column(SQLEnum(ApprovalType), nullable=False, default=ApprovalType.CASE_RECORD)
    
    # Can link to different record types
    case_record_id = Column(String, ForeignKey("case_records.id"), nullable=True, index=True)
    admission_id = Column(String, ForeignKey("admissions.id"), nullable=True, index=True)
    prescription_id = Column(String, ForeignKey("prescriptions.id"), nullable=True, index=True)
    
    faculty_id = Column(String, ForeignKey("faculty.id"), nullable=False, index=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=True, index=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=True, index=True)
    
    status = Column(SQLEnum(ApprovalStatus), default=ApprovalStatus.PENDING, index=True)
    score = Column(Integer, nullable=True)  # 1-5 score for approved records
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    processed_at = Column(DateTime, nullable=True)

    case_record = relationship("CaseRecord", back_populates="approval")
    admission = relationship("Admission", back_populates="approval")
    prescription = relationship("Prescription", back_populates="approval")
    faculty = relationship("Faculty", back_populates="approvals")
    patient = relationship("Patient")
    student = relationship("Student")
