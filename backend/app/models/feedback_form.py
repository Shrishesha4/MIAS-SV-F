from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class FeedbackForm(Base):
    """A feedback form deployed by an academic manager to collect ratings."""

    __tablename__ = "feedback_forms"
    __table_args__ = (
        Index("idx_feedback_forms_target", "target_type", "target_id"),
        Index("idx_feedback_forms_created_by", "created_by"),
    )

    id = Column(String, primary_key=True)
    # 'STUDENT' or 'GROUP'
    target_type = Column(String, nullable=False)
    target_id = Column(String, nullable=False)
    target_name = Column(String, nullable=True)
    # 'PATIENTS', 'STUDENTS', 'FACULTY'
    recipient_type = Column(String, nullable=False, default="PATIENTS")
    # JSON array of {"id": str, "text": str}
    questions = Column(JSONB, nullable=False, default=list)
    is_deployed = Column(Boolean, nullable=False, default=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow(), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
        nullable=False,
    )

    responses = relationship(
        "FeedbackFormResponse",
        back_populates="form",
        cascade="all, delete-orphan",
    )
    creator = relationship("User", foreign_keys=[created_by])


class FeedbackFormResponse(Base):
    """A single respondent's answers to a deployed feedback form."""

    __tablename__ = "feedback_form_responses"
    __table_args__ = (
        Index("idx_ffr_form_id", "form_id"),
        Index("idx_ffr_respondent", "respondent_id"),
    )

    id = Column(String, primary_key=True)
    form_id = Column(
        String, ForeignKey("feedback_forms.id", ondelete="CASCADE"), nullable=False
    )
    respondent_id = Column(String, nullable=True)
    # JSON: {question_id: score (1-5)}
    ratings = Column(JSONB, nullable=False, default=dict)
    # 'VERY_SATISFIED' | 'SATISFIED' | 'NEUTRAL' | 'UNSATISFIED' | 'VERY_UNSATISFIED'
    overall_satisfaction = Column(String, nullable=True)
    submitted_at = Column(DateTime, default=lambda: datetime.utcnow(), nullable=False)

    form = relationship("FeedbackForm", back_populates="responses")
