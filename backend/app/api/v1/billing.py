"""Billing & Cashier API – profile and patient wallet management."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.api.deps import require_role
from app.models.user import User, UserRole
from app.models.billing import Billing

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/me")
async def get_billing_profile(
    user: User = Depends(require_role(UserRole.BILLING)),
    db: AsyncSession = Depends(get_db),
):
    billing = (await db.execute(select(Billing).where(Billing.user_id == user.id))).scalar_one_or_none()
    if not billing:
        raise HTTPException(status_code=404, detail="Billing profile not found")
    return {
        "id": billing.id,
        "billing_id": billing.billing_id,
        "name": billing.name,
        "counter_name": billing.counter_name,
        "phone": billing.phone,
        "email": billing.email,
        "username": user.username,
    }
