"""Database seeding script – creates test users and sample data."""
import asyncio
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal

import sys
import os

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal, engine, Base
from app.models.user import User, UserRole
from app.models.patient import (
    Patient, Gender, PatientCategory, EmergencyContact,
    Allergy, MedicalAlert, Appointment,
)
from app.models.student import (
    Student, StudentAttendance, DisciplinaryAction,
    StudentPatientAssignment,
)
from app.models.faculty import Faculty
from app.models.vital import Vital
from app.models.medical_record import MedicalRecord, RecordType, MedicalFinding
from app.models.prescription import Prescription, PrescriptionMedication, PrescriptionStatus
from app.models.admission import Admission
from app.models.report import Report, ReportStatus
from app.models.wallet import WalletTransaction, WalletType, TransactionType
from app.models.notification import PatientNotification
from app.models.case_record import CaseRecord, Approval
from app.core.security import get_password_hash


def uid() -> str:
    return str(uuid.uuid4())


async def seed():
    # Import all models so metadata is complete
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # ──────────────────────────────────────────────
        # 1. Users
        # ──────────────────────────────────────────────
        patient_user_id = uid()
        student_user_id = uid()
        faculty_user_id = uid()

        patient_user = User(
            id=patient_user_id,
            username="p",
            email="patient@saveetha.com",
            password_hash=get_password_hash("p"),
            role=UserRole.PATIENT,
        )
        student_user = User(
            id=student_user_id,
            username="s",
            email="student@saveetha.com",
            password_hash=get_password_hash("s"),
            role=UserRole.STUDENT,
        )
        faculty_user = User(
            id=faculty_user_id,
            username="t",
            email="faculty@saveetha.com",
            password_hash=get_password_hash("t"),
            role=UserRole.FACULTY,
        )
        db.add_all([patient_user, student_user, faculty_user])

        # ──────────────────────────────────────────────
        # 2. Patient
        # ──────────────────────────────────────────────
        patient_id = uid()
        patient = Patient(
            id=patient_id,
            patient_id="SMC-2023-1234",
            user_id=patient_user_id,
            name="Rajesh Kumar",
            date_of_birth=date(1990, 5, 15),
            gender=Gender.MALE,
            blood_group="O+",
            phone="+91 98765 43210",
            email="rajesh.kumar@email.com",
            address="123 Anna Nagar, Chennai 600040",
            category=PatientCategory.ELITE,
        )
        db.add(patient)

        # Emergency contact for patient
        db.add(EmergencyContact(
            id=uid(), patient_id=patient_id,
            name="Priya Kumar", relationship_="Wife",
            phone="+91 98765 43211", email="priya.kumar@email.com",
        ))

        # Allergies
        db.add(Allergy(id=uid(), patient_id=patient_id, allergen="Penicillin", severity="HIGH", reaction="Anaphylaxis"))
        db.add(Allergy(id=uid(), patient_id=patient_id, allergen="Aspirin", severity="MEDIUM", reaction="Hives"))
        db.add(Allergy(id=uid(), patient_id=patient_id, allergen="Latex", severity="LOW", reaction="Skin irritation"))

        # Medical alerts
        db.add(MedicalAlert(
            id=uid(), patient_id=patient_id,
            type="RISK", severity="HIGH",
            title="High risk for falls",
            description="Patient has history of falls",
            symptoms="[]", is_active=True,
        ))
        db.add(MedicalAlert(
            id=uid(), patient_id=patient_id,
            type="CONDITION", severity="HIGH",
            title="Immunocompromised",
            description="Patient is immunocompromised",
            symptoms="[]", is_active=True,
        ))

        # ──────────────────────────────────────────────
        # 3. Additional patients (for student assignments)
        # ──────────────────────────────────────────────
        extra_patients = []
        for i, (name, dob, gender, bg, condition) in enumerate([
            ("John Doe", date(1978, 3, 10), Gender.MALE, "A+", "Hypertension"),
            ("Maria Garcia", date(1961, 7, 22), Gender.FEMALE, "B+", "Diabetes Type 2"),
            ("Robert Chen", date(1989, 11, 5), Gender.MALE, "AB+", "Bronchitis"),
        ], start=1):
            pid = uid()
            extra_user_id = uid()
            db.add(User(
                id=extra_user_id,
                username=f"patient{i}",
                email=f"patient{i}@saveetha.com",
                password_hash=get_password_hash("password"),
                role=UserRole.PATIENT,
            ))
            p = Patient(
                id=pid,
                patient_id=f"SMC-2023-{5000+i}",
                user_id=extra_user_id,
                name=name,
                date_of_birth=dob,
                gender=gender,
                blood_group=bg,
                phone=f"+91 98765 4{3210+i}",
                email=f"{name.lower().replace(' ', '.')}@email.com",
                address=f"{100+i} Main Street, Chennai 600001",
                category=PatientCategory.GENERAL,
            )
            db.add(p)
            extra_patients.append((pid, name, condition))

        # ──────────────────────────────────────────────
        # 4. Student
        # ──────────────────────────────────────────────
        student_id = uid()
        student = Student(
            id=student_id,
            student_id="SMS-2023-1234",
            user_id=student_user_id,
            name="Sarah Smith",
            year=3,
            semester=6,
            program="MBBS",
            degree="Bachelor of Medicine and Bachelor of Surgery (MBBS)",
            gpa=3.8,
            academic_standing="Good Standing",
            academic_advisor="Dr. James Wilson",
        )
        db.add(student)

        # Student attendance
        db.add(StudentAttendance(
            id=uid(), student_id=student_id,
            overall=92.0, clinical=95.0, lecture=88.0, lab=94.0,
        ))

        # Emergency contact for student
        db.add(EmergencyContact(
            id=uid(), student_id=student_id,
            name="Robert Smith", relationship_="Father",
            phone="+91 98765 43210", email="robert.smith@example.com",
            address="45 Park Avenue, Chennai, Tamil Nadu - 600040",
        ))

        # Disciplinary action
        db.add(DisciplinaryAction(
            id=uid(), student_id=student_id,
            type="Warning",
            description="Late submission of clinical reports",
            date="September 15, 2022",
            status="Resolved",
            details="Verbal warning issued by department head",
            resolution="Student completed all pending reports and acknowledged the warning",
        ))

        # Assign patients to student
        for pid, name, condition in extra_patients:
            db.add(StudentPatientAssignment(
                id=uid(), student_id=student_id, patient_id=pid, status="Active",
            ))

        # ──────────────────────────────────────────────
        # 5. Faculty
        # ──────────────────────────────────────────────
        faculty_id = uid()
        faculty = Faculty(
            id=faculty_id,
            faculty_id="FAC-2023-1234",
            user_id=faculty_user_id,
            name="Dr. James Wilson",
            department="Internal Medicine",
            specialty="Cardiology",
            phone="+91 44 2680 1050",
            email="james.wilson@saveetha.com",
            availability="Mon, Wed, Fri – 9 AM to 4 PM",
        )
        db.add(faculty)

        # ──────────────────────────────────────────────
        # 6. Vitals (30 days of data for the main patient)
        # ──────────────────────────────────────────────
        import random
        now = datetime.utcnow()
        for day in range(30):
            dt = now - timedelta(days=29 - day, hours=random.randint(0, 12))
            db.add(Vital(
                id=uid(), patient_id=patient_id,
                recorded_at=dt, recorded_by="Nurse Station A",
                systolic_bp=random.randint(115, 140),
                diastolic_bp=random.randint(70, 90),
                heart_rate=random.randint(62, 88),
                respiratory_rate=random.randint(14, 20),
                temperature=round(random.uniform(97.5, 99.5), 1),
                oxygen_saturation=random.randint(94, 100),
                weight=round(random.uniform(154, 158), 1),
                blood_glucose=random.randint(90, 140),
                cholesterol=random.randint(180, 220),
                bmi=round(random.uniform(23.5, 25.5), 1),
            ))

        # ──────────────────────────────────────────────
        # 7. Medical Records
        # ──────────────────────────────────────────────
        rec1_id = uid()
        db.add(MedicalRecord(
            id=rec1_id, patient_id=patient_id,
            date=now - timedelta(days=5), time="10:30 AM",
            type=RecordType.CONSULTATION,
            description="Routine follow-up for hypertension management",
            performed_by="Dr. Sarah Johnson",
            supervised_by="Dr. James Wilson",
            department="Internal Medicine",
            status="Completed",
            diagnosis="Essential hypertension, well-controlled",
            recommendations="Continue current medication. Follow up in 3 months.",
        ))
        db.add(MedicalFinding(id=uid(), record_id=rec1_id, parameter="Blood Pressure", value="128/82 mmHg", reference="<120/80 mmHg", status="Slightly Elevated"))
        db.add(MedicalFinding(id=uid(), record_id=rec1_id, parameter="Heart Rate", value="72 bpm", reference="60-100 bpm", status="Normal"))

        rec2_id = uid()
        db.add(MedicalRecord(
            id=rec2_id, patient_id=patient_id,
            date=now - timedelta(days=15), time="09:00 AM",
            type=RecordType.LABORATORY,
            description="Complete Blood Count & Metabolic Panel",
            performed_by="Lab Technician",
            department="Pathology",
            status="Completed",
            diagnosis="Slightly elevated fasting glucose",
        ))
        db.add(MedicalFinding(id=uid(), record_id=rec2_id, parameter="Fasting Glucose", value="118 mg/dL", reference="70-100 mg/dL", status="High"))
        db.add(MedicalFinding(id=uid(), record_id=rec2_id, parameter="HbA1c", value="5.9%", reference="<5.7%", status="Borderline"))
        db.add(MedicalFinding(id=uid(), record_id=rec2_id, parameter="Hemoglobin", value="14.2 g/dL", reference="13.5-17.5 g/dL", status="Normal"))

        # ──────────────────────────────────────────────
        # 8. Prescriptions
        # ──────────────────────────────────────────────
        rx_id = uid()
        db.add(Prescription(
            id=rx_id, patient_id=patient_id,
            date=now - timedelta(days=5),
            doctor="Dr. Sarah Johnson",
            department="Internal Medicine",
            status=PrescriptionStatus.ACTIVE,
        ))
        db.add(PrescriptionMedication(
            id=uid(), prescription_id=rx_id,
            name="Lisinopril", dosage="10mg", frequency="Once daily",
            duration="90 days", instructions="Take in the morning with food",
            refills_remaining=2, start_date="2025-02-01", end_date="2025-05-01",
        ))
        db.add(PrescriptionMedication(
            id=uid(), prescription_id=rx_id,
            name="Metformin", dosage="500mg", frequency="Twice daily",
            duration="90 days", instructions="Take with meals",
            refills_remaining=2, start_date="2025-02-01", end_date="2025-05-01",
        ))

        rx2_id = uid()
        db.add(Prescription(
            id=rx2_id, patient_id=patient_id,
            date=now - timedelta(days=30),
            doctor="Dr. Michael Chang",
            department="Internal Medicine",
            status=PrescriptionStatus.COMPLETED,
        ))
        db.add(PrescriptionMedication(
            id=uid(), prescription_id=rx2_id,
            name="Amoxicillin", dosage="500mg", frequency="Three times daily",
            duration="7 days", instructions="Complete entire course",
            refills_remaining=0,
            start_date="2025-01-01", end_date="2025-01-08",
        ))

        # ──────────────────────────────────────────────
        # 9. Admissions
        # ──────────────────────────────────────────────
        db.add(Admission(
            id=uid(), patient_id=patient_id,
            admission_date=now - timedelta(days=60),
            discharge_date=now - timedelta(days=55),
            department="Internal Medicine",
            ward="Ward 3A", bed_number="B-12",
            attending_doctor="Dr. James Wilson",
            diagnosis="Hypertensive crisis – managed with IV antihypertensives",
            status="Discharged",
            notes="Patient responded well to treatment. Discharged with modified oral regimen.",
        ))

        # ──────────────────────────────────────────────
        # 9b. Appointments
        # ──────────────────────────────────────────────
        # Upcoming appointment
        db.add(Appointment(
            id=uid(), patient_id=patient_id,
            date=now + timedelta(days=89),  # About 3 months from now (28 May)
            time="10:30 AM",
            doctor="Dr. Sarah Johnson",
            department="Internal Medicine",
            status="Scheduled",
            notes="Follow-up for hypertension management",
        ))
        # Past appointment
        db.add(Appointment(
            id=uid(), patient_id=patient_id,
            date=now - timedelta(days=30),
            time="2:00 PM",
            doctor="Dr. James Wilson",
            department="Cardiology",
            status="Completed",
            notes="Routine cardiac evaluation",
        ))

        # ──────────────────────────────────────────────
        # 10. Reports
        # ──────────────────────────────────────────────
        db.add(Report(
            id=uid(), patient_id=patient_id,
            date=now - timedelta(days=15),
            title="Complete Blood Count", type="Laboratory",
            department="Pathology", ordered_by="Dr. Sarah Johnson",
            status=ReportStatus.NORMAL,
            result_summary="All values within normal limits except borderline glucose.",
        ))
        db.add(Report(
            id=uid(), patient_id=patient_id,
            date=now - timedelta(days=10),
            title="Chest X-Ray", type="Radiology",
            department="Radiology", ordered_by="Dr. James Wilson",
            status=ReportStatus.NORMAL,
            result_summary="No acute cardiopulmonary disease.",
        ))
        db.add(Report(
            id=uid(), patient_id=patient_id,
            date=now - timedelta(days=2),
            title="Lipid Panel", type="Laboratory",
            department="Pathology", ordered_by="Dr. Sarah Johnson",
            status=ReportStatus.ABNORMAL,
            result_summary="LDL slightly elevated at 142 mg/dL (target <130).",
        ))

        # ──────────────────────────────────────────────
        # 11. Wallet Transactions
        # ──────────────────────────────────────────────
        for i, (desc, amt, typ, wt, dept) in enumerate([
            ("Initial Deposit", Decimal("5000.00"), TransactionType.CREDIT, WalletType.HOSPITAL, "Billing"),
            ("Consultation Fee", Decimal("500.00"), TransactionType.DEBIT, WalletType.HOSPITAL, "Internal Medicine"),
            ("Lab Tests – CBC", Decimal("1200.00"), TransactionType.DEBIT, WalletType.HOSPITAL, "Pathology"),
            ("X-Ray Charges", Decimal("800.00"), TransactionType.DEBIT, WalletType.HOSPITAL, "Radiology"),
            ("Insurance Reimbursement", Decimal("2000.00"), TransactionType.CREDIT, WalletType.HOSPITAL, "Billing"),
            ("Admission Charges", Decimal("4149.25"), TransactionType.DEBIT, WalletType.HOSPITAL, "Billing"),
            ("Pharmacy Deposit", Decimal("1000.00"), TransactionType.CREDIT, WalletType.PHARMACY, "Pharmacy"),
            ("Lisinopril 10mg (30 tabs)", Decimal("350.00"), TransactionType.DEBIT, WalletType.PHARMACY, "Pharmacy"),
            ("Metformin 500mg (60 tabs)", Decimal("220.00"), TransactionType.DEBIT, WalletType.PHARMACY, "Pharmacy"),
            ("OTC Medications", Decimal("304.50"), TransactionType.DEBIT, WalletType.PHARMACY, "Pharmacy"),
        ]):
            db.add(WalletTransaction(
                id=uid(), patient_id=patient_id,
                wallet_type=wt, date=now - timedelta(days=30 - i * 5),
                time=f"{9 + i}:00 AM", description=desc,
                amount=amt, type=typ, department=dept,
                payment_method="UPI" if typ == TransactionType.DEBIT else "Bank Transfer",
                reference_number=f"REF-{2025000 + i}",
            ))

        # ──────────────────────────────────────────────
        # 12. Notifications (for patient)
        # ──────────────────────────────────────────────
        for title, msg, ntype, days_ago in [
            ("Appointment Reminder", "You have an appointment with Dr. Wilson tomorrow at 10 AM", "APPOINTMENT", 1),
            ("Lab Results Ready", "Your Complete Blood Count results are now available", "REPORT", 3),
            ("Prescription Refill", "Your Lisinopril prescription is due for refill in 7 days", "PRESCRIPTION", 5),
            ("System Update", "We've updated our patient portal. Check out the new features!", "SYSTEM", 7),
        ]:
            db.add(PatientNotification(
                id=uid(), patient_id=patient_id,
                title=title, message=msg, type=ntype,
                is_read=0, created_at=now - timedelta(days=days_ago),
            ))

        # ──────────────────────────────────────────────
        # 13. Case Records (student-created)
        # ──────────────────────────────────────────────
        cr1_id = uid()
        db.add(CaseRecord(
            id=cr1_id,
            patient_id=extra_patients[0][0],
            student_id=student_id,
            date=now - timedelta(days=3),
            time="10:30 AM",
            type="Physical Examination",
            description="Routine physical examination and vitals check",
            department="Internal Medicine",
            findings="BP 128/82 mmHg, HR 72 bpm, Temp 98.4°F",
            diagnosis="Essential hypertension, well-controlled",
            treatment="Continue current medication regimen",
            notes="Patient compliant with medication",
            grade="A",
            provider="Sarah Smith (Student)",
            status="Approved",
            approved_by="Dr. James Wilson",
            approved_at="May 25, 2025 – 2:30 PM",
        ))

        cr2_id = uid()
        db.add(CaseRecord(
            id=cr2_id,
            patient_id=extra_patients[1][0],
            student_id=student_id,
            date=now - timedelta(days=7),
            time="09:15 AM",
            type="Blood Glucose Monitoring",
            description="Fasting blood glucose measurement and HbA1c review",
            department="Endocrinology",
            findings="Fasting glucose 118 mg/dL, HbA1c 5.9%",
            diagnosis="Pre-diabetic state, monitoring required",
            treatment="Lifestyle modifications, re-check in 3 months",
            notes="Discussed dietary changes with patient",
            grade="B+",
            provider="Sarah Smith (Student)",
            status="Approved",
            approved_by="Dr. James Wilson",
            approved_at="May 21, 2025 – 4:00 PM",
        ))

        # Approvals for case records
        db.add(Approval(
            id=uid(), case_record_id=cr1_id, faculty_id=faculty_id,
            status="Approved", comments="Good clinical documentation",
            created_at=now - timedelta(days=3),
            processed_at=now - timedelta(days=3, hours=-4),
        ))
        db.add(Approval(
            id=uid(), case_record_id=cr2_id, faculty_id=faculty_id,
            status="Approved", comments="Well done",
            created_at=now - timedelta(days=7),
            processed_at=now - timedelta(days=7, hours=-4),
        ))

        await db.commit()
        print("✅ Database seeded successfully!")
        print("   Test credentials: p/p (Patient), s/s (Student), t/t (Faculty)")


if __name__ == "__main__":
    asyncio.run(seed())
