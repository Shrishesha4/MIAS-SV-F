import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


class SBARNote(Base):
    __tablename__ = "sbar_notes"
    __table_args__ = (
        Index('idx_sbar_patient_created', 'patient_id', 'created_at'),
        Index('idx_sbar_admission_created', 'admission_id', 'created_at'),
        Index('idx_sbar_nurse_created', 'nurse_id', 'created_at'),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sbar_id = Column(String, unique=True, nullable=False)  # Display ID like SBAR-001
    
    # Relations
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    admission_id = Column(String, ForeignKey("admissions.id"), nullable=False)
    nurse_id = Column(String, ForeignKey("nurses.id"), nullable=False)
    nurse_name = Column(String, nullable=False)  # Stored for display
    
    # SBAR content
    situation = Column(Text, nullable=True)
    background = Column(Text, nullable=True)
    assessment = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("Patient", back_populates="sbar_notes")
    admission = relationship("Admission", back_populates="sbar_notes")
    nurse = relationship("Nurse", back_populates="sbar_notes")
