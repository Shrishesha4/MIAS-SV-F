from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class AcademicGroup(Base):
    __tablename__ = "academic_groups"
    __table_args__ = (
        UniqueConstraint("programme_id", "name", name="uq_academic_groups_programme_name"),
        Index("idx_academic_groups_programme_active", "programme_id", "is_active"),
    )

    id = Column(String, primary_key=True)
    programme_id = Column(String, ForeignKey("programmes.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow(), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
        nullable=False,
    )

    programme = relationship("Programme", back_populates="academic_groups")
    students = relationship("Student", back_populates="academic_group")
    targets = relationship(
        "AcademicTarget",
        back_populates="group",
        cascade="all, delete-orphan",
        order_by="AcademicTarget.sort_order.asc()",
    )


class AcademicTarget(Base):
    __tablename__ = "academic_targets"
    __table_args__ = (
        Index("idx_academic_targets_group_sort", "group_id", "sort_order"),
        Index("idx_academic_targets_group_category", "group_id", "category"),
    )

    id = Column(String, primary_key=True)
    group_id = Column(String, ForeignKey("academic_groups.id"), nullable=False, index=True)
    form_definition_id = Column(String, ForeignKey("form_definitions.id"), nullable=True, index=True)
    metric_name = Column(String, nullable=False)
    category = Column(String, nullable=False, default="ACADEMIC")
    target_value = Column(Integer, nullable=False, default=0)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.utcnow(), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
        nullable=False,
    )

    group = relationship("AcademicGroup", back_populates="targets")
    form_definition = relationship("FormDefinition")


class AcademicFormWeightage(Base):
    __tablename__ = "academic_form_weightages"
    __table_args__ = (
        UniqueConstraint("form_definition_id", name="uq_academic_form_weightages_form_definition"),
    )

    id = Column(String, primary_key=True)
    form_definition_id = Column(String, ForeignKey("form_definitions.id"), nullable=False, index=True)
    points = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.utcnow(), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
        nullable=False,
    )

    form_definition = relationship("FormDefinition", back_populates="academic_weightage")