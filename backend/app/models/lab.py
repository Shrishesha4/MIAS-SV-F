from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Table, Numeric, Integer, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class ChargeCategory(str, enum.Enum):
    CLINICAL = "CLINICAL"
    LABS = "LABS"
    ADMIN = "ADMIN"


# Junction table for many-to-many relationship between test groups and tests
lab_test_group_members = Table(
    "lab_test_group_members",
    Base.metadata,
    Column("group_id", String, ForeignKey("lab_test_groups.id"), primary_key=True),
    Column("test_id", String, ForeignKey("lab_tests.id"), primary_key=True),
)


class Lab(Base):
    """Hospital laboratories for diagnostics"""
    __tablename__ = "labs"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    block = Column(String, nullable=True)  # e.g., "Block C", "Block D"
    lab_type = Column(String, nullable=False, default="General")  # e.g., "Pathology", "Radiology"
    department = Column(String, nullable=False)
    location = Column(String, nullable=True)  # e.g., "Ground Floor, Wing A"
    contact_phone = Column(String, nullable=True)
    operating_hours = Column(String, nullable=True)  # e.g., "24/7" or "8 AM - 6 PM"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )

    # Relationships
    tests = relationship("LabTest", back_populates="lab", cascade="all, delete-orphan")
    test_groups = relationship("LabTestGroup", back_populates="lab", cascade="all, delete-orphan")


class LabTest(Base):
    """Individual lab tests available in a lab"""
    __tablename__ = "lab_tests"

    id = Column(String, primary_key=True)
    lab_id = Column(String, ForeignKey("labs.id"), nullable=False, index=True)
    name = Column(String, nullable=False)  # e.g., "Complete Blood Count (CBC)"
    code = Column(String, nullable=False)  # e.g., "HEM001"
    category = Column(String, nullable=False)  # e.g., "Hematology", "Biochemistry"
    description = Column(Text, nullable=True)
    sample_type = Column(String, nullable=True)  # e.g., "Blood", "Urine"
    turnaround_time = Column(String, nullable=True)  # e.g., "2 hours", "24 hours"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )

    # Relationships
    lab = relationship("Lab", back_populates="tests")
    groups = relationship("LabTestGroup", secondary=lab_test_group_members, back_populates="tests")


class LabTestGroup(Base):
    """Groups/packages of lab tests (e.g., Executive Health Checkup)"""
    __tablename__ = "lab_test_groups"

    id = Column(String, primary_key=True)
    lab_id = Column(String, ForeignKey("labs.id"), nullable=False, index=True)
    name = Column(String, nullable=False)  # e.g., "Executive Health Checkup"
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )

    # Relationships
    lab = relationship("Lab", back_populates="test_groups")
    tests = relationship("LabTest", secondary=lab_test_group_members, back_populates="groups")


class ChargeItem(Base):
    """Charge master items with tiered pricing"""
    __tablename__ = "charge_items"

    id = Column(String, primary_key=True)
    item_code = Column(String, nullable=False, index=True)  # e.g., "i1", "HEM001"
    name = Column(String, nullable=False)  # e.g., "Consultation Fee", "Complete Blood Count (CBC)"
    category = Column(SQLEnum(ChargeCategory), nullable=False, index=True)
    description = Column(Text, nullable=True)
    # Reference to source (lab_test_id or null for clinical/admin items)
    source_type = Column(String, nullable=True)  # "lab_test", "lab_test_group", or null
    source_id = Column(String, nullable=True)  # ID of the referenced test/group
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )

    # Relationships
    prices = relationship("ChargePrice", back_populates="item", cascade="all, delete-orphan")


class ChargePrice(Base):
    """Pricing for each patient category of a charge item"""
    __tablename__ = "charge_prices"

    id = Column(String, primary_key=True)
    item_id = Column(String, ForeignKey("charge_items.id"), nullable=False, index=True)
    tier = Column(String, nullable=False, index=True)
    price = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )

    # Relationships
    item = relationship("ChargeItem", back_populates="prices")
