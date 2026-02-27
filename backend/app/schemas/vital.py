from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class VitalBase(BaseModel):
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    heart_rate: Optional[int] = None
    respiratory_rate: Optional[int] = None
    temperature: Optional[float] = None
    oxygen_saturation: Optional[int] = None
    weight: Optional[float] = None
    blood_glucose: Optional[int] = None
    cholesterol: Optional[int] = None
    bmi: Optional[float] = None


class VitalCreate(VitalBase):
    recorded_by: Optional[str] = None


class VitalResponse(VitalBase):
    id: str
    patient_id: str
    recorded_at: datetime
    recorded_by: Optional[str] = None

    model_config = {"from_attributes": True}
