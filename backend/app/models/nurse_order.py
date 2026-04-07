import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Boolean, Text
from sqlalchemy.orm import relationship
from app.database import Base


class NurseOrder(Base):
    __tablename__ = "nurse_orders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String, unique=True, nullable=False)  # Display ID like ORD-001
    
    # Relations
    patient_id = Column(String, nullable=False)
    admission_id = Column(String, nullable=False)
    nurse_id = Column(String, nullable=True)  # Nurse who completed it
    
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
