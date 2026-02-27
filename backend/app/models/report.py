from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum as SQLEnum
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

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    date = Column(DateTime, nullable=False)
    title = Column(String, nullable=False)
    type = Column(String, nullable=False)
    department = Column(String, nullable=False)
    ordered_by = Column(String, nullable=False)
    status = Column(SQLEnum(ReportStatus), default=ReportStatus.PENDING)
    result_summary = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    file_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    patient = relationship("Patient", back_populates="reports")
