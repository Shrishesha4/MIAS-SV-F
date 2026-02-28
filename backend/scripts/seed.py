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
    StudentPatientAssignment, ClinicSession, Clinic, ClinicAppointment,
)
from app.models.faculty import Faculty
from app.models.vital import Vital
from app.models.medical_record import MedicalRecord, RecordType, MedicalFinding
from app.models.prescription import Prescription, PrescriptionMedication, PrescriptionStatus
from app.models.admission import Admission
from app.models.report import Report, ReportStatus, ReportFinding, ReportImage
from app.models.wallet import WalletTransaction, WalletType, TransactionType
from app.models.notification import PatientNotification
from app.models.case_record import CaseRecord, Approval, ApprovalType, ApprovalStatus
from app.models.faculty import Faculty, FacultyNotification, FacultySchedule
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
        # 3. Additional patients (for student assignments and approvals)
        # ──────────────────────────────────────────────
        extra_patients = []
        extra_patient_data = [
            {
                "name": "John Doe",
                "dob": date(1978, 3, 10),
                "gender": Gender.MALE,
                "bg": "O+",
                "condition": "Hypertension",
                "photo": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&h=200&fit=crop&crop=faces",
                "allergies": [("Penicillin", "HIGH")],
            },
            {
                "name": "Maria Garcia",
                "dob": date(1961, 7, 22),
                "gender": Gender.FEMALE,
                "bg": "B+",
                "condition": "Type 2 Diabetes",
                "photo": "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=200&h=200&fit=crop&crop=faces",
                "allergies": [],
            },
            {
                "name": "Robert Chen",
                "dob": date(1989, 11, 5),
                "gender": Gender.MALE,
                "bg": "AB+",
                "condition": "Acute Bronchitis",
                "photo": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=200&h=200&fit=crop&crop=faces",
                "allergies": [("Sulfa drugs", "HIGH")],
            },
            {
                "name": "Emily Wong",
                "dob": date(1994, 8, 15),
                "gender": Gender.FEMALE,
                "bg": "A+",
                "condition": "Migraine",
                "photo": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200&h=200&fit=crop&crop=faces",
                "allergies": [],
            },
            {
                "name": "James Smith",
                "dob": date(1970, 5, 20),
                "gender": Gender.MALE,
                "bg": "O-",
                "condition": "Lower Back Pain",
                "photo": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=200&h=200&fit=crop&crop=faces",
                "allergies": [("Ibuprofen", "MEDIUM")],
            },
            {
                "name": "Sophia Rodriguez",
                "dob": date(1982, 12, 3),
                "gender": Gender.FEMALE,
                "bg": "A+",
                "condition": "Asthma",
                "photo": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&h=200&fit=crop&crop=faces",
                "allergies": [("Dust", "MEDIUM")],
            },
            {
                "name": "David Kim",
                "dob": date(1956, 9, 8),
                "gender": Gender.MALE,
                "bg": "B-",
                "condition": "Arthritis",
                "photo": "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=200&h=200&fit=crop&crop=faces",
                "allergies": [],
            },
            {
                "name": "Olivia Johnson",
                "dob": date(1987, 2, 14),
                "gender": Gender.FEMALE,
                "bg": "AB-",
                "condition": "Gastritis",
                "photo": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=200&h=200&fit=crop&crop=faces",
                "allergies": [("Aspirin", "HIGH")],
            },
        ]
        
        for i, pdata in enumerate(extra_patient_data, start=1):
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
                patient_id=f"SMC-2023-00{41+i}",
                user_id=extra_user_id,
                name=pdata["name"],
                date_of_birth=pdata["dob"],
                gender=pdata["gender"],
                blood_group=pdata["bg"],
                phone=f"+91 98765 4{3210+i}",
                email=f"{pdata['name'].lower().replace(' ', '.')}@email.com",
                address=f"{100+i} Main Street, Chennai 600001",
                category=PatientCategory.GENERAL,
                photo=pdata.get("photo"),
            )
            db.add(p)
            extra_patients.append((pid, pdata["name"], pdata["condition"], pdata.get("photo")))
            
            # Add allergies for this patient
            for allergen, severity in pdata.get("allergies", []):
                db.add(Allergy(
                    id=uid(), patient_id=pid,
                    allergen=allergen, severity=severity, reaction="Various symptoms",
                ))

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

        # Assign patients to student and create case records with diagnoses
        for i, patient_info in enumerate(extra_patients):
            pid = patient_info[0]
            condition = patient_info[2]
            db.add(StudentPatientAssignment(
                id=uid(), student_id=student_id, patient_id=pid, status="Active",
            ))
            # Add case record with diagnosis for this patient
            db.add(CaseRecord(
                id=uid(),
                patient_id=pid,
                student_id=student_id,
                date=datetime.utcnow() - timedelta(days=i+1),
                time="10:00 AM",
                type="Examination",
                description=f"Initial assessment for {condition}",
                department="Internal Medicine",
                diagnosis=condition,
                treatment="As prescribed",
                status="Completed",
            ))

        # ──────────────────────────────────────────────
        # 5. Faculty (including emergency contacts)
        # ──────────────────────────────────────────────
        faculty_id = uid()
        faculty = Faculty(
            id=faculty_id,
            faculty_id="FAC-2023-0078",
            user_id=faculty_user_id,
            name="Dr. Sarah Johnson",
            department="Internal Medicine",
            specialty="General Medicine",
            phone="+91 44 2680 1050",
            email="sarah.johnson@saveetha.com",
            photo="https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=200&h=200&fit=crop&crop=faces",
            availability="On-call 24/7",
            availability_status="Available",
            is_emergency_contact=1,
        )
        db.add(faculty)

        # More faculty as emergency contacts
        emergency_faculty_data = [
            {
                "name": "Dr. Robert Miller",
                "department": "Cardiology",
                "specialty": "Cardiac Care",
                "photo": "https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?w=200&h=200&fit=crop&crop=faces",
                "availability": "Available 8AM-8PM",
                "availability_status": "Available",
            },
            {
                "name": "Dr. Emily Rodriguez",
                "department": "Pediatrics",
                "specialty": "Children's Care",
                "photo": "https://images.unsplash.com/photo-1594824476967-48c8b964273f?w=200&h=200&fit=crop&crop=faces",
                "availability": "Available 9AM-5PM",
                "availability_status": "Busy",
            },
            {
                "name": "Dr. Michael Chang",
                "department": "Surgery",
                "specialty": "Surgical Unit",
                "photo": "https://images.unsplash.com/photo-1622253692010-333f2da6031d?w=200&h=200&fit=crop&crop=faces",
                "availability": "On-call for emergencies",
                "availability_status": "Unavailable",
            },
            {
                "name": "Dr. Jessica Williams",
                "department": "Emergency Medicine",
                "specialty": "Emergency Department",
                "photo": "https://images.unsplash.com/photo-1651008376811-b90baee60c1f?w=200&h=200&fit=crop&crop=faces",
                "availability": "On-call 24/7",
                "availability_status": "Available",
            },
        ]
        
        for i, fdata in enumerate(emergency_faculty_data):
            fid = uid()
            fac_user_id = uid()
            # Create a user for this faculty member
            db.add(User(
                id=fac_user_id,
                username=f"faculty{i+1}",
                email=f"{fdata['name'].lower().replace(' ', '.').replace('dr.', '')}@saveetha.com",
                password_hash=get_password_hash("password"),
                role=UserRole.FACULTY,
            ))
            db.add(Faculty(
                id=fid,
                faculty_id=f"FAC-2023-{1001+i:04d}",
                user_id=fac_user_id,
                name=fdata["name"],
                department=fdata["department"],
                specialty=fdata["specialty"],
                phone=f"+91 44 2680 {1051+i}",
                email=f"{fdata['name'].lower().replace(' ', '.').replace('dr.', '')}@saveetha.com",
                photo=fdata["photo"],
                availability=fdata["availability"],
                availability_status=fdata["availability_status"],
                is_emergency_contact=1,
            ))

        # Faculty schedule for today
        today = date.today()
        db.add(FacultySchedule(
            id=uid(), faculty_id=faculty_id,
            date=today, time_start="9:00 AM", time_end="11:00 AM",
            title="Outpatient Consultations", type="consultation", location="OPD Block A",
        ))
        db.add(FacultySchedule(
            id=uid(), faculty_id=faculty_id,
            date=today, time_start="1:00 PM", time_end="2:00 PM",
            title="Department Meeting", type="meeting", location="Conference Room 3",
        ))
        db.add(FacultySchedule(
            id=uid(), faculty_id=faculty_id,
            date=today, time_start="3:00 PM", time_end="5:00 PM",
            title="Student Case Reviews", type="review", location="Teaching Lab B",
        ))

        # ──────────────────────────────────────────────
        # 5b. Clinics and Clinic Sessions for Students
        # ──────────────────────────────────────────────
        clinic_gm_id = uid()
        clinic_cardio_id = uid()
        clinic_pedia_id = uid()
        
        db.add(Clinic(
            id=clinic_gm_id,
            name="General Medicine Clinic",
            department="Internal Medicine",
            location="Outpatient Wing, 2nd Floor",
            faculty_id=faculty_id,
        ))
        db.add(Clinic(
            id=clinic_cardio_id,
            name="Cardiology Clinic",
            department="Cardiology",
            location="Cardiac Care Unit, 3rd Floor",
        ))
        db.add(Clinic(
            id=clinic_pedia_id,
            name="Pediatrics Clinic",
            department="Pediatrics",
            location="Children's Wing, 1st Floor",
        ))
        
        # Clinic sessions for the student
        db.add(ClinicSession(
            id=uid(), student_id=student_id, clinic_id=clinic_gm_id,
            clinic_name="General Medicine Clinic", department="Internal Medicine",
            date=datetime.combine(today, datetime.min.time()),
            time_start="9:00 AM", time_end="12:00 PM",
            status="Active", is_selected=1,
        ))
        db.add(ClinicSession(
            id=uid(), student_id=student_id, clinic_id=clinic_cardio_id,
            clinic_name="Cardiology Clinic", department="Cardiology",
            date=datetime.combine(today + timedelta(days=1), datetime.min.time()),
            time_start="10:00 AM", time_end="2:00 PM",
            status="Scheduled", is_selected=0,
        ))
        db.add(ClinicSession(
            id=uid(), student_id=student_id, clinic_id=clinic_pedia_id,
            clinic_name="Pediatrics Clinic", department="Pediatrics",
            date=datetime.combine(today + timedelta(days=2), datetime.min.time()),
            time_start="8:30 AM", time_end="11:30 AM",
            status="Scheduled", is_selected=0,
        ))
        
        # Today's clinic appointments
        db.add(ClinicAppointment(
            id=uid(), clinic_id=clinic_gm_id, patient_id=patient_id,
            appointment_date=datetime.combine(today, datetime.min.time()),
            appointment_time="9:15 AM", provider_name="Dr. Michael Chang",
            status="Checked In",
        ))
        # Add appointments for extra patients
        if len(extra_patients) >= 2:
            db.add(ClinicAppointment(
                id=uid(), clinic_id=clinic_gm_id, patient_id=extra_patients[1][0],
                appointment_date=datetime.combine(today, datetime.min.time()),
                appointment_time="9:45 AM", provider_name="Dr. Sarah Johnson",
                status="In Progress",
            ))
        if len(extra_patients) >= 3:
            db.add(ClinicAppointment(
                id=uid(), clinic_id=clinic_gm_id, patient_id=extra_patients[2][0],
                appointment_date=datetime.combine(today, datetime.min.time()),
                appointment_time="10:15 AM", provider_name="Dr. Robert Miller",
                status="Scheduled",
            ))

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
        # 8. Prescriptions (with full hospital details)
        # ──────────────────────────────────────────────
        hospital_name = "Saveetha Medical College Hospital"
        hospital_address = "Saveetha Nagar, Thandalam, Chennai 600077"
        hospital_contact = "(044) 2680-1050"
        hospital_email = "pharmacy@saveetha.com"
        hospital_website = "www.saveethamedical.com"

        # Active prescription 1
        rx_id1 = uid()
        db.add(Prescription(
            id=rx_id1, prescription_id="RX-2023-0056",
            patient_id=patient_id,
            date=datetime(2023, 5, 15),
            doctor="Dr. Sarah Johnson", doctor_license="SMC-DR-2023-0056",
            department="Cardiology",
            hospital_name=hospital_name, hospital_address=hospital_address,
            hospital_contact=hospital_contact, hospital_email=hospital_email,
            hospital_website=hospital_website,
            status=PrescriptionStatus.ACTIVE,
            notes="Please take medications as prescribed. Contact your doctor if you experience any severe side effects. Prescription can be refilled at any Saveetha Medical College Hospital pharmacy.",
        ))
        db.add(PrescriptionMedication(
            id=uid(), prescription_id=rx_id1,
            name="Lisinopril", dosage="10mg", frequency="Once daily",
            duration="3 months", instructions="Take in the morning with food",
            refills_remaining=2, start_date="May 15, 2023", end_date="Aug 15, 2023",
        ))
        db.add(PrescriptionMedication(
            id=uid(), prescription_id=rx_id1,
            name="Aspirin", dosage="81mg", frequency="Once daily",
            duration="3 months", instructions="Take with food",
            refills_remaining=2, start_date="May 15, 2023", end_date="Aug 15, 2023",
        ))

        # Active prescription 2
        rx_id2 = uid()
        db.add(Prescription(
            id=rx_id2, prescription_id="RX-2023-0042",
            patient_id=patient_id,
            date=datetime(2023, 4, 10),
            doctor="Dr. Michael Chang", doctor_license="SMC-DR-2023-0042",
            department="Orthopedics",
            hospital_name=hospital_name, hospital_address=hospital_address,
            hospital_contact=hospital_contact, hospital_email=hospital_email,
            hospital_website=hospital_website,
            status=PrescriptionStatus.ACTIVE,
            notes="For post-surgical pain management. Do not exceed prescribed dosage.",
        ))
        db.add(PrescriptionMedication(
            id=uid(), prescription_id=rx_id2,
            name="Acetaminophen", dosage="500mg", frequency="Every 6 hours as needed",
            duration="2 weeks", instructions="Take with or without food",
            refills_remaining=1, start_date="Apr 10, 2023", end_date="Apr 24, 2023",
        ))
        db.add(PrescriptionMedication(
            id=uid(), prescription_id=rx_id2,
            name="Ibuprofen", dosage="400mg", frequency="Three times daily",
            duration="10 days", instructions="Take with food to avoid stomach upset",
            refills_remaining=0, start_date="Apr 10, 2023", end_date="Apr 20, 2023",
        ))

        # Receive status prescription
        rx_id3 = uid()
        db.add(Prescription(
            id=rx_id3, prescription_id="RX-2023-0035",
            patient_id=patient_id,
            date=datetime(2023, 3, 20),
            doctor="Dr. Lisa Wong", doctor_license="SMC-DR-2023-0035",
            department="Dermatology",
            hospital_name=hospital_name, hospital_address=hospital_address,
            hospital_contact=hospital_contact, hospital_email=hospital_email,
            hospital_website=hospital_website,
            status=PrescriptionStatus.RECEIVE,
            notes="Apply as directed. Avoid sun exposure while using this medication.",
        ))
        db.add(PrescriptionMedication(
            id=uid(), prescription_id=rx_id3,
            name="Tretinoin Cream", dosage="0.025%", frequency="Once daily at night",
            duration="6 weeks", instructions="Apply thin layer to affected areas",
            refills_remaining=2, start_date="Mar 20, 2023", end_date="May 1, 2023",
        ))

        # Completed prescription 1
        rx_id4 = uid()
        db.add(Prescription(
            id=rx_id4, prescription_id="RX-2023-0028",
            patient_id=patient_id,
            date=datetime(2023, 2, 15),
            doctor="Dr. James Wilson", doctor_license="SMC-DR-2023-0028",
            department="Internal Medicine",
            hospital_name=hospital_name, hospital_address=hospital_address,
            hospital_contact=hospital_contact, hospital_email=hospital_email,
            hospital_website=hospital_website,
            status=PrescriptionStatus.COMPLETED,
            notes="Complete the entire course of antibiotics.",
        ))
        db.add(PrescriptionMedication(
            id=uid(), prescription_id=rx_id4,
            name="Amoxicillin", dosage="500mg", frequency="Three times daily",
            duration="7 days", instructions="Complete entire course even if symptoms improve",
            refills_remaining=0, start_date="Feb 15, 2023", end_date="Feb 22, 2023",
        ))

        # Completed prescription 2
        rx_id5 = uid()
        db.add(Prescription(
            id=rx_id5, prescription_id="RX-2023-0019",
            patient_id=patient_id,
            date=datetime(2023, 1, 25),
            doctor="Dr. Emily Rodriguez", doctor_license="SMC-DR-2023-0019",
            department="Pulmonology",
            hospital_name=hospital_name, hospital_address=hospital_address,
            hospital_contact=hospital_contact, hospital_email=hospital_email,
            hospital_website=hospital_website,
            status=PrescriptionStatus.COMPLETED,
        ))
        db.add(PrescriptionMedication(
            id=uid(), prescription_id=rx_id5,
            name="Montelukast", dosage="10mg", frequency="Once daily at bedtime",
            duration="30 days", instructions="Take at the same time each day",
            refills_remaining=0, start_date="Jan 25, 2023", end_date="Feb 24, 2023",
        ))
        db.add(PrescriptionMedication(
            id=uid(), prescription_id=rx_id5,
            name="Albuterol Inhaler", dosage="90mcg/puff", frequency="As needed",
            duration="30 days", instructions="2 puffs every 4-6 hours as needed for breathing difficulty",
            refills_remaining=0, start_date="Jan 25, 2023", end_date="Feb 24, 2023",
        ))

        # Bought prescription
        rx_id6 = uid()
        db.add(Prescription(
            id=rx_id6, prescription_id="RX-2023-0012",
            patient_id=patient_id,
            date=datetime(2023, 1, 10),
            doctor="Dr. Robert Kim", doctor_license="SMC-DR-2023-0012",
            department="Gastroenterology",
            hospital_name=hospital_name, hospital_address=hospital_address,
            hospital_contact=hospital_contact, hospital_email=hospital_email,
            hospital_website=hospital_website,
            status=PrescriptionStatus.BOUGHT,
        ))
        db.add(PrescriptionMedication(
            id=uid(), prescription_id=rx_id6,
            name="Omeprazole", dosage="20mg", frequency="Once daily before breakfast",
            duration="14 days", instructions="Take 30 minutes before eating",
            refills_remaining=1, start_date="Jan 10, 2023", end_date="Jan 24, 2023",
        ))

        # One more active prescription
        rx_id7 = uid()
        db.add(Prescription(
            id=rx_id7, prescription_id="RX-2023-0063",
            patient_id=patient_id,
            date=datetime(2023, 5, 20),
            doctor="Dr. James Wilson", doctor_license="SMC-DR-2023-0063",
            department="Internal Medicine",
            hospital_name=hospital_name, hospital_address=hospital_address,
            hospital_contact=hospital_contact, hospital_email=hospital_email,
            hospital_website=hospital_website,
            status=PrescriptionStatus.ACTIVE,
            notes="Monitor blood glucose levels regularly.",
        ))
        db.add(PrescriptionMedication(
            id=uid(), prescription_id=rx_id7,
            name="Metformin", dosage="500mg", frequency="Twice daily",
            duration="3 months", instructions="Take with meals",
            refills_remaining=3, start_date="May 20, 2023", end_date="Aug 20, 2023",
        ))

        # ──────────────────────────────────────────────
        # 9. Admissions (with related admissions for transfers)
        # ──────────────────────────────────────────────
        # First admission - Orthopedics (original)
        admission1_id = uid()
        db.add(Admission(
            id=admission1_id, patient_id=patient_id,
            admission_date=datetime(2023, 2, 18),
            discharge_date=datetime(2023, 2, 20),
            department="Orthopedics",
            ward="W-401", bed_number="B-15",
            attending_doctor="Dr. Michael Chang",
            reason="Right femur fracture - surgical repair",
            diagnosis="Right femur fracture requiring ORIF",
            status="Discharged",
            notes="Successful ORIF procedure",
            program_duration_days=2,
            discharge_summary="Patient underwent successful open reduction internal fixation (ORIF) of right femur. Post-op recovery uneventful.",
            discharge_instructions="Rest, physical therapy, follow-up in 2 weeks",
        ))

        # Second admission - Rehabilitation (transferred from Orthopedics)
        admission2_id = uid()
        db.add(Admission(
            id=admission2_id, patient_id=patient_id,
            admission_date=datetime(2023, 2, 20),
            discharge_date=datetime(2023, 3, 15),
            department="Physical Medicine and Rehabilitation",
            ward="R-103", bed_number="B-07",
            attending_doctor="Dr. Jessica Williams",
            reason="Intensive rehabilitation following right femur ORIF",
            diagnosis="Post-surgical rehabilitation of right femur fracture",
            status="Discharged",
            notes="Excellent progress in rehabilitation",
            program_duration_days=23,
            related_admission_id=admission1_id,
            transferred_from_department="Orthopedics",
            referring_doctor="Dr. Michael Chang",
            discharge_summary="Patient completed rehabilitation program successfully. Full weight bearing achieved. Range of motion restored.",
            discharge_instructions="Continue home exercises, outpatient PT 2x/week for 6 weeks",
            follow_up_date=datetime(2023, 3, 29),
        ))

        # Third admission - Cardiology
        admission3_id = uid()
        db.add(Admission(
            id=admission3_id, patient_id=patient_id,
            admission_date=datetime(2023, 5, 15),
            discharge_date=datetime(2023, 5, 18),
            department="Cardiology",
            ward="W-301", bed_number="B-12",
            attending_doctor="Dr. Sarah Johnson",
            reason="Hypertensive crisis evaluation and management",
            diagnosis="Hypertensive crisis - blood pressure 210/120 mmHg",
            status="Discharged",
            notes="BP stabilized with IV medications, transitioned to oral regimen",
            program_duration_days=3,
            discharge_summary="Patient presented with severe hypertension. Managed with IV labetalol, then transitioned to oral medications. BP at discharge: 138/88 mmHg.",
            discharge_instructions="Follow low-sodium diet, take medications as prescribed, monitor BP daily",
        ))

        # Fourth admission - Pulmonology (active)
        admission4_id = uid()
        db.add(Admission(
            id=admission4_id, patient_id=patient_id,
            admission_date=datetime(2023, 8, 10),
            discharge_date=None,
            department="Pulmonology",
            ward="W-205", bed_number="B-04",
            attending_doctor="Dr. Robert Miller",
            reason="Pneumonia - community acquired",
            diagnosis="Community-acquired pneumonia, right lower lobe",
            status="Active",
            notes="Started on IV antibiotics, responding well to treatment",
            program_duration_days=None,
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
        # 10. Reports (Investigation Reports)
        # ──────────────────────────────────────────────
        # Pending report - LFT
        report1_id = uid()
        db.add(Report(
            id=report1_id, patient_id=patient_id,
            date=datetime(2023, 5, 15), time="09:30 AM",
            title="Liver Function Test (LFT)", type="Laboratory",
            department="Pathology", ordered_by="Dr. Sarah Johnson",
            performed_by="Lab Tech. Sarah Johnson",
            supervised_by="Dr. Emily Rodriguez",
            status=ReportStatus.PENDING,
            result_summary="Results pending",
        ))

        # Completed report - CBC with findings and images
        report2_id = uid()
        db.add(Report(
            id=report2_id, patient_id=patient_id,
            date=datetime(2023, 5, 10), time="11:45 AM",
            title="Complete Blood Count (CBC)", type="Laboratory",
            department="Pathology", ordered_by="Dr. Sarah Johnson",
            performed_by="Lab Tech. Michael Wong",
            supervised_by="Dr. Emily Rodriguez",
            status=ReportStatus.NORMAL,
            result_summary="All values within normal limits.",
        ))
        # CBC findings
        db.add(ReportFinding(id=uid(), report_id=report2_id, parameter="Hemoglobin", value="14.2 g/dL", reference="13.5-17.5 g/dL", status="Normal"))
        db.add(ReportFinding(id=uid(), report_id=report2_id, parameter="WBC Count", value="7.5 x 10^9/L", reference="4.5-11.0 x 10^9/L", status="Normal"))
        db.add(ReportFinding(id=uid(), report_id=report2_id, parameter="Platelet Count", value="250 x 10^9/L", reference="150-450 x 10^9/L", status="Normal"))
        db.add(ReportFinding(id=uid(), report_id=report2_id, parameter="RBC Count", value="4.8 x 10^12/L", reference="4.5-5.5 x 10^12/L", status="Normal"))
        db.add(ReportFinding(id=uid(), report_id=report2_id, parameter="Hematocrit", value="42%", reference="38-50%", status="Normal"))
        # CBC image
        db.add(ReportImage(
            id=uid(), report_id=report2_id,
            title="Blood Smear Analysis",
            description="Peripheral blood smear showing normal red blood cells, white blood cells, and platelets under 100x magnification.",
            url="https://upload.wikimedia.org/wikipedia/commons/thumb/8/82/Sickle_cell_anemia.jpg/220px-Sickle_cell_anemia.jpg",
            type="Blood Smear",
        ))

        # Abnormal report - Lipid Profile
        report3_id = uid()
        db.add(Report(
            id=report3_id, patient_id=patient_id,
            date=datetime(2023, 3, 22), time="09:15 AM",
            title="Lipid Profile", type="Laboratory",
            department="Pathology", ordered_by="Dr. James Wilson",
            performed_by="Lab Tech. Jennifer Lee",
            supervised_by="Dr. Emily Rodriguez",
            status=ReportStatus.ABNORMAL,
            result_summary="LDL cholesterol elevated.",
        ))
        # Lipid profile findings
        db.add(ReportFinding(id=uid(), report_id=report3_id, parameter="Total Cholesterol", value="242 mg/dL", reference="<200 mg/dL", status="High"))
        db.add(ReportFinding(id=uid(), report_id=report3_id, parameter="LDL Cholesterol", value="158 mg/dL", reference="<100 mg/dL", status="High"))
        db.add(ReportFinding(id=uid(), report_id=report3_id, parameter="HDL Cholesterol", value="52 mg/dL", reference=">40 mg/dL", status="Normal"))
        db.add(ReportFinding(id=uid(), report_id=report3_id, parameter="Triglycerides", value="140 mg/dL", reference="<150 mg/dL", status="Normal"))
        db.add(ReportImage(
            id=uid(), report_id=report3_id,
            title="Lipid Analysis Chart",
            description="Graphical representation of lipid levels.",
            url="https://via.placeholder.com/400x300?text=Lipid+Analysis",
            type="Chart",
        ))

        # Radiology report - X-Ray Chest
        report4_id = uid()
        db.add(Report(
            id=report4_id, patient_id=patient_id,
            date=datetime(2023, 2, 28), time="11:00 AM",
            title="X-Ray - Chest", type="Radiology",
            department="Radiology", ordered_by="Dr. James Wilson",
            performed_by="Rad. Tech. David Brown",
            supervised_by="Dr. Robert Kim",
            status=ReportStatus.NORMAL,
            result_summary="No acute cardiopulmonary abnormality.",
        ))
        db.add(ReportFinding(id=uid(), report_id=report4_id, parameter="Heart Size", value="Normal", reference="Normal", status="Normal"))
        db.add(ReportFinding(id=uid(), report_id=report4_id, parameter="Lung Fields", value="Clear", reference="Clear", status="Normal"))
        db.add(ReportFinding(id=uid(), report_id=report4_id, parameter="Mediastinum", value="Normal", reference="Normal", status="Normal"))
        db.add(ReportImage(
            id=uid(), report_id=report4_id,
            title="PA Chest X-Ray",
            description="Posteroanterior view of chest showing normal heart size and clear lung fields.",
            url="https://upload.wikimedia.org/wikipedia/commons/thumb/c/c6/Chest_Xray_PA_3-8-2010.png/220px-Chest_Xray_PA_3-8-2010.png",
            type="X-Ray",
        ))
        db.add(ReportImage(
            id=uid(), report_id=report4_id,
            title="Lateral Chest X-Ray",
            description="Lateral view of chest.",
            url="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e9/Medical_X-Ray_imaging_NJR04_nevridge_left_lateral.png/220px-Medical_X-Ray_imaging_NJR04_nevridge_left_lateral.png",
            type="X-Ray",
        ))

        # Thyroid Function Test
        report5_id = uid()
        db.add(Report(
            id=report5_id, patient_id=patient_id,
            date=datetime(2023, 4, 5), time="10:30 AM",
            title="Thyroid Function Test", type="Laboratory",
            department="Pathology", ordered_by="Dr. Sarah Johnson",
            performed_by="Lab Tech. Maria Garcia",
            supervised_by="Dr. Emily Rodriguez",
            status=ReportStatus.NORMAL,
            result_summary="Thyroid function within normal limits.",
        ))
        db.add(ReportFinding(id=uid(), report_id=report5_id, parameter="TSH", value="2.1 mIU/L", reference="0.4-4.0 mIU/L", status="Normal"))
        db.add(ReportFinding(id=uid(), report_id=report5_id, parameter="T4 (Free)", value="1.2 ng/dL", reference="0.8-1.8 ng/dL", status="Normal"))
        db.add(ReportFinding(id=uid(), report_id=report5_id, parameter="T3 (Free)", value="3.0 pg/mL", reference="2.3-4.2 pg/mL", status="Normal"))

        # Kidney Function Test
        report6_id = uid()
        db.add(Report(
            id=report6_id, patient_id=patient_id,
            date=datetime(2023, 1, 18), time="08:45 AM",
            title="Kidney Function Test", type="Laboratory",
            department="Pathology", ordered_by="Dr. James Wilson",
            performed_by="Lab Tech. Robert Chen",
            supervised_by="Dr. Emily Rodriguez",
            status=ReportStatus.NORMAL,
            result_summary="Kidney function normal.",
        ))
        db.add(ReportFinding(id=uid(), report_id=report6_id, parameter="Creatinine", value="0.9 mg/dL", reference="0.7-1.3 mg/dL", status="Normal"))
        db.add(ReportFinding(id=uid(), report_id=report6_id, parameter="BUN", value="15 mg/dL", reference="7-20 mg/dL", status="Normal"))
        db.add(ReportFinding(id=uid(), report_id=report6_id, parameter="eGFR", value="95 mL/min", reference=">90 mL/min", status="Normal"))

        # Urinalysis
        report7_id = uid()
        db.add(Report(
            id=report7_id, patient_id=patient_id,
            date=datetime(2023, 4, 20), time="02:30 PM",
            title="Urinalysis", type="Laboratory",
            department="Pathology", ordered_by="Dr. Sarah Johnson",
            performed_by="Lab Tech. Sarah Johnson",
            supervised_by="Dr. Emily Rodriguez",
            status=ReportStatus.NORMAL,
            result_summary="No abnormalities detected.",
        ))
        db.add(ReportFinding(id=uid(), report_id=report7_id, parameter="pH", value="6.0", reference="5.0-8.0", status="Normal"))
        db.add(ReportFinding(id=uid(), report_id=report7_id, parameter="Protein", value="Negative", reference="Negative", status="Normal"))
        db.add(ReportFinding(id=uid(), report_id=report7_id, parameter="Glucose", value="Negative", reference="Negative", status="Normal"))

        # ECG
        report8_id = uid()
        db.add(Report(
            id=report8_id, patient_id=patient_id,
            date=datetime(2023, 5, 8), time="03:15 PM",
            title="Electrocardiogram (ECG)", type="Cardiology",
            department="Cardiology", ordered_by="Dr. James Wilson",
            performed_by="Cardio Tech. Lisa Wong",
            supervised_by="Dr. James Wilson",
            status=ReportStatus.NORMAL,
            result_summary="Normal sinus rhythm.",
        ))
        db.add(ReportFinding(id=uid(), report_id=report8_id, parameter="Heart Rate", value="72 bpm", reference="60-100 bpm", status="Normal"))
        db.add(ReportFinding(id=uid(), report_id=report8_id, parameter="PR Interval", value="160 ms", reference="120-200 ms", status="Normal"))
        db.add(ReportFinding(id=uid(), report_id=report8_id, parameter="QRS Duration", value="90 ms", reference="<120 ms", status="Normal"))
        db.add(ReportFinding(id=uid(), report_id=report8_id, parameter="QTc Interval", value="420 ms", reference="<450 ms", status="Normal"))
        db.add(ReportImage(
            id=uid(), report_id=report8_id,
            title="ECG Tracing",
            description="12-lead ECG showing normal sinus rhythm.",
            url="https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/SinusRhythmLabels.svg/300px-SinusRhythmLabels.svg.png",
            type="ECG",
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
        # 13. Case Records and Approvals (comprehensive data)
        # ──────────────────────────────────────────────
        # Pending Case Record Approvals (8 pending as per mockup)
        pending_case_records = [
            {
                "patient_idx": 0,  # John Doe
                "type": "Echocardiogram",
                "procedure_name": "Echocardiogram",
                "procedure_description": "Routine echocardiogram to assess cardiac function following medication adjustment.",
                "doctor_name": "Dr. Michael Chang",
                "days_ago": 0,
                "time": "09:30 AM",
            },
            {
                "patient_idx": 1,  # Emily Wilson
                "type": "Spirometry Test",
                "procedure_name": "Spirometry",
                "procedure_description": "Pulmonary function testing to evaluate asthma control.",
                "doctor_name": "Dr. Sarah Johnson",
                "days_ago": 0,
                "time": "10:00 AM",
            },
            {
                "patient_idx": 2,  # Maria Garcia
                "type": "HbA1c Monitoring",
                "procedure_name": "HbA1c Blood Test",
                "procedure_description": "Quarterly glucose control assessment for diabetes management.",
                "doctor_name": "Dr. Emily Watson",
                "days_ago": 1,
                "time": "11:30 AM",
            },
            {
                "patient_idx": 3,  # Robert Chen
                "type": "Chest X-Ray Review",
                "procedure_name": "Chest Radiograph",
                "procedure_description": "Follow-up imaging for bronchitis resolution assessment.",
                "doctor_name": "Dr. James Wilson",
                "days_ago": 1,
                "time": "02:00 PM",
            },
            {
                "patient_idx": 4,  # Lisa Thompson
                "type": "Neurological Exam",
                "procedure_name": "Neurological Assessment",
                "procedure_description": "Comprehensive neurological examination for migraine management.",
                "doctor_name": "Dr. Robert Kim",
                "days_ago": 2,
                "time": "09:00 AM",
            },
            {
                "patient_idx": 0,  # John Doe (second case)
                "type": "Blood Pressure Monitoring",
                "procedure_name": "24-Hour BP Monitoring",
                "procedure_description": "Ambulatory blood pressure assessment for hypertension control.",
                "doctor_name": "Dr. Sarah Johnson",
                "days_ago": 2,
                "time": "03:30 PM",
            },
            {
                "patient_idx": 1,  # Emily Wilson (second case)
                "type": "Allergy Testing",
                "procedure_name": "Skin Prick Test",
                "procedure_description": "Comprehensive allergy panel to identify asthma triggers.",
                "doctor_name": "Dr. Michael Chang",
                "days_ago": 3,
                "time": "10:30 AM",
            },
            {
                "patient_idx": 3,  # Robert Chen (second case)
                "type": "Physical Examination",
                "procedure_name": "General Physical",
                "procedure_description": "Routine physical examination and wellness check.",
                "doctor_name": "Dr. Sarah Johnson",
                "days_ago": 3,
                "time": "11:00 AM",
            },
        ]

        pending_cr_ids = []
        for cr_data in pending_case_records:
            cr_id = uid()
            pending_cr_ids.append(cr_id)
            patient_info = extra_patients[cr_data["patient_idx"]]
            db.add(CaseRecord(
                id=cr_id,
                patient_id=patient_info[0],
                student_id=student_id,
                date=now - timedelta(days=cr_data["days_ago"]),
                time=cr_data["time"],
                type=cr_data["type"],
                description=cr_data["procedure_description"],
                procedure_name=cr_data["procedure_name"],
                procedure_description=cr_data["procedure_description"],
                doctor_name=cr_data["doctor_name"],
                department="Cardiology",
                findings="Pending review",
                diagnosis="Awaiting faculty approval",
                treatment="To be determined",
                notes="Case submitted for faculty review",
                provider="Sarah Smith (Student)",
                status="Pending",
            ))
            
            # Create pending approval for each case record
            db.add(Approval(
                id=uid(),
                approval_type=ApprovalType.CASE_RECORD,
                case_record_id=cr_id,
                faculty_id=faculty_id,
                patient_id=patient_info[0],
                student_id=student_id,
                status=ApprovalStatus.PENDING,
                created_at=now - timedelta(days=cr_data["days_ago"]),
            ))

        # Approval History (Approved and Rejected case records)
        history_case_records = [
            {
                "patient_idx": 0,  # John Doe
                "type": "Physical Examination",
                "procedure_name": "Physical Examination",
                "status": "APPROVED",
                "score": 4,
                "days_ago": 7,
            },
            {
                "patient_idx": 2,  # Maria Garcia
                "type": "Blood Glucose Monitoring",
                "procedure_name": "Blood Glucose Monitoring",
                "status": "REJECTED",
                "score": None,
                "days_ago": 8,
            },
            {
                "patient_idx": 3,  # Robert Chen
                "type": "ECG Interpretation",
                "procedure_name": "ECG Interpretation",
                "status": "APPROVED",
                "score": 5,
                "days_ago": 10,
            },
        ]

        for cr_data in history_case_records:
            cr_id = uid()
            patient_info = extra_patients[cr_data["patient_idx"]]
            db.add(CaseRecord(
                id=cr_id,
                patient_id=patient_info[0],
                student_id=student_id,
                date=now - timedelta(days=cr_data["days_ago"]),
                time="09:30 AM",
                type=cr_data["type"],
                description=f"Case record for {cr_data['type'].lower()}",
                procedure_name=cr_data["procedure_name"],
                doctor_name="Dr. Sarah Johnson",
                department="Cardiology",
                provider="Sarah Smith (Student)",
                status=cr_data["status"].capitalize(),
                approved_by="Dr. Sarah Johnson",
                approved_at=(now - timedelta(days=cr_data["days_ago"] - 1)).strftime("%Y-%m-%d %I:%M %p"),
            ))
            
            db.add(Approval(
                id=uid(),
                approval_type=ApprovalType.CASE_RECORD,
                case_record_id=cr_id,
                faculty_id=faculty_id,
                patient_id=patient_info[0],
                student_id=student_id,
                status=ApprovalStatus.APPROVED if cr_data["status"] == "APPROVED" else ApprovalStatus.REJECTED,
                score=cr_data["score"],
                comments="Good clinical documentation" if cr_data["status"] == "APPROVED" else "Needs more detail",
                created_at=now - timedelta(days=cr_data["days_ago"]),
                processed_at=now - timedelta(days=cr_data["days_ago"] - 1),
            ))

        # Discharge Summary Approvals (3 pending)
        for i, patient_info in enumerate(extra_patients[:3]):
            db.add(Approval(
                id=uid(),
                approval_type=ApprovalType.DISCHARGE_SUMMARY,
                faculty_id=faculty_id,
                patient_id=patient_info[0],
                student_id=student_id,
                status=ApprovalStatus.PENDING,
                created_at=now - timedelta(days=i),
            ))

        # Admission Approvals (5 pending)
        for i, patient_info in enumerate(extra_patients):
            db.add(Approval(
                id=uid(),
                approval_type=ApprovalType.ADMISSION,
                faculty_id=faculty_id,
                patient_id=patient_info[0],
                student_id=student_id,
                status=ApprovalStatus.PENDING,
                created_at=now - timedelta(days=i),
            ))

        # Prescription Approvals (12 pending)
        for i in range(12):
            patient_info = extra_patients[i % len(extra_patients)]
            db.add(Approval(
                id=uid(),
                approval_type=ApprovalType.PRESCRIPTION,
                faculty_id=faculty_id,
                patient_id=patient_info[0],
                student_id=student_id,
                status=ApprovalStatus.PENDING,
                created_at=now - timedelta(days=i % 5),
            ))

        await db.commit()
        print("✅ Database seeded successfully!")
        print("   Test credentials: p/p (Patient), s/s (Student), t/t (Faculty)")


if __name__ == "__main__":
    asyncio.run(seed())
