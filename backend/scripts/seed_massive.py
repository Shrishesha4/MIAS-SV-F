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
    "Endocrinology", "Rheumatology", "Hematology", "Infectious Diseases",
    "Neonatology", "Physical Medicine & Rehabilitation", "Community Medicine",
    "Dental Surgery", "Prosthodontics", "Oral Medicine", "Periodontics",
    "Conservative Dentistry", "Oral & Maxillofacial Surgery", "Orthodontics",
    "Pediatric Dentistry",
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
        main_seeded = result.scalar() > 0
        if main_seeded:
            print("\n  ℹ️  Main data exists. Running supplementary phases only...\n")
            await _seed_supplementary(db, now, start_date)
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

        # ── Run supplementary phases (clinics, labs, assignments, sessions) ──
        await _seed_supplementary(db, now, start_date)

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


async def _seed_supplementary(db, now, start_date):
    """Phases 7-10: Clinics, Labs (with tests/groups), Student assignments, Clinic sessions."""

    # ── Reference data ────────────────────────────────────────────────────
    fac_r = await db.execute(text("SELECT id FROM faculty"))
    faculty_ids = [r[0] for r in fac_r.fetchall()]
    stu_r = await db.execute(text("SELECT id FROM students"))
    student_ids = [r[0] for r in stu_r.fetchall()]
    pat_r = await db.execute(text("SELECT id FROM patients LIMIT 50000"))
    patient_ids = [r[0] for r in pat_r.fetchall()]

    if not faculty_ids or not student_ids or not patient_ids:
        print("  ⚠️  Missing reference data. Run main seed first.")
        return

    print(f"\n  📋 Reference: {len(faculty_ids)} faculty, {len(student_ids)} students, {len(patient_ids):,} patients")

    # ── Clinic definitions (45) ───────────────────────────────────────────
    CLINIC_DEFS = [
        ("General Medicine Clinic", "Internal Medicine", "A", "General", "WALK_IN"),
        ("Diabetes & Metabolic Clinic", "Internal Medicine", "A", "Specialty", "APPOINTMENT_ONLY"),
        ("Infectious Diseases Clinic", "Infectious Diseases", "A", "Specialty", "APPOINTMENT_ONLY"),
        ("Cardiology OPD", "Cardiology", "B", "Specialty", "APPOINTMENT_ONLY"),
        ("Heart Failure Clinic", "Cardiology", "B", "Specialty", "APPOINTMENT_ONLY"),
        ("Preventive Cardiology Clinic", "Cardiology", "B", "Specialty", "APPOINTMENT_ONLY"),
        ("Pediatrics OPD", "Pediatrics", "C", "General", "WALK_IN"),
        ("Well-Baby Clinic", "Pediatrics", "C", "Specialty", "APPOINTMENT_ONLY"),
        ("Neonatology Clinic", "Neonatology", "C", "Specialty", "APPOINTMENT_ONLY"),
        ("Orthopedics OPD", "Orthopedics", "D", "General", "WALK_IN"),
        ("Sports Medicine Clinic", "Orthopedics", "D", "Specialty", "APPOINTMENT_ONLY"),
        ("Spine Clinic", "Orthopedics", "D", "Specialty", "APPOINTMENT_ONLY"),
        ("Surgery OPD", "General Surgery", "E", "General", "WALK_IN"),
        ("Minor Procedures Clinic", "General Surgery", "E", "General", "WALK_IN"),
        ("Wound Care Clinic", "General Surgery", "E", "Specialty", "WALK_IN"),
        ("Neurology OPD", "Neurology", "F", "Specialty", "APPOINTMENT_ONLY"),
        ("Headache Clinic", "Neurology", "F", "Specialty", "APPOINTMENT_ONLY"),
        ("Epilepsy Clinic", "Neurology", "F", "Specialty", "APPOINTMENT_ONLY"),
        ("Dermatology OPD", "Dermatology", "G", "General", "WALK_IN"),
        ("Cosmetic Dermatology Clinic", "Dermatology", "G", "Specialty", "APPOINTMENT_ONLY"),
        ("Allergy Clinic", "Dermatology", "G", "Specialty", "WALK_IN"),
        ("Eye OPD", "Ophthalmology", "H", "General", "WALK_IN"),
        ("Retina Clinic", "Ophthalmology", "H", "Specialty", "APPOINTMENT_ONLY"),
        ("ENT OPD", "ENT", "I", "General", "WALK_IN"),
        ("Audiology Clinic", "ENT", "I", "Specialty", "APPOINTMENT_ONLY"),
        ("Voice & Swallowing Clinic", "ENT", "I", "Specialty", "APPOINTMENT_ONLY"),
        ("Gynecology OPD", "Gynecology", "J", "General", "WALK_IN"),
        ("Antenatal Clinic", "Gynecology", "J", "Specialty", "WALK_IN"),
        ("Fertility Clinic", "Gynecology", "J", "Specialty", "APPOINTMENT_ONLY"),
        ("Urology OPD", "Urology", "K", "General", "WALK_IN"),
        ("Psychiatry OPD", "Psychiatry", "L", "Specialty", "APPOINTMENT_ONLY"),
        ("De-addiction Clinic", "Psychiatry", "L", "Specialty", "APPOINTMENT_ONLY"),
        ("Pulmonology OPD", "Pulmonology", "M", "General", "WALK_IN"),
        ("Asthma Clinic", "Pulmonology", "M", "Specialty", "APPOINTMENT_ONLY"),
        ("GI OPD", "Gastroenterology", "N", "General", "WALK_IN"),
        ("Liver Clinic", "Gastroenterology", "N", "Specialty", "APPOINTMENT_ONLY"),
        ("Nephrology OPD", "Nephrology", "O", "General", "WALK_IN"),
        ("Dialysis Clinic", "Nephrology", "O", "Specialty", "WALK_IN"),
        ("Medical Oncology OPD", "Oncology", "P", "Specialty", "APPOINTMENT_ONLY"),
        ("Pain Management Clinic", "Anesthesiology", "Q", "Specialty", "APPOINTMENT_ONLY"),
        ("Emergency Clinic", "Emergency Medicine", "R", "General", "WALK_IN"),
        ("Plastic Surgery OPD", "Plastic Surgery", "S", "Specialty", "APPOINTMENT_ONLY"),
        ("Endocrinology OPD", "Endocrinology", "T", "Specialty", "APPOINTMENT_ONLY"),
        ("Rheumatology OPD", "Rheumatology", "T", "Specialty", "APPOINTMENT_ONLY"),
        ("Dental Surgery OPD", "Dental Surgery", "U", "General", "WALK_IN"),
    ]

    # ── Lab definitions (40) ──────────────────────────────────────────────
    LAB_DEFS = [
        ("Central Hematology Lab", "Pathology", "Hematology", "A"),
        ("Biochemistry Lab", "Pathology", "Biochemistry", "A"),
        ("Clinical Chemistry Lab", "Pathology", "Clinical Chemistry", "A"),
        ("Serology & Immunology Lab", "Pathology", "Immunology", "B"),
        ("Microbiology Lab", "Microbiology", "Microbiology", "B"),
        ("Bacteriology Lab", "Microbiology", "Microbiology", "B"),
        ("Virology Lab", "Microbiology", "Virology", "C"),
        ("Parasitology Lab", "Microbiology", "Parasitology", "C"),
        ("Mycology Lab", "Microbiology", "Mycology", "C"),
        ("Histopathology Lab", "Pathology", "Histopathology", "D"),
        ("Cytopathology Lab", "Pathology", "Cytology", "D"),
        ("Molecular Biology Lab", "Pathology", "Molecular Biology", "D"),
        ("Genetics Lab", "Pathology", "Genetics", "E"),
        ("Flow Cytometry Lab", "Pathology", "Hematology", "E"),
        ("Coagulation Lab", "Pathology", "Hematology", "E"),
        ("Blood Bank", "Pathology", "Blood Bank", "F"),
        ("Urinalysis Lab", "Pathology", "Urinalysis", "F"),
        ("Toxicology Lab", "Pathology", "Toxicology", "F"),
        ("Hormones Lab", "Pathology", "Endocrinology", "G"),
        ("Cardiac Markers Lab", "Pathology", "Cardiology", "G"),
        ("X-Ray Lab", "Radiology", "Radiology", "H"),
        ("CT Scan Lab", "Radiology", "Radiology", "H"),
        ("MRI Lab", "Radiology", "Radiology", "H"),
        ("Ultrasound Lab", "Radiology", "Radiology", "I"),
        ("Mammography Lab", "Radiology", "Radiology", "I"),
        ("Fluoroscopy Lab", "Radiology", "Radiology", "I"),
        ("Nuclear Medicine Lab", "Radiology", "Nuclear Medicine", "J"),
        ("PET-CT Lab", "Radiology", "Nuclear Medicine", "J"),
        ("Interventional Radiology Lab", "Radiology", "Radiology", "J"),
        ("Dental Radiology Lab", "Radiology", "Dentistry", "K"),
        ("ECG Lab", "General", "Cardiology", "K"),
        ("EEG Lab", "General", "Neurology", "K"),
        ("EMG/NCV Lab", "General", "Neurology", "L"),
        ("Pulmonary Function Lab", "General", "Pulmonology", "L"),
        ("Audiometry Lab", "General", "ENT", "L"),
        ("Sleep Study Lab", "General", "Pulmonology", "M"),
        ("Endoscopy Lab", "General", "Gastroenterology", "M"),
        ("Cardiac Catheterization Lab", "General", "Cardiology", "M"),
        ("Dialysis Lab", "General", "Nephrology", "N"),
        ("Physiotherapy Lab", "General", "Rehabilitation", "N"),
    ]

    # ── Test name pools ───────────────────────────────────────────────────
    PATHOLOGY_TESTS = [
        "Complete Blood Count", "Hemoglobin", "WBC Differential", "Platelet Count",
        "ESR", "Reticulocyte Count", "Peripheral Smear", "PT/INR", "aPTT", "D-Dimer",
        "LFT", "RFT", "Lipid Profile", "Blood Sugar (F)", "Blood Sugar (PP)", "HbA1c",
        "Thyroid Panel", "Electrolytes", "Serum Calcium", "Iron Studies", "Vitamin D",
        "Vitamin B12", "CRP", "Troponin I", "BNP", "Ferritin", "Uric Acid", "PSA",
        "Blood Culture", "Urine Culture", "Sputum Culture", "Gram Stain", "AFB Stain",
        "FNAC", "Biopsy H&E", "PAP Smear", "IHC", "Flow Cytometry",
        "Urine Routine", "Stool Routine", "HIV Antibody", "HBsAg", "Anti-HCV",
        "ANA", "RA Factor", "Procalcitonin", "Widal Test", "Dengue NS1",
    ]
    RADIOLOGY_TESTS = [
        "Chest X-Ray PA", "X-Ray Lateral", "Abdomen X-Ray", "X-Ray Extremity",
        "CT Brain Plain", "CT Brain Contrast", "CT Abdomen", "CT Chest HRCT",
        "MRI Brain", "MRI Spine Cervical", "MRI Spine Lumbar", "MRI Knee",
        "USG Abdomen", "USG Pelvis", "USG Obstetric", "Doppler USG",
        "Echocardiography", "Mammography", "Fluoroscopy Barium", "DEXA Scan",
        "OPG Dental", "IOPA Dental", "PET-CT", "Thyroid Scan", "Bone Scan",
        "CT Angiography", "MRI Abdomen", "MRI Shoulder", "X-Ray Pelvis", "X-Ray Spine",
    ]
    GENERAL_TESTS = [
        "12-Lead ECG", "Holter Monitor 24hr", "Treadmill Test", "EEG Routine",
        "EEG Sleep-Deprived", "Video EEG", "EMG", "Nerve Conduction", "Spirometry",
        "DLCO", "Peak Flow", "Bronchial Challenge", "Audiometry", "Impedance Audio",
        "BERA", "Polysomnography", "Upper GI Endoscopy", "Colonoscopy", "ERCP",
        "Cardiac Catheterization", "Coronary Angiography", "Hemodialysis Session",
        "Peritoneal Dialysis", "Physio Assessment", "Gait Analysis", "ROM Assessment",
    ]

    # ══════════════════════════════════════════════════════════════════════
    # ── PHASE 7: 45 Clinics ──────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════
    clinic_count = (await db.execute(text("SELECT COUNT(*) FROM clinics"))).scalar()
    clinic_ids = []

    if clinic_count >= 45:
        print("\n  🏥 Phase 7: Clinics already seeded.")
        cr = await db.execute(text("SELECT id FROM clinics"))
        clinic_ids = [r[0] for r in cr.fetchall()]
    else:
        print(f"\n  🏥 Phase 7: Creating {len(CLINIC_DEFS)} clinics...")
        existing_names_r = await db.execute(text("SELECT name FROM clinics"))
        existing_names = {r[0] for r in existing_names_r.fetchall()}

        for i, (name, dept, block, ctype, access) in enumerate(CLINIC_DEFS):
            if name in existing_names:
                continue
            cid = uid()
            clinic_ids.append(cid)
            fac_id = faculty_ids[i % len(faculty_ids)]
            walk_in = "GENERAL" if access == "WALK_IN" else "NO_WALK_IN"
            await db.execute(text(
                "INSERT INTO clinics (id, name, block, clinic_type, access_mode, walk_in_type, "
                "department, location, faculty_id, is_active, created_at, updated_at) "
                "VALUES (:id, :name, :block, :ctype, :access, :walk, :dept, :loc, :fac, true, :now, :now)"
            ), {
                "id": cid, "name": name, "block": f"Block {block}",
                "ctype": ctype, "access": access, "walk": walk_in, "dept": dept,
                "loc": f"Block {block}, Floor {1 + i % 3}", "fac": fac_id, "now": now,
            })

        cr = await db.execute(text("SELECT id FROM clinics"))
        clinic_ids = [r[0] for r in cr.fetchall()]
        await db.commit()
        print(f"    ✓ {len(clinic_ids)} total clinics")

    # ══════════════════════════════════════════════════════════════════════
    # ── PHASE 8: 40 Labs + 4 Tests + 2 Groups Each ──────────────────────
    # ══════════════════════════════════════════════════════════════════════
    lab_count = (await db.execute(text("SELECT COUNT(*) FROM labs"))).scalar()
    lab_ids = []

    if lab_count >= 40:
        print("\n  🔬 Phase 8: Labs already seeded.")
        lr = await db.execute(text("SELECT id FROM labs"))
        lab_ids = [r[0] for r in lr.fetchall()]
    else:
        print(f"\n  🔬 Phase 8: Creating {len(LAB_DEFS)} labs with tests & groups...")
        existing_lab_names_r = await db.execute(text("SELECT name FROM labs"))
        existing_lab_names = {r[0] for r in existing_lab_names_r.fetchall()}

        new_labs = 0
        for i, (name, lab_type, dept, block) in enumerate(LAB_DEFS):
            if name in existing_lab_names:
                continue
            lid = uid()
            lab_ids.append(lid)
            new_labs += 1

            await db.execute(text(
                "INSERT INTO labs (id, name, block, lab_type, department, location, "
                "is_active, created_at, updated_at) "
                "VALUES (:id, :name, :block, :ltype, :dept, :loc, true, :now, :now)"
            ), {
                "id": lid, "name": name, "block": f"Block {block}",
                "ltype": lab_type, "dept": dept,
                "loc": f"Block {block}, Floor {1 + i % 3}", "now": now,
            })

            # Pick 4 tests from appropriate pool
            pool = (PATHOLOGY_TESTS if lab_type == "Pathology"
                    else RADIOLOGY_TESTS if lab_type == "Radiology"
                    else GENERAL_TESTS)
            offset = (i * 4) % len(pool)
            test_names = [pool[(offset + j) % len(pool)] for j in range(4)]
            sample = "Blood" if lab_type == "Pathology" else "N/A"
            tat = "2 hours" if lab_type == "Pathology" else "1 hour"

            test_ids = []
            for j, tname in enumerate(test_names):
                tid = uid()
                test_ids.append(tid)
                await db.execute(text(
                    "INSERT INTO lab_tests (id, lab_id, name, code, category, "
                    "sample_type, turnaround_time, is_active, created_at, updated_at) "
                    "VALUES (:id, :lab_id, :name, :code, :cat, :sample, :tat, true, :now, :now)"
                ), {
                    "id": tid, "lab_id": lid, "name": tname,
                    "code": f"L{i+1:02d}T{j+1:02d}", "cat": dept,
                    "sample": sample, "tat": tat, "now": now,
                })

            # Create 2 groups: tests 0,1 in group 1; tests 2,3 in group 2
            focus = name.replace(" Lab", "").replace("Central ", "").strip()
            for g in range(2):
                gid = uid()
                gname = f"{'Routine' if g == 0 else 'Comprehensive'} {focus} Panel"
                await db.execute(text(
                    "INSERT INTO lab_test_groups (id, lab_id, name, description, "
                    "is_active, created_at, updated_at) "
                    "VALUES (:id, :lab_id, :name, :desc, true, :now, :now)"
                ), {
                    "id": gid, "lab_id": lid, "name": gname,
                    "desc": f"Standard {'routine' if g == 0 else 'comprehensive'} panel for {focus}",
                    "now": now,
                })
                # Add 2 tests to each group
                for t_idx in range(2):
                    await db.execute(text(
                        "INSERT INTO lab_test_group_members (group_id, test_id) "
                        "VALUES (:gid, :tid)"
                    ), {"gid": gid, "tid": test_ids[g * 2 + t_idx]})

        lr = await db.execute(text("SELECT id FROM labs"))
        lab_ids = [r[0] for r in lr.fetchall()]
        await db.commit()
        print(f"    ✓ {len(lab_ids)} labs, {new_labs * 4} tests, {new_labs * 2} groups")

    # ══════════════════════════════════════════════════════════════════════
    # ── PHASE 9: Student Patient Assignments ─────────────────────────────
    # ══════════════════════════════════════════════════════════════════════
    assign_count = (await db.execute(text("SELECT COUNT(*) FROM student_patient_assignments"))).scalar()

    if assign_count >= 2000:
        print(f"\n  📋 Phase 9: Student assignments exist ({assign_count:,}). Skipping.")
    else:
        print("\n  📋 Phase 9: Generating student patient assignments...")
        assign_records = []
        for si, sid in enumerate(student_ids):
            num_patients = random.randint(15, 50)
            for j in range(num_patients):
                pi = (si * 53 + j * 7) % len(patient_ids)  # spread across pool
                assign_date = random_date_in_range(start_date, now)
                is_active = j < 5  # First 5 are active, rest completed
                assign_records.append({
                    "id": uid(), "student_id": sid,
                    "patient_id": patient_ids[pi],
                    "assigned_date": assign_date,
                    "status": "Active" if is_active else "Completed",
                })

        await execute_batch(db,
            "INSERT INTO student_patient_assignments (id, student_id, patient_id, assigned_date, status) "
            "VALUES (:id, :student_id, :patient_id, :assigned_date, :status)",
            assign_records, "Assignments")
        await db.commit()
        print(f"    ✓ {len(assign_records):,} student patient assignments")
        del assign_records

    # ══════════════════════════════════════════════════════════════════════
    # ── PHASE 10: Clinic Sessions ────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════
    session_count = (await db.execute(text("SELECT COUNT(*) FROM clinic_sessions"))).scalar()

    if session_count >= 5000:
        print(f"\n  🗓️  Phase 10: Clinic sessions exist ({session_count:,}). Skipping.")
    else:
        print("\n  🗓️  Phase 10: Generating clinic sessions...")
        clinic_r = await db.execute(text("SELECT id, name, department FROM clinics"))
        clinic_data = [(r[0], r[1], r[2]) for r in clinic_r.fetchall()]
        if not clinic_data:
            print("    ⚠️  No clinics found. Skipping sessions.")
        else:
            session_records = []
            time_slots = [("09:00", "12:00"), ("10:00", "13:00"),
                          ("14:00", "17:00"), ("13:00", "16:00")]

            for si, sid in enumerate(student_ids):
                num_sessions = random.randint(30, 60)
                for j in range(num_sessions):
                    sess_date = random_date_in_range(start_date, now)
                    clinic = clinic_data[(si + j) % len(clinic_data)]
                    slot = time_slots[j % len(time_slots)]
                    is_past = sess_date < now - timedelta(days=1)

                    if is_past:
                        status = "Completed"
                        checked_in = sess_date.replace(hour=random.randint(8, 10), minute=random.randint(0, 30))
                        checked_out = checked_in + timedelta(hours=random.randint(2, 4))
                        verified_fac = faculty_ids[(si + j) % len(faculty_ids)]
                    else:
                        status = random.choice(["Scheduled", "Active"])
                        checked_in = sess_date.replace(hour=9) if status == "Active" else None
                        checked_out = None
                        verified_fac = None

                    session_records.append({
                        "id": uid(), "student_id": sid,
                        "clinic_id": clinic[0], "clinic_name": clinic[1],
                        "department": clinic[2], "date": sess_date,
                        "time_start": slot[0], "time_end": slot[1],
                        "status": status, "is_selected": 0,
                        "checked_in_at": checked_in,
                        "checked_out_at": checked_out,
                        "verified_by_faculty_id": verified_fac,
                    })

            await execute_batch(db,
                "INSERT INTO clinic_sessions (id, student_id, clinic_id, clinic_name, department, "
                "date, time_start, time_end, status, is_selected, checked_in_at, checked_out_at, "
                "verified_by_faculty_id) "
                "VALUES (:id, :student_id, :clinic_id, :clinic_name, :department, "
                ":date, :time_start, :time_end, :status, :is_selected, :checked_in_at, :checked_out_at, "
                ":verified_by_faculty_id)",
                session_records, "Clinic Sessions")
            await db.commit()
            print(f"    ✓ {len(session_records):,} clinic sessions")
            del session_records

    print("\n  ✅ Supplementary seed phases complete.")


if __name__ == "__main__":
    asyncio.run(seed_massive())
