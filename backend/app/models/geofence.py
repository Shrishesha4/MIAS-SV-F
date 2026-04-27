from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, JSON, String
from sqlalchemy.orm import relationship

from app.database import Base


class GeofenceZone(Base):
    __tablename__ = "geofence_zones"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    # List of {lat: float, lng: float} objects defining the polygon vertices
    polygon = Column(JSON, nullable=False, default=list)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.utcnow())
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.utcnow())


class PatientGeofenceProof(Base):
    """
    One-time location proof generated on a patient's own device.
    Staff submit the proof_id when checking a patient in on their terminal.
    """

    __tablename__ = "patient_geofence_proofs"
    __table_args__ = (
        Index("idx_geofence_proof_patient", "patient_id"),
        Index("idx_geofence_proof_expires", "expires_at"),
    )

    id = Column(String, primary_key=True)
    # 8-character uppercase alphanumeric code shown to patient on their device
    short_code = Column(String(8), nullable=True, index=True)
    # Null for new-registration patients (account not yet created)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=True, index=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=True)
    is_valid = Column(Boolean, nullable=False)  # True = was inside a zone at capture time
    # ISO-format zone_id for audit trail
    zone_id = Column(String, ForeignKey("geofence_zones.id"), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    consumed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.utcnow())

    patient = relationship("Patient", foreign_keys=[patient_id])
    zone = relationship("GeofenceZone", foreign_keys=[zone_id])
