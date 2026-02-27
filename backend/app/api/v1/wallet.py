"""Wallet endpoints are part of patients.py.
This module provides standalone wallet queries."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
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
