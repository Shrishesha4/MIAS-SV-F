"""Wallet endpoints are part of patients.py.
This module provides standalone wallet queries."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.wallet import WalletTransaction, WalletType, TransactionType

router = APIRouter(prefix="/wallet", tags=["Wallet"])


@router.get("/balance/{patient_id}/{wallet_type}")
async def get_wallet_balance(
    patient_id: str,
    wallet_type: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    wt = WalletType.HOSPITAL if wallet_type.upper() == "HOSPITAL" else WalletType.PHARMACY

    # Calculate balance from transactions
    credit_result = await db.execute(
        select(func.coalesce(func.sum(WalletTransaction.amount), 0))
        .where(WalletTransaction.patient_id == patient_id)
        .where(WalletTransaction.wallet_type == wt)
        .where(WalletTransaction.type == TransactionType.CREDIT)
    )
    credits = float(credit_result.scalar() or 0)

    debit_result = await db.execute(
        select(func.coalesce(func.sum(WalletTransaction.amount), 0))
        .where(WalletTransaction.patient_id == patient_id)
        .where(WalletTransaction.wallet_type == wt)
        .where(WalletTransaction.type == TransactionType.DEBIT)
    )
    debits = float(debit_result.scalar() or 0)

    return {
        "patient_id": patient_id,
        "wallet_type": wallet_type.upper(),
        "balance": credits - debits,
        "total_credits": credits,
        "total_debits": debits,
    }


class TopupRequest(BaseModel):
    patient_id: str
    wallet_type: str  # "HOSPITAL" or "PHARMACY"
    amount: float
    transaction_type: str = "CREDIT"
    reference_id: str = ""
    description: str = ""


@router.post("/topup")
async def topup_wallet(
    request: TopupRequest,
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.RECEPTION)),
    db: AsyncSession = Depends(get_db),
):
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    wt = WalletType.HOSPITAL if request.wallet_type.upper() == "HOSPITAL" else WalletType.PHARMACY
    tt = TransactionType.CREDIT if request.transaction_type.upper() == "CREDIT" else TransactionType.DEBIT

    now = datetime.utcnow()
    txn = WalletTransaction(
        id=str(uuid.uuid4()),
        patient_id=request.patient_id,
        wallet_type=wt,
        date=now,
        time=now.strftime("%H:%M"),
        description=request.description or f"Wallet top-up ({request.wallet_type})",
        amount=request.amount,
        type=tt,
        reference_number=request.reference_id or None,
    )
    db.add(txn)
    await db.commit()

    return {
        "id": txn.id,
        "patient_id": request.patient_id,
        "wallet_type": request.wallet_type.upper(),
        "amount": request.amount,
        "transaction_type": request.transaction_type.upper(),
        "description": txn.description,
    }
