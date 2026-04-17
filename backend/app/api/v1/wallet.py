"""Wallet endpoints – balance, topup, patient search for billing staff."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.wallet import WalletTransaction, WalletType, TransactionType
from app.models.patient import Patient

router = APIRouter(prefix="/wallet", tags=["Wallet"])


async def _calc_balance(db: AsyncSession, patient_id: str, wt: WalletType) -> dict:
    credits = float(
        (await db.execute(
            select(func.coalesce(func.sum(WalletTransaction.amount), 0))
            .where(WalletTransaction.patient_id == patient_id)
            .where(WalletTransaction.wallet_type == wt)
            .where(WalletTransaction.type == TransactionType.CREDIT)
        )).scalar() or 0
    )
    debits = float(
        (await db.execute(
            select(func.coalesce(func.sum(WalletTransaction.amount), 0))
            .where(WalletTransaction.patient_id == patient_id)
            .where(WalletTransaction.wallet_type == wt)
            .where(WalletTransaction.type == TransactionType.DEBIT)
        )).scalar() or 0
    )
    return {"balance": credits - debits, "total_credits": credits, "total_debits": debits}


@router.get("/balance/{patient_id}/{wallet_type}")
async def get_wallet_balance(
    patient_id: str,
    wallet_type: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    wt = WalletType.HOSPITAL if wallet_type.upper() == "HOSPITAL" else WalletType.PHARMACY
    bal = await _calc_balance(db, patient_id, wt)
    return {"patient_id": patient_id, "wallet_type": wallet_type.upper(), **bal}


@router.get("/patients/search")
async def search_patients_for_billing(
    q: str = Query(..., min_length=1),
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.RECEPTION, UserRole.BILLING)),
    db: AsyncSession = Depends(get_db),
):
    """Search patients by name, patient_id, email or phone."""
    result = await db.execute(
        select(Patient)
        .where(
            or_(
                Patient.name.ilike(f"%{q}%"),
                Patient.patient_id.ilike(f"%{q}%"),
                Patient.email.ilike(f"%{q}%"),
                Patient.phone.ilike(f"%{q}%"),
            )
        )
        .limit(20)
    )
    patients = result.scalars().all()
    return [
        {
            "id": p.id,
            "patient_id": p.patient_id,
            "name": p.name,
            "phone": p.phone,
            "email": p.email,
            "photo": p.photo,
            "category": p.category,
        }
        for p in patients
    ]


@router.get("/patient/{patient_id}/summary")
async def get_patient_wallet_summary(
    patient_id: str,
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.RECEPTION, UserRole.BILLING, UserRole.PATIENT)),
    db: AsyncSession = Depends(get_db),
):
    """Get both wallet balances + recent transactions for a patient."""
    hosp = await _calc_balance(db, patient_id, WalletType.HOSPITAL)
    phar = await _calc_balance(db, patient_id, WalletType.PHARMACY)

    txn_result = await db.execute(
        select(WalletTransaction)
        .where(WalletTransaction.patient_id == patient_id)
        .order_by(WalletTransaction.date.desc())
        .limit(50)
    )
    txns = txn_result.scalars().all()

    return {
        "hospital": hosp,
        "pharmacy": phar,
        "transactions": [
            {
                "id": t.id,
                "wallet_type": t.wallet_type.value,
                "date": t.date.isoformat() if t.date else None,
                "time": t.time,
                "description": t.description,
                "amount": float(t.amount),
                "type": t.type.value,
                "reference_number": t.reference_number,
                "payment_method": t.payment_method,
                "notes": t.notes,
            }
            for t in txns
        ],
    }


class TopupRequest(BaseModel):
    patient_id: str
    wallet_type: str  # "HOSPITAL" or "PHARMACY"
    amount: float
    transaction_type: str = "CREDIT"
    reference_id: str = ""
    description: str = ""
    payment_method: str = ""


@router.post("/topup")
async def topup_wallet(
    request: TopupRequest,
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.RECEPTION, UserRole.BILLING)),
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
        payment_method=request.payment_method or None,
        reference_number=request.reference_id or None,
    )
    db.add(txn)
    await db.commit()

    bal = await _calc_balance(db, request.patient_id, wt)
    return {
        "id": txn.id,
        "patient_id": request.patient_id,
        "wallet_type": request.wallet_type.upper(),
        "amount": request.amount,
        "transaction_type": request.transaction_type.upper(),
        "description": txn.description,
        "new_balance": bal["balance"],
    }


class SelfTopupRequest(BaseModel):
    wallet_type: str  # "HOSPITAL" or "PHARMACY"
    amount: float
    payment_method: str = "Online"
    reference_id: str = ""


@router.post("/self-topup")
async def patient_self_topup(
    request: SelfTopupRequest,
    user: User = Depends(require_role(UserRole.PATIENT)),
    db: AsyncSession = Depends(get_db),
):
    """Patient adds funds to their own wallet."""
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    patient = (await db.execute(select(Patient).where(Patient.user_id == user.id))).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    wt = WalletType.HOSPITAL if request.wallet_type.upper() == "HOSPITAL" else WalletType.PHARMACY
    now = datetime.utcnow()
    txn = WalletTransaction(
        id=str(uuid.uuid4()),
        patient_id=patient.id,
        wallet_type=wt,
        date=now,
        time=now.strftime("%H:%M"),
        description=f"Self top-up ({request.wallet_type.title()})",
        amount=request.amount,
        type=TransactionType.CREDIT,
        payment_method=request.payment_method,
        reference_number=request.reference_id or None,
    )
    db.add(txn)
    await db.commit()

    bal = await _calc_balance(db, patient.id, wt)
    return {
        "id": txn.id,
        "wallet_type": request.wallet_type.upper(),
        "amount": request.amount,
        "new_balance": bal["balance"],
    }
