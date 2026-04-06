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
from app.models.department import Department
from app.models.vital import Vital
from app.models.prescription import Prescription, PrescriptionMedication, PrescriptionStatus
from app.models.programme import Programme
from app.models.admission import Admission
from app.models.io_event import IOEvent, SOAPNote, AdmissionEquipment
from app.models.case_record import CaseRecord, Approval, ApprovalType, ApprovalStatus
from app.models.student_permission import StudentPermission
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
    {"name": "General Medicine OPD",     "department": "Internal Medicine", "location": "Outpatient Wing, Ground Floor", "faculty_idx": 0},
    {"name": "Cardiology Clinic",        "department": "Cardiology",        "location": "Block B, 1st Floor",           "faculty_idx": 1},
    {"name": "Pediatrics & Child Health", "department": "Pediatrics",        "location": "Block C, 2nd Floor",           "faculty_idx": 2},
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
        fac_result = await db.execute(select(Faculty))
        all_faculty = fac_result.scalars().all()
        faculty_list = list(all_faculty)

        clinic_objs = []
        for c in CLINICS:
            clinic = Clinic(
                id=uid(),
                name=c["name"],
                department=c["department"],
                location=c["location"],
                faculty_id=faculty_list[c["faculty_idx"]].id if c["faculty_idx"] < len(faculty_list) else None,
            )
            db.add(clinic)
            clinic_objs.append(clinic)
        await db.flush()

        # ── Clinic Appointments ──────────────────────────
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
            },
            3: {  # Priya Lakshmi
                "subjective": "Chest pain reduced to 3/10 with GTN. No radiation. Patient anxious about angiography.",
                "objective": "ECG: ST depression stable at 0.5mm V4-V6. Troponin I serial: 0.08→0.12 ng/mL (rising). BP 138/88 mmHg. HR 76 bpm.",
                "assessment": "NSTEMI confirmed by rising troponin. Haemodynamically stable. Angiography planned for tomorrow.",
                "plan": "Continue heparin, dual antiplatelet, GTN PRN. Cardiology consult confirmed angiography 10 AM. NPO from midnight. Echo booked.",
                "by": "Karthik Rajan (STU-002)",
            },
        }

        equipment_data = {
            3: [  # Priya Lakshmi - ICU (more equipment)
                {"type": "Bedside Monitor", "equipment_id": "MON-ICU-042", "status": "Active"},
                {"type": "Pulse Oximeter", "equipment_id": "OXI-042",     "status": "Active"},
                {"type": "Ventilator",      "equipment_id": "VENT-ICU-03", "status": "Standby"},
                {"type": "ABG Analyzer",    "equipment_id": "ABG-004",     "status": "Active"},
            ],
            0: [  # Rajesh Kumar - General Ward
                {"type": "Bedside Monitor", "equipment_id": "MON-GW-A12", "status": "Active"},
                {"type": "Pulse Oximeter",  "equipment_id": "OXI-A12",    "status": "Active"},
            ],
        }

        for pat_idx, (adm_id, patient_id) in active_admission_map.items():
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
