from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, String, Text

from app.database import Base


class ICDCode(Base):
    __tablename__ = "icd_codes"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    code = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=False)
    category = Column(String, nullable=False, default="General")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )