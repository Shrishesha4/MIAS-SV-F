from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List
from enum import Enum


class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class PatientCategory(str, Enum):
    GENERAL = "GENERAL"
    ELITE = "ELITE"
    VIP = "VIP"
    STAFF = "STAFF"


class EmergencyContactResponse(BaseModel):
    id: str
    name: str
    relationship_: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None

    model_config = {"from_attributes": True}


class InsurancePolicyResponse(BaseModel):
    id: str
    provider: str
    policy_number: str
    valid_until: Optional[date] = None
    coverage_type: Optional[str] = None

    model_config = {"from_attributes": True}


class AllergyResponse(BaseModel):
    id: str
    allergen: str
    severity: str
    reaction: Optional[str] = None

    model_config = {"from_attributes": True}


class MedicalAlertResponse(BaseModel):
    id: str
    type: str
    severity: str
    title: str
    description: Optional[str] = None
    symptoms: Optional[str] = None
    is_active: bool
    added_by: Optional[str] = None
    added_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PatientResponse(BaseModel):
    id: str
    patient_id: str
    name: str
    date_of_birth: date
    gender: Gender
    blood_group: str
    phone: str
    email: Optional[str] = None
    photo: Optional[str] = None
    category: PatientCategory

    model_config = {"from_attributes": True}


class PatientDetailResponse(PatientResponse):
    address: str
    aadhaar_id: Optional[str] = None
    abha_id: Optional[str] = None
    primary_diagnosis: Optional[str] = None
    diagnosis_doctor: Optional[str] = None
    diagnosis_date: Optional[str] = None
    diagnosis_time: Optional[str] = None
    emergency_contact: Optional[EmergencyContactResponse] = None
    allergies: List[AllergyResponse] = []
    medical_alerts: List[MedicalAlertResponse] = []
    insurance_policies: List[InsurancePolicyResponse] = []

    model_config = {"from_attributes": True}
