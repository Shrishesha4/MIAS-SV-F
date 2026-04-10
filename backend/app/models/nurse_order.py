import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


class NurseOrder(Base):
    __tablename__ = "nurse_orders"
    __table_args__ = (
        Index('idx_nurse_order_patient_created', 'patient_id', 'created_at'),
        Index('idx_nurse_order_admission_created', 'admission_id', 'created_at'),
        Index('idx_nurse_order_nurse_created', 'nurse_id', 'created_at'),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String, unique=True, nullable=False)  # Display ID like ORD-001
    
    # Relations
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    admission_id = Column(String, ForeignKey("admissions.id"), nullable=False)
    nurse_id = Column(String, ForeignKey("nurses.id"), nullable=True)  # Nurse who completed it
    
    # Order details
    order_type = Column(String, nullable=False)  # DRUG, INVESTIGATION, PROCEDURE, etc.
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    scheduled_time = Column(String, nullable=True)  # e.g., "22:00", "6-hourly"
    
    # Status
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("Patient", back_populates="nurse_orders")
    admission = relationship("Admission", back_populates="nurse_orders")
    nurse = relationship("Nurse", back_populates="completed_orders")
