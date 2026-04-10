from datetime import datetime
import enum

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, Float, String, Text

from app.database import Base


class AIProviderType(str, enum.Enum):
    OPENAI = "OPENAI"
    ANTHROPIC = "ANTHROPIC"
    GEMINI = "GEMINI"
    OPENAI_COMPATIBLE = "OPENAI_COMPATIBLE"


class AIProviderSettings(Base):
    __tablename__ = "ai_provider_settings"

    id = Column(String, primary_key=True, default="default")
    provider = Column(SQLEnum(AIProviderType), nullable=False, default=AIProviderType.OPENAI)
    model = Column(String, nullable=False, default="gpt-4.1-mini")
    api_key = Column(Text, nullable=True)
    base_url = Column(String, nullable=True)
    system_prompt = Column(Text, nullable=True)
    temperature = Column(Float, nullable=False, default=0.2)
    is_enabled = Column(Boolean, nullable=False, default=False)
    last_tested_at = Column(DateTime, nullable=True)
    last_test_status = Column(String, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )