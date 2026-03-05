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
from app.models.student import Student, StudentPatientAssignment, Clinic, ClinicAppointment
from app.models.faculty import Faculty
from app.models.department import Department
from app.models.vital import Vital
from app.models.prescription import Prescription, PrescriptionMedication, PrescriptionStatus
from app.models.programme import Programme
from app.models.admission import Admission
from app.models.case_record import Approval, ApprovalType, ApprovalStatus
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
    # Active admissions
    {"patient_idx": 0, "department": "Internal Medicine", "ward": "General Ward A", "bed_number": "A-12",
     "attending_doctor": "Dr. Arun Kumar", "reason": "Acute hypertensive crisis",
     "diagnosis": "Essential Hypertension - Stage 2", "status": "Active", "days_ago": 2},
    {"patient_idx": 3, "department": "Cardiology", "ward": "ICU", "bed_number": "ICU-3",
     "attending_doctor": "Dr. Priya Sharma", "reason": "Chest pain evaluation",
     "diagnosis": "Unstable Angina", "status": "Active", "days_ago": 1},
    # Discharged admissions
    {"patient_idx": 1, "department": "Pediatrics", "ward": "General Ward B", "bed_number": "B-05",
     "attending_doctor": "Dr. Ravi Menon", "reason": "High fever and dehydration",
     "diagnosis": "Viral Gastroenteritis", "status": "Discharged", "days_ago": 10, "discharge_days_ago": 5,
     "discharge_summary": "Patient recovered well with IV fluids and supportive care.",
     "discharge_instructions": "Continue oral rehydration. Follow up in 1 week."},
    {"patient_idx": 4, "department": "Internal Medicine", "ward": "General Ward A", "bed_number": "A-07",
     "attending_doctor": "Dr. Arun Kumar", "reason": "Diabetic ketoacidosis",
     "diagnosis": "Uncontrolled Type 2 Diabetes Mellitus", "status": "Discharged", "days_ago": 15, "discharge_days_ago": 8,
     "discharge_summary": "Blood sugar levels stabilized. Insulin regimen adjusted.",
     "discharge_instructions": "Monitor blood glucose daily. Follow strict diabetic diet. Review in 2 weeks."},
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

        # ── Sample Admissions ────────────────────────────
        for a in ADMISSIONS_DATA:
            patient = all_patients[a["patient_idx"]]
            adm_date = datetime.utcnow() - timedelta(days=a["days_ago"])
            discharge_date = None
            if a["status"] == "Discharged" and "discharge_days_ago" in a:
                discharge_date = datetime.utcnow() - timedelta(days=a["discharge_days_ago"])
            follow_up = None
            if discharge_date:
                follow_up = discharge_date + timedelta(days=14)
            db.add(Admission(
                id=uid(),
                patient_id=patient.id,
                admission_date=adm_date,
                discharge_date=discharge_date,
                department=a["department"],
                ward=a["ward"],
                bed_number=a["bed_number"],
                attending_doctor=a["attending_doctor"],
                reason=a["reason"],
                diagnosis=a["diagnosis"],
                status=a["status"],
                discharge_summary=a.get("discharge_summary"),
                discharge_instructions=a.get("discharge_instructions"),
                follow_up_date=follow_up,
            ))

        # ── Pending Admission Approvals ──────────────────
        # Create a few admission requests pending faculty approval
        pending_admission_data = [
            {
                "patient_idx": 2,
                "student_idx": 0,
                "faculty_idx": 0,
                "department": "Internal Medicine",
                "ward": "General Ward A",
                "bed_number": "A-15",
                "reason": "Persistent high blood pressure unresponsive to medication adjustment",
                "diagnosis": "Resistant Hypertension",
            },
            {
                "patient_idx": 5,
                "student_idx": 1,
                "faculty_idx": 1,
                "department": "Cardiology",
                "ward": "General Ward C",
                "bed_number": "C-08",
                "reason": "Recurring chest pain and shortness of breath during physical activity",
                "diagnosis": "Chronic Stable Angina",
            },
            {
                "patient_idx": 6,
                "student_idx": 2,
                "faculty_idx": 2,
                "department": "Pediatrics",
                "ward": "Pediatric Ward",
                "bed_number": "P-03",
                "reason": "Severe dehydration and persistent vomiting",
                "diagnosis": "Acute Gastroenteritis with Dehydration",
            },
        ]
        for pa in pending_admission_data:
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
                diagnosis=pa["diagnosis"],
                status="Pending Approval",
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
