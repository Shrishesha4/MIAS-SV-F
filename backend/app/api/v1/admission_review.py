"""Endpoints for I/O events, SOAP notes, and equipment for admitted patients."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import uuid

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.admission import Admission
from app.models.io_event import IOEvent, SOAPNote, AdmissionEquipment

router = APIRouter(prefix="/admissions", tags=["Admission Review"])


def _user_label(user: User) -> str:
    return user.username or "MIAS User"


def _default_connected_since() -> str:
    return datetime.utcnow().strftime("%I:%M %p")


def _default_live_data(equipment_type: str) -> dict | None:
    defaults = {
        "Bedside Monitor": {
            "hr": 82,
            "bp_sys": 128,
            "bp_dia": 78,
            "map": 95,
            "spo2": 98,
            "rr": 16,
            "temp": 98.6,
            "etco2": 38,
        },
        "Pulse Oximeter": {
            "spo2": 98,
            "pulse": 82,
        },
        "Ventilator": {
            "pip": 17,
            "peep": 5,
            "fio2": 40,
            "tidal_vol": 524,
        },
        "ABG Analyzer": {
            "ph": 7.39,
            "pco2": 43,
            "po2": 70,
            "hco3": 20,
            "lactate": 1.3,
        },
    }
    return defaults.get(equipment_type)


def _build_io_summary(events: list[IOEvent]) -> dict:
    summary = {
        "iv_input_ml": 0,
        "oral_intake_ml": 0,
        "urine_output_ml": 0,
        "stool_count": 0,
    }
    for event in events:
        amount = event.amount_ml or 0
        if event.event_type == "IV Input":
            summary["iv_input_ml"] += amount
        elif event.event_type == "Food":
            summary["oral_intake_ml"] += amount
        elif event.event_type == "Urine":
            summary["urine_output_ml"] += amount
        elif event.event_type == "Stool":
            summary["stool_count"] += 1
    return summary


# ── I/O Events ──────────────────────────────────────────────────────────────

@router.get("/{admission_id}/io-events")
async def list_io_events(
    admission_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(IOEvent)
        .where(IOEvent.admission_id == admission_id)
        .order_by(IOEvent.event_time)
    )
    events = result.scalars().all()
    return {
        "events": [
            {
                "id": e.id,
                "admission_id": e.admission_id,
                "patient_id": e.patient_id,
                "event_time": e.event_time,
                "event_type": e.event_type,
                "description": e.description,
                "amount_ml": e.amount_ml,
                "recorded_by": e.recorded_by,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
        "summary": _build_io_summary(events),
    }


@router.post("/{admission_id}/io-events", status_code=201)
async def add_io_event(
    admission_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    admission = (await db.execute(select(Admission).where(Admission.id == admission_id))).scalar_one_or_none()
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found")

    event = IOEvent(
        id=str(uuid.uuid4()),
        admission_id=admission_id,
        patient_id=admission.patient_id,
        event_time=body.get("event_time", ""),
        event_type=body.get("event_type", ""),
        description=body.get("description"),
        amount_ml=body.get("amount_ml"),
        recorded_by=body.get("recorded_by") or _user_label(user),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return {"id": event.id, "message": "Event added"}


@router.delete("/{admission_id}/io-events/{event_id}", status_code=204)
async def delete_io_event(
    admission_id: str,
    event_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    event = (await db.execute(
        select(IOEvent).where(IOEvent.id == event_id, IOEvent.admission_id == admission_id)
    )).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    await db.delete(event)
    await db.commit()


# ── SOAP Notes ───────────────────────────────────────────────────────────────

@router.get("/{admission_id}/soap-notes")
async def list_soap_notes(
    admission_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SOAPNote)
        .where(SOAPNote.admission_id == admission_id)
        .order_by(SOAPNote.created_at.desc())
    )
    notes = result.scalars().all()
    return [
        {
            "id": n.id,
            "admission_id": n.admission_id,
            "patient_id": n.patient_id,
            "subjective": n.subjective,
            "objective": n.objective,
            "assessment": n.assessment,
            "plan": n.plan,
            "plan_items": n.plan_items,
            "note_meta": n.note_meta,
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "created_by": n.created_by,
            "updated_at": n.updated_at.isoformat() if n.updated_at else None,
            "updated_by": n.updated_by,
        }
        for n in notes
    ]


@router.post("/{admission_id}/soap-notes", status_code=201)
async def create_soap_note(
    admission_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    admission = (await db.execute(select(Admission).where(Admission.id == admission_id))).scalar_one_or_none()
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found")

    note = SOAPNote(
        id=str(uuid.uuid4()),
        admission_id=admission_id,
        patient_id=admission.patient_id,
        subjective=body.get("subjective"),
        objective=body.get("objective"),
        assessment=body.get("assessment"),
        plan=body.get("plan"),
        plan_items=body.get("plan_items"),
        note_meta=body.get("note_meta") or {
            "author": _user_label(user),
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %I:%M %p"),
        },
        created_by=body.get("created_by") or _user_label(user),
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return {"id": note.id, "message": "SOAP note created"}


@router.put("/{admission_id}/soap-notes/{note_id}")
async def update_soap_note(
    admission_id: str,
    note_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    note = (await db.execute(
        select(SOAPNote).where(SOAPNote.id == note_id, SOAPNote.admission_id == admission_id)
    )).scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="SOAP note not found")

    for field in ["subjective", "objective", "assessment", "plan", "plan_items", "note_meta"]:
        if field in body:
            setattr(note, field, body[field])
    note.updated_at = datetime.utcnow()
    note.updated_by = body.get("updated_by") or _user_label(user)
    await db.commit()
    return {"message": "Note updated", "id": note.id}


# ── Connected Equipment ───────────────────────────────────────────────────────

@router.get("/{admission_id}/equipment")
async def list_equipment(
    admission_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AdmissionEquipment)
        .where(AdmissionEquipment.admission_id == admission_id)
    )
    items = result.scalars().all()
    return [
        {
            "id": e.id,
            "admission_id": e.admission_id,
            "equipment_type": e.equipment_type,
            "equipment_id": e.equipment_id,
            "connected_since": e.connected_since,
            "status": e.status,
            "live_data": e.live_data,
        }
        for e in items
    ]


@router.post("/{admission_id}/equipment", status_code=201)
async def connect_equipment(
    admission_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    admission = (await db.execute(select(Admission).where(Admission.id == admission_id))).scalar_one_or_none()
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found")

    equip = AdmissionEquipment(
        id=str(uuid.uuid4()),
        admission_id=admission_id,
        patient_id=admission.patient_id,
        equipment_type=body.get("equipment_type", ""),
        equipment_id=body.get("equipment_id"),
        connected_since=body.get("connected_since") or _default_connected_since(),
        status=body.get("status", "active"),
        live_data=body.get("live_data") or _default_live_data(body.get("equipment_type", "")),
    )
    db.add(equip)
    await db.commit()
    await db.refresh(equip)
    return {"id": equip.id, "message": "Equipment connected"}


@router.delete("/{admission_id}/equipment/{equip_id}", status_code=204)
async def disconnect_equipment(
    admission_id: str,
    equip_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    equip = (await db.execute(
        select(AdmissionEquipment).where(
            AdmissionEquipment.id == equip_id,
            AdmissionEquipment.admission_id == admission_id,
        )
    )).scalar_one_or_none()
    if not equip:
        raise HTTPException(status_code=404, detail="Equipment not found")
    await db.delete(equip)
    await db.commit()
