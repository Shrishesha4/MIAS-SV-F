from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Index, Integer
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Admission(Base):
    __tablename__ = "admissions"
    __table_args__ = (
        Index('idx_admission_status_date', 'status', 'admission_date'),
        Index('idx_admission_patient_status', 'patient_id', 'status'),
    )

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    admission_date = Column(DateTime, nullable=False, index=True)
    discharge_date = Column(DateTime, nullable=True)
    department = Column(String, nullable=False)
    ward = Column(String, nullable=True)
    bed_number = Column(String, nullable=True)
    attending_doctor = Column(String, nullable=False)
    reason = Column(Text, nullable=True)  # Reason for admission
    diagnosis = Column(Text, nullable=True)
    status = Column(String, default="Active", index=True)  # Active, Discharged, Transferred
    notes = Column(Text, nullable=True)
    program_duration_days = Column(Integer, nullable=True)  # Duration of program/stay
    
    # Related/transferred admission info
    related_admission_id = Column(String, ForeignKey("admissions.id"), nullable=True)
    transferred_from_department = Column(String, nullable=True)
    referring_doctor = Column(String, nullable=True)
    
    # Discharge summary fields
    discharge_summary = Column(Text, nullable=True)
    discharge_instructions = Column(Text, nullable=True)
    follow_up_date = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    # Relationships
    patient = relationship("Patient", back_populates="admissions")
    related_admission = relationship("Admission", remote_side=[id], backref="child_admissions")
    approval = relationship("Approval", back_populates="admission", uselist=False)
