from sqlalchemy import Boolean, Column, DateTime, Integer, String, UniqueConstraint
from datetime import datetime

from app.database import Base


class FormCategoryOption(Base):
    __tablename__ = "form_category_options"
    __table_args__ = (
        UniqueConstraint("name", name="uq_form_category_options_name"),
    )

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, index=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    is_system = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=lambda: datetime.utcnow(), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow(), nullable=False)