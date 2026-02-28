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
from app.models.user import User, UserRole
from app.models.patient import Patient, Gender, PatientCategory, MedicalAlert
from app.models.student import Student, StudentPatientAssignment
from app.models.faculty import Faculty
from app.models.department import Department
from app.models.vital import Vital
from app.models.prescription import Prescription, PrescriptionMedication, PrescriptionStatus
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


async def seed():
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
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

        # Flush to get IDs
        await db.flush()

        # ── Fetch all student and patient records ────────
        from sqlalchemy import select
        stu_result = await db.execute(select(Student))
        all_students = stu_result.scalars().all()
        pat_result = await db.execute(select(Patient))
        all_patients = pat_result.scalars().all()

        student_map = {s.student_id: s for s in all_students}
        patient_map = {p.patient_id: p for p in all_patients}

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

        await db.commit()

    # ── Print credentials ────────────────────────────────
    print("\n✅ Database seeded successfully!\n")
    print("=" * 50)
    print("LOGIN CREDENTIALS")
    print("=" * 50)

    print("\n🔑 Admin (1):")
    print(f"  {'Username':<10} {'Password':<10}")
    print(f"  {'─'*10} {'─'*10}")
    print(f"  {'admin':<10} {'admin':<10}")

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
