from fastapi import APIRouter

from app.api.v1 import (
    auth,
    ai_provider,
    patients,
    students,
    faculty,
    nutritionists,
    lab_technicians,
    nurses,
    vitals,
    prescriptions,
    reports,
    admissions,
    admission_review,
    wallet,
    notifications,
    pharmacy,
    approvals,
    autocomplete,
    admin,
    clinics,
    labs,
    forms,
    staff,
    insurance_categories,
    attendance,
    billing,
    operation_theaters,
    mrd,
    diagnosis,
    geofencing,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(ai_provider.router)
api_router.include_router(patients.router)
api_router.include_router(students.router)
api_router.include_router(faculty.router)
api_router.include_router(nutritionists.router)
api_router.include_router(lab_technicians.router)
api_router.include_router(nurses.router)
api_router.include_router(pharmacy.router)
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
api_router.include_router(labs.router)
api_router.include_router(labs.charge_router)
api_router.include_router(forms.router)
api_router.include_router(staff.router)
api_router.include_router(insurance_categories.router)
api_router.include_router(attendance.router)
api_router.include_router(billing.router)
api_router.include_router(operation_theaters.router)
api_router.include_router(mrd.router)
api_router.include_router(diagnosis.router)
api_router.include_router(geofencing.router)
