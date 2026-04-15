from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.database import Base


DEFAULT_PATIENT_CATEGORY_COLOR_PRIMARY = "#60A5FA"
DEFAULT_PATIENT_CATEGORY_COLOR_SECONDARY = "#1D4ED8"

PATIENT_CATEGORY_COLOR_PRESETS = {
    "classic": ("#60A5FA", "#1D4ED8"),
    "prime": ("#A78BFA", "#6D28D9"),
    "elite": ("#FBBF24", "#D97706"),
    "community": ("#34D399", "#047857"),
}


def get_default_patient_category_colors(name: str | None) -> tuple[str, str]:
    normalized = str(name or "").strip().lower()
    return PATIENT_CATEGORY_COLOR_PRESETS.get(
        normalized,
        (DEFAULT_PATIENT_CATEGORY_COLOR_PRIMARY, DEFAULT_PATIENT_CATEGORY_COLOR_SECONDARY),
    )


class PatientCategoryOption(Base):
    __tablename__ = "patient_category_options"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    color_primary = Column(String, nullable=False, default=DEFAULT_PATIENT_CATEGORY_COLOR_PRIMARY)
    color_secondary = Column(String, nullable=False, default=DEFAULT_PATIENT_CATEGORY_COLOR_SECONDARY)
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    registration_fee = Column(Integer, nullable=False, default=100)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )