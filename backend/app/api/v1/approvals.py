"""Approvals are accessible via faculty routes.
This module provides top-level approval queries."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.case_record import Approval

router = APIRouter(prefix="/approvals", tags=["Approvals"])


@router.get("/{approval_id}")
async def get_approval(
    approval_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Approval)
        .options(selectinload(Approval.case_record))
        .where(Approval.id == approval_id)
    )
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Approval not found")

    return {
        "id": a.id,
        "case_record_id": a.case_record_id,
        "faculty_id": a.faculty_id,
        "status": a.status,
        "comments": a.comments,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "processed_at": a.processed_at.isoformat() if a.processed_at else None,
    }
