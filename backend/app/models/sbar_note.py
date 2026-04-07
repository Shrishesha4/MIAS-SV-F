import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text
from app.database import Base


class SBARNote(Base):
    __tablename__ = "sbar_notes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sbar_id = Column(String, unique=True, nullable=False)  # Display ID like SBAR-001
    
    # Relations
    patient_id = Column(String, nullable=False)
    admission_id = Column(String, nullable=False)
    nurse_id = Column(String, nullable=False)
    nurse_name = Column(String, nullable=False)  # Stored for display
    
    # SBAR content
    situation = Column(Text, nullable=True)
    background = Column(Text, nullable=True)
    assessment = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
