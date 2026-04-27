"""
Geofencing API — admin zone CRUD + patient proof endpoints.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.database import get_db
from app.models.geofence import GeofenceZone, PatientGeofenceProof
from app.models.user import User, UserRole
from app.services.geofencing import create_patient_proof, _find_proof

router = APIRouter(prefix="/geofencing", tags=["Geofencing"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ZoneCreate(BaseModel):
    name: str
    polygon: list[dict]  # [{lat: float, lng: float}, ...]
    is_active: bool = True


class ZoneUpdate(BaseModel):
    name: str | None = None
    polygon: list[dict] | None = None
    is_active: bool | None = None


class PatientProofRequest(BaseModel):
    lat: float
    lng: float
    accuracy: float | None = None
    patient_id: str | None = None  # Null for new-registration flow


# ---------------------------------------------------------------------------
# Admin zone CRUD
# ---------------------------------------------------------------------------

@router.get("/zones")
async def list_zones(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(GeofenceZone).order_by(GeofenceZone.created_at))
    zones = result.scalars().all()
    return [_serialize_zone(z) for z in zones]


@router.post("/zones")
async def create_zone(
    body: ZoneCreate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    if len(body.polygon) < 3:
        raise HTTPException(status_code=400, detail="A polygon must have at least 3 vertices.")
    zone = GeofenceZone(
        id=str(uuid.uuid4()),
        name=body.name,
        polygon=body.polygon,
        is_active=body.is_active,
    )
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return _serialize_zone(zone)


@router.patch("/zones/{zone_id}")
async def update_zone(
    zone_id: str,
    body: ZoneUpdate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(GeofenceZone).where(GeofenceZone.id == zone_id))
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found.")
    if body.name is not None:
        zone.name = body.name
    if body.polygon is not None:
        if len(body.polygon) < 3:
            raise HTTPException(status_code=400, detail="A polygon must have at least 3 vertices.")
        zone.polygon = body.polygon
    if body.is_active is not None:
        zone.is_active = body.is_active
    zone.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(zone)
    return _serialize_zone(zone)


@router.delete("/zones/{zone_id}")
async def delete_zone(
    zone_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(GeofenceZone).where(GeofenceZone.id == zone_id))
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found.")
    await db.delete(zone)
    await db.commit()
    return {"message": "Zone deleted."}


# ---------------------------------------------------------------------------
# Patient device proof endpoint (no auth required — patient not logged in yet
# during new registration; existing patients present their JWT)
# ---------------------------------------------------------------------------

@router.post("/patient-proof")
async def submit_patient_proof(
    body: PatientProofRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Called from the patient's own device.
    Returns a short-lived proof_id that staff use when checking the patient in.
    """
    proof = await create_patient_proof(
        lat=body.lat,
        lng=body.lng,
        accuracy=body.accuracy,
        db=db,
        patient_id=body.patient_id,
    )
    await db.commit()
    await db.refresh(proof)

    if not proof.is_valid:
        # Still return the proof but signal invalidity so the patient knows
        return {
            "proof_id": proof.id,
            "short_code": proof.short_code,
            "is_valid": False,
            "expires_at": proof.expires_at.isoformat(),
            "message": "Your location is outside campus premises. Check-in will be blocked.",
        }

    return {
        "proof_id": proof.id,
        "short_code": proof.short_code,
        "is_valid": True,
        "expires_at": proof.expires_at.isoformat(),
        "message": "Location verified. Show this to the receptionist.",
    }


@router.get("/patient-proof/{proof_id}/status")
async def get_proof_status(
    proof_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Let staff poll proof validity before consuming it. Accepts UUID or short code."""
    proof = await _find_proof(proof_id, db)
    if not proof:
        raise HTTPException(status_code=404, detail="Proof not found.")
    return {
        "proof_id": proof.id,
        "short_code": proof.short_code,
        "is_valid": proof.is_valid,
        "is_consumed": proof.consumed_at is not None,
        "is_expired": proof.expires_at < datetime.utcnow(),
        "expires_at": proof.expires_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Public read — active zones for the map on patient devices
# ---------------------------------------------------------------------------

@router.get("/zones/public")
async def list_active_zones_public(db: AsyncSession = Depends(get_db)):
    """Return active zone polygons so the patient's device can render the map."""
    result = await db.execute(
        select(GeofenceZone).where(GeofenceZone.is_active == True)
    )
    zones = result.scalars().all()
    return [{"id": z.id, "name": z.name, "polygon": z.polygon} for z in zones]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize_zone(z: GeofenceZone) -> dict:
    return {
        "id": z.id,
        "name": z.name,
        "polygon": z.polygon,
        "is_active": z.is_active,
        "created_at": z.created_at.isoformat() if z.created_at else None,
        "updated_at": z.updated_at.isoformat() if z.updated_at else None,
    }
