"""Database seeding script – creates test users and sample data."""
import asyncio
import uuid
import random
from datetime import datetime, date, timedelta
from decimal import Decimal

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal, engine, Base
from sqlalchemy import text
from app.models.user import User, UserRole
from app.models.patient import Patient, Gender, PatientCategory, MedicalAlert
from app.models.student import Student, StudentPatientAssignment, Clinic, ClinicAppointment
from app.models.faculty import Faculty
from app.models.nurse import Nurse
from app.models.nurse_order import NurseOrder
from app.models.department import Department
from app.models.vital import Vital
from app.models.prescription import Prescription, PrescriptionMedication, PrescriptionStatus
from app.models.programme import Programme
from app.models.admission import Admission
from app.models.io_event import IOEvent, SOAPNote, AdmissionEquipment
from app.models.case_record import CaseRecord, Approval, ApprovalType, ApprovalStatus
from app.models.student_permission import StudentPermission
from app.models.form_definition import FormDefinition
from app.core.security import get_password_hash


def uid() -> str:
    return str(uuid.uuid4())


# ── Data ─────────────────────────────────────────────────────────────

DOCTORS = [
    {
        "username": "d1", "password": "d1",
        "email": "dr.kumar@saveetha.com",
        "name": "Dr. Arun Kumar",
        "faculty_id": "FAC-001",
        "department": "Internal Medicine",
        "specialty": "General Medicine",
    },
    {
        "username": "d2", "password": "d2",
        "email": "dr.priya@saveetha.com",
        "name": "Dr. Priya Sharma",
        "faculty_id": "FAC-002",
        "department": "Cardiology",
        "specialty": "Cardiac Care",
    },
    {
        "username": "d3", "password": "d3",
        "email": "dr.ravi@saveetha.com",
        "name": "Dr. Ravi Menon",
        "faculty_id": "FAC-003",
        "department": "Pediatrics",
        "specialty": "Child Health",
    },
]

STUDENTS = [
    {"username": "s1", "password": "s1", "email": "s1@saveetha.com", "name": "Ananya Iyer",      "student_id": "STU-001", "year": 3, "semester": 5, "program": "BDS", "gpa": 8.5},
    {"username": "s2", "password": "s2", "email": "s2@saveetha.com", "name": "Karthik Rajan",     "student_id": "STU-002", "year": 3, "semester": 5, "program": "BDS", "gpa": 7.8},
    {"username": "s3", "password": "s3", "email": "s3@saveetha.com", "name": "Divya Nair",        "student_id": "STU-003", "year": 4, "semester": 7, "program": "BDS", "gpa": 9.1},
    {"username": "s4", "password": "s4", "email": "s4@saveetha.com", "name": "Rahul Krishnan",    "student_id": "STU-004", "year": 2, "semester": 3, "program": "BDS", "gpa": 7.2},
    {"username": "s5", "password": "s5", "email": "s5@saveetha.com", "name": "Meera Sundar",      "student_id": "STU-005", "year": 4, "semester": 8, "program": "BDS", "gpa": 8.9},
    {"username": "s6", "password": "s6", "email": "s6@saveetha.com", "name": "Vikram Patel",      "student_id": "STU-006", "year": 2, "semester": 4, "program": "BDS", "gpa": 7.5},
    {"username": "s7", "password": "s7", "email": "s7@saveetha.com", "name": "Sneha Reddy",       "student_id": "STU-007", "year": 3, "semester": 6, "program": "BDS", "gpa": 8.3},
    {"username": "s8", "password": "s8", "email": "s8@saveetha.com", "name": "Arjun Mohan",       "student_id": "STU-008", "year": 1, "semester": 2, "program": "BDS", "gpa": 8.0},
    {"username": "s9", "password": "s9", "email": "s9@saveetha.com", "name": "Lakshmi Venkat",    "student_id": "STU-009", "year": 1, "semester": 1, "program": "BDS", "gpa": 7.6},
]

NURSES = [
    {
        "username": "n1", "password": "n1",
        "email": "nurse1@saveetha.com",
        "name": "Nurse Radha Krishnan",
        "nurse_id": "NUR-001",
        "phone": "+91 90002 00001",
    },
    {
        "username": "n2", "password": "n2",
        "email": "nurse2@saveetha.com",
        "name": "Nurse Meena Kumar",
        "nurse_id": "NUR-002",
        "phone": "+91 90002 00002",
    },
    {
        "username": "n3", "password": "n3",
        "email": "nurse3@saveetha.com",
        "name": "Nurse Pooja Singh",
        "nurse_id": "NUR-003",
        "phone": "+91 90002 00003",
    },
]

PATIENTS = [
    {"username": "p1",  "password": "p1",  "email": "p1@email.com",  "name": "Rajesh Kumar",     "patient_id": "PAT-001", "dob": date(1990, 5, 15),  "gender": Gender.MALE,   "blood_group": "O+",  "phone": "+91 90001 00001", "address": "1 Anna Nagar, Chennai"},
    {"username": "p2",  "password": "p2",  "email": "p2@email.com",  "name": "Sunita Devi",      "patient_id": "PAT-002", "dob": date(1985, 8, 22),  "gender": Gender.FEMALE, "blood_group": "A+",  "phone": "+91 90001 00002", "address": "2 T Nagar, Chennai"},
    {"username": "p3",  "password": "p3",  "email": "p3@email.com",  "name": "Mohammed Ali",     "patient_id": "PAT-003", "dob": date(1978, 3, 10),  "gender": Gender.MALE,   "blood_group": "B+",  "phone": "+91 90001 00003", "address": "3 Adyar, Chennai"},
    {"username": "p4",  "password": "p4",  "email": "p4@email.com",  "name": "Priya Lakshmi",    "patient_id": "PAT-004", "dob": date(1995, 11, 5),  "gender": Gender.FEMALE, "blood_group": "AB+", "phone": "+91 90001 00004", "address": "4 Velachery, Chennai"},
    {"username": "p5",  "password": "p5",  "email": "p5@email.com",  "name": "Ganesh Babu",      "patient_id": "PAT-005", "dob": date(1970, 1, 20),  "gender": Gender.MALE,   "blood_group": "O-",  "phone": "+91 90001 00005", "address": "5 Porur, Chennai"},
    {"username": "p6",  "password": "p6",  "email": "p6@email.com",  "name": "Kavitha Rani",     "patient_id": "PAT-006", "dob": date(1988, 7, 14),  "gender": Gender.FEMALE, "blood_group": "A-",  "phone": "+91 90001 00006", "address": "6 Tambaram, Chennai"},
    {"username": "p7",  "password": "p7",  "email": "p7@email.com",  "name": "Suresh Pandian",   "patient_id": "PAT-007", "dob": date(1965, 12, 30), "gender": Gender.MALE,   "blood_group": "B-",  "phone": "+91 90001 00007", "address": "7 Chromepet, Chennai"},
    {"username": "p8",  "password": "p8",  "email": "p8@email.com",  "name": "Deepa Murthy",     "patient_id": "PAT-008", "dob": date(1992, 4, 8),   "gender": Gender.FEMALE, "blood_group": "O+",  "phone": "+91 90001 00008", "address": "8 Guindy, Chennai"},
    {"username": "p9",  "password": "p9",  "email": "p9@email.com",  "name": "Vijay Anand",      "patient_id": "PAT-009", "dob": date(1982, 9, 25),  "gender": Gender.MALE,   "blood_group": "A+",  "phone": "+91 90001 00009", "address": "9 Mylapore, Chennai"},
    {"username": "p10", "password": "p10", "email": "p10@email.com", "name": "Revathi Shankar",   "patient_id": "PAT-010", "dob": date(1998, 6, 3),   "gender": Gender.FEMALE, "blood_group": "AB-", "phone": "+91 90001 00010", "address": "10 Nungambakkam, Chennai"},
]

DEPARTMENTS = [
    {"name": "Internal Medicine", "code": "IM",   "description": "General internal medicine and diagnostics"},
    {"name": "Cardiology",        "code": "CARD", "description": "Heart and cardiovascular care"},
    {"name": "Pediatrics",        "code": "PED",  "description": "Child and adolescent healthcare"},
]

CLINICS = [
    {"name": "Saveetha General Clinic", "block": "Block A", "clinic_type": "General", "department": "Internal Medicine", "location": "Outpatient Wing, Ground Floor", "faculty_idx": 0},
    {"name": "Saveetha Dental Clinic",  "block": "Block B", "clinic_type": "General", "department": "Dentistry",        "location": "Block B, 1st Floor",           "faculty_idx": 2},
    {"name": "Cardiology Clinic",       "block": "Block C", "clinic_type": "Specialty", "department": "Cardiology",     "location": "Block C, 2nd Floor",           "faculty_idx": 1},
]

LABS = [
    {"name": "Central Pathology Lab", "block": "Block C", "lab_type": "Pathology", "department": "Pathology", "location": "Block C, Ground Floor", "contact_phone": "+91-44-2680-1234", "operating_hours": "24/7"},
    {"name": "Radiology & Imaging", "block": "Block D", "lab_type": "Radiology", "department": "Radiology", "location": "Block D, 1st Floor", "contact_phone": "+91-44-2680-1235", "operating_hours": "8 AM - 8 PM"},
    {"name": "Microbiology Lab", "block": "Block C", "lab_type": "Microbiology", "department": "Microbiology", "location": "Block C, 2nd Floor", "contact_phone": "+91-44-2680-1236", "operating_hours": "9 AM - 6 PM"},
]

CLINIC_APPOINTMENTS = [
    # General Medicine OPD – 4 patients
    {"clinic_idx": 0, "patient_idx": 0, "time": "9:00 AM",  "status": "Completed",   "provider": "Dr. Arun Kumar"},
    {"clinic_idx": 0, "patient_idx": 1, "time": "9:30 AM",  "status": "In Progress", "provider": "Dr. Arun Kumar"},
    {"clinic_idx": 0, "patient_idx": 2, "time": "10:00 AM", "status": "Checked In",  "provider": "Dr. Arun Kumar"},
    {"clinic_idx": 0, "patient_idx": 3, "time": "10:30 AM", "status": "Scheduled",   "provider": "Dr. Arun Kumar"},
    # Cardiology Clinic – 3 patients
    {"clinic_idx": 1, "patient_idx": 4, "time": "9:15 AM",  "status": "Completed",   "provider": "Dr. Priya Sharma"},
    {"clinic_idx": 1, "patient_idx": 5, "time": "10:00 AM", "status": "In Progress", "provider": "Dr. Priya Sharma"},
    {"clinic_idx": 1, "patient_idx": 6, "time": "10:45 AM", "status": "Scheduled",   "provider": "Dr. Priya Sharma"},
    # Pediatrics – 3 patients
    {"clinic_idx": 2, "patient_idx": 7, "time": "9:00 AM",  "status": "In Progress", "provider": "Dr. Ravi Menon"},
    {"clinic_idx": 2, "patient_idx": 8, "time": "9:45 AM",  "status": "Checked In",  "provider": "Dr. Ravi Menon"},
    {"clinic_idx": 2, "patient_idx": 9, "time": "10:30 AM", "status": "Scheduled",   "provider": "Dr. Ravi Menon"},
]

PROGRAMMES = [
    {"name": "BDS",  "code": "BDS",  "description": "Bachelor of Dental Surgery",               "degree_type": "Undergraduate", "duration_years": "4"},
    {"name": "MDS",  "code": "MDS",  "description": "Master of Dental Surgery",                 "degree_type": "Postgraduate",  "duration_years": "3"},
    {"name": "MBBS", "code": "MBBS", "description": "Bachelor of Medicine and Bachelor of Surgery", "degree_type": "Undergraduate", "duration_years": "5"},
    {"name": "MD",   "code": "MD",   "description": "Doctor of Medicine",                       "degree_type": "Postgraduate",  "duration_years": "3"},
    {"name": "MS",   "code": "MS",   "description": "Master of Surgery",                        "degree_type": "Postgraduate",  "duration_years": "3"},
]

ADMISSIONS_DATA = [
    # Active admissions with full assessment form data
    {
        "patient_idx": 0, "student_idx": 0, "faculty_idx": 0,
        "department": "Internal Medicine", "ward": "General Ward A", "bed_number": "A-12",
        "reason": "Acute hypertensive crisis with persistent headache and blurred vision",
        "diagnosis": "Essential Hypertension - Stage 2", "status": "Active", "days_ago": 2,
        "accompanied_by": "Wife - Meena Kumar", "accompanied_by_contact": "+91 98765 43210",
        "airway_patent": True, "breathing_adequate": True, "pulse_present": True, "capillary_refill_time": 2.0,
        "bp_admission": "178/110", "heart_rate_admission": "92", "resp_rate_admission": "18",
        "spo2_admission": "97", "temp_admission": "98.6", "weight_admission": "76",
        "gcs_eye": 4, "gcs_verbal": 5, "gcs_motor": 6, "cbg": "138", "pain_score": 6,
        "drug_allergy": "Penicillin - rash", "identification_marks": "Scar on left forearm",
        "chief_complaints": "Severe headache since 2 days, blurred vision, dizziness on exertion",
        "history_of_present_illness": "Known hypertensive for 5 years. On Tab Amlodipine 5mg OD. BP uncontrolled despite medication.",
        "past_medical_history": "Hypertension x5 years, no diabetes",
        "medication_history": "Tab Amlodipine 5mg OD, Tab Aspirin 75mg OD",
        "surgical_history": "Appendicectomy 2015",
        "physical_examination": "Conscious, oriented. BP 178/110 mmHg. Fundus: Grade II hypertensive retinopathy.",
        "pain_score_reassessment": 4,
        "provisional_diagnosis": "Essential Hypertension Stage 2 with end-organ damage",
        "expected_cost": 25000.0,
        "proposed_plan": "IV antihypertensives, 24-hr BP monitoring, nephrology consult, echocardiogram",
    },
    {
        "patient_idx": 3, "student_idx": 1, "faculty_idx": 1,
        "department": "Cardiology", "ward": "ICU", "bed_number": "ICU-3",
        "reason": "Chest pain evaluation - crushing pain radiating to left arm",
        "diagnosis": "Unstable Angina", "status": "Active", "days_ago": 1,
        "accompanied_by": "Husband - Suresh", "accompanied_by_contact": "+91 98765 11111",
        "airway_patent": True, "breathing_adequate": True, "pulse_present": True, "capillary_refill_time": 2.5,
        "bp_admission": "145/92", "heart_rate_admission": "88", "resp_rate_admission": "20",
        "spo2_admission": "96", "temp_admission": "98.4", "weight_admission": "62",
        "gcs_eye": 4, "gcs_verbal": 5, "gcs_motor": 6, "cbg": "180", "pain_score": 8,
        "drug_allergy": "None known", "identification_marks": "None",
        "menstrual_history": "Regular cycles, 28-day cycle, LMP 15 days ago",
        "chief_complaints": "Crushing chest pain since 4 hours, radiating to left arm and jaw, associated with sweating",
        "history_of_present_illness": "No prior cardiac history. Type 2 DM x3 years. Sudden onset chest pain at rest.",
        "past_medical_history": "Type 2 Diabetes Mellitus x3 years",
        "medication_history": "Tab Metformin 500mg BD",
        "physical_examination": "Anxious, diaphoretic. HR 88 bpm irregular. ECG: ST depression leads V4-V6.",
        "pain_score_reassessment": 5,
        "provisional_diagnosis": "Unstable Angina / NSTEMI",
        "expected_cost": 75000.0,
        "proposed_plan": "Heparin infusion, dual antiplatelet therapy, coronary angiography planned",
    },
    # Discharged admissions
    {
        "patient_idx": 1, "student_idx": 2, "faculty_idx": 2,
        "department": "Pediatrics", "ward": "General Ward B", "bed_number": "B-05",
        "reason": "High fever and dehydration for 3 days in a child",
        "diagnosis": "Viral Gastroenteritis", "status": "Discharged", "days_ago": 10, "discharge_days_ago": 5,
        "accompanying_by": "Father - Ramesh Devi", "accompanied_by_contact": "+91 98765 22222",
        "airway_patent": True, "breathing_adequate": True, "pulse_present": True, "capillary_refill_time": 3.5,
        "bp_admission": "100/70", "heart_rate_admission": "110", "resp_rate_admission": "22",
        "spo2_admission": "98", "temp_admission": "102.4", "weight_admission": "48",
        "gcs_eye": 4, "gcs_verbal": 5, "gcs_motor": 6, "cbg": "90", "pain_score": 4,
        "chief_complaints": "Vomiting 8-10 episodes, loose stools, high-grade fever",
        "history_of_present_illness": "3-day history of gastroenteritis symptoms. Unable to tolerate orally.",
        "physical_examination": "Dehydrated, sunken eyes, reduced skin turgor. Abdomen soft, mildly tender.",
        "provisional_diagnosis": "Acute gastroenteritis with moderate dehydration",
        "expected_cost": 12000.0,
        "proposed_plan": "IV fluids, antiemetics, electrolyte correction",
        "discharge_summary": "Patient recovered well with IV fluids and supportive care. Tolerating orally at discharge.",
        "discharge_instructions": "Continue oral rehydration. Follow up in 1 week. Avoid outside food.",
    },
    {
        "patient_idx": 4, "student_idx": 0, "faculty_idx": 0,
        "department": "Internal Medicine", "ward": "General Ward A", "bed_number": "A-07",
        "reason": "Diabetic ketoacidosis - vomiting, polyuria, altered sensorium",
        "diagnosis": "Uncontrolled Type 2 Diabetes Mellitus with DKA", "status": "Discharged",
        "days_ago": 15, "discharge_days_ago": 8,
        "airway_patent": True, "breathing_adequate": True, "pulse_present": True, "capillary_refill_time": 3.0,
        "bp_admission": "100/65", "heart_rate_admission": "114", "resp_rate_admission": "26",
        "spo2_admission": "95", "temp_admission": "99.1", "weight_admission": "82",
        "gcs_eye": 3, "gcs_verbal": 4, "gcs_motor": 5, "cbg": "480", "pain_score": 5,
        "drug_allergy": "Sulfonamides", "chief_complaints": "Vomiting, excessive thirst, frequent urination, drowsiness",
        "history_of_present_illness": "Known T2DM x8 years. Missed medications for 4 days. RBS 480 mg/dL at presentation.",
        "past_medical_history": "Type 2 DM x8 years, Hypertension x5 years",
        "medication_history": "Tab Metformin 1g BD, Tab Glimepiride 2mg OD (missed for 4 days)",
        "physical_examination": "Kussmaul breathing, fruity odour in breath. GCS E3V4M5.",
        "provisional_diagnosis": "DKA secondary to medication non-compliance",
        "expected_cost": 35000.0,
        "proposed_plan": "Insulin protocol, IV fluids, bicarb correction, close monitoring",
        "discharge_summary": "Blood sugar levels stabilized. Insulin regimen adjusted. Patient counselled on medication compliance.",
        "discharge_instructions": "Monitor blood glucose daily. Follow strict diabetic diet. Review in 2 weeks.",
    },
]

# Pending student admission requests
PENDING_ADMISSIONS = [
    {
        "patient_idx": 2, "student_idx": 0, "faculty_idx": 0,
        "department": "Internal Medicine", "ward": "General Ward A", "bed_number": "A-15",
        "reason": "Persistent high blood pressure unresponsive to medication adjustment",
        "provisional_diagnosis": "Resistant Hypertension",
        "chief_complaints": "Headache and dizziness despite medication",
        "bp_admission": "168/104", "heart_rate_admission": "86", "spo2_admission": "98",
        "gcs_eye": 4, "gcs_verbal": 5, "gcs_motor": 6, "pain_score": 5,
    },
    {
        "patient_idx": 5, "student_idx": 1, "faculty_idx": 1,
        "department": "Cardiology", "ward": "General Ward C", "bed_number": "C-08",
        "reason": "Recurring chest pain and shortness of breath during physical activity",
        "provisional_diagnosis": "Chronic Stable Angina",
        "chief_complaints": "Exertional chest pain for 2 weeks",
        "bp_admission": "138/88", "heart_rate_admission": "78", "spo2_admission": "97",
        "gcs_eye": 4, "gcs_verbal": 5, "gcs_motor": 6, "pain_score": 6,
    },
]

# Case records for all 10 patients
CASE_RECORDS_DATA = [
    # Patient 1 - Rajesh Kumar (Hypertension)
    {"patient_idx": 0, "student_idx": 0, "faculty_idx": 0, "department": "Internal Medicine",
     "type": "Physical Examination", "procedure_name": "General Examination",
     "findings": "BP 168/104 mmHg. Regular pulse 88 bpm. No edema. Grade II hypertensive retinopathy on fundoscopy.",
     "diagnosis": "Essential Hypertension Stage 2", "treatment": "Antihypertensive therapy intensification",
     "status": "Approved", "grade": "A", "days_ago": 5},
    {"patient_idx": 0, "student_idx": 0, "faculty_idx": 0, "department": "Internal Medicine",
     "type": "Follow-up", "procedure_name": "BP Monitoring Review",
     "findings": "BP improved to 145/92 mmHg after intensified therapy. Patient compliant.",
     "diagnosis": "Hypertension - improving", "treatment": "Continue current regimen",
     "status": "Approved", "grade": "B+", "days_ago": 2},
    # Patient 2 - Sunita Devi (Diabetes)
    {"patient_idx": 1, "student_idx": 1, "faculty_idx": 0, "department": "Internal Medicine",
     "type": "Physical Examination", "procedure_name": "Diabetic Review",
     "findings": "RBS 280 mg/dL. HbA1c 9.2%. No diabetic foot lesions. Mild peripheral neuropathy.",
     "diagnosis": "Type 2 Diabetes Mellitus - Uncontrolled", "treatment": "Insulin sliding scale added",
     "status": "Approved", "grade": "A-", "days_ago": 7},
    {"patient_idx": 1, "student_idx": 1, "faculty_idx": 0, "department": "Internal Medicine",
     "type": "Counselling", "procedure_name": "Diabetic Education",
     "findings": "Patient counselled on diet, exercise, and medication compliance.",
     "diagnosis": "T2DM - Education provided", "treatment": "Lifestyle modification",
     "status": "Pending", "days_ago": 1},
    # Patient 3 - Mohammed Ali (COPD)
    {"patient_idx": 2, "student_idx": 2, "faculty_idx": 0, "department": "Internal Medicine",
     "type": "Physical Examination", "procedure_name": "Respiratory Assessment",
     "findings": "Reduced air entry bilaterally. Wheeze +. SpO2 93% on room air. FEV1/FVC ratio 0.65.",
     "diagnosis": "COPD Stage II", "treatment": "Bronchodilator therapy, pulmonary rehabilitation",
     "status": "Approved", "grade": "B+", "days_ago": 4},
    # Patient 4 - Priya Lakshmi (Cardiac)
    {"patient_idx": 3, "student_idx": 0, "faculty_idx": 1, "department": "Cardiology",
     "type": "Physical Examination", "procedure_name": "Cardiac Assessment",
     "findings": "ECG: ST depression V4-V6. Troponin I: 0.08 ng/mL (elevated). Echo: EF 52%, mild LV dysfunction.",
     "diagnosis": "NSTEMI", "treatment": "Dual antiplatelet, heparin, statin, beta-blocker",
     "status": "Approved", "grade": "A", "days_ago": 1},
    # Patient 5 - Ganesh Babu (Diabetes)
    {"patient_idx": 4, "student_idx": 1, "faculty_idx": 0, "department": "Internal Medicine",
     "type": "Physical Examination", "procedure_name": "Diabetic Foot Exam",
     "findings": "Grade 1 diabetic foot ulcer on right plantar surface. Peripheral pulses intact.",
     "diagnosis": "Diabetic foot ulcer Grade 1", "treatment": "Wound dressing, antibiotics, offloading",
     "status": "Approved", "grade": "B", "days_ago": 8},
    # Patient 6 - Kavitha Rani (Anaemia)
    {"patient_idx": 5, "student_idx": 2, "faculty_idx": 1, "department": "Cardiology",
     "type": "Physical Examination", "procedure_name": "Cardiovascular Risk Assessment",
     "findings": "BP 148/94. Total cholesterol 240 mg/dL. LDL 160 mg/dL. Mild exertional dyspnoea.",
     "diagnosis": "Dyslipidaemia with hypertension", "treatment": "Statin therapy, dietary counselling",
     "status": "Approved", "grade": "B+", "days_ago": 6},
    # Patient 7 - Suresh Pandian (Thyroid)
    {"patient_idx": 6, "student_idx": 3, "faculty_idx": 2, "department": "Pediatrics",
     "type": "Physical Examination", "procedure_name": "General Examination",
     "findings": "Weight appropriate. Mild thyroid enlargement noted. TSH 8.2 mIU/L.",
     "diagnosis": "Subclinical Hypothyroidism", "treatment": "Levothyroxine 25mcg OD, repeat TSH in 6 weeks",
     "status": "Pending", "days_ago": 3},
    # Patient 8 - Deepa Murthy (Migraine)
    {"patient_idx": 7, "student_idx": 4, "faculty_idx": 0, "department": "Internal Medicine",
     "type": "Physical Examination", "procedure_name": "Neurological Examination",
     "findings": "Normal neurological exam. No meningeal signs. Characteristic migraine aura described.",
     "diagnosis": "Migraine with aura", "treatment": "Sumatriptan PRN, topiramate prophylaxis",
     "status": "Approved", "grade": "A-", "days_ago": 5},
    # Patient 9 - Vijay Anand (Asthma)
    {"patient_idx": 8, "student_idx": 5, "faculty_idx": 2, "department": "Pediatrics",
     "type": "Physical Examination", "procedure_name": "Pulmonary Function Test Review",
     "findings": "FEV1 78% predicted. Good bronchodilator response. Mild persistent asthma.",
     "diagnosis": "Mild Persistent Asthma", "treatment": "ICS-LABA combination, rescue inhaler PRN",
     "status": "Approved", "grade": "B+", "days_ago": 9},
    # Patient 10 - Revathi Shankar (Anaemia)
    {"patient_idx": 9, "student_idx": 6, "faculty_idx": 0, "department": "Internal Medicine",
     "type": "Physical Examination", "procedure_name": "Anaemia Workup",
     "findings": "Pallor ++. Hb 8.2 g/dL. MCV 68 fL. Microcytic hypochromic. Serum ferritin 6 ng/mL.",
     "diagnosis": "Iron Deficiency Anaemia", "treatment": "IV iron sucrose infusion, dietary advice",
     "status": "Approved", "grade": "A", "days_ago": 4},
    {"patient_idx": 9, "student_idx": 6, "faculty_idx": 0, "department": "Internal Medicine",
     "type": "Follow-up", "procedure_name": "Anaemia Follow-up",
     "findings": "Hb improved to 9.8 g/dL after 2 weeks of IV iron. Patient less symptomatic.",
     "diagnosis": "IDA - Responding to treatment", "treatment": "Continue oral iron, repeat CBC in 4 weeks",
     "status": "Pending", "days_ago": 1},
]

# Form definitions for case record entry
FORM_DEFINITIONS_DATA = [
    {
        "slug": "internal-medicine-history-physical",
        "name": "History & Physical Examination",
        "description": "Complete initial history and physical assessment for internal medicine patients",
        "form_type": "CASE_RECORD",
        "department": "Internal Medicine",
        "procedure_name": "General Examination",
        "sort_order": 1,
        "fields": [
            {"id": "chief_complaint", "label": "Chief Complaint", "type": "textarea", "required": True, "placeholder": "Brief description of presenting complaint"},
            {"id": "history_present_illness", "label": "History of Present Illness", "type": "textarea", "required": True, "placeholder": "Detailed history of current illness"},
            {"id": "past_medical_history", "label": "Past Medical History", "type": "textarea", "required": False, "placeholder": "Previous medical conditions, surgeries, hospitalizations"},
            {"id": "medications", "label": "Current Medications", "type": "textarea", "required": False, "placeholder": "List all current medications with dosages"},
            {"id": "allergies", "label": "Known Allergies", "type": "text", "required": False, "placeholder": "Drug allergies, food allergies"},
            {"id": "vital_signs", "label": "Vital Signs", "type": "text", "required": True, "placeholder": "BP, HR, RR, Temp, SpO2"},
            {"id": "general_appearance", "label": "General Appearance", "type": "textarea", "required": True, "placeholder": "Patient's general condition, consciousness level"},
            {"id": "systemic_examination", "label": "Systemic Examination", "type": "textarea", "required": True, "placeholder": "CVS, RS, Abdomen, CNS findings"},
            {"id": "provisional_diagnosis", "label": "Provisional Diagnosis", "type": "text", "required": True, "placeholder": "Working diagnosis"},
            {"id": "treatment_plan", "label": "Treatment Plan", "type": "textarea", "required": True, "placeholder": "Investigations and management plan"},
        ],
    },
    {
        "slug": "internal-medicine-progress-note",
        "name": "Progress Note",
        "description": "Daily progress documentation for admitted patients",
        "form_type": "CASE_RECORD",
        "department": "Internal Medicine",
        "procedure_name": "Progress Note",
        "sort_order": 2,
        "fields": [
            {"id": "subjective", "label": "Subjective", "type": "textarea", "required": True, "placeholder": "Patient complaints and subjective symptoms"},
            {"id": "objective", "label": "Objective", "type": "textarea", "required": True, "placeholder": "Vital signs, examination findings, lab results"},
            {"id": "assessment", "label": "Assessment", "type": "textarea", "required": True, "placeholder": "Current diagnosis and patient status"},
            {"id": "plan", "label": "Plan", "type": "textarea", "required": True, "placeholder": "Management plan and follow-up"},
        ],
    },
    {
        "slug": "cardiology-cardiac-assessment",
        "name": "Cardiac Assessment",
        "description": "Comprehensive cardiac evaluation for cardiology patients",
        "form_type": "CASE_RECORD",
        "department": "Cardiology",
        "procedure_name": "Cardiac Evaluation",
        "sort_order": 1,
        "fields": [
            {"id": "chest_pain_type", "label": "Chest Pain Character", "type": "text", "required": True, "placeholder": "Crushing/Sharp/Dull, radiation pattern"},
            {"id": "onset_duration", "label": "Onset & Duration", "type": "text", "required": True, "placeholder": "When did symptoms start, duration"},
            {"id": "risk_factors", "label": "Cardiac Risk Factors", "type": "textarea", "required": True, "placeholder": "DM, HTN, smoking, family history, dyslipidemia"},
            {"id": "ecg_findings", "label": "ECG Findings", "type": "textarea", "required": True, "placeholder": "Rhythm, ST changes, Q waves, conduction abnormalities"},
            {"id": "cardiac_markers", "label": "Cardiac Biomarkers", "type": "text", "required": False, "placeholder": "Troponin I, CK-MB levels"},
            {"id": "echo_findings", "label": "Echo Findings (if done)", "type": "textarea", "required": False, "placeholder": "LV function, wall motion, valves"},
            {"id": "diagnosis", "label": "Cardiac Diagnosis", "type": "text", "required": True, "placeholder": "STEMI/NSTEMI/Unstable Angina/etc"},
            {"id": "intervention", "label": "Intervention/Management", "type": "textarea", "required": True, "placeholder": "Medical management, PCI, CABG plan"},
        ],
    },
    {
        "slug": "pediatrics-growth-development",
        "name": "Growth & Development Assessment",
        "description": "Pediatric growth monitoring and developmental milestones",
        "form_type": "CASE_RECORD",
        "department": "Pediatrics",
        "procedure_name": "Well Child Visit",
        "sort_order": 1,
        "fields": [
            {"id": "age", "label": "Age (months/years)", "type": "text", "required": True, "placeholder": "Child's exact age"},
            {"id": "weight", "label": "Weight (kg)", "type": "text", "required": True, "placeholder": "Current weight"},
            {"id": "height", "label": "Height/Length (cm)", "type": "text", "required": True, "placeholder": "Current height/length"},
            {"id": "head_circumference", "label": "Head Circumference (cm)", "type": "text", "required": False, "placeholder": "For children <2 years"},
            {"id": "growth_percentile", "label": "Growth Percentile", "type": "text", "required": True, "placeholder": "Weight-for-age, height-for-age percentiles"},
            {"id": "developmental_milestones", "label": "Developmental Milestones", "type": "textarea", "required": True, "placeholder": "Motor, language, social milestones achieved"},
            {"id": "immunization_status", "label": "Immunization Status", "type": "textarea", "required": True, "placeholder": "Vaccines received and pending"},
            {"id": "nutritional_assessment", "label": "Nutritional Assessment", "type": "textarea", "required": True, "placeholder": "Feeding pattern, dietary intake"},
            {"id": "concerns", "label": "Parental Concerns", "type": "textarea", "required": False, "placeholder": "Any concerns raised by parents"},
            {"id": "advice", "label": "Advice Given", "type": "textarea", "required": True, "placeholder": "Counselling and follow-up plan"},
        ],
    },
    {
        "slug": "pediatrics-acute-illness",
        "name": "Pediatric Acute Illness",
        "description": "Assessment for acute pediatric presentations",
        "form_type": "CASE_RECORD",
        "department": "Pediatrics",
        "procedure_name": "Acute Care",
        "sort_order": 2,
        "fields": [
            {"id": "presenting_complaint", "label": "Presenting Complaint", "type": "text", "required": True, "placeholder": "Main symptom (fever, cough, vomiting, etc)"},
            {"id": "duration", "label": "Duration of Illness", "type": "text", "required": True, "placeholder": "How long has child been sick"},
            {"id": "associated_symptoms", "label": "Associated Symptoms", "type": "textarea", "required": True, "placeholder": "Other symptoms present"},
            {"id": "feeding_urine", "label": "Feeding & Urine Output", "type": "text", "required": True, "placeholder": "Intake and output status"},
            {"id": "vitals", "label": "Vital Signs", "type": "text", "required": True, "placeholder": "HR, RR, Temp, SpO2, BP (if applicable)"},
            {"id": "hydration_status", "label": "Hydration Status", "type": "text", "required": True, "placeholder": "Well hydrated/Mild/Moderate/Severe dehydration"},
            {"id": "examination_findings", "label": "Examination Findings", "type": "textarea", "required": True, "placeholder": "Relevant clinical findings"},
            {"id": "investigations", "label": "Investigations", "type": "textarea", "required": False, "placeholder": "Labs, imaging ordered/results"},
            {"id": "diagnosis", "label": "Diagnosis", "type": "text", "required": True, "placeholder": "Clinical diagnosis"},
            {"id": "management", "label": "Management Plan", "type": "textarea", "required": True, "placeholder": "Treatment given and follow-up"},
        ],
    },
    {
        "slug": "cardiology-hypertension-review",
        "name": "Hypertension Follow-up",
        "description": "Follow-up assessment for hypertensive patients",
        "form_type": "CASE_RECORD",
        "department": "Cardiology",
        "procedure_name": "BP Monitoring Review",
        "sort_order": 2,
        "fields": [
            {"id": "current_bp", "label": "Current Blood Pressure", "type": "text", "required": True, "placeholder": "Systolic/Diastolic mmHg"},
            {"id": "home_readings", "label": "Home BP Readings", "type": "textarea", "required": False, "placeholder": "Patient's home monitoring log"},
            {"id": "medication_compliance", "label": "Medication Compliance", "type": "text", "required": True, "placeholder": "Good/Fair/Poor, reasons for non-compliance"},
            {"id": "current_medications", "label": "Current Antihypertensives", "type": "textarea", "required": True, "placeholder": "List of BP medications with doses"},
            {"id": "side_effects", "label": "Side Effects", "type": "textarea", "required": False, "placeholder": "Any drug-related adverse effects"},
            {"id": "lifestyle_modifications", "label": "Lifestyle Changes", "type": "textarea", "required": True, "placeholder": "Diet, exercise, salt restriction, weight"},
            {"id": "target_organ_damage", "label": "Target Organ Assessment", "type": "textarea", "required": False, "placeholder": "Renal function, retinopathy, LVH status"},
            {"id": "plan", "label": "Management Plan", "type": "textarea", "required": True, "placeholder": "Continue/modify medications, follow-up interval"},
        ],
    },
    {
        "slug": "internal-medicine-diabetes-follow-up",
        "name": "Diabetes Management Review",
        "description": "Follow-up for diabetic patients with glycemic control assessment",
        "form_type": "CASE_RECORD",
        "department": "Internal Medicine",
        "procedure_name": "Diabetes Review",
        "sort_order": 3,
        "fields": [
            {"id": "fasting_glucose", "label": "Fasting Blood Glucose", "type": "text", "required": True, "placeholder": "mg/dL"},
            {"id": "postprandial_glucose", "label": "Postprandial Glucose", "type": "text", "required": False, "placeholder": "2-hour post-meal"},
            {"id": "hba1c", "label": "HbA1c", "type": "text", "required": False, "placeholder": "% (if available)"},
            {"id": "hypoglycemia_episodes", "label": "Hypoglycemia Episodes", "type": "text", "required": True, "placeholder": "Frequency of low sugar episodes"},
            {"id": "current_regimen", "label": "Current Diabetes Regimen", "type": "textarea", "required": True, "placeholder": "Oral agents, insulin doses"},
            {"id": "diet_exercise", "label": "Diet & Exercise Compliance", "type": "textarea", "required": True, "placeholder": "Dietary adherence and physical activity"},
            {"id": "foot_examination", "label": "Foot Examination", "type": "text", "required": True, "placeholder": "Pulses, sensation, ulcers, calluses"},
            {"id": "complications_screening", "label": "Complications Screening", "type": "textarea", "required": False, "placeholder": "Retinopathy, nephropathy, neuropathy status"},
            {"id": "adjustments", "label": "Treatment Adjustments", "type": "textarea", "required": True, "placeholder": "Changes to medications or insulin"},
        ],
    },
    {
        "slug": "cardiology-heart-failure-review",
        "name": "Heart Failure Follow-up",
        "description": "Monitoring for patients with congestive heart failure",
        "form_type": "CASE_RECORD",
        "department": "Cardiology",
        "procedure_name": "Heart Failure Review",
        "sort_order": 3,
        "fields": [
            {"id": "nyha_class", "label": "NYHA Functional Class", "type": "text", "required": True, "placeholder": "I / II / III / IV"},
            {"id": "dyspnea", "label": "Dyspnea Status", "type": "text", "required": True, "placeholder": "At rest / On exertion / PND / Orthopnea"},
            {"id": "weight_change", "label": "Weight Change", "type": "text", "required": True, "placeholder": "Current weight vs last visit"},
            {"id": "edema", "label": "Peripheral Edema", "type": "text", "required": True, "placeholder": "Present/Absent, grade if present"},
            {"id": "jvp", "label": "JVP", "type": "text", "required": True, "placeholder": "Elevated/Normal"},
            {"id": "lung_sounds", "label": "Lung Auscultation", "type": "text", "required": True, "placeholder": "Crepitations/Clear"},
            {"id": "medications", "label": "HF Medications", "type": "textarea", "required": True, "placeholder": "Diuretics, ACEi/ARB, beta-blockers, doses"},
            {"id": "fluid_restriction", "label": "Fluid Restriction Compliance", "type": "text", "required": True, "placeholder": "Good/Fair/Poor"},
            {"id": "salt_restriction", "label": "Salt Restriction", "type": "text", "required": True, "placeholder": "Adhering / Not adhering"},
            {"id": "plan", "label": "Management Adjustments", "type": "textarea", "required": True, "placeholder": "Diuretic titration, device therapy, follow-up"},
        ],
    },
]


async def seed():
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # ── Admin ────────────────────────────────────────
        admin_user_id = uid()
        db.add(User(
            id=admin_user_id,
            username="admin",
            email="admin@saveetha.com",
            password_hash=get_password_hash("admin"),
            role=UserRole.ADMIN,
        ))
        # Additional admin user with short credentials
        db.add(User(
            id=uid(),
            username="a",
            email="a@saveetha.com",
            password_hash=get_password_hash("a"),
            role=UserRole.ADMIN,
        ))

        # ── Reception ───────────────────────────────────
        db.add(User(
            id=uid(),
            username="r1",
            email="r1@saveetha.com",
            password_hash=get_password_hash("r1"),
            role=UserRole.RECEPTION,
        ))
        db.add(User(
            id=uid(),
            username="r",
            email="r@saveetha.com",
            password_hash=get_password_hash("r"),
            role=UserRole.RECEPTION,
        ))

        # ── Doctors ──────────────────────────────────────
        for d in DOCTORS:
            user_id = uid()
            db.add(User(
                id=user_id,
                username=d["username"],
                email=d["email"],
                password_hash=get_password_hash(d["password"]),
                role=UserRole.FACULTY,
            ))
            db.add(Faculty(
                id=uid(),
                faculty_id=d["faculty_id"],
                user_id=user_id,
                name=d["name"],
                department=d["department"],
                specialty=d["specialty"],
                availability_status="Available",
            ))

        # ── Students ─────────────────────────────────────
        for s in STUDENTS:
            user_id = uid()
            db.add(User(
                id=user_id,
                username=s["username"],
                email=s["email"],
                password_hash=get_password_hash(s["password"]),
                role=UserRole.STUDENT,
            ))
            db.add(Student(
                id=uid(),
                student_id=s["student_id"],
                user_id=user_id,
                name=s["name"],
                year=s["year"],
                semester=s["semester"],
                program=s["program"],
                gpa=s["gpa"],
            ))

        # ── Nurses ───────────────────────────────────────
        for n in NURSES:
            user_id = uid()
            db.add(User(
                id=user_id,
                username=n["username"],
                email=n["email"],
                password_hash=get_password_hash(n["password"]),
                role=UserRole.NURSE,
            ))
            db.add(Nurse(
                id=uid(),
                nurse_id=n["nurse_id"],
                user_id=user_id,
                name=n["name"],
                phone=n["phone"],
                email=n["email"],
                has_selected_station=0,  # Requires first-time setup
            ))

        # ── Patients ─────────────────────────────────────
        for p in PATIENTS:
            user_id = uid()
            db.add(User(
                id=user_id,
                username=p["username"],
                email=p["email"],
                password_hash=get_password_hash(p["password"]),
                role=UserRole.PATIENT,
            ))
            db.add(Patient(
                id=uid(),
                patient_id=p["patient_id"],
                user_id=user_id,
                name=p["name"],
                date_of_birth=p["dob"],
                gender=p["gender"],
                blood_group=p["blood_group"],
                phone=p["phone"],
                email=p["email"],
                address=p["address"],
                category=PatientCategory.GENERAL,
            ))

        # ── Departments ──────────────────────────────────
        for dept in DEPARTMENTS:
            db.add(Department(
                id=uid(),
                name=dept["name"],
                code=dept["code"],
                description=dept["description"],
            ))

        # ── Programmes ───────────────────────────────────
        for prog in PROGRAMMES:
            db.add(Programme(
                id=uid(),
                name=prog["name"],
                code=prog["code"],
                description=prog["description"],
                degree_type=prog["degree_type"],
                duration_years=prog["duration_years"],
            ))

        # ── Form Definitions ─────────────────────────────
        for form_def in FORM_DEFINITIONS_DATA:
            db.add(FormDefinition(
                id=uid(),
                slug=form_def["slug"],
                name=form_def["name"],
                description=form_def.get("description", ""),
                form_type=form_def["form_type"],
                department=form_def.get("department"),
                procedure_name=form_def.get("procedure_name"),
                fields=form_def["fields"],
                sort_order=form_def.get("sort_order", 0),
                is_active=True,
            ))

        # Flush to get IDs
        await db.flush()

        # ── Fetch all student and patient records ────────
        from sqlalchemy import select
        stu_result = await db.execute(select(Student))
        all_students = stu_result.scalars().all()
        pat_result = await db.execute(select(Patient))
        all_patients = pat_result.scalars().all()
        fac_result = await db.execute(select(Faculty))
        all_faculty = fac_result.scalars().all()

        student_map = {s.student_id: s for s in all_students}
        patient_map = {p.patient_id: p for p in all_patients}
        faculty_map = {f.faculty_id: f for f in all_faculty}

        # ── Student-Patient Assignments ──────────────────
        # Assign 3-4 patients to each student (round-robin with overlap)
        for i, s in enumerate(all_students):
            for j in range(3):
                pat_idx = (i * 2 + j) % len(all_patients)
                p = all_patients[pat_idx]
                db.add(StudentPatientAssignment(
                    id=uid(),
                    student_id=s.id,
                    patient_id=p.id,
                    assigned_date=datetime.utcnow() - timedelta(days=random.randint(5, 30)),
                    status="Active",
                ))

        # ── Student Department Permissions ──────────────
        # Grant some departments to each student (granted by first faculty)
        PERMISSION_DEPARTMENTS = [
            "Internal Medicine", "Pediatrics", "Surgery",
            "OB/GYN", "Psychiatry", "Emergency Medicine",
        ]
        granter = all_faculty[0]  # Dr. Arun Kumar
        for i, s in enumerate(all_students):
            # Give each student 2-4 departments based on their year
            year = s.year if hasattr(s, 'year') and s.year else 2
            num_depts = min(year + 1, len(PERMISSION_DEPARTMENTS))
            for dept in PERMISSION_DEPARTMENTS[:num_depts]:
                db.add(StudentPermission(
                    id=uid(),
                    student_id=s.id,
                    department=dept,
                    granted_by_faculty_id=granter.id,
                ))

        # ── Sample Vitals for first 5 patients ──────────
        for p in all_patients[:5]:
            for day_offset in range(10):
                db.add(Vital(
                    id=uid(),
                    patient_id=p.id,
                    recorded_at=datetime.utcnow() - timedelta(days=day_offset, hours=random.randint(0, 8)),
                    recorded_by="Dr. Arun Kumar",
                    systolic_bp=random.randint(110, 140),
                    diastolic_bp=random.randint(65, 90),
                    heart_rate=random.randint(60, 100),
                    respiratory_rate=random.randint(14, 22),
                    temperature=round(random.uniform(97.5, 99.5), 1),
                    oxygen_saturation=random.randint(94, 100),
                    weight=round(random.uniform(120, 200), 1),
                    blood_glucose=random.randint(80, 140),
                    creatinine=round(random.uniform(0.8, 1.4), 2),
                    urea=round(random.uniform(18, 38), 1),
                    sodium=round(random.uniform(134, 142), 1),
                    potassium=round(random.uniform(3.6, 4.8), 1),
                    sgot=round(random.uniform(20, 46), 1),
                    sgpt=round(random.uniform(18, 52), 1),
                    hemoglobin=round(random.uniform(10.8, 14.6), 1),
                    wbc=round(random.uniform(5.4, 11.2), 1),
                    platelet=round(random.uniform(180, 330), 1),
                    rbc=round(random.uniform(3.8, 5.1), 1),
                    hct=round(random.uniform(34, 44), 1),
                ))

        # ── Sample Medical Alerts ────────────────────────
        alert_data = [
            ("Penicillin Allergy", "ALLERGY", "HIGH"),
            ("Latex Sensitivity", "ALLERGY", "MEDIUM"),
            ("Diabetic", "CONDITION", "HIGH"),
            ("Hypertension", "CONDITION", "MEDIUM"),
            ("Asthma", "CONDITION", "MEDIUM"),
        ]
        for i, p in enumerate(all_patients[:5]):
            t, ty, sev = alert_data[i]
            db.add(MedicalAlert(
                id=uid(),
                patient_id=p.id,
                type=ty,
                severity=sev,
                title=t,
                is_active=True,
                added_by="Dr. Arun Kumar",
                added_at=datetime.utcnow() - timedelta(days=random.randint(1, 15)),
            ))

        # ── Sample Prescriptions for first 3 patients ────
        rx_data = [
            ("Amoxicillin", "500mg", "Three times daily", "7 days"),
            ("Lisinopril", "10mg", "Once daily", "30 days"),
            ("Metformin", "500mg", "Twice daily", "30 days"),
        ]
        for i, p in enumerate(all_patients[:3]):
            rx_id = uid()
            name, dose, freq, dur = rx_data[i]
            db.add(Prescription(
                id=rx_id,
                prescription_id=f"RX-2025-{str(i+1).zfill(4)}",
                patient_id=p.id,
                date=datetime.utcnow() - timedelta(days=random.randint(1, 10)),
                doctor="Dr. Arun Kumar",
                department="Internal Medicine",
                status=PrescriptionStatus.ACTIVE,
                hospital_name="SMC Hospital",
            ))
            db.add(PrescriptionMedication(
                id=uid(),
                prescription_id=rx_id,
                name=name,
                dosage=dose,
                frequency=freq,
                duration=dur,
                instructions="Take with food",
                start_date=date.today().isoformat(),
                end_date=(date.today() + timedelta(days=int(dur.split()[0]))).isoformat(),
            ))

        # ── Set primary diagnosis for first 3 patients ───
        diagnoses = [
            "Essential Hypertension",
            "Type 2 Diabetes Mellitus",
            "Acute Bronchitis",
        ]
        for i, p in enumerate(all_patients[:3]):
            p.primary_diagnosis = diagnoses[i]
            p.diagnosis_doctor = "Dr. Arun Kumar"
            p.diagnosis_date = date.today().isoformat()
            p.diagnosis_time = "09:30 AM"

        # ── Clinics ──────────────────────────────────────
        # Uncomment faculty creation above to enable this
        fac_result = await db.execute(select(Faculty))
        all_faculty = fac_result.scalars().all()
        faculty_list = list(all_faculty)

        clinic_objs = []
        for c in CLINICS:
            clinic = Clinic(
                id=uid(),
                name=c["name"],
                block=c.get("block"),
                clinic_type=c.get("clinic_type", "General"),
                department=c["department"],
                location=c.get("location", ""),
                faculty_id=None,  # Set to None for now, or uncomment faculty creation above to assign faculty
                is_active=True,
            )
            db.add(clinic)
            clinic_objs.append(clinic)
        await db.flush()

        # ── Labs ─────────────────────────────────────────
        from app.models.lab import Lab
        lab_objs = []
        for lab_data in LABS:
            lab = Lab(
                id=uid(),
                name=lab_data["name"],
                block=lab_data.get("block"),
                lab_type=lab_data.get("lab_type", "General"),
                department=lab_data["department"],
                location=lab_data.get("location", ""),
                contact_phone=lab_data.get("contact_phone"),
                operating_hours=lab_data.get("operating_hours"),
                is_active=True,
            )
            db.add(lab)
            lab_objs.append(lab)
        await db.flush()

        # ── Clinic Appointments ──────────────────────────
        # Uncomment patient creation above to enable this
        from datetime import datetime as dt
        today = datetime.combine(date.today(), datetime.min.time())
        for ca in CLINIC_APPOINTMENTS:
            clinic = clinic_objs[ca["clinic_idx"]]
            patient = all_patients[ca["patient_idx"]]
            db.add(ClinicAppointment(
                id=uid(),
                clinic_id=clinic.id,
                patient_id=patient.id,
                appointment_date=today,
                appointment_time=ca["time"],
                provider_name=ca["provider"],
                status=ca["status"],
            ))

        # ── Admissions (Active + Discharged) ────────────
        active_admission_map = {}  # patient_idx -> Admission object for IO/SOAP seeding
        for a in ADMISSIONS_DATA:
            patient = all_patients[a["patient_idx"]]
            student = all_students[a.get("student_idx", 0)]
            faculty = faculty_list[a.get("faculty_idx", 0)]
            adm_date = datetime.utcnow() - timedelta(days=a["days_ago"])
            discharge_date = None
            if a["status"] == "Discharged" and "discharge_days_ago" in a:
                discharge_date = datetime.utcnow() - timedelta(days=a["discharge_days_ago"])
            follow_up = discharge_date + timedelta(days=14) if discharge_date else None
            adm_id = uid()
            db.add(Admission(
                id=adm_id,
                patient_id=patient.id,
                admission_date=adm_date,
                discharge_date=discharge_date,
                department=a["department"],
                ward=a["ward"],
                bed_number=a["bed_number"],
                attending_doctor=faculty.name,
                reason=a["reason"],
                diagnosis=a.get("diagnosis"),
                status=a["status"],
                submitted_by_student_id=student.id,
                faculty_approver_id=faculty.id,
                # Triage
                accompanied_by=a.get("accompanied_by"),
                accompanied_by_contact=a.get("accompanied_by_contact"),
                airway_patent=a.get("airway_patent", True),
                breathing_adequate=a.get("breathing_adequate", True),
                pulse_present=a.get("pulse_present", True),
                capillary_refill_time=a.get("capillary_refill_time"),
                # Vitals at admission
                bp_admission=a.get("bp_admission"),
                heart_rate_admission=a.get("heart_rate_admission"),
                resp_rate_admission=a.get("resp_rate_admission"),
                spo2_admission=a.get("spo2_admission"),
                temp_admission=a.get("temp_admission"),
                weight_admission=a.get("weight_admission"),
                # GCS
                gcs_eye=a.get("gcs_eye"),
                gcs_verbal=a.get("gcs_verbal"),
                gcs_motor=a.get("gcs_motor"),
                cbg=a.get("cbg"),
                pain_score=a.get("pain_score"),
                # Clinical history
                drug_allergy=a.get("drug_allergy"),
                menstrual_history=a.get("menstrual_history"),
                identification_marks=a.get("identification_marks"),
                chief_complaints=a.get("chief_complaints"),
                history_of_present_illness=a.get("history_of_present_illness"),
                past_medical_history=a.get("past_medical_history"),
                medication_history=a.get("medication_history"),
                surgical_history=a.get("surgical_history"),
                physical_examination=a.get("physical_examination"),
                # Assessment & plan
                pain_score_reassessment=a.get("pain_score_reassessment"),
                provisional_diagnosis=a.get("provisional_diagnosis"),
                expected_cost=a.get("expected_cost"),
                proposed_plan=a.get("proposed_plan"),
                # Discharge
                discharge_summary=a.get("discharge_summary"),
                discharge_instructions=a.get("discharge_instructions"),
                follow_up_date=follow_up,
            ))
            if a["status"] == "Active":
                active_admission_map[a["patient_idx"]] = (adm_id, patient.id)

        await db.flush()

        # ── IO Events for Active Admissions ──────────────
        io_events_data = {
            0: [  # Rajesh Kumar - Hypertension
                {"time": "06:00", "type": "IV Input", "description": "NS 0.9% 500mL",        "amount": 500, "by": "Nurse Kavitha"},
                {"time": "08:00", "type": "Drugs",    "description": "Tab Amlodipine 10mg",   "amount": None, "by": "Nurse Kavitha"},
                {"time": "08:30", "type": "Food",     "description": "Breakfast - soft diet",  "amount": 300, "by": "Nurse Lakshmi"},
                {"time": "10:00", "type": "Urine",    "description": "Catheter urine output",  "amount": 350, "by": "Nurse Kavitha"},
                {"time": "12:00", "type": "Drugs",    "description": "Inj. Labetalol 50mg IV", "amount": None, "by": "Nurse Kavitha"},
                {"time": "12:30", "type": "Food",     "description": "Lunch - low-salt diet",  "amount": 400, "by": "Nurse Lakshmi"},
                {"time": "14:00", "type": "Stool",    "description": "Stool - normal",         "amount": None, "by": "Nurse Lakshmi"},
                {"time": "14:00", "type": "IV Input", "description": "RL 500mL",               "amount": 500, "by": "Nurse Kavitha"},
                {"time": "16:00", "type": "Urine",    "description": "Spontaneous urine",      "amount": 280, "by": "Nurse Kavitha"},
                {"time": "18:00", "type": "Food",     "description": "Evening snack",          "amount": 150, "by": "Nurse Lakshmi"},
                {"time": "20:00", "type": "Drugs",    "description": "Tab Telmisartan 40mg",   "amount": None, "by": "Night Nurse"},
            ],
            3: [  # Priya Lakshmi - Cardiac ICU
                {"time": "00:00", "type": "IV Input", "description": "Heparin infusion 1000U/hr", "amount": 50, "by": "ICU Nurse Priya"},
                {"time": "06:00", "type": "IV Input", "description": "NS 0.9% KVO rate",          "amount": 100, "by": "ICU Nurse Priya"},
                {"time": "07:00", "type": "Drugs",    "description": "Tab Aspirin 325mg + Clopidogrel 75mg", "amount": None, "by": "ICU Nurse Priya"},
                {"time": "08:00", "type": "Food",     "description": "Liquid diet only",          "amount": 200, "by": "ICU Nurse Priya"},
                {"time": "10:00", "type": "Urine",    "description": "Catheter urine output",      "amount": 250, "by": "ICU Nurse Priya"},
                {"time": "12:00", "type": "Drugs",    "description": "Inj. GTN 10mcg/min IV",      "amount": None, "by": "ICU Nurse Priya"},
                {"time": "14:00", "type": "Urine",    "description": "Catheter urine output",      "amount": 200, "by": "ICU Nurse Rajan"},
                {"time": "18:00", "type": "IV Input", "description": "NS 0.9% 250mL",             "amount": 250, "by": "ICU Nurse Rajan"},
                {"time": "20:00", "type": "Drugs",    "description": "Tab Atorvastatin 80mg",      "amount": None, "by": "ICU Nurse Rajan"},
                {"time": "22:00", "type": "Urine",    "description": "Catheter urine output",      "amount": 180, "by": "ICU Nurse Rajan"},
            ],
        }

        soap_notes_data = {
            0: {  # Rajesh Kumar
                "subjective": "Patient reports headache improved from 7/10 to 4/10. Blurred vision persisting. No nausea today.",
                "objective": "BP 155/98 mmHg (down from 178/110). HR 84 bpm regular. SpO2 98%. No papilloedema on fundoscopy today.",
                "assessment": "Hypertensive urgency - improving with IV antihypertensives. Target BP <150/90 within 24 hours.",
                "plan": "Continue Labetalol infusion, reduce to oral Amlodipine 10mg OD tomorrow. ECG scheduled. Nephrology consult done - recommends 24hr urine protein.",
                "by": "Ananya Iyer (STU-001)",
                "plan_items": {
                    "drug_notes": "Hold oral antihypertensives if SBP < 120 mmHg. Continue overnight BP monitoring.",
                    "investigation_notes": "Repeat urine protein and renal function panel tomorrow morning.",
                    "diet_notes": "Strict low-salt diet, fluid restriction at 1.5 L/day.",
                    "drugs": [
                        {"id": uid(), "name": "Inj. Labetalol", "dose": "50mg", "route": "IV", "frequency": "STAT / PRN", "status": "pending"},
                        {"id": uid(), "name": "Tab. Amlodipine", "dose": "10mg", "route": "PO", "frequency": "OD", "status": "pending"},
                        {"id": uid(), "name": "Tab. Telmisartan", "dose": "40mg", "route": "PO", "frequency": "HS", "status": "planned"}
                    ],
                    "investigations": [
                        {"id": uid(), "name": "24-hr urine protein", "status": "pending"},
                        {"id": uid(), "name": "ECG repeat", "status": "pending"},
                        {"id": uid(), "name": "Renal function panel", "status": "pending"}
                    ],
                    "diet": [
                        {"id": uid(), "name": "Low sodium diet", "status": "pending"},
                        {"id": uid(), "name": "Fluid restriction 1.5 L/day", "status": "pending"}
                    ]
                },
                "meta": {
                    "author": "Ananya Iyer (STU-001)",
                    "supervisor": "Dr. Arun Kumar",
                    "next_review": "06:00 PM",
                    "timestamp": datetime.utcnow().strftime("%Y-%m-%d %I:%M %p")
                },
            },
            3: {  # Priya Lakshmi
                "subjective": "Patient reports persistent chest tightness and mild breathlessness since morning. States pain is 4/10, dull aching, non-radiating. Sleep was disturbed due to discomfort.",
                "objective": "Patient conscious, oriented, afebrile. Mild pallor present. BP 138/88 mmHg | HR 82 bpm | RR 16/min | SpO2 98% RA | Temp 98.6°F. RBS 168 mg/dL. ECG: Normal sinus rhythm.",
                "assessment": "Primary: Type 2 Diabetes Mellitus - Uncontrolled. Secondary: Essential Hypertension - Stage 2, Mild Diabetic Nephropathy. Improving trend with better sugar control and BP trending towards target.",
                "plan": "Continue insulin, antihypertensives, diabetic diet, and scheduled investigations. Reassess in evening round.",
                "by": "Karthik Rajan (STU-002)",
                "plan_items": {
                    "drug_notes": "Monitor blood sugar before each insulin dose. Escalate antihypertensive review if BP remains above 150/90.",
                    "investigation_notes": "Trend renal profile and capillary blood sugars. Review repeat ECG if chest pain recurs.",
                    "diet_notes": "Diabetic 1800 kcal diet with low sodium restriction.",
                    "drugs": [
                        {"id": uid(), "name": "Inj. Insulin Glargine", "dose": "18U", "route": "SC", "frequency": "HS", "status": "pending"},
                        {"id": uid(), "name": "Tab. Amlodipine", "dose": "5mg", "route": "PO", "frequency": "OD", "status": "pending"},
                        {"id": uid(), "name": "Tab. Pantoprazole", "dose": "40mg", "route": "PO", "frequency": "OD BBF", "status": "completed"}
                    ],
                    "investigations": [
                        {"id": uid(), "name": "RBS 6-hourly monitoring", "status": "pending"},
                        {"id": uid(), "name": "Renal Function Test", "status": "pending"},
                        {"id": uid(), "name": "Fasting lipid profile", "status": "pending"}
                    ],
                    "diet": [
                        {"id": uid(), "name": "Diabetic diet - 1800 kcal/day", "status": "pending"},
                        {"id": uid(), "name": "Low sodium", "status": "pending"}
                    ]
                },
                "meta": {
                    "author": "Dr. Priya Sharma (PG-2, General Medicine)",
                    "supervisor": "Dr. Sarah Johnson (Associate Professor)",
                    "next_review": "06:00 PM",
                    "timestamp": datetime.utcnow().strftime("%Y-%m-%d %I:%M %p")
                },
            },
        }

        equipment_data = {
            3: [  # Priya Lakshmi - ICU (more equipment)
                {"type": "Bedside Monitor", "equipment_id": "MON-ICU-042", "status": "Active", "live_data": {"hr": 80, "bp_sys": 127, "bp_dia": 81, "map": 96, "spo2": 100, "rr": 10, "temp": 98.0, "etco2": 45}},
                {"type": "Pulse Oximeter", "equipment_id": "PO-301",     "status": "Active", "live_data": {"spo2": 98, "pulse": 82}},
                {"type": "Ventilator",      "equipment_id": "VENT-12", "status": "Standby", "live_data": {"pip": 17, "peep": 5, "fio2": 40, "tidal_vol": 524}},
                {"type": "ABG Analyzer",    "equipment_id": "ABG-07",     "status": "Active", "live_data": {"ph": 7.39, "pco2": 43, "po2": 70, "hco3": 20, "lactate": 1.3}},
            ],
            0: [  # Rajesh Kumar - General Ward
                {"type": "Bedside Monitor", "equipment_id": "MON-GW-A12", "status": "Active", "live_data": {"hr": 84, "bp_sys": 155, "bp_dia": 98, "spo2": 98, "rr": 18, "temp": 98.4}},
                {"type": "Pulse Oximeter",  "equipment_id": "OXI-A12",    "status": "Active", "live_data": {"spo2": 98, "pulse": 84}},
            ],
        }

        review_vitals_data = {
            0: [
                {"time": 6, "systolic_bp": 150, "diastolic_bp": 92, "heart_rate": 78, "respiratory_rate": 18, "temperature": 98.4, "oxygen_saturation": 98, "weight": 71.5, "blood_glucose": 122, "creatinine": 1.1, "urea": 24, "sodium": 138, "potassium": 4.1, "sgot": 28, "sgpt": 31, "hemoglobin": 12.8, "wbc": 8.9, "platelet": 242, "rbc": 4.6, "hct": 39.8},
                {"time": 8, "systolic_bp": 152, "diastolic_bp": 94, "heart_rate": 82, "respiratory_rate": 18, "temperature": 98.6, "oxygen_saturation": 98, "weight": 71.5, "blood_glucose": 128, "creatinine": 1.1, "urea": 25, "sodium": 138, "potassium": 4.0, "sgot": 29, "sgpt": 31, "hemoglobin": 12.7, "wbc": 9.1, "platelet": 240, "rbc": 4.6, "hct": 39.6},
                {"time": 10, "systolic_bp": 154, "diastolic_bp": 96, "heart_rate": 84, "respiratory_rate": 19, "temperature": 98.7, "oxygen_saturation": 97, "weight": 71.4, "blood_glucose": 132, "creatinine": 1.2, "urea": 25, "sodium": 137, "potassium": 4.1, "sgot": 30, "sgpt": 32, "hemoglobin": 12.6, "wbc": 9.2, "platelet": 239, "rbc": 4.5, "hct": 39.2},
                {"time": 12, "systolic_bp": 155, "diastolic_bp": 98, "heart_rate": 88, "respiratory_rate": 18, "temperature": 98.7, "oxygen_saturation": 98, "weight": 71.4, "blood_glucose": 130, "creatinine": 1.2, "urea": 26, "sodium": 137, "potassium": 4.1, "sgot": 30, "sgpt": 33, "hemoglobin": 12.6, "wbc": 9.0, "platelet": 238, "rbc": 4.5, "hct": 39.0},
                {"time": 14, "systolic_bp": 148, "diastolic_bp": 92, "heart_rate": 86, "respiratory_rate": 17, "temperature": 98.6, "oxygen_saturation": 98, "weight": 71.3, "blood_glucose": 124, "creatinine": 1.1, "urea": 24, "sodium": 138, "potassium": 4.0, "sgot": 29, "sgpt": 31, "hemoglobin": 12.7, "wbc": 8.8, "platelet": 240, "rbc": 4.5, "hct": 39.4},
                {"time": 16, "systolic_bp": 145, "diastolic_bp": 90, "heart_rate": 84, "respiratory_rate": 17, "temperature": 98.5, "oxygen_saturation": 99, "weight": 71.3, "blood_glucose": 118, "creatinine": 1.1, "urea": 23, "sodium": 139, "potassium": 4.0, "sgot": 28, "sgpt": 30, "hemoglobin": 12.8, "wbc": 8.6, "platelet": 244, "rbc": 4.6, "hct": 39.7},
                {"time": 18, "systolic_bp": 142, "diastolic_bp": 88, "heart_rate": 81, "respiratory_rate": 16, "temperature": 98.4, "oxygen_saturation": 99, "weight": 71.2, "blood_glucose": 112, "creatinine": 1.0, "urea": 22, "sodium": 139, "potassium": 4.0, "sgot": 28, "sgpt": 29, "hemoglobin": 12.9, "wbc": 8.4, "platelet": 245, "rbc": 4.6, "hct": 40.0},
                {"time": 20, "systolic_bp": 140, "diastolic_bp": 86, "heart_rate": 79, "respiratory_rate": 16, "temperature": 98.3, "oxygen_saturation": 99, "weight": 71.2, "blood_glucose": 110, "creatinine": 1.0, "urea": 22, "sodium": 140, "potassium": 4.1, "sgot": 27, "sgpt": 29, "hemoglobin": 12.9, "wbc": 8.2, "platelet": 247, "rbc": 4.7, "hct": 40.1},
            ],
            3: [
                {"time": 6, "systolic_bp": 132, "diastolic_bp": 82, "heart_rate": 78, "respiratory_rate": 15, "temperature": 98.2, "oxygen_saturation": 99, "weight": 63.4, "blood_glucose": 154, "creatinine": 1.2, "urea": 30, "sodium": 136, "potassium": 4.3, "sgot": 34, "sgpt": 30, "hemoglobin": 11.4, "wbc": 9.6, "platelet": 274, "rbc": 4.1, "hct": 35.4},
                {"time": 8, "systolic_bp": 136, "diastolic_bp": 84, "heart_rate": 82, "respiratory_rate": 16, "temperature": 98.4, "oxygen_saturation": 98, "weight": 63.3, "blood_glucose": 168, "creatinine": 1.2, "urea": 29, "sodium": 136, "potassium": 4.2, "sgot": 35, "sgpt": 30, "hemoglobin": 11.3, "wbc": 9.8, "platelet": 276, "rbc": 4.1, "hct": 35.2},
                {"time": 10, "systolic_bp": 138, "diastolic_bp": 86, "heart_rate": 84, "respiratory_rate": 16, "temperature": 98.5, "oxygen_saturation": 98, "weight": 63.3, "blood_glucose": 172, "creatinine": 1.2, "urea": 29, "sodium": 137, "potassium": 4.2, "sgot": 34, "sgpt": 31, "hemoglobin": 11.4, "wbc": 9.7, "platelet": 278, "rbc": 4.1, "hct": 35.3},
                {"time": 12, "systolic_bp": 140, "diastolic_bp": 88, "heart_rate": 90, "respiratory_rate": 16, "temperature": 98.6, "oxygen_saturation": 98, "weight": 63.2, "blood_glucose": 170, "creatinine": 1.2, "urea": 28, "sodium": 137, "potassium": 4.2, "sgot": 33, "sgpt": 31, "hemoglobin": 11.5, "wbc": 9.4, "platelet": 281, "rbc": 4.2, "hct": 35.6},
                {"time": 14, "systolic_bp": 138, "diastolic_bp": 88, "heart_rate": 88, "respiratory_rate": 16, "temperature": 98.6, "oxygen_saturation": 98, "weight": 63.2, "blood_glucose": 162, "creatinine": 1.1, "urea": 27, "sodium": 138, "potassium": 4.1, "sgot": 32, "sgpt": 30, "hemoglobin": 11.6, "wbc": 9.2, "platelet": 284, "rbc": 4.2, "hct": 35.9},
                {"time": 16, "systolic_bp": 136, "diastolic_bp": 86, "heart_rate": 85, "respiratory_rate": 15, "temperature": 98.5, "oxygen_saturation": 99, "weight": 63.1, "blood_glucose": 156, "creatinine": 1.1, "urea": 27, "sodium": 138, "potassium": 4.1, "sgot": 31, "sgpt": 29, "hemoglobin": 11.7, "wbc": 8.9, "platelet": 286, "rbc": 4.2, "hct": 36.0},
                {"time": 18, "systolic_bp": 132, "diastolic_bp": 84, "heart_rate": 82, "respiratory_rate": 15, "temperature": 98.4, "oxygen_saturation": 99, "weight": 63.1, "blood_glucose": 150, "creatinine": 1.0, "urea": 26, "sodium": 138, "potassium": 4.0, "sgot": 30, "sgpt": 28, "hemoglobin": 11.8, "wbc": 8.7, "platelet": 289, "rbc": 4.3, "hct": 36.2},
                {"time": 20, "systolic_bp": 128, "diastolic_bp": 78, "heart_rate": 80, "respiratory_rate": 14, "temperature": 98.2, "oxygen_saturation": 100, "weight": 63.0, "blood_glucose": 148, "creatinine": 1.0, "urea": 25, "sodium": 139, "potassium": 4.0, "sgot": 29, "sgpt": 28, "hemoglobin": 11.9, "wbc": 8.4, "platelet": 291, "rbc": 4.3, "hct": 36.5},
            ],
        }

        for pat_idx, (adm_id, patient_id) in active_admission_map.items():
            for rv in review_vitals_data.get(pat_idx, []):
                recorded_at = datetime.utcnow().replace(hour=rv["time"], minute=0, second=0, microsecond=0)
                db.add(Vital(
                    id=uid(),
                    patient_id=patient_id,
                    recorded_at=recorded_at,
                    recorded_by="Dr. Arun Kumar" if pat_idx == 0 else "Dr. Sarah Johnson",
                    systolic_bp=rv["systolic_bp"],
                    diastolic_bp=rv["diastolic_bp"],
                    heart_rate=rv["heart_rate"],
                    respiratory_rate=rv["respiratory_rate"],
                    temperature=rv["temperature"],
                    oxygen_saturation=rv["oxygen_saturation"],
                    weight=rv["weight"],
                    blood_glucose=rv["blood_glucose"],
                    creatinine=rv["creatinine"],
                    urea=rv["urea"],
                    sodium=rv["sodium"],
                    potassium=rv["potassium"],
                    sgot=rv["sgot"],
                    sgpt=rv["sgpt"],
                    hemoglobin=rv["hemoglobin"],
                    wbc=rv["wbc"],
                    platelet=rv["platelet"],
                    rbc=rv["rbc"],
                    hct=rv["hct"],
                ))
            # IO Events
            for ev in io_events_data.get(pat_idx, []):
                db.add(IOEvent(
                    id=uid(),
                    patient_id=patient_id,
                    admission_id=adm_id,
                    event_time=ev["time"],
                    event_type=ev["type"],
                    description=ev["description"],
                    amount_ml=ev["amount"],
                    recorded_by=ev["by"],
                ))
            # SOAP Note
            if pat_idx in soap_notes_data:
                sn = soap_notes_data[pat_idx]
                db.add(SOAPNote(
                    id=uid(),
                    patient_id=patient_id,
                    admission_id=adm_id,
                    subjective=sn["subjective"],
                    objective=sn["objective"],
                    assessment=sn["assessment"],
                    plan=sn["plan"],
                    plan_items=sn.get("plan_items"),
                    note_meta=sn.get("meta"),
                    created_by=sn["by"],
                    updated_at=datetime.utcnow(),
                    updated_by=sn["by"],
                ))
            # Equipment
            for eq in equipment_data.get(pat_idx, []):
                connected_at = datetime.utcnow() - timedelta(hours=random.randint(4, 18))
                db.add(AdmissionEquipment(
                    id=uid(),
                    patient_id=patient_id,
                    admission_id=adm_id,
                    equipment_type=eq["type"],
                    equipment_id=eq["equipment_id"],
                    connected_since=connected_at.strftime("%I:%M %p"),
                    status=eq["status"].lower(),
                    live_data=eq.get("live_data"),
                ))

        # ── Pending Admission Approvals ──────────────────
        for pa in PENDING_ADMISSIONS:
            patient = all_patients[pa["patient_idx"]]
            student = all_students[pa["student_idx"]]
            faculty = faculty_list[pa["faculty_idx"]]
            adm_id = uid()
            db.add(Admission(
                id=adm_id,
                patient_id=patient.id,
                admission_date=datetime.utcnow(),
                department=pa["department"],
                ward=pa["ward"],
                bed_number=pa["bed_number"],
                attending_doctor=faculty.name,
                reason=pa["reason"],
                diagnosis=pa.get("provisional_diagnosis"),
                status="Pending Approval",
                submitted_by_student_id=student.id,
                faculty_approver_id=faculty.id,
                chief_complaints=pa.get("chief_complaints"),
                provisional_diagnosis=pa.get("provisional_diagnosis"),
                bp_admission=pa.get("bp_admission"),
                heart_rate_admission=pa.get("heart_rate_admission"),
                spo2_admission=pa.get("spo2_admission"),
                gcs_eye=pa.get("gcs_eye"),
                gcs_verbal=pa.get("gcs_verbal"),
                gcs_motor=pa.get("gcs_motor"),
                pain_score=pa.get("pain_score"),
            ))
            db.add(Approval(
                id=uid(),
                approval_type=ApprovalType.ADMISSION,
                admission_id=adm_id,
                faculty_id=faculty.id,
                patient_id=patient.id,
                student_id=student.id,
                status=ApprovalStatus.PENDING,
            ))

        # ── Case Records ─────────────────────────────────
        for cr in CASE_RECORDS_DATA:
            patient = all_patients[cr["patient_idx"]]
            student = all_students[cr["student_idx"]]
            faculty = faculty_list[cr["faculty_idx"]]
            cr_date = datetime.utcnow() - timedelta(days=cr["days_ago"])
            cr_id = uid()
            db.add(CaseRecord(
                id=cr_id,
                patient_id=patient.id,
                student_id=student.id,
                department=cr["department"],
                date=cr_date,
                type=cr["type"],
                description=cr["findings"],  # use findings as the description
                procedure_name=cr["procedure_name"],
                findings=cr["findings"],
                diagnosis=cr["diagnosis"],
                treatment=cr["treatment"],
                status=cr.get("status", "Pending"),
                grade=cr.get("grade"),
                created_by_name=student.name,
                created_by_role="STUDENT",
            ))
            if cr.get("status") == "Approved":
                db.add(Approval(
                    id=uid(),
                    approval_type=ApprovalType.CASE_RECORD,
                    case_record_id=cr_id,
                    faculty_id=faculty.id,
                    patient_id=patient.id,
                    student_id=student.id,
                    status=ApprovalStatus.APPROVED,
                    processed_at=cr_date + timedelta(hours=2),
                    comments="Reviewed and approved.",
                ))

        # ── Nurse Orders (Sample pending tasks) ──────────
        # Create sample orders for first 3 patients
        order_types = [
            {"type": "DRUG", "title": "Inj. Insulin Glargine", "desc": "18U SC HS", "time": "22:00"},
            {"type": "INVESTIGATION", "title": "RBS monitoring", "desc": "6-hourly", "time": "18:00"},
            {"type": "DRUG", "title": "Tab. Amlodipine", "desc": "5mg PO OD", "time": "08:00"},
            {"type": "DRUG", "title": "Inj. Heparin", "desc": "5000 units SC BD", "time": "20:00"},
            {"type": "INVESTIGATION", "title": "Vital signs monitoring", "desc": "Every 4 hours", "time": "16:00"},
        ]
        
        for i, p in enumerate(all_patients[:3]):
            for j, order in enumerate(order_types[:3]):
                db.add(NurseOrder(
                    id=uid(),
                    order_id=f"ORD-{i*3+j+1:03d}",
                    patient_id=p.id,
                    admission_id=p.id,  # Use patient ID as placeholder
                    order_type=order["type"],
                    title=order["title"],
                    description=order["desc"],
                    scheduled_time=order["time"],
                    is_completed=(j == 2),  # Mark last one as completed
                ))

        await db.commit()

    # ── Print credentials ────────────────────────────────
    print("\n✅ Database seeded successfully!\n")
    print("=" * 50)
    print("LOGIN CREDENTIALS")
    print("=" * 50)

    print("\n🔑 Admin (2):")
    print(f"  {'Username':<10} {'Password':<10}")
    print(f"  {'─'*10} {'─'*10}")
    print(f"  {'admin':<10} {'admin':<10}")
    print(f"  {'a':<10} {'a':<10}")

    print("\n🏢 Reception (2):")
    print(f"  {'Username':<10} {'Password':<10}")
    print(f"  {'─'*10} {'─'*10}")
    print(f"  {'r1':<10} {'r1':<10}")
    print(f"  {'r':<10} {'r':<10}")

    print("\n🩺 Doctors (3):")
    print(f"  {'Username':<10} {'Password':<10} {'Name':<25} {'Department'}")
    print(f"  {'─'*10} {'─'*10} {'─'*25} {'─'*20}")
    for d in DOCTORS:
        print(f"  {d['username']:<10} {d['password']:<10} {d['name']:<25} {d['department']}")

    print(f"\n🎓 Students (9):")
    print(f"  {'Username':<10} {'Password':<10} {'Name':<25} {'Year/Sem'}")
    print(f"  {'─'*10} {'─'*10} {'─'*25} {'─'*10}")
    for s in STUDENTS:
        print(f"  {s['username']:<10} {s['password']:<10} {s['name']:<25} Y{s['year']}/S{s['semester']}")

    print(f"\n🏥 Patients (10):")
    print(f"  {'Username':<10} {'Password':<10} {'Name':<25} {'Blood Group'}")
    print(f"  {'─'*10} {'─'*10} {'─'*25} {'─'*12}")
    for p in PATIENTS:
        print(f"  {p['username']:<10} {p['password']:<10} {p['name']:<25} {p['blood_group']}")

    print()


if __name__ == "__main__":
    asyncio.run(seed())
