from pydantic import BaseModel
from typing import Optional, List


class FacultyResponse(BaseModel):
    id: str
    faculty_id: str
    name: str
    department: str
    specialty: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    photo: Optional[str] = None
    availability: Optional[str] = None

    model_config = {"from_attributes": True}


class ApprovalResponse(BaseModel):
    id: str
    case_record_id: str
    faculty_id: str
    status: str
    comments: Optional[str] = None
    created_at: str
    processed_at: Optional[str] = None

    model_config = {"from_attributes": True}


class ApprovalUpdateRequest(BaseModel):
    status: str  # Approved or Rejected
    comments: Optional[str] = None
