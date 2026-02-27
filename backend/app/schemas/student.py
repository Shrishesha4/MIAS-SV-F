from pydantic import BaseModel
from typing import Optional, List


class StudentAttendanceResponse(BaseModel):
    overall: float
    clinical: float
    lecture: float
    lab: float

    model_config = {"from_attributes": True}


class DisciplinaryActionResponse(BaseModel):
    id: str
    type: str
    description: str
    date: str
    status: str
    details: Optional[str] = None
    resolution: Optional[str] = None

    model_config = {"from_attributes": True}


class StudentResponse(BaseModel):
    id: str
    student_id: str
    name: str
    year: int
    semester: int
    program: str
    degree: Optional[str] = None
    photo: Optional[str] = None
    gpa: float
    academic_standing: str
    academic_advisor: Optional[str] = None

    model_config = {"from_attributes": True}


class StudentDetailResponse(StudentResponse):
    attendance: Optional[StudentAttendanceResponse] = None
    disciplinary_actions: List[DisciplinaryActionResponse] = []

    model_config = {"from_attributes": True}


class AssignedPatientResponse(BaseModel):
    id: str
    patient_id: str
    name: str
    age: Optional[int] = None
    condition: Optional[str] = None
    status: str

    model_config = {"from_attributes": True}
