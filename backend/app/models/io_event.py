from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Index, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class IOEvent(Base):
    """Intake/Output & clinical event log for an admitted patient."""
    __tablename__ = "io_events"
    __table_args__ = (
        Index('idx_io_admission_time', 'admission_id', 'event_time'),
    )

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    admission_id = Column(String, ForeignKey("admissions.id"), nullable=False, index=True)
    event_time = Column(String, nullable=False)    # HH:MM  (24-hr display string)
    event_type = Column(String, nullable=False)    # Drugs | Food | IV Input | Urine | Stool
    description = Column(Text, nullable=True)
    amount_ml = Column(Float, nullable=True)       # volume in ml or quantity
    recorded_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    patient = relationship("Patient")
    admission = relationship("Admission", back_populates="io_events")


class SOAPNote(Base):
    """Clinical Progress Note (SOAP format) for an admitted patient."""
    __tablename__ = "soap_notes"
    __table_args__ = (
        Index('idx_soap_admission', 'admission_id'),
    )

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    admission_id = Column(String, ForeignKey("admissions.id"), nullable=False, index=True)
    subjective = Column(Text, nullable=True)
    objective = Column(Text, nullable=True)
    assessment = Column(Text, nullable=True)
    plan = Column(Text, nullable=True)
    plan_items = Column(JSON, nullable=True)
    note_meta = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    created_by = Column(String, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    updated_by = Column(String, nullable=True)

    patient = relationship("Patient")
    admission = relationship("Admission", back_populates="soap_notes")


class AdmissionEquipment(Base):
    """Equipment connected to an admitted patient."""
    __tablename__ = "admission_equipment"
    __table_args__ = (
        Index('idx_equipment_admission', 'admission_id'),
    )

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    admission_id = Column(String, ForeignKey("admissions.id"), nullable=False, index=True)
    equipment_type = Column(String, nullable=False)  # Bedside Monitor | Pulse Oximeter | Ventilator | ABG Analyzer
    equipment_id = Column(String, nullable=True)     # e.g. MON-ICU-042
    connected_since = Column(String, nullable=True)  # display string e.g. "06:00 AM"
    status = Column(String, default="active")        # active | inactive
    live_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    patient = relationship("Patient")
    admission = relationship("Admission", back_populates="equipment")
