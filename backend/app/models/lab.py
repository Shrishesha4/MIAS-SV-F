from sqlalchemy import Column, String, DateTime, Boolean, Text
from datetime import datetime

from app.database import Base


class Lab(Base):
    """Hospital laboratories for diagnostics"""
    __tablename__ = "labs"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    block = Column(String, nullable=True)  # e.g., "Block C", "Block D"
    lab_type = Column(String, nullable=False, default="General")  # e.g., "Pathology", "Radiology"
    department = Column(String, nullable=False)
    location = Column(String, nullable=True)  # e.g., "Ground Floor, Wing A"
    contact_phone = Column(String, nullable=True)
    operating_hours = Column(String, nullable=True)  # e.g., "24/7" or "8 AM - 6 PM"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )
