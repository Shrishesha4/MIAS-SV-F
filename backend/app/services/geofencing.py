"""
Geofencing service — point-in-polygon validation and patient proof management.
Uses a pure-Python ray-casting algorithm (no PostGIS required).
"""
from __future__ import annotations

import random
import string
import uuid
from datetime import datetime, timedelta
from typing import Sequence

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.geofence import GeofenceZone, PatientGeofenceProof

# Proof TTL — patient must complete check-in within this window
_PROOF_TTL_MINUTES = 15


def _point_in_polygon(lat: float, lng: float, polygon: list[dict]) -> bool:
    """
    Ray-casting algorithm to determine if (lat, lng) is inside a polygon.
    polygon: list of {lat, lng} dicts.
    """
    n = len(polygon)
    if n < 3:
        return False
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]["lng"], polygon[i]["lat"]
        xj, yj = polygon[j]["lng"], polygon[j]["lat"]
        if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

def _generate_short_code() -> str:
    """Generate an 8-character uppercase alphanumeric code for staff entry."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


async def _find_proof(proof_id_or_code: str, db: AsyncSession) -> PatientGeofenceProof | None:
    """Look up a proof by full UUID or 8-character short code."""
    # Try UUID first
    result = await db.execute(
        select(PatientGeofenceProof).where(PatientGeofenceProof.id == proof_id_or_code)
    )
    proof = result.scalar_one_or_none()
    if proof:
        return proof
    # Fallback to short code (case-insensitive)
    result = await db.execute(
        select(PatientGeofenceProof).where(
            PatientGeofenceProof.short_code == proof_id_or_code.upper()
        )
    )
    return result.scalar_one_or_none()


async def get_active_zones(db: AsyncSession) -> Sequence[GeofenceZone]:
    result = await db.execute(select(GeofenceZone).where(GeofenceZone.is_active == True))
    return result.scalars().all()


async def validate_location(
    lat: float,
    lng: float,
    db: AsyncSession,
) -> GeofenceZone | None:
    """
    Return the first active zone that contains (lat, lng), or raise 403 if none.
    Returns None only when there are NO active zones (enforcement disabled).
    """
    zones = await get_active_zones(db)
    if not zones:
        # No zones configured → enforcement disabled, allow all
        return None

    for zone in zones:
        polygon = zone.polygon or []
        if _point_in_polygon(lat, lng, polygon):
            return zone

    raise HTTPException(
        status_code=403,
        detail="Check-in is only allowed from within the campus premises.",
    )


async def create_patient_proof(
    lat: float,
    lng: float,
    accuracy: float | None,
    db: AsyncSession,
    patient_id: str | None = None,
) -> PatientGeofenceProof:
    """
    Create a one-time geofence proof for a patient device.
    is_valid reflects whether the point was inside an active zone.
    """
    zones = await get_active_zones(db)
    matched_zone: GeofenceZone | None = None

    if zones:
        for zone in zones:
            if _point_in_polygon(lat, lng, zone.polygon or []):
                matched_zone = zone
                break

    proof = PatientGeofenceProof(
        id=str(uuid.uuid4()),
        short_code=_generate_short_code(),
        patient_id=patient_id,
        lat=lat,
        lng=lng,
        accuracy=accuracy,
        is_valid=matched_zone is not None or not zones,
        zone_id=matched_zone.id if matched_zone else None,
        expires_at=datetime.utcnow() + timedelta(minutes=_PROOF_TTL_MINUTES),
        consumed_at=None,
    )
    db.add(proof)
    await db.flush()  # write without committing so caller can batch
    return proof


async def consume_proof(
    proof_id: str,
    db: AsyncSession,
) -> PatientGeofenceProof:
    """
    Validate and consume a patient geofence proof.
    Accepts full UUID or 8-character short code.
    Raises 400 on invalid/expired/already-consumed proofs.
    Raises 403 if proof marks the patient as outside all zones.
    """
    proof = await _find_proof(proof_id, db)

    if not proof:
        raise HTTPException(status_code=400, detail="Invalid geofence proof.")
    if proof.consumed_at is not None:
        raise HTTPException(status_code=400, detail="Geofence proof already used.")
    if proof.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Geofence proof has expired.")
    if not proof.is_valid:
        raise HTTPException(
            status_code=403,
            detail="Patient location is outside campus premises.",
        )

    proof.consumed_at = datetime.utcnow()
    await db.flush()
    return proof
