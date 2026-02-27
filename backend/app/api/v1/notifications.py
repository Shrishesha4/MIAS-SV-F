"""Notifications endpoints are part of patients/students/faculty routes.
This module provides a general notifications endpoint."""

from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/unread-count")
async def get_unread_count(user: User = Depends(get_current_user)):
    # In production, count from the appropriate notification table based on role
    return {"count": 0}
