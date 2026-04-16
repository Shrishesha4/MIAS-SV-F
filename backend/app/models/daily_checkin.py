from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Enum as SQLEnum, ForeignKey, Index, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.user import UserRole


class DailyCheckIn(Base):
    __tablename__ = "daily_checkins"
    __table_args__ = (
        Index("idx_daily_checkins_user_date", "user_id", "check_in_date", unique=True),
        Index("idx_daily_checkins_role_date", "role", "check_in_date"),
    )

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(SQLEnum(UserRole), nullable=False, index=True)
    check_in_date = Column(Date, nullable=False, index=True)
    checked_in_at = Column(DateTime, nullable=False, default=lambda: datetime.utcnow())
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.utcnow())

    user = relationship("User")
    clinic = relationship("Clinic")
