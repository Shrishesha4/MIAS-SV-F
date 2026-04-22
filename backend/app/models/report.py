from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum as SQLEnum, Integer, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class ReportStatus(str, enum.Enum):
    NORMAL = "NORMAL"
    ABNORMAL = "ABNORMAL"
    CRITICAL = "CRITICAL"
    PENDING = "PENDING"


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        Index('idx_report_patient_date', 'patient_id', 'date'),
        Index('idx_report_status', 'status'),
    )

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    lab_id = Column(String, ForeignKey("labs.id"), nullable=True, index=True)
    date = Column(DateTime, nullable=False)
    time = Column(String, nullable=True)
    title = Column(String, nullable=False)
    type = Column(String, nullable=False)  # Laboratory, Radiology, etc.
    department = Column(String, nullable=False)
    ordered_by = Column(String, nullable=False)
    accepted_by_user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    accepted_at = Column(DateTime, nullable=True)
    performed_by = Column(String, nullable=True)
    supervised_by = Column(String, nullable=True)
    status = Column(SQLEnum(ReportStatus), default=ReportStatus.PENDING)
    result_summary = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    file_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    # Relationships
    patient = relationship("Patient", back_populates="reports")
    lab = relationship("Lab")
    accepted_by_user = relationship("User")
    findings = relationship("ReportFinding", back_populates="report", cascade="all, delete-orphan")
    images = relationship("ReportImage", back_populates="report", cascade="all, delete-orphan")


class ReportFinding(Base):
    __tablename__ = "report_findings"

    id = Column(String, primary_key=True)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False)
    parameter = Column(String, nullable=False)
    value = Column(String, nullable=False)
    reference = Column(String, nullable=True)
    status = Column(String, nullable=False)  # Normal, High, Low, Critical

    report = relationship("Report", back_populates="findings")


class ReportImage(Base):
    __tablename__ = "report_images"

    id = Column(String, primary_key=True)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String, nullable=False)
    type = Column(String, nullable=True)  # X-Ray, MRI, CT, Blood Smear, etc.

    report = relationship("Report", back_populates="images")
