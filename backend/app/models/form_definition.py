from sqlalchemy import Boolean, Column, DateTime, Index, Integer, JSON, String, Text
from datetime import datetime

from app.database import Base


class FormDefinition(Base):
    __tablename__ = "form_definitions"
    __table_args__ = (
        Index('idx_form_definition_type_active', 'form_type', 'is_active'),
        Index('idx_form_definition_context', 'department', 'procedure_name'),
        Index('idx_form_definition_slug', 'slug'),
    )

    id = Column(String, primary_key=True)
    slug = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    form_type = Column(String, nullable=False, index=True)
    department = Column(String, nullable=True, index=True)
    procedure_name = Column(String, nullable=True, index=True)
    fields = Column(JSON, nullable=False, default=list)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow(), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow(), nullable=False)
