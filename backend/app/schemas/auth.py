from pydantic import BaseModel
from typing import Optional
from enum import Enum


class UserRoleEnum(str, Enum):
    PATIENT = "PATIENT"
    STUDENT = "STUDENT"
    FACULTY = "FACULTY"


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user_id: str
    role: str


class RefreshRequest(BaseModel):
    refresh_token: str


# Registration schemas
class EmergencyContactCreate(BaseModel):
    name: str
    phone: str
    relationship: str


class PatientDataCreate(BaseModel):
    name: str
    date_of_birth: str
    gender: str
    blood_group: str
    phone: str
    email: str
    address: Optional[str] = None
    aadhaar_id: Optional[str] = None
    abha_id: Optional[str] = None
    emergency_contact: Optional[EmergencyContactCreate] = None


class StudentDataCreate(BaseModel):
    name: str
    program: str
    year: int
    semester: int
    gpa: float = 0.0
    academic_advisor: Optional[str] = None


class FacultyDataCreate(BaseModel):
    name: str
    department: str
    specialty: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str
    role: UserRoleEnum
    patient_data: Optional[PatientDataCreate] = None
    student_data: Optional[StudentDataCreate] = None
    faculty_data: Optional[FacultyDataCreate] = None


class RegisterResponse(BaseModel):
    message: str
    user_id: str
