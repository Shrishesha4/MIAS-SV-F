from sqlalchemy import Column, String, DateTime, Numeric, Text, ForeignKey, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class WalletType(str, enum.Enum):
    HOSPITAL = "HOSPITAL"
    PHARMACY = "PHARMACY"


class TransactionType(str, enum.Enum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


class PatientWallet(Base):
    """Stored running balance per patient per wallet type.

    Single source of truth for balance (O(1) read).
    Updated atomically via SQL UPDATE ... SET balance = balance + delta
    on every topup or debit — never recomputed from transactions.
    """
    __tablename__ = "patient_wallets"
    __table_args__ = (UniqueConstraint("patient_id", "wallet_type"),)

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    wallet_type = Column(SQLEnum(WalletType), nullable=False)
    balance = Column(Numeric(12, 2), nullable=False, default=0)
    updated_at = Column(DateTime, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow())

    patient = relationship("Patient", back_populates="wallets")


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    wallet_type = Column(SQLEnum(WalletType), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    time = Column(String, nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    type = Column(SQLEnum(TransactionType), nullable=False)
    payment_method = Column(String, nullable=True)
    reference_number = Column(String, nullable=True)
    invoice_number = Column(String, nullable=True)
    department = Column(String, nullable=True)
    provider = Column(String, nullable=True)
    subtotal = Column(Numeric(10, 2), nullable=True)
    tax = Column(Numeric(10, 2), nullable=True)
    insurance_coverage = Column(Numeric(10, 2), nullable=True)
    insurance_provider = Column(String, nullable=True)
    policy_number = Column(String, nullable=True)
    claim_number = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    patient = relationship("Patient", back_populates="wallet_transactions")
    items = relationship("TransactionItem", back_populates="transaction", cascade="all, delete-orphan")


class TransactionItem(Base):
    __tablename__ = "transaction_items"

    id = Column(String, primary_key=True)
    transaction_id = Column(String, ForeignKey("wallet_transactions.id"), nullable=False)
    description = Column(String, nullable=False)
    quantity = Column(Numeric(10, 2), default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total = Column(Numeric(10, 2), nullable=False)

    transaction = relationship("WalletTransaction", back_populates="items")
