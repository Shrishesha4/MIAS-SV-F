"""
Massive-scale seeding script for MIAS.
Generates ~50,000 patients, ~500,000 OT procedures, ~200,000 case records,
~150,000 lab reports over a 3-month period.

Uses raw SQL bulk inserts for performance (asyncpg copy_records_to_table).
Run: docker compose exec backend python scripts/seed_massive.py
All bulk user passwords: "bulk" (single precomputed hash for speed)
"""
import asyncio
import uuid
import random
import sys
import os
from datetime import datetime, date, timedelta
from itertools import islice

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal, engine
from app.core.security import get_password_hash
from sqlalchemy import text

# ── Constants ────────────────────────────────────────────────────────────────
BULK_PASSWORD_HASH = None  # Computed once at startup
NUM_PATIENTS = 50_000
NUM_OT_PROCEDURES = 500_000
NUM_CASE_RECORDS = 200_000
NUM_REPORTS = 150_000
NUM_ADMISSIONS = 80_000
NUM_FACULTY = 50
NUM_STUDENTS = 200
BATCH_SIZE = 5_000
THREE_MONTHS_AGO = datetime.utcnow() - timedelta(days=90)

DEPARTMENTS = [
    "Internal Medicine", "Cardiology", "Pediatrics", "Orthopedics",
    "General Surgery", "Neurology", "Dermatology", "Ophthalmology",
    "ENT", "Gynecology", "Urology", "Psychiatry", "Pulmonology",
    "Gastroenterology", "Nephrology", "Oncology", "Radiology",
    "Anesthesiology", "Emergency Medicine", "Plastic Surgery",
]
WARDS = [
    "General Ward A", "General Ward B", "General Ward C", "General Ward D",
    "ICU", "NICU", "HDU", "PICU", "Private Ward 1", "Private Ward 2",
    "Emergency Ward", "Burns Ward", "Maternity Ward", "Pediatric Ward",
]
PROCEDURES_OT = [
    "Appendectomy", "Cholecystectomy", "Hernia Repair", "LSCS",
    "Knee Replacement", "Hip Replacement", "Cataract Surgery",
    "Tonsillectomy", "Mastectomy", "Thyroidectomy", "Coronary Bypass",
    "Angioplasty", "Craniotomy", "Spinal Fusion", "Laparoscopic Surgery",
    "Hysterectomy", "Prostatectomy", "Rhinoplasty", "Septoplasty",
    "Nephrectomy", "Colectomy", "Gastrectomy", "Lobectomy",
    "Valve Replacement", "Pacemaker Insertion", "Arthroscopy",
    "Fracture Fixation (ORIF)", "Skin Grafting", "Debridement",
    "Tracheostomy", "Drainage of Abscess", "Biopsy (excisional)",
]
DIAGNOSES = [
    "Essential Hypertension", "Type 2 Diabetes Mellitus", "Acute Bronchitis",
    "Viral Gastroenteritis", "Iron Deficiency Anaemia", "Migraine",
    "COPD", "Unstable Angina", "Community Acquired Pneumonia", "UTI",
    "Dengue Fever", "Cellulitis", "Acute Appendicitis", "Fracture",
    "Acute Pancreatitis", "CKD Stage 3", "DVT", "DKA",
    "Seizure Disorder", "Allergic Rhinitis", "Bronchial Asthma",
    "Peptic Ulcer Disease", "Cholelithiasis", "Hypothyroidism",
    "Rheumatoid Arthritis", "Osteoarthritis", "Normal Delivery",
    "LSCS", "Neonatal Jaundice", "Preterm Birth", "Stroke",
    "Myocardial Infarction", "Pulmonary Embolism", "Sepsis",
    "Meningitis", "Tuberculosis", "Malaria", "Typhoid Fever",
]
CASE_TYPES = [
    "Physical Examination", "Follow-up", "Counselling", "Procedure",
    "Lab Review", "Admission Note", "Discharge Summary", "Progress Note",
    "Consultation", "Emergency Assessment",
]
REPORT_TYPES = ["Laboratory", "Radiology", "Microbiology", "Pathology"]
REPORT_TITLES = {
    "Laboratory": ["CBC", "LFT", "RFT", "Lipid Profile", "Thyroid Panel",
                   "HbA1c", "Blood Sugar (F)", "Blood Sugar (PP)", "Electrolytes",
                   "Coagulation Profile", "Urine Routine", "ESR", "CRP",
                   "D-Dimer", "Troponin I", "BNP", "Iron Studies", "Vitamin D",
                   "Vitamin B12", "Serum Calcium"],
    "Radiology": ["Chest X-Ray", "CT Abdomen", "MRI Brain", "USG Abdomen",
                  "X-Ray Knee", "CT Chest", "MRI Spine", "CT Head",
                  "X-Ray Pelvis", "Echocardiogram", "Doppler USG"],
    "Microbiology": ["Blood Culture", "Urine Culture", "Sputum Culture",
                     "Wound Swab C/S", "Stool Culture", "CSF Culture",
                     "Pleural Fluid Culture"],
    "Pathology": ["Biopsy - Skin", "FNAC Thyroid", "Histopathology",
                  "Pap Smear", "Bone Marrow Aspiration", "FNAC Lymph Node",
                  "Cervical Biopsy"],
}
BLOOD_GROUPS = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]
GENDERS = ["MALE", "FEMALE"]
CATEGORIES = ["Classic", "Prime", "Elite", "Community"]
CATEGORY_COLORS = {
    "Classic": ("#60A5FA", "#1D4ED8"),
    "Prime": ("#34D399", "#059669"),
    "Elite": ("#F59E0B", "#D97706"),
    "Community": ("#A78BFA", "#7C3AED"),
}
OT_STATUSES = ["COMPLETED", "COMPLETED", "COMPLETED", "COMPLETED",
               "SCHEDULED", "CONFIRMED", "CANCELLED"]
REPORT_STATUSES = ["NORMAL", "NORMAL", "ABNORMAL", "PENDING"]


def uid():
    return str(uuid.uuid4())


def random_date_in_range(start: datetime, end: datetime) -> datetime:
    delta = (end - start).total_seconds()
    offset = random.random() * delta
    return start + timedelta(seconds=offset)


def name_from_index(i: int) -> str:
    """Generate A, B, ..., Z, AA, AB, ..., AZ, BA, ..."""
    if i < 26:
        return chr(65 + i)
    first = chr(65 + (i // 26) - 1)
    second = chr(65 + (i % 26))
    return f"{first}{second}"


def batched(iterable, n):
    """Batch data into lists of length n."""
    it = iter(iterable)
    while True:
        batch = list(islice(it, n))
        if not batch:
            break
        yield batch


async def execute_batch(db, query: str, records: list[dict], label: str = ""):
    """Execute batch insert in chunks."""
    total = len(records)
    inserted = 0
    for batch in batched(records, BATCH_SIZE):
        await db.execute(text(query), batch)
        inserted += len(batch)
        if inserted % 20_000 == 0 or inserted == total:
            print(f"    {label}: {inserted:,}/{total:,} ({100*inserted//total}%)")


async def seed_massive():
    global BULK_PASSWORD_HASH

    print("\n🚀 MASSIVE SEED — Generating hospital data at scale\n")
    print(f"  Patients:       {NUM_PATIENTS:>10,}")
    print(f"  OT Procedures:  {NUM_OT_PROCEDURES:>10,}")
    print(f"  Case Records:   {NUM_CASE_RECORDS:>10,}")
    print(f"  Lab Reports:    {NUM_REPORTS:>10,}")
    print(f"  Admissions:     {NUM_ADMISSIONS:>10,}")
    print(f"  Time Span:      3 months")
    print()

    # Precompute single password hash for all bulk users
    print("  🔑 Computing password hash...")
    BULK_PASSWORD_HASH = get_password_hash("bulk")

    now = datetime.utcnow()
    start_date = THREE_MONTHS_AGO

    async with AsyncSessionLocal() as db:
        # Check if massive seed already ran
        result = await db.execute(text(
            "SELECT COUNT(*) FROM users WHERE username = 'bp_00001'"
        ))
        if result.scalar() > 0:
            print("\n  ℹ️  Massive seed already exists. Skipping.\n")
            return

        # ── Get existing reference data ──────────────────────────────────
        print("\n  📋 Fetching existing reference data...")

        # Get existing OT theaters (create more if needed)
        ot_result = await db.execute(text("SELECT id FROM operation_theaters"))
        theater_ids = [r[0] for r in ot_result.fetchall()]

        if len(theater_ids) < 10:
            print("    Creating 10 operation theaters...")
            for i in range(10 - len(theater_ids)):
                tid = uid()
                await db.execute(text(
                    "INSERT INTO operation_theaters (id, ot_id, name, location, is_active, created_at) "
                    "VALUES (:id, :ot_id, :name, :location, true, :now)"
                ), {"id": tid, "ot_id": f"OT-{len(theater_ids)+i+1:02d}",
                    "name": f"OT {len(theater_ids)+i+1}", "location": f"Block {chr(65+i)}, Floor 2", "now": now})
                theater_ids.append(tid)

        # Get/create faculty for references
        fac_result = await db.execute(text("SELECT id, name FROM faculty"))
        existing_faculty = [(r[0], r[1]) for r in fac_result.fetchall()]
        faculty_ids = [f[0] for f in existing_faculty]
        faculty_names = [f[1] for f in existing_faculty]

        if len(faculty_ids) < NUM_FACULTY:
            print(f"    Creating {NUM_FACULTY - len(faculty_ids)} additional faculty...")
            new_faculty = []
            for i in range(NUM_FACULTY - len(faculty_ids)):
                fid = uid()
                user_id = uid()
                idx = len(faculty_ids) + i + 1
                dept = DEPARTMENTS[i % len(DEPARTMENTS)]
                name = f"Dr. {name_from_index(i)}"
                await db.execute(text(
                    "INSERT INTO users (id, username, email, password_hash, role, is_active, created_at, updated_at) "
                    "VALUES (:id, :un, :em, :ph, 'FACULTY', true, :now, :now)"
                ), {"id": user_id, "un": f"bf{idx}", "em": f"bf{idx}@saveetha.com",
                    "ph": BULK_PASSWORD_HASH, "now": now})
                await db.execute(text(
                    "INSERT INTO faculty (id, faculty_id, user_id, name, department, specialty, availability_status) "
                    "VALUES (:id, :fid, :uid, :name, :dept, :spec, 'Available')"
                ), {"id": fid, "fid": f"FAC-B{idx:03d}", "uid": user_id,
                    "name": name, "dept": dept, "spec": dept})
                faculty_ids.append(fid)
                faculty_names.append(name)

        # Get/create students for references
        stu_result = await db.execute(text("SELECT id, name FROM students"))
        existing_students = [(r[0], r[1]) for r in stu_result.fetchall()]
        student_ids = [s[0] for s in existing_students]

        if len(student_ids) < NUM_STUDENTS:
            print(f"    Creating {NUM_STUDENTS - len(student_ids)} additional students...")
            for i in range(NUM_STUDENTS - len(student_ids)):
                sid = uid()
                user_id = uid()
                idx = len(student_ids) + i + 1
                await db.execute(text(
                    "INSERT INTO users (id, username, email, password_hash, role, is_active, created_at, updated_at) "
                    "VALUES (:id, :un, :em, :ph, 'STUDENT', true, :now, :now)"
                ), {"id": user_id, "un": f"bs{idx}", "em": f"bs{idx}@saveetha.com",
                    "ph": BULK_PASSWORD_HASH, "now": now})
                await db.execute(text(
                    "INSERT INTO students (id, student_id, user_id, name, year, semester, program, gpa) "
                    "VALUES (:id, :sid, :uid, :name, :yr, :sem, 'BDS', :gpa)"
                ), {"id": sid, "sid": f"STU-B{idx:03d}", "uid": user_id,
                    "name": f"Student {name_from_index(i)}", "yr": random.randint(1, 4),
                    "sem": random.randint(1, 8), "gpa": round(random.uniform(7.0, 9.5), 1)})
                student_ids.append(sid)

        await db.commit()
        print(f"    ✓ {len(theater_ids)} theaters, {len(faculty_ids)} faculty, {len(student_ids)} students")

        # ══════════════════════════════════════════════════════════════════
        # ── PHASE 1: Generate 50,000 Patients ────────────────────────────
        # ══════════════════════════════════════════════════════════════════
        print("\n  👥 Phase 1: Generating patients...")

        patient_ids = []
        user_records = []
        patient_records = []

        for i in range(NUM_PATIENTS):
            pid = uid()
            user_id = uid()
            patient_ids.append(pid)
            idx = i + 1
            gender = GENDERS[i % 2]
            cat = CATEGORIES[i % 4]
            cp, cs = CATEGORY_COLORS[cat]
            dob = date(1940 + (i % 60), (i % 12) + 1, (i % 28) + 1)

            user_records.append({
                "id": user_id, "username": f"bp_{idx:05d}",
                "email": f"bp_{idx:05d}@bulk.local",
                "password_hash": BULK_PASSWORD_HASH,
                "role": "PATIENT", "is_active": True,
                "created_at": now, "updated_at": now,
            })
            patient_records.append({
                "id": pid, "patient_id": f"BP{idx:06d}",
                "user_id": user_id, "name": f"Patient {name_from_index(i % 702)}_{idx}",
                "date_of_birth": dob, "gender": gender,
                "blood_group": BLOOD_GROUPS[i % 8],
                "phone": f"+91 9{idx:09d}", "email": f"bp_{idx:05d}@bulk.local",
                "address": f"{idx} Bulk Street, Chennai",
                "category": cat,
                "category_color_primary": cp,
                "category_color_secondary": cs,
                "is_deceased": False,
                "created_at": now, "updated_at": now,
            })

        user_insert = text(
            "INSERT INTO users (id, username, email, password_hash, role, is_active, created_at, updated_at) "
            "VALUES (:id, :username, :email, :password_hash, :role, :is_active, :created_at, :updated_at)"
        )
        patient_insert = text(
            "INSERT INTO patients (id, patient_id, user_id, name, date_of_birth, gender, "
            "blood_group, phone, email, address, category, category_color_primary, "
            "category_color_secondary, is_deceased, created_at, updated_at) "
            "VALUES (:id, :patient_id, :user_id, :name, :date_of_birth, :gender, "
            ":blood_group, :phone, :email, :address, :category, :category_color_primary, "
            ":category_color_secondary, :is_deceased, :created_at, :updated_at)"
        )

        await execute_batch(db, str(user_insert), user_records, "Users")
        await execute_batch(db, str(patient_insert), patient_records, "Patients")
        await db.commit()
        print(f"    ✓ {NUM_PATIENTS:,} patients created")

        del user_records, patient_records  # Free memory

        # ══════════════════════════════════════════════════════════════════
        # ── PHASE 2: Generate 80,000 Admissions ──────────────────────────
        # ══════════════════════════════════════════════════════════════════
        print("\n  🏥 Phase 2: Generating admissions...")

        admission_ids = []
        admission_records = []

        for i in range(NUM_ADMISSIONS):
            aid = uid()
            admission_ids.append(aid)
            pat_id = patient_ids[i % NUM_PATIENTS]
            fac_idx = i % len(faculty_ids)
            stu_idx = i % len(student_ids)
            dept = DEPARTMENTS[i % len(DEPARTMENTS)]
            ward = WARDS[i % len(WARDS)]
            diag = DIAGNOSES[i % len(DIAGNOSES)]
            adm_date = random_date_in_range(start_date, now)
            is_discharged = i < int(NUM_ADMISSIONS * 0.7)  # 70% discharged
            discharge_date = adm_date + timedelta(days=random.randint(2, 14)) if is_discharged else None
            is_birth = "Delivery" in diag or "LSCS" in diag or "Neonatal" in diag
            is_death = i % 500 == 0 and is_discharged  # ~0.2% mortality

            admission_records.append({
                "id": aid, "patient_id": pat_id,
                "submitted_by_student_id": student_ids[stu_idx],
                "faculty_approver_id": faculty_ids[fac_idx],
                "admission_date": adm_date,
                "discharge_date": discharge_date,
                "department": dept, "ward": ward,
                "bed_number": f"{ward[0]}-{(i % 30)+1:02d}",
                "attending_doctor": faculty_names[fac_idx],
                "reason": f"Admitted for {diag}",
                "diagnosis": diag,
                "status": "Discharged" if is_discharged else "Active",
                "chief_complaints": f"Presenting with {diag.lower()}",
                "provisional_diagnosis": diag,
                "bp_admission": f"{random.randint(110,160)}/{random.randint(60,95)}",
                "heart_rate_admission": str(random.randint(60, 110)),
                "spo2_admission": str(random.randint(92, 100)),
                "is_birth_related": is_birth,
                "discharge_summary": ("Patient expired." if is_death else
                                      "Recovered. Discharged." if is_discharged else None),
                "discharge_type": ("DEATH" if is_death else
                                   "REGULAR" if is_discharged else None),
                "created_at": adm_date,
            })

        admission_insert = text(
            "INSERT INTO admissions (id, patient_id, submitted_by_student_id, faculty_approver_id, "
            "admission_date, discharge_date, department, ward, bed_number, attending_doctor, "
            "reason, diagnosis, status, chief_complaints, provisional_diagnosis, "
            "bp_admission, heart_rate_admission, spo2_admission, is_birth_related, "
            "discharge_summary, discharge_type, created_at) "
            "VALUES (:id, :patient_id, :submitted_by_student_id, :faculty_approver_id, "
            ":admission_date, :discharge_date, :department, :ward, :bed_number, :attending_doctor, "
            ":reason, :diagnosis, :status, :chief_complaints, :provisional_diagnosis, "
            ":bp_admission, :heart_rate_admission, :spo2_admission, :is_birth_related, "
            ":discharge_summary, :discharge_type, :created_at)"
        )

        await execute_batch(db, str(admission_insert), admission_records, "Admissions")
        await db.commit()
        print(f"    ✓ {NUM_ADMISSIONS:,} admissions created")
        del admission_records

        # ══════════════════════════════════════════════════════════════════
        # ── PHASE 3: Generate 500,000 OT Procedures ─────────────────────
        # ══════════════════════════════════════════════════════════════════
        print("\n  🔪 Phase 3: Generating OT procedures...")

        ot_records = []
        for i in range(NUM_OT_PROCEDURES):
            proc_date = random_date_in_range(start_date, now)
            hour = 7 + (i % 14)  # 07:00 to 20:00
            duration = random.choice([1, 1, 2, 2, 3, 4])
            status = OT_STATUSES[i % len(OT_STATUSES)]

            ot_records.append({
                "id": uid(),
                "theater_id": theater_ids[i % len(theater_ids)],
                "patient_id": patient_ids[i % NUM_PATIENTS],
                "student_id": student_ids[i % len(student_ids)] if i % 3 != 0 else None,
                "date": proc_date.strftime("%Y-%m-%d"),
                "start_time": f"{hour:02d}:{(i*7)%60:02d}",
                "end_time": f"{hour+duration:02d}:{(i*7)%60:02d}",
                "procedure": PROCEDURES_OT[i % len(PROCEDURES_OT)],
                "doctor_name": faculty_names[i % len(faculty_names)],
                "notes": None,
                "status": status,
                "approved_by": faculty_ids[i % len(faculty_ids)] if status in ("COMPLETED", "CONFIRMED") else None,
                "approved_at": proc_date if status in ("COMPLETED", "CONFIRMED") else None,
                "created_at": proc_date,
            })

            # Flush in batches to avoid memory explosion
            if len(ot_records) >= BATCH_SIZE:
                await db.execute(text(
                    "INSERT INTO ot_bookings (id, theater_id, patient_id, student_id, date, "
                    "start_time, end_time, procedure, doctor_name, notes, status, "
                    "approved_by, approved_at, created_at) "
                    "VALUES (:id, :theater_id, :patient_id, :student_id, :date, "
                    ":start_time, :end_time, :procedure, :doctor_name, :notes, :status, "
                    ":approved_by, :approved_at, :created_at)"
                ), ot_records)
                if (i + 1) % 50_000 == 0:
                    await db.commit()
                    print(f"    OT Procedures: {i+1:,}/{NUM_OT_PROCEDURES:,} ({100*(i+1)//NUM_OT_PROCEDURES}%)")
                ot_records = []

        if ot_records:
            await db.execute(text(
                "INSERT INTO ot_bookings (id, theater_id, patient_id, student_id, date, "
                "start_time, end_time, procedure, doctor_name, notes, status, "
                "approved_by, approved_at, created_at) "
                "VALUES (:id, :theater_id, :patient_id, :student_id, :date, "
                ":start_time, :end_time, :procedure, :doctor_name, :notes, :status, "
                ":approved_by, :approved_at, :created_at)"
            ), ot_records)

        await db.commit()
        print(f"    ✓ {NUM_OT_PROCEDURES:,} OT procedures created")

        # ══════════════════════════════════════════════════════════════════
        # ── PHASE 4: Generate 200,000 Case Records ──────────────────────
        # ══════════════════════════════════════════════════════════════════
        print("\n  📝 Phase 4: Generating case records...")

        cr_records = []
        for i in range(NUM_CASE_RECORDS):
            cr_date = random_date_in_range(start_date, now)
            status = "Approved" if i % 4 != 0 else "Pending"
            dept = DEPARTMENTS[i % len(DEPARTMENTS)]
            diag = DIAGNOSES[i % len(DIAGNOSES)]
            cr_type = CASE_TYPES[i % len(CASE_TYPES)]

            cr_records.append({
                "id": uid(),
                "patient_id": patient_ids[i % NUM_PATIENTS],
                "student_id": student_ids[i % len(student_ids)],
                "date": cr_date,
                "type": cr_type,
                "description": f"Patient assessed for {diag}. Findings documented.",
                "procedure_name": cr_type,
                "department": dept,
                "findings": f"Clinical findings consistent with {diag}.",
                "diagnosis": diag,
                "treatment": f"Managed per protocol for {diag}.",
                "status": status,
                "grade": random.choice(["A", "A-", "B+", "B", "B-"]) if status == "Approved" else None,
                "doctor_name": faculty_names[i % len(faculty_names)],
                "created_by_name": f"Student {name_from_index(i % 200)}",
                "created_by_role": "STUDENT",
                "created_at": cr_date,
            })

            if len(cr_records) >= BATCH_SIZE:
                await db.execute(text(
                    "INSERT INTO case_records (id, patient_id, student_id, date, type, "
                    "description, procedure_name, department, findings, diagnosis, "
                    "treatment, status, grade, doctor_name, created_by_name, created_by_role, created_at) "
                    "VALUES (:id, :patient_id, :student_id, :date, :type, "
                    ":description, :procedure_name, :department, :findings, :diagnosis, "
                    ":treatment, :status, :grade, :doctor_name, :created_by_name, :created_by_role, :created_at)"
                ), cr_records)
                if (i + 1) % 50_000 == 0:
                    await db.commit()
                    print(f"    Case Records: {i+1:,}/{NUM_CASE_RECORDS:,} ({100*(i+1)//NUM_CASE_RECORDS}%)")
                cr_records = []

        if cr_records:
            await db.execute(text(
                "INSERT INTO case_records (id, patient_id, student_id, date, type, "
                "description, procedure_name, department, findings, diagnosis, "
                "treatment, status, grade, doctor_name, created_by_name, created_by_role, created_at) "
                "VALUES (:id, :patient_id, :student_id, :date, :type, "
                ":description, :procedure_name, :department, :findings, :diagnosis, "
                ":treatment, :status, :grade, :doctor_name, :created_by_name, :created_by_role, :created_at)"
            ), cr_records)

        await db.commit()
        print(f"    ✓ {NUM_CASE_RECORDS:,} case records created")

        # ══════════════════════════════════════════════════════════════════
        # ── PHASE 5: Generate 150,000 Lab Reports ────────────────────────
        # ══════════════════════════════════════════════════════════════════
        print("\n  🧪 Phase 5: Generating lab/investigation reports...")

        report_records = []
        for i in range(NUM_REPORTS):
            rtype = REPORT_TYPES[i % len(REPORT_TYPES)]
            titles = REPORT_TITLES[rtype]
            title = titles[i % len(titles)]
            report_date = random_date_in_range(start_date, now)
            dept = DEPARTMENTS[i % len(DEPARTMENTS)]
            status = REPORT_STATUSES[i % len(REPORT_STATUSES)]

            report_records.append({
                "id": uid(),
                "patient_id": patient_ids[i % NUM_PATIENTS],
                "date": report_date,
                "time": f"{8 + (i % 12):02d}:{(i*7) % 60:02d}",
                "title": title,
                "type": rtype,
                "department": dept,
                "ordered_by": faculty_names[i % len(faculty_names)],
                "performed_by": f"Tech {name_from_index(i % 26)}",
                "status": status,
                "result_summary": f"{title} - findings within expected range" if status != "PENDING" else None,
                "created_at": report_date,
            })

            if len(report_records) >= BATCH_SIZE:
                await db.execute(text(
                    "INSERT INTO reports (id, patient_id, date, time, title, type, "
                    "department, ordered_by, performed_by, status, result_summary, created_at) "
                    "VALUES (:id, :patient_id, :date, :time, :title, :type, "
                    ":department, :ordered_by, :performed_by, :status, :result_summary, :created_at)"
                ), report_records)
                if (i + 1) % 50_000 == 0:
                    await db.commit()
                    print(f"    Reports: {i+1:,}/{NUM_REPORTS:,} ({100*(i+1)//NUM_REPORTS}%)")
                report_records = []

        if report_records:
            await db.execute(text(
                "INSERT INTO reports (id, patient_id, date, time, title, type, "
                "department, ordered_by, performed_by, status, result_summary, created_at) "
                "VALUES (:id, :patient_id, :date, :time, :title, :type, "
                ":department, :ordered_by, :performed_by, :status, :result_summary, :created_at)"
            ), report_records)

        await db.commit()
        print(f"    ✓ {NUM_REPORTS:,} reports created")

        # ══════════════════════════════════════════════════════════════════
        # ── PHASE 6: Generate Report Findings (for lab reports) ──────────
        # ══════════════════════════════════════════════════════════════════
        print("\n  📊 Phase 6: Generating report findings...")

        # Query lab report IDs for findings
        lab_reports = await db.execute(text(
            "SELECT id FROM reports WHERE type = 'Laboratory' AND status != 'PENDING' "
            "ORDER BY created_at DESC LIMIT 50000"
        ))
        lab_report_ids = [r[0] for r in lab_reports.fetchall()]

        finding_records = []
        findings_params = [
            ("Hemoglobin", "g/dL", 8.0, 16.0, "12-16"),
            ("WBC", "x10³/µL", 3.5, 18.0, "4-11"),
            ("Platelets", "x10³/µL", 100, 450, "150-400"),
            ("RBC", "x10⁶/µL", 3.0, 6.0, "4.5-5.5"),
            ("Creatinine", "mg/dL", 0.5, 4.0, "0.7-1.3"),
            ("Urea", "mg/dL", 10, 80, "15-40"),
            ("SGOT", "U/L", 10, 120, "10-40"),
            ("SGPT", "U/L", 10, 100, "7-56"),
        ]

        for i, report_id in enumerate(lab_report_ids):
            num_findings = random.randint(3, 6)
            for j in range(num_findings):
                param = findings_params[j % len(findings_params)]
                value = round(random.uniform(param[2], param[3]), 1)
                # Determine if abnormal
                ref_parts = param[4].split("-")
                low, high = float(ref_parts[0]), float(ref_parts[1])
                is_abn = value < low or value > high
                status = "High" if value > high else ("Low" if value < low else "Normal")

                finding_records.append({
                    "id": uid(),
                    "report_id": report_id,
                    "parameter": param[0],
                    "value": f"{value} {param[1]}",
                    "reference": param[4] + " " + param[1],
                    "status": status,
                })

            if len(finding_records) >= BATCH_SIZE:
                await db.execute(text(
                    "INSERT INTO report_findings (id, report_id, parameter, value, reference, status) "
                    "VALUES (:id, :report_id, :parameter, :value, :reference, :status)"
                ), finding_records)
                if (i + 1) % 20_000 == 0:
                    await db.commit()
                    print(f"    Findings: processed {i+1:,}/{len(lab_report_ids):,} reports")
                finding_records = []

        if finding_records:
            await db.execute(text(
                "INSERT INTO report_findings (id, report_id, parameter, value, reference, status) "
                "VALUES (:id, :report_id, :parameter, :value, :reference, :status)"
            ), finding_records)

        await db.commit()
        total_findings = len(lab_report_ids) * 4  # approx
        print(f"    ✓ ~{total_findings:,} report findings created")

        # ══════════════════════════════════════════════════════════════════
        # ── Done ─────────────────────────────────────────────────────────
        # ══════════════════════════════════════════════════════════════════
        print("\n" + "=" * 60)
        print("  ✅ MASSIVE SEED COMPLETE")
        print("=" * 60)
        print(f"\n  Total records created:")
        print(f"    Users (patients):    {NUM_PATIENTS:>10,}")
        print(f"    Patients:            {NUM_PATIENTS:>10,}")
        print(f"    Faculty:             {NUM_FACULTY:>10,}")
        print(f"    Students:            {NUM_STUDENTS:>10,}")
        print(f"    Admissions:          {NUM_ADMISSIONS:>10,}")
        print(f"    OT Procedures:       {NUM_OT_PROCEDURES:>10,}")
        print(f"    Case Records:        {NUM_CASE_RECORDS:>10,}")
        print(f"    Lab Reports:         {NUM_REPORTS:>10,}")
        print(f"    Report Findings:     ~{total_findings:>9,}")
        print(f"\n  All bulk patient passwords: 'bulk'")
        print(f"  Usernames: bp_00001 through bp_{NUM_PATIENTS:05d}")
        print(f"  Faculty: bf1 through bf{NUM_FACULTY}")
        print(f"  Students: bs1 through bs{NUM_STUDENTS}")
        print()


if __name__ == "__main__":
    asyncio.run(seed_massive())
