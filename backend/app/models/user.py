from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class UserRole(str, enum.Enum):
    PATIENT = "PATIENT"
    STUDENT = "STUDENT"
    FACULTY = "FACULTY"
    LAB_TECHNICIAN = "LAB_TECHNICIAN"
    ADMIN = "ADMIN"
    RECEPTION = "RECEPTION"
    NURSE = "NURSE"
    BILLING = "BILLING"
    OT_MANAGER = "OT_MANAGER"
    MRD = "MRD"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    patient = relationship("Patient", back_populates="user", uselist=False)
    student = relationship("Student", back_populates="user", uselist=False)
    faculty = relationship("Faculty", back_populates="user", uselist=False)
    lab_technician = relationship("LabTechnician", back_populates="user", uselist=False)
    nurse = relationship("Nurse", back_populates="user", uselist=False)
    billing = relationship("Billing", back_populates="user", uselist=False)
    ot_manager = relationship("OTManager", back_populates="user", uselist=False)
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token = Column(String, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    user = relationship("User", back_populates="refresh_tokens")
