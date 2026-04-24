from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Programme(Base):
    __tablename__ = "programmes"

    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False, index=True)
    code = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    degree_type = Column(String, nullable=True)  # e.g. Undergraduate, Postgraduate
    duration_years = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )

    academic_groups = relationship("AcademicGroup", back_populates="programme")
