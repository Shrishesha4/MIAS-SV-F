from pydantic import BaseModel
from typing import Optional


class NurseBase(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    clinic_id: Optional[str] = None
    hospital: Optional[str] = None
    ward: Optional[str] = None
    shift: Optional[str] = None
    department: Optional[str] = None


class NurseCreate(NurseBase):
    pass


class NurseUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    clinic_id: Optional[str] = None
    hospital: Optional[str] = None
    ward: Optional[str] = None
    shift: Optional[str] = None
    department: Optional[str] = None


class NurseStationSelect(BaseModel):
    clinic_id: Optional[str] = None
    hospital: Optional[str] = None
    ward: Optional[str] = None
    shift: Optional[str] = None
    department: Optional[str] = None


class NurseResponse(NurseBase):
    id: str
    nurse_id: str
    user_id: str
    has_selected_station: int
    photo: Optional[str] = None

    class Config:
        from_attributes = True


class SBARNoteCreate(BaseModel):
    situation: Optional[str] = None
    background: Optional[str] = None
    assessment: Optional[str] = None
    recommendation: Optional[str] = None
