# MIAS-MP: Medical Information Application System
## Comprehensive AI Agent Prompt for Svelte (Frontend) + FastAPI (Backend) + PostgreSQL Implementation

---

# PROJECT OVERVIEW

You are tasked with building **MIAS-MP** (Medical Information Application System - Multi Portal), a production-ready medical information management system for **Saveetha Medical College Hospital**. This application must handle **1,000+ concurrent users** and serves three user roles: **Patients**, **Medical Students**, and **Faculty**.

## Architecture Overview

This application follows a **decoupled architecture** with:
- **Frontend**: Svelte + Vite (TypeScript)
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy (Python) / Prisma (optional for type generation)

Both frontend and backend can be developed **in parallel** by separate teams.

---

## Core Requirements

### Frontend (Svelte + Vite)
1. **Framework**: Svelte 4+ with TypeScript
2. **Build Tool**: Vite
3. **Routing**: svelte-routing or @sveltejs/kit (SPA mode)
4. **Styling**: TailwindCSS with exact Mac OS X Aqua-style skeuomorphic design (DO NOT CHANGE ANY COLORS OR STYLES)
5. **Charts**: Chart.js or similar for vitals charts
6. **HTTP Client**: Axios or Fetch API
7. **State Management**: Svelte stores
8. **Mobile-First**: Max-width 448px (max-w-md) centered layout

### Backend (FastAPI)
1. **Framework**: FastAPI with Python 3.11+
2. **ORM**: SQLAlchemy 2.0+ with async support
3. **Database**: PostgreSQL 15+
4. **Authentication**: JWT-based auth with refresh tokens
5. **Validation**: Pydantic v2
6. **Security**: bcrypt, CORS, rate limiting (slowapi)
7. **Documentation**: Auto-generated OpenAPI/Swagger
8. **Testing**: pytest + httpx

---

# SECTION 1: EXACT DESIGN SYSTEM (DO NOT MODIFY)

## 1.1 Background Pattern (App Container)
```css
background-image: repeating-linear-gradient(
  0deg,
  rgba(180, 190, 210, 0.2),
  rgba(180, 190, 210, 0.2) 1px,
  rgba(210, 220, 230, 0.4) 1px,
  rgba(210, 220, 230, 0.4) 2px
);
background-color: #e0e5eb;
box-shadow: inset 0 0 100px rgba(180, 190, 210, 0.3);
```

## 1.2 Primary Blue Gradient (Buttons, Icons, Accents)
```css
background: linear-gradient(to bottom, #4d90fe, #0066cc);
border: 1px solid rgba(0,0,0,0.2);
box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4);
```

## 1.3 Secondary/Light Button Style
```css
background: linear-gradient(to bottom, #f0f4fa, #d5dde8);
border: 1px solid rgba(0,0,0,0.2);
box-shadow: 0 1px 2px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.8);
```

## 1.4 NavBar Gradient
```css
background-image: linear-gradient(to bottom, #d1dbed, #b8c6df);
box-shadow: 0 1px 3px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.7);
border-bottom: 1px solid rgba(0,0,0,0.2);
```

## 1.5 Card Style
```css
background-color: white;
border-radius: 10px;
box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24), 
            0 0 0 1px rgba(0,0,0,0.05), inset 0 -5px 10px rgba(0,0,0,0.05);
border: 1px solid rgba(0,0,0,0.1);
```

## 1.6 Card Section Header
```css
background-image: linear-gradient(to bottom, #f8f9fb, #d9e1ea);
box-shadow: 0 1px 0 rgba(255,255,255,0.8) inset, 0 1px 0 rgba(0,0,0,0.1);
border-bottom: 1px solid rgba(0,0,0,0.1);
```

## 1.7 Input Field Style
```css
border: 1px solid rgba(0,0,0,0.2);
border-radius: 6px;
background-color: rgba(255,255,255,0.8);
box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
```

## 1.8 Status Colors

### Success/Verified Badge
```css
background: linear-gradient(to bottom, #a7f3d0, #6ee7b7);
border: 1px solid rgba(16,185,129,0.3);
```

### Error/Logout/Red Button
```css
background: linear-gradient(to bottom, #ff5a5a, #cc0000);
/* OR alternative red: */
background: linear-gradient(to bottom, #f87171, #dc2626);
```

### Credit Transaction (Green)
```css
background: linear-gradient(to bottom, #4ade80, #22c55e);
```

### Medical Alert Background
```css
background-color: rgba(255,0,0,0.05);
border: 1px solid rgba(220,50,50,0.2);
```

### Report Status Badges
```css
/* Normal */ background: linear-gradient(to bottom, #34c759, #30b350);
/* Abnormal */ background: linear-gradient(to bottom, #ff9500, #ff5e3a);
/* Critical */ background: linear-gradient(to bottom, #ff3b30, #d70015);
/* Pending */ background: linear-gradient(to bottom, #8e8e93, #636366);
```

## 1.9 Aqua Button Classes (Reusable)
```svelte
<script>
  const aquaButtonStyle = 'relative overflow-hidden transition-all active:translate-y-0.5 active:shadow-inner';
  const aquaGlossEffect = 'before:absolute before:inset-0 before:bg-gradient-to-b before:from-white before:via-transparent before:to-transparent before:opacity-50';
</script>
```

## 1.10 Text Shadows
```css
/* Primary text shadow */
text-shadow: 0 1px 0 rgba(255,255,255,0.7);
/* Links */
text-shadow: 0 1px 0 rgba(255,255,255,0.5);
```

## 1.11 Avatar/Photo Style
```css
border: 2px solid rgba(255,255,255,0.9);
box-shadow: 0 1px 3px rgba(0,0,0,0.2), 0 0 0 1px rgba(0,0,0,0.05);
border-radius: 9999px; /* rounded-full */
```

## 1.12 Side Menu Animation
```css
@keyframes slideInRight {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}
```

## 1.13 Notification Pulse Animation
```css
@keyframes notificationPulse {
  0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 0, 0, 0.7); }
  70% { transform: scale(1.2); box-shadow: 0 0 0 10px rgba(255, 0, 0, 0); }
  100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 0, 0, 0); }
}
```

## 1.14 Tailwind Text Colors Used
- Headings: `text-blue-900`, `text-blue-800`
- Body: `text-gray-800`, `text-gray-700`, `text-gray-600`
- Muted: `text-gray-500`, `text-gray-400`
- Accent: `text-blue-700`, `text-blue-600`, `text-blue-500`
- Error: `text-red-700`, `text-red-600`, `text-red-500`
- Success: `text-green-800`, `text-green-600`
- Warning: `text-yellow-600`, `text-yellow-800`, `text-orange-600`
- Special: `text-purple-600`, `text-purple-800`

---

# SECTION 2: PROJECT STRUCTURE

## 2.1 Monorepo Structure

```
mias-mp/
├── frontend/                      # Svelte + Vite Application
│   ├── public/
│   │   └── hospital-banner.png
│   ├── src/
│   │   ├── lib/
│   │   │   ├── api/               # API client & endpoints
│   │   │   │   ├── client.ts      # Axios/Fetch wrapper
│   │   │   │   ├── auth.ts        # Auth API calls
│   │   │   │   ├── patients.ts    # Patient API calls
│   │   │   │   ├── students.ts    # Student API calls
│   │   │   │   ├── faculty.ts     # Faculty API calls
│   │   │   │   └── types.ts       # API response types
│   │   │   ├── stores/            # Svelte stores
│   │   │   │   ├── auth.ts        # Auth state
│   │   │   │   ├── user.ts        # User data
│   │   │   │   └── notifications.ts
│   │   │   ├── styles/
│   │   │   │   ├── aqua.ts        # Design system constants
│   │   │   │   └── animations.css
│   │   │   └── utils/
│   │   │       ├── formatters.ts
│   │   │       └── helpers.ts
│   │   ├── components/
│   │   │   ├── ui/                # Reusable UI primitives
│   │   │   │   ├── AquaButton.svelte
│   │   │   │   ├── AquaCard.svelte
│   │   │   │   ├── AquaInput.svelte
│   │   │   │   ├── AquaBadge.svelte
│   │   │   │   ├── AquaModal.svelte
│   │   │   │   ├── AquaTabs.svelte
│   │   │   │   ├── Avatar.svelte
│   │   │   │   ├── StatusBadge.svelte
│   │   │   │   ├── ExpandableCard.svelte
│   │   │   │   └── SearchFilter.svelte
│   │   │   ├── layout/
│   │   │   │   ├── NavBar.svelte
│   │   │   │   ├── SideMenu.svelte
│   │   │   │   └── AppShell.svelte
│   │   │   ├── charts/
│   │   │   │   ├── VitalsChart.svelte
│   │   │   │   └── SparklineChart.svelte
│   │   │   └── features/
│   │   │       ├── patient/
│   │   │       ├── wallet/
│   │   │       ├── records/
│   │   │       ├── student/
│   │   │       └── faculty/
│   │   ├── routes/                # Page components
│   │   │   ├── Login.svelte
│   │   │   ├── Dashboard.svelte
│   │   │   ├── StudentDashboard.svelte
│   │   │   ├── FacultyDashboard.svelte
│   │   │   ├── Profile.svelte
│   │   │   ├── Records.svelte
│   │   │   ├── Admissions.svelte
│   │   │   ├── Wallet.svelte
│   │   │   ├── Reports.svelte
│   │   │   ├── Prescriptions.svelte
│   │   │   ├── Vitals.svelte
│   │   │   ├── Notifications.svelte
│   │   │   └── CaseRecord.svelte
│   │   ├── App.svelte
│   │   ├── Router.svelte          # Route definitions
│   │   ├── main.ts
│   │   └── app.css
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── postcss.config.js
│
├── backend/                       # FastAPI Application
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI app entry
│   │   ├── config.py             # Settings & env vars
│   │   ├── database.py           # Database connection
│   │   ├── models/               # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── patient.py
│   │   │   ├── student.py
│   │   │   ├── faculty.py
│   │   │   ├── medical_record.py
│   │   │   ├── admission.py
│   │   │   ├── prescription.py
│   │   │   ├── report.py
│   │   │   ├── vital.py
│   │   │   ├── wallet.py
│   │   │   ├── notification.py
│   │   │   └── case_record.py
│   │   ├── schemas/              # Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── patient.py
│   │   │   ├── student.py
│   │   │   ├── faculty.py
│   │   │   ├── auth.py
│   │   │   └── common.py
│   │   ├── api/                  # API routes
│   │   │   ├── __init__.py
│   │   │   ├── deps.py           # Dependencies (auth, db)
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py     # Main router
│   │   │   │   ├── auth.py
│   │   │   │   ├── patients.py
│   │   │   │   ├── students.py
│   │   │   │   ├── faculty.py
│   │   │   │   ├── vitals.py
│   │   │   │   ├── prescriptions.py
│   │   │   │   ├── reports.py
│   │   │   │   ├── admissions.py
│   │   │   │   ├── wallet.py
│   │   │   │   ├── notifications.py
│   │   │   │   └── approvals.py
│   │   ├── services/             # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── patient.py
│   │   │   ├── student.py
│   │   │   └── faculty.py
│   │   ├── core/                 # Core utilities
│   │   │   ├── __init__.py
│   │   │   ├── security.py       # JWT, password hashing
│   │   │   ├── exceptions.py     # Custom exceptions
│   │   │   └── middleware.py     # Custom middleware
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── helpers.py
│   ├── migrations/               # Alembic migrations
│   │   ├── versions/
│   │   ├── env.py
│   │   └── alembic.ini
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   └── test_patients.py
│   ├── scripts/
│   │   └── seed.py               # Database seeding
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── Dockerfile
│
├── prisma/                        # Optional: Prisma for type generation
│   └── schema.prisma             # Schema reference (not for runtime)
│
├── docker-compose.yml            # Development environment
├── .env.example
└── README.md
```

---

# SECTION 3: DATABASE SCHEMA (SQLAlchemy Models)

## 3.1 Core Models (Python/SQLAlchemy)

```python
# backend/app/models/user.py
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base

class UserRole(str, enum.Enum):
    PATIENT = "PATIENT"
    STUDENT = "STUDENT"
    FACULTY = "FACULTY"
    ADMIN = "ADMIN"

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    patient = relationship("Patient", back_populates="user", uselist=False)
    student = relationship("Student", back_populates="user", uselist=False)
    faculty = relationship("Faculty", back_populates="user", uselist=False)
    refresh_tokens = relationship("RefreshToken", back_populates="user")
```

```python
# backend/app/models/patient.py
from sqlalchemy import Column, String, Date, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base

class Gender(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"

class PatientCategory(str, enum.Enum):
    GENERAL = "GENERAL"
    ELITE = "ELITE"
    VIP = "VIP"
    STAFF = "STAFF"

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(String, primary_key=True)
    patient_id = Column(String, unique=True, nullable=False, index=True)  # SMC-2023-XXXX
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(SQLEnum(Gender), nullable=False)
    blood_group = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String, nullable=True)
    address = Column(String, nullable=False)
    photo = Column(String, nullable=True)
    aadhaar_id = Column(String, nullable=True)  # Masked
    abha_id = Column(String, nullable=True)
    category = Column(SQLEnum(PatientCategory), default=PatientCategory.GENERAL)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="patient")
    emergency_contact = relationship("EmergencyContact", back_populates="patient", uselist=False)
    insurance_policies = relationship("InsurancePolicy", back_populates="patient")
    allergies = relationship("Allergy", back_populates="patient")
    medical_alerts = relationship("MedicalAlert", back_populates="patient")
    admissions = relationship("Admission", back_populates="patient")
    medical_records = relationship("MedicalRecord", back_populates="patient")
    prescriptions = relationship("Prescription", back_populates="patient")
    reports = relationship("Report", back_populates="patient")
    vitals = relationship("Vital", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient")
    notifications = relationship("PatientNotification", back_populates="patient")
    wallet_transactions = relationship("WalletTransaction", back_populates="patient")
    assigned_students = relationship("StudentPatientAssignment", back_populates="patient")
    case_records = relationship("CaseRecord", back_populates="patient")
```

```python
# backend/app/models/student.py
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Student(Base):
    __tablename__ = "students"
    
    id = Column(String, primary_key=True)
    student_id = Column(String, unique=True, nullable=False, index=True)  # SMS-2023-XXXX
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String, nullable=False)
    year = Column(Integer, nullable=False)  # 1-6
    semester = Column(Integer, nullable=False)  # 1-12
    program = Column(String, nullable=False)  # e.g., "MBBS"
    photo = Column(String, nullable=True)
    gpa = Column(Float, nullable=False)
    academic_standing = Column(String, default="Good Standing")
    academic_advisor = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="student")
    emergency_contact = relationship("EmergencyContact", back_populates="student", uselist=False)
    attendance = relationship("StudentAttendance", back_populates="student", uselist=False)
    disciplinary_actions = relationship("DisciplinaryAction", back_populates="student")
    assigned_patients = relationship("StudentPatientAssignment", back_populates="student")
    case_records = relationship("CaseRecord", back_populates="student")
    notifications = relationship("StudentNotification", back_populates="student")
    clinic_sessions = relationship("ClinicSession", back_populates="student")
```

```python
# backend/app/models/faculty.py
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Faculty(Base):
    __tablename__ = "faculty"
    
    id = Column(String, primary_key=True)
    faculty_id = Column(String, unique=True, nullable=False, index=True)  # FAC-2023-XXXX
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String, nullable=False)  # "Dr. FirstName LastName"
    department = Column(String, nullable=False, index=True)
    specialty = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    photo = Column(String, nullable=True)
    availability = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="faculty")
    approvals = relationship("Approval", back_populates="faculty")
    notifications = relationship("FacultyNotification", back_populates="faculty")
```

## 3.2 Medical Records & Supporting Models

```python
# backend/app/models/medical_record.py
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base

class RecordType(str, enum.Enum):
    CONSULTATION = "CONSULTATION"
    LABORATORY = "LABORATORY"
    PROCEDURE = "PROCEDURE"
    MEDICATION = "MEDICATION"

class MedicalRecord(Base):
    __tablename__ = "medical_records"
    
    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    time = Column(String, nullable=False)
    type = Column(SQLEnum(RecordType), nullable=False, index=True)
    description = Column(Text, nullable=False)
    performed_by = Column(String, nullable=False)
    supervised_by = Column(String, nullable=True)
    department = Column(String, nullable=False)
    status = Column(String, nullable=False)
    diagnosis = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)
    evaluation = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient", back_populates="medical_records")
    findings = relationship("MedicalFinding", back_populates="medical_record")
    images = relationship("MedicalImage", back_populates="medical_record")
```

```python
# backend/app/models/vital.py
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Vital(Base):
    __tablename__ = "vitals"
    
    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    recorded_by = Column(String, nullable=True)
    
    # Primary Vitals
    systolic_bp = Column(Integer, nullable=True)  # mmHg
    diastolic_bp = Column(Integer, nullable=True)  # mmHg
    heart_rate = Column(Integer, nullable=True)  # bpm
    respiratory_rate = Column(Integer, nullable=True)  # breaths/min
    temperature = Column(Float, nullable=True)  # °F
    oxygen_saturation = Column(Integer, nullable=True)  # %
    
    # Secondary Vitals
    weight = Column(Float, nullable=True)  # lbs
    blood_glucose = Column(Integer, nullable=True)  # mg/dL
    cholesterol = Column(Integer, nullable=True)  # mg/dL
    bmi = Column(Float, nullable=True)  # kg/m²
    
    # Relationships
    patient = relationship("Patient", back_populates="vitals")
```

```python
# backend/app/models/wallet.py
from sqlalchemy import Column, String, DateTime, Numeric, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base

class WalletType(str, enum.Enum):
    HOSPITAL = "HOSPITAL"
    PHARMACY = "PHARMACY"

class TransactionType(str, enum.Enum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"

class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"
    
    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    wallet_type = Column(SQLEnum(WalletType), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    time = Column(String, nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    type = Column(SQLEnum(TransactionType), nullable=False)
    payment_method = Column(String, nullable=True)
    reference_number = Column(String, nullable=True)
    invoice_number = Column(String, nullable=True)
    department = Column(String, nullable=True)
    provider = Column(String, nullable=True)
    subtotal = Column(Numeric(10, 2), nullable=True)
    tax = Column(Numeric(10, 2), nullable=True)
    insurance_coverage = Column(Numeric(10, 2), nullable=True)
    insurance_provider = Column(String, nullable=True)
    policy_number = Column(String, nullable=True)
    claim_number = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient", back_populates="wallet_transactions")
    items = relationship("TransactionItem", back_populates="transaction")
```

---

# SECTION 4: BACKEND API IMPLEMENTATION (FastAPI)

## 4.1 Application Entry Point

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import engine, Base
from app.api.v1.router import api_router
from app.core.middleware import RateLimitMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()

app = FastAPI(
    title="MIAS-MP API",
    description="Medical Information Application System API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting
app.add_middleware(RateLimitMiddleware)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
```

## 4.2 Configuration

```python
# backend/app/config.py
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # App
    DEBUG: bool = False
    
    class Config:
        env_file = ".env"

settings = Settings()
```

## 4.3 Database Connection

```python
# backend/app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Convert sync URL to async
DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(DATABASE_URL, echo=settings.DEBUG)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

## 4.4 Security & Authentication

```python
# backend/app/core/security.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
```

## 4.5 API Dependencies

```python
# backend/app/api/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.security import decode_token
from app.models.user import User

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    return user

def require_role(*roles):
    async def role_checker(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user
    return role_checker
```

## 4.6 Auth API Routes

```python
# backend/app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest
from app.core.security import (
    verify_password, 
    create_access_token, 
    create_refresh_token,
    decode_token
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Find user
    result = await db.execute(select(User).where(User.username == request.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled"
        )
    
    # Create tokens
    access_token = create_access_token({"sub": user.id, "role": user.role.value})
    refresh_token = create_refresh_token({"sub": user.id})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user_id=user.id,
        role=user.role.value
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(request.refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    access_token = create_access_token({"sub": user.id, "role": user.role.value})
    new_refresh_token = create_refresh_token({"sub": user.id})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        user_id=user.id,
        role=user.role.value
    )

@router.post("/logout")
async def logout():
    # For JWT, logout is handled client-side by removing tokens
    # Optionally implement token blacklisting here
    return {"message": "Successfully logged out"}
```

## 4.7 Patient API Routes

```python
# backend/app/api/v1/patients.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.patient import Patient
from app.models.vital import Vital
from app.models.prescription import Prescription
from app.schemas.patient import PatientResponse, PatientDetailResponse
from app.schemas.vital import VitalResponse, VitalCreate

router = APIRouter(prefix="/patients", tags=["Patients"])

@router.get("/me", response_model=PatientDetailResponse)
async def get_current_patient(
    user: User = Depends(require_role(UserRole.PATIENT)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Patient)
        .options(
            selectinload(Patient.emergency_contact),
            selectinload(Patient.allergies),
            selectinload(Patient.medical_alerts)
        )
        .where(Patient.user_id == user.id)
    )
    patient = result.scalar_one_or_none()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    return patient

@router.get("/{patient_id}", response_model=PatientDetailResponse)
async def get_patient(
    patient_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check permissions
    if user.role == UserRole.PATIENT and user.patient.id != patient_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await db.execute(
        select(Patient)
        .options(
            selectinload(Patient.emergency_contact),
            selectinload(Patient.allergies),
            selectinload(Patient.medical_alerts)
        )
        .where(Patient.id == patient_id)
    )
    patient = result.scalar_one_or_none()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    return patient

@router.get("/{patient_id}/vitals", response_model=List[VitalResponse])
async def get_patient_vitals(
    patient_id: str,
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from datetime import datetime, timedelta
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(
        select(Vital)
        .where(Vital.patient_id == patient_id)
        .where(Vital.recorded_at >= cutoff_date)
        .order_by(Vital.recorded_at.desc())
    )
    
    return result.scalars().all()

@router.post("/{patient_id}/vitals", response_model=VitalResponse)
async def create_vital(
    patient_id: str,
    vital_data: VitalCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    import uuid
    
    vital = Vital(
        id=str(uuid.uuid4()),
        patient_id=patient_id,
        **vital_data.model_dump()
    )
    
    db.add(vital)
    await db.commit()
    await db.refresh(vital)
    
    return vital
```

## 4.8 Main API Router

```python
# backend/app/api/v1/router.py
from fastapi import APIRouter

from app.api.v1 import auth, patients, students, faculty, vitals, prescriptions, reports, admissions, wallet, notifications, approvals

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(patients.router)
api_router.include_router(students.router)
api_router.include_router(faculty.router)
api_router.include_router(vitals.router)
api_router.include_router(prescriptions.router)
api_router.include_router(reports.router)
api_router.include_router(admissions.router)
api_router.include_router(wallet.router)
api_router.include_router(notifications.router)
api_router.include_router(approvals.router)
```

---

# SECTION 5: PYDANTIC SCHEMAS

```python
# backend/app/schemas/auth.py
from pydantic import BaseModel

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
```

```python
# backend/app/schemas/patient.py
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List
from enum import Enum

class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"

class PatientCategory(str, Enum):
    GENERAL = "GENERAL"
    ELITE = "ELITE"
    VIP = "VIP"
    STAFF = "STAFF"

class EmergencyContactResponse(BaseModel):
    id: str
    name: str
    relationship: str
    phone: str
    email: Optional[str]
    
    class Config:
        from_attributes = True

class AllergyResponse(BaseModel):
    id: str
    allergen: str
    severity: str
    reaction: Optional[str]
    
    class Config:
        from_attributes = True

class MedicalAlertResponse(BaseModel):
    id: str
    type: str
    severity: str
    title: str
    description: str
    symptoms: List[str]
    is_active: bool
    
    class Config:
        from_attributes = True

class PatientResponse(BaseModel):
    id: str
    patient_id: str
    name: str
    date_of_birth: date
    gender: Gender
    blood_group: str
    phone: str
    email: Optional[str]
    photo: Optional[str]
    category: PatientCategory
    
    class Config:
        from_attributes = True

class PatientDetailResponse(PatientResponse):
    address: str
    aadhaar_id: Optional[str]
    abha_id: Optional[str]
    emergency_contact: Optional[EmergencyContactResponse]
    allergies: List[AllergyResponse]
    medical_alerts: List[MedicalAlertResponse]
    
    class Config:
        from_attributes = True
```

```python
# backend/app/schemas/vital.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class VitalBase(BaseModel):
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    heart_rate: Optional[int] = None
    respiratory_rate: Optional[int] = None
    temperature: Optional[float] = None
    oxygen_saturation: Optional[int] = None
    weight: Optional[float] = None
    blood_glucose: Optional[int] = None
    cholesterol: Optional[int] = None
    bmi: Optional[float] = None

class VitalCreate(VitalBase):
    recorded_by: Optional[str] = None

class VitalResponse(VitalBase):
    id: str
    patient_id: str
    recorded_at: datetime
    recorded_by: Optional[str]
    
    class Config:
        from_attributes = True
```

---

# SECTION 6: FRONTEND IMPLEMENTATION (Svelte)

## 6.1 API Client

```typescript
// frontend/src/lib/api/client.ts
import axios from 'axios';
import { authStore } from '../stores/auth';
import { get } from 'svelte/store';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add auth token
client.interceptors.request.use((config) => {
  const auth = get(authStore);
  if (auth.accessToken) {
    config.headers.Authorization = `Bearer ${auth.accessToken}`;
  }
  return config;
});

// Response interceptor - handle token refresh
client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      const auth = get(authStore);
      if (auth.refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: auth.refreshToken,
          });
          
          const { access_token, refresh_token } = response.data;
          authStore.setTokens(access_token, refresh_token);
          
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return client(originalRequest);
        } catch (refreshError) {
          authStore.logout();
          window.location.href = '/login';
        }
      }
    }
    
    return Promise.reject(error);
  }
);

export default client;
```

## 6.2 Auth Store

```typescript
// frontend/src/lib/stores/auth.ts
import { writable, derived } from 'svelte/store';

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  userId: string | null;
  role: string | null;
  isAuthenticated: boolean;
}

const initialState: AuthState = {
  accessToken: localStorage.getItem('accessToken'),
  refreshToken: localStorage.getItem('refreshToken'),
  userId: localStorage.getItem('userId'),
  role: localStorage.getItem('role'),
  isAuthenticated: !!localStorage.getItem('accessToken'),
};

function createAuthStore() {
  const { subscribe, set, update } = writable<AuthState>(initialState);

  return {
    subscribe,
    setTokens: (accessToken: string, refreshToken: string, userId?: string, role?: string) => {
      localStorage.setItem('accessToken', accessToken);
      localStorage.setItem('refreshToken', refreshToken);
      if (userId) localStorage.setItem('userId', userId);
      if (role) localStorage.setItem('role', role);
      
      update((state) => ({
        ...state,
        accessToken,
        refreshToken,
        userId: userId || state.userId,
        role: role || state.role,
        isAuthenticated: true,
      }));
    },
    logout: () => {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('userId');
      localStorage.removeItem('role');
      
      set({
        accessToken: null,
        refreshToken: null,
        userId: null,
        role: null,
        isAuthenticated: false,
      });
    },
  };
}

export const authStore = createAuthStore();
export const isAuthenticated = derived(authStore, ($auth) => $auth.isAuthenticated);
export const userRole = derived(authStore, ($auth) => $auth.role);
```

## 6.3 Auth API

```typescript
// frontend/src/lib/api/auth.ts
import client from './client';
import type { LoginResponse } from './types';

export const authApi = {
  async login(username: string, password: string): Promise<LoginResponse> {
    const response = await client.post('/auth/login', { username, password });
    return response.data;
  },
  
  async refresh(refreshToken: string): Promise<LoginResponse> {
    const response = await client.post('/auth/refresh', { refresh_token: refreshToken });
    return response.data;
  },
  
  async logout(): Promise<void> {
    await client.post('/auth/logout');
  },
};
```

## 6.4 Patient API

```typescript
// frontend/src/lib/api/patients.ts
import client from './client';
import type { Patient, Vital, MedicalRecord, Prescription } from './types';

export const patientApi = {
  async getCurrentPatient(): Promise<Patient> {
    const response = await client.get('/patients/me');
    return response.data;
  },
  
  async getPatient(patientId: string): Promise<Patient> {
    const response = await client.get(`/patients/${patientId}`);
    return response.data;
  },
  
  async getVitals(patientId: string, days: number = 30): Promise<Vital[]> {
    const response = await client.get(`/patients/${patientId}/vitals`, {
      params: { days },
    });
    return response.data;
  },
  
  async createVital(patientId: string, vital: Partial<Vital>): Promise<Vital> {
    const response = await client.post(`/patients/${patientId}/vitals`, vital);
    return response.data;
  },
  
  async getRecords(patientId: string): Promise<MedicalRecord[]> {
    const response = await client.get(`/patients/${patientId}/records`);
    return response.data;
  },
  
  async getPrescriptions(patientId: string): Promise<Prescription[]> {
    const response = await client.get(`/patients/${patientId}/prescriptions`);
    return response.data;
  },
  
  async getNotifications(patientId: string): Promise<any[]> {
    const response = await client.get(`/patients/${patientId}/notifications`);
    return response.data;
  },
  
  async getWalletTransactions(patientId: string, walletType: 'hospital' | 'pharmacy'): Promise<any[]> {
    const response = await client.get(`/patients/${patientId}/wallet/${walletType}/transactions`);
    return response.data;
  },
};
```

## 6.5 API Types

```typescript
// frontend/src/lib/api/types.ts
export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user_id: string;
  role: string;
}

export interface Patient {
  id: string;
  patient_id: string;
  name: string;
  date_of_birth: string;
  gender: 'MALE' | 'FEMALE' | 'OTHER';
  blood_group: string;
  phone: string;
  email?: string;
  address: string;
  photo?: string;
  aadhaar_id?: string;
  abha_id?: string;
  category: 'GENERAL' | 'ELITE' | 'VIP' | 'STAFF';
  emergency_contact?: EmergencyContact;
  allergies: Allergy[];
  medical_alerts: MedicalAlert[];
}

export interface EmergencyContact {
  id: string;
  name: string;
  relationship: string;
  phone: string;
  email?: string;
}

export interface Allergy {
  id: string;
  allergen: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  reaction?: string;
}

export interface MedicalAlert {
  id: string;
  type: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  title: string;
  description: string;
  symptoms: string[];
  is_active: boolean;
}

export interface Vital {
  id: string;
  patient_id: string;
  recorded_at: string;
  recorded_by?: string;
  systolic_bp?: number;
  diastolic_bp?: number;
  heart_rate?: number;
  respiratory_rate?: number;
  temperature?: number;
  oxygen_saturation?: number;
  weight?: number;
  blood_glucose?: number;
  cholesterol?: number;
  bmi?: number;
}

export interface MedicalRecord {
  id: string;
  patient_id: string;
  date: string;
  time: string;
  type: 'CONSULTATION' | 'LABORATORY' | 'PROCEDURE' | 'MEDICATION';
  description: string;
  performed_by: string;
  supervised_by?: string;
  department: string;
  status: string;
  diagnosis?: string;
  recommendations?: string;
  findings: MedicalFinding[];
  images: MedicalImage[];
}

export interface MedicalFinding {
  id: string;
  parameter: string;
  value: string;
  reference?: string;
  status: string;
}

export interface MedicalImage {
  id: string;
  title: string;
  description?: string;
  url: string;
  type: string;
}

export interface Prescription {
  id: string;
  patient_id: string;
  date: string;
  doctor: string;
  department: string;
  status: 'ACTIVE' | 'BOUGHT' | 'RECEIVE' | 'COMPLETED';
  medications: PrescriptionMedication[];
}

export interface PrescriptionMedication {
  id: string;
  name: string;
  dosage: string;
  frequency: string;
  duration: string;
  instructions?: string;
  refills_remaining: number;
  start_date: string;
  end_date: string;
}

export interface Student {
  id: string;
  student_id: string;
  name: string;
  year: number;
  semester: number;
  program: string;
  photo?: string;
  gpa: number;
  academic_standing: string;
  academic_advisor?: string;
}

export interface Faculty {
  id: string;
  faculty_id: string;
  name: string;
  department: string;
  specialty?: string;
  phone?: string;
  email?: string;
  photo?: string;
  availability?: string;
}
```

## 6.6 Router Setup

```svelte
<!-- frontend/src/Router.svelte -->
<script lang="ts">
  import { Router, Route, navigate } from 'svelte-routing';
  import { isAuthenticated, userRole } from './lib/stores/auth';
  
  // Pages
  import Login from './routes/Login.svelte';
  import Dashboard from './routes/Dashboard.svelte';
  import StudentDashboard from './routes/StudentDashboard.svelte';
  import FacultyDashboard from './routes/FacultyDashboard.svelte';
  import Profile from './routes/Profile.svelte';
  import Records from './routes/Records.svelte';
  import Admissions from './routes/Admissions.svelte';
  import HospitalWallet from './routes/HospitalWallet.svelte';
  import PharmacyWallet from './routes/PharmacyWallet.svelte';
  import Reports from './routes/Reports.svelte';
  import Prescriptions from './routes/Prescriptions.svelte';
  import Vitals from './routes/Vitals.svelte';
  import Notifications from './routes/Notifications.svelte';
  import CaseRecord from './routes/CaseRecord.svelte';
  
  // Layout
  import AppShell from './components/layout/AppShell.svelte';
  
  // Redirect based on auth state
  $: if (!$isAuthenticated && window.location.pathname !== '/login') {
    navigate('/login', { replace: true });
  }
</script>

<Router>
  <Route path="/login" component={Login} />
  
  {#if $isAuthenticated}
    <AppShell>
      {#if $userRole === 'PATIENT'}
        <Route path="/" component={Dashboard} />
        <Route path="/dashboard" component={Dashboard} />
      {:else if $userRole === 'STUDENT'}
        <Route path="/" component={StudentDashboard} />
        <Route path="/dashboard" component={StudentDashboard} />
        <Route path="/patient/:id" let:params>
          <CaseRecord patientId={params.id} />
        </Route>
      {:else if $userRole === 'FACULTY'}
        <Route path="/" component={FacultyDashboard} />
        <Route path="/dashboard" component={FacultyDashboard} />
      {/if}
      
      <Route path="/profile" component={Profile} />
      <Route path="/records" component={Records} />
      <Route path="/admissions" component={Admissions} />
      <Route path="/wallet/hospital" component={HospitalWallet} />
      <Route path="/wallet/pharmacy" component={PharmacyWallet} />
      <Route path="/reports" component={Reports} />
      <Route path="/prescriptions" component={Prescriptions} />
      <Route path="/vitals" component={Vitals} />
      <Route path="/notifications" component={Notifications} />
    </AppShell>
  {/if}
</Router>
```

## 6.7 Reusable Components

### AquaButton.svelte
```svelte
<script lang="ts">
  export let variant: 'primary' | 'secondary' | 'danger' = 'primary';
  export let size: 'sm' | 'md' | 'lg' = 'md';
  export let fullWidth: boolean = false;
  export let disabled: boolean = false;
  export let type: 'button' | 'submit' = 'button';
  
  const variants = {
    primary: 'background: linear-gradient(to bottom, #4d90fe, #0066cc); color: white;',
    secondary: 'background: linear-gradient(to bottom, #f0f4fa, #d5dde8); color: #1e40af;',
    danger: 'background: linear-gradient(to bottom, #ff5a5a, #cc0000); color: white;'
  };
  
  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg'
  };
</script>

<button
  {type}
  {disabled}
  class="relative overflow-hidden transition-all active:translate-y-0.5 active:shadow-inner
         before:absolute before:inset-0 before:bg-gradient-to-b before:from-white 
         before:via-transparent before:to-transparent before:opacity-50
         font-medium rounded-lg
         {sizes[size]}
         {fullWidth ? 'w-full' : ''}"
  style="{variants[variant]}
         border: 1px solid rgba(0,0,0,0.2);
         box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4);"
  on:click
>
  <slot />
</button>
```

### AquaCard.svelte
```svelte
<script lang="ts">
  export let padding: boolean = true;
</script>

<div
  class="overflow-hidden"
  style="background-color: white;
         border-radius: 10px;
         box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24), 
                     0 0 0 1px rgba(0,0,0,0.05), inset 0 -5px 10px rgba(0,0,0,0.05);
         border: 1px solid rgba(0,0,0,0.1);"
>
  {#if $$slots.header}
    <div
      class="px-4 py-3 flex items-center"
      style="background-image: linear-gradient(to bottom, #f8f9fb, #d9e1ea);
             box-shadow: 0 1px 0 rgba(255,255,255,0.8) inset, 0 1px 0 rgba(0,0,0,0.1);
             border-bottom: 1px solid rgba(0,0,0,0.1);"
    >
      <slot name="header" />
    </div>
  {/if}
  <div class={padding ? 'p-4' : ''}>
    <slot />
  </div>
</div>
```

### AquaInput.svelte
```svelte
<script lang="ts">
  import type { ComponentType } from 'svelte';
  
  export let type: string = 'text';
  export let placeholder: string = '';
  export let value: string = '';
  export let icon: ComponentType | null = null;
  export let name: string = '';
</script>

<div
  class="flex items-center px-4 py-3"
  style="border: 1px solid rgba(0,0,0,0.2);
         border-radius: 6px;
         background-color: rgba(255,255,255,0.8);
         box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);"
>
  {#if icon}
    <svelte:component this={icon} class="h-5 w-5 text-gray-400 mr-3" />
  {/if}
  <input
    {type}
    {placeholder}
    {name}
    bind:value
    class="flex-1 outline-none text-gray-700 bg-transparent"
    on:input
    on:change
  />
</div>
```

---

# SECTION 7: API ENDPOINTS REFERENCE

## 7.1 Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | User login |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/auth/logout` | User logout |

## 7.2 Patients
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/patients/me` | Get current patient profile |
| GET | `/api/v1/patients/{id}` | Get patient by ID |
| GET | `/api/v1/patients/{id}/records` | Get patient medical records |
| GET | `/api/v1/patients/{id}/vitals` | Get patient vitals (query: days) |
| POST | `/api/v1/patients/{id}/vitals` | Create new vital reading |
| GET | `/api/v1/patients/{id}/prescriptions` | Get patient prescriptions |
| PUT | `/api/v1/patients/{id}/prescriptions/{rx_id}/status` | Update prescription status |
| GET | `/api/v1/patients/{id}/admissions` | Get patient admissions |
| GET | `/api/v1/patients/{id}/reports` | Get patient reports |
| GET | `/api/v1/patients/{id}/wallet/{type}/transactions` | Get wallet transactions |
| GET | `/api/v1/patients/{id}/notifications` | Get patient notifications |
| PUT | `/api/v1/patients/{id}/notifications/read` | Mark notifications as read |

## 7.3 Students
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/students/me` | Get current student profile |
| GET | `/api/v1/students/{id}` | Get student by ID |
| GET | `/api/v1/students/{id}/patients` | Get assigned patients |
| GET | `/api/v1/students/{id}/case-records` | Get student case records |
| POST | `/api/v1/students/{id}/case-records` | Create case record |
| GET | `/api/v1/students/{id}/progress` | Get academic progress |
| GET | `/api/v1/students/{id}/clinic-sessions` | Get clinic sessions |
| GET | `/api/v1/students/{id}/notifications` | Get student notifications |

## 7.4 Faculty
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/faculty/me` | Get current faculty profile |
| GET | `/api/v1/faculty/{id}` | Get faculty by ID |
| GET | `/api/v1/faculty/{id}/approvals` | Get pending approvals |
| PUT | `/api/v1/faculty/{id}/approvals/{approval_id}` | Process approval |
| GET | `/api/v1/faculty/{id}/schedule` | Get faculty schedule |
| GET | `/api/v1/faculty/{id}/notifications` | Get faculty notifications |

---

# SECTION 8: DEVELOPMENT WORKFLOW

## 8.1 Running the Application

### Backend (FastAPI)
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Seed database (dev only)
python scripts/seed.py

# Start development server
uvicorn app.main:app --reload --port 8000
```

### Frontend (Svelte)
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Docker Compose (Full Stack)
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

## 8.2 Docker Compose Configuration

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: mias
      POSTGRES_PASSWORD: mias_secret
      POSTGRES_DB: mias_mp
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mias -d mias_mp"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://mias:mias_secret@postgres:5432/mias_mp
      JWT_SECRET_KEY: your-secret-key-change-in-production
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    environment:
      VITE_API_URL: http://localhost:8000/api/v1
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev -- --host

volumes:
  postgres_data:
```

## 8.3 Environment Variables

### Backend (.env)
```env
DATABASE_URL=postgresql://mias:mias_secret@localhost:5432/mias_mp
JWT_SECRET_KEY=your-256-bit-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
DEBUG=true
```

### Frontend (.env)
```env
VITE_API_URL=http://localhost:8000/api/v1
```

---

# SECTION 9: DATABASE SEEDING

```python
# backend/scripts/seed.py
import asyncio
from datetime import datetime, date, timedelta
import uuid
from decimal import Decimal

from app.database import AsyncSessionLocal, engine, Base
from app.models.user import User, UserRole
from app.models.patient import Patient, Gender, PatientCategory
from app.models.student import Student
from app.models.faculty import Faculty
from app.core.security import get_password_hash

async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as db:
        # Create test users
        # Patient: p/p
        patient_user = User(
            id=str(uuid.uuid4()),
            username="p",
            email="patient@saveetha.com",
            password_hash=get_password_hash("p"),
            role=UserRole.PATIENT
        )
        db.add(patient_user)
        
        patient = Patient(
            id=str(uuid.uuid4()),
            patient_id="SMC-2023-1234",
            user_id=patient_user.id,
            name="John Doe",
            date_of_birth=date(1990, 5, 15),
            gender=Gender.MALE,
            blood_group="O+",
            phone="+91 98765 43210",
            email="john.doe@email.com",
            address="123 Main Street, Chennai 600001",
            category=PatientCategory.ELITE
        )
        db.add(patient)
        
        # Student: s/s
        student_user = User(
            id=str(uuid.uuid4()),
            username="s",
            email="student@saveetha.com",
            password_hash=get_password_hash("s"),
            role=UserRole.STUDENT
        )
        db.add(student_user)
        
        student = Student(
            id=str(uuid.uuid4()),
            student_id="SMS-2023-1234",
            user_id=student_user.id,
            name="Sarah Smith",
            year=3,
            semester=5,
            program="MBBS",
            gpa=3.8,
            academic_standing="Good Standing"
        )
        db.add(student)
        
        # Faculty: t/t (teacher)
        faculty_user = User(
            id=str(uuid.uuid4()),
            username="t",
            email="faculty@saveetha.com",
            password_hash=get_password_hash("t"),
            role=UserRole.FACULTY
        )
        db.add(faculty_user)
        
        faculty = Faculty(
            id=str(uuid.uuid4()),
            faculty_id="FAC-2023-1234",
            user_id=faculty_user.id,
            name="Dr. James Wilson",
            department="Internal Medicine",
            specialty="Cardiology"
        )
        db.add(faculty)
        
        await db.commit()
        print("Database seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed())
```

---

# SECTION 10: PRODUCTION DEPLOYMENT

## 10.1 Backend Requirements

```txt
# backend/requirements.txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy[asyncio]==2.0.25
asyncpg==0.29.0
pydantic==2.5.3
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
alembic==1.13.1
python-multipart==0.0.6
httpx==0.26.0
pytest==7.4.4
pytest-asyncio==0.23.3
slowapi==0.1.9
```

## 10.2 Frontend Package.json

```json
{
  "name": "mias-mp-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "check": "svelte-check --tsconfig ./tsconfig.json"
  },
  "devDependencies": {
    "@sveltejs/vite-plugin-svelte": "^3.0.0",
    "@types/node": "^20.10.0",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32",
    "svelte": "^4.2.8",
    "svelte-check": "^3.6.2",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.3.3",
    "vite": "^5.0.10"
  },
  "dependencies": {
    "axios": "^1.6.2",
    "chart.js": "^4.4.1",
    "lucide-svelte": "^0.303.0",
    "svelte-routing": "^2.10.0"
  }
}
```

## 10.3 Deployment Checklist

### Backend
- [ ] Set production DATABASE_URL with SSL
- [ ] Generate strong JWT_SECRET_KEY (256-bit)
- [ ] Set DEBUG=false
- [ ] Configure proper CORS_ORIGINS
- [ ] Set up Gunicorn with Uvicorn workers
- [ ] Configure PostgreSQL connection pooling
- [ ] Set up Redis for rate limiting (production)
- [ ] Configure logging (JSON format)
- [ ] Set up health check endpoints
- [ ] Enable HTTPS

### Frontend
- [ ] Set production VITE_API_URL
- [ ] Build optimized bundle: `npm run build`
- [ ] Configure CDN for static assets
- [ ] Set up proper caching headers
- [ ] Enable gzip compression

---

# SECTION 11: ICONS REFERENCE (lucide-svelte)

Import all icons from `lucide-svelte`. Here are the icons used:

**Navigation**: `ArrowLeft`, `ChevronRight`, `ChevronDown`, `ChevronUp`, `ChevronLeft`, `Menu`, `X`

**User**: `User`, `Users`, `UserCheck`

**Medical**: `HeartPulse`, `Stethoscope`, `Pill`, `TestTube`, `Activity`, `Thermometer`, `Droplet`, `Scale`, `Syringe`, `Hospital`, `Bed`, `Ambulance`, `FlaskConical`

**Documents**: `FileText`, `Clipboard`, `ClipboardList`, `ClipboardCheck`, `BookOpen`, `Book`

**Actions**: `Plus`, `Minus`, `Edit`, `Pencil`, `Trash`, `Download`, `Printer`, `Save`, `Eye`, `ZoomIn`, `ZoomOut`, `RefreshCw`, `ExternalLink`, `ShoppingBag`, `Inbox`

**Status**: `Check`, `CheckCircle`, `XCircle`, `AlertTriangle`, `AlertCircle`, `Bell`, `Clock`, `Calendar`

**Finance**: `Wallet`, `CreditCard`

**Education**: `GraduationCap`, `Award`, `Star`

**Communication**: `Phone`, `PhoneCall`, `Mail`, `MessageCircle`

**Other**: `Crown`, `Shield`, `BadgeCheck`, `Filter`, `Search`, `Sliders`, `Settings`, `HelpCircle`, `LogOut`, `Link`, `ArrowUp`, `ArrowDown`, `ArrowRightCircle`, `ArrowRightFromLine`, `ArrowLeftFromLine`, `MapPin`, `Building`, `Home`, `Image`, `ChartBar`

---

# SECTION 12: BRANDING

**Organization**: Saveetha Medical College Hospital
**Tagline**: "College Hospital"
**Location**: Saveetha Nagar, Thandalam, Chennai 600077
**Phone**: Tel: (044) 2680-1050
**Emails**: 
- support@saveethamedical.com
- billing@saveethamedical.com
- records@saveethamedical.com

---

# IMPLEMENTATION NOTES

1. **Mobile-First**: All screens are designed for mobile (max-w-md = 448px). Center the app container.

2. **No Color Changes**: The exact color values and gradients MUST be preserved. The Mac OS X Aqua skeuomorphic design is intentional.

3. **Animations**: Include all CSS animations (pulse, slide, fade) for the polished feel.

4. **State Management**: Use Svelte stores for client-side state. API calls handle server state.

5. **API Communication**: All data flows through the FastAPI backend. No direct database access from frontend.

6. **Token Management**: Store JWT tokens in localStorage. Implement automatic token refresh.

7. **Error Handling**: Implement proper error boundaries and user-friendly error messages on both frontend and backend.

8. **Loading States**: Add skeleton loaders and spinners where appropriate.

9. **Accessibility**: Ensure proper ARIA labels, keyboard navigation, and color contrast.

10. **Print Styles**: Medical reports and invoices should have proper print CSS.

11. **Parallel Development**: Frontend and backend can be developed simultaneously:
    - Backend team focuses on API endpoints and database
    - Frontend team uses mock data until APIs are ready
    - Use OpenAPI/Swagger documentation as contract

12. **Testing Strategy**:
    - Backend: pytest with async support
    - Frontend: Vitest + Svelte Testing Library
    - E2E: Playwright

---

# END OF PROMPT

This prompt provides all the necessary information to build MIAS-MP with a decoupled Svelte frontend and FastAPI backend architecture, allowing parallel development while maintaining the exact same UI design and color system.
