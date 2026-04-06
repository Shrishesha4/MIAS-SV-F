from fastapi import APIRouter

from app.api.v1 import (
    auth,
    patients,
    students,
    faculty,
    vitals,
    prescriptions,
    reports,
    admissions,
    admission_review,
    wallet,
    notifications,
    approvals,
    autocomplete,
    admin,
    clinics,
    forms,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(patients.router)
api_router.include_router(students.router)
api_router.include_router(faculty.router)
api_router.include_router(vitals.router)
api_router.include_router(prescriptions.router)
api_router.include_router(reports.router)
api_router.include_router(admissions.router)
api_router.include_router(admission_review.router)
api_router.include_router(wallet.router)
api_router.include_router(notifications.router)
api_router.include_router(approvals.router)
api_router.include_router(autocomplete.router)
api_router.include_router(admin.router)
api_router.include_router(clinics.router)
api_router.include_router(forms.router)
