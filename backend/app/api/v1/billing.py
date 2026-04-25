"""Billing & Cashier API – profile and accounts analytics."""

from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_role
from app.database import get_db
from app.models.billing import Billing
from app.models.case_record import CaseRecord
from app.models.patient import Patient
from app.models.prescription import (
    Prescription,
    PrescriptionDispensingStatus,
)
from app.models.report import Report
from app.models.user import User, UserRole
from app.models.wallet import TransactionType, WalletTransaction, WalletType

router = APIRouter(prefix="/billing", tags=["Billing"])


def _to_float(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _safe_iso(value):
    return value.isoformat() if value else None


def _normalize_payment_method(value):
    if not value:
        return "UNSPECIFIED"

    normalized = value.strip().upper()
    if normalized in {"CASH"}:
        return "CASH"
    if normalized in {"CARD", "UPI", "NET BANKING", "CHEQUE", "ONLINE", "DIGITAL"}:
        return "DIGITAL"
    return normalized


def _bucket_label(timestamp: datetime, range_key: str) -> str:
    if range_key == "1Y":
        return timestamp.strftime("%b")
    if range_key == "1Q":
        return f"W{((timestamp.day - 1) // 7) + 1}"
    return timestamp.strftime("%d %b")


def _build_range_points(range_key: str):
    now = datetime.utcnow()

    if range_key == "1W":
        start = now - timedelta(days=6)
        labels = [
            (start + timedelta(days=index)).strftime("%d %b") for index in range(7)
        ]
    elif range_key == "1M":
        start = now - timedelta(days=29)
        labels = [
            (start + timedelta(days=index)).strftime("%d %b") for index in range(30)
        ]
    elif range_key == "1Q":
        start = now - timedelta(days=83)
        labels = []
        cursor = start
        while cursor <= now:
            label = _bucket_label(cursor, range_key)
            if label not in labels:
                labels.append(label)
            cursor += timedelta(days=1)
    else:
        start = now - timedelta(days=364)
        labels = []
        cursor = start.replace(day=1)
        while cursor <= now:
            label = _bucket_label(cursor, range_key)
            if label not in labels:
                labels.append(label)
            month = cursor.month + 1
            year = cursor.year
            if month == 13:
                month = 1
                year += 1
            cursor = cursor.replace(year=year, month=month, day=1)

    return labels, {label: index for index, label in enumerate(labels)}, start


@router.get("/me")
async def get_billing_profile(
    user: User = Depends(require_role(UserRole.BILLING, UserRole.ACCOUNTS)),
    db: AsyncSession = Depends(get_db),
):
    billing = (
        await db.execute(select(Billing).where(Billing.user_id == user.id))
    ).scalar_one_or_none()
    if not billing:
        raise HTTPException(status_code=404, detail="Billing profile not found")
    return {
        "id": billing.id,
        "billing_id": billing.billing_id,
        "name": billing.name,
        "counter_name": billing.counter_name,
        "phone": billing.phone,
        "email": billing.email,
        "username": user.username,
    }


@router.get("/accounts/analytics")
async def get_accounts_analytics(
    start_date: str = Query(None),
    end_date: str = Query(None),
    branch: str = Query(None),
    department: str = Query(None),
    trend_range: str = Query("1W"),
    user: User = Depends(require_role(UserRole.ACCOUNTS)),
    db: AsyncSession = Depends(get_db),
):
    try:
        parsed_end = (
            datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.utcnow()
        )
        parsed_start = (
            datetime.strptime(start_date, "%Y-%m-%d")
            if start_date
            else parsed_end - timedelta(days=30)
        )
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Dates must be in YYYY-MM-DD format"
        )

    if parsed_start > parsed_end:
        raise HTTPException(
            status_code=400, detail="Start date cannot be after end date"
        )

    trend_key = trend_range.upper()
    if trend_key not in {"1W", "1M", "1Q", "1Y"}:
        raise HTTPException(status_code=400, detail="Unsupported trend range")

    range_labels, range_index, trend_start = _build_range_points(trend_key)
    end_boundary = parsed_end + timedelta(days=1)

    billing_users_result = await db.execute(
        select(Billing).options(selectinload(Billing.user)).order_by(Billing.name.asc())
    )
    billing_users = list(billing_users_result.scalars().all())
    billing_user_names = {
        str(item.name).strip()
        for item in billing_users
        if getattr(item, "name", None) is not None and str(item.name).strip()
    }

    wallet_transactions_result = await db.execute(
        select(WalletTransaction, Patient)
        .join(Patient, Patient.id == WalletTransaction.patient_id)
        .where(WalletTransaction.date >= parsed_start)
        .where(WalletTransaction.date < end_boundary)
        .order_by(WalletTransaction.date.desc())
    )
    wallet_rows = wallet_transactions_result.all()

    pharmacy_result = await db.execute(
        select(Prescription, Patient)
        .join(Patient, Patient.id == Prescription.patient_id)
        .options(selectinload(Prescription.medications))
        .where(Prescription.issued_at.is_not(None))
        .where(Prescription.issued_at >= parsed_start)
        .where(Prescription.issued_at < end_boundary)
        .where(Prescription.dispensing_status == PrescriptionDispensingStatus.ISSUED)
        .order_by(Prescription.issued_at.desc())
    )
    pharmacy_rows = pharmacy_result.all()

    case_record_result = await db.execute(
        select(CaseRecord, Patient)
        .join(Patient, Patient.id == CaseRecord.patient_id)
        .where(CaseRecord.price.is_not(None))
        .where(CaseRecord.last_modified_at >= parsed_start)
        .where(CaseRecord.last_modified_at < end_boundary)
        .order_by(CaseRecord.last_modified_at.desc())
    )
    case_record_rows = case_record_result.all()

    lab_result = await db.execute(
        select(Report, Patient)
        .join(Patient, Patient.id == Report.patient_id)
        .where(Report.date >= parsed_start)
        .where(Report.date < end_boundary)
        .order_by(Report.date.desc())
    )
    lab_rows = lab_result.all()

    total_collection = 0.0
    cash_collection = 0.0
    digital_collection = 0.0

    department_totals: dict[str, dict[str, float]] = {}
    billing_center_totals: dict[str, float] = {}
    user_totals = {}
    live_transactions = []

    trend_overview = {
        "wallet_credit": [0.0 for _ in range_labels],
        "wallet_debit": [0.0 for _ in range_labels],
        "pharmacy": [0.0 for _ in range_labels],
        "forms": [0.0 for _ in range_labels],
        "labs": [0.0 for _ in range_labels],
    }

    def ensure_department(name: str):
        if name not in department_totals:
            department_totals[name] = {"cash": 0.0, "digital": 0.0, "total": 0.0}
        return department_totals[name]

    def ensure_user(name: str):
        if name not in user_totals:
            user_totals[name] = {
                "name": name,
                "total_collection": 0.0,
                "transactions": 0,
                "status": "Active",
            }
        return user_totals[name]

    for txn, patient in wallet_rows:
        txn_date = txn.date
        if not txn_date:
            continue

        txn_department = txn.department or (
            "Pharmacy" if txn.wallet_type == WalletType.PHARMACY else "Billing"
        )
        if (
            department
            and department != "All Departments"
            and txn_department != department
        ):
            continue

        amount = _to_float(txn.amount)
        payment_method = _normalize_payment_method(txn.payment_method)
        patient_name = patient.name if patient else "Unknown Patient"
        provider_name = txn.provider or "System"
        center_name = txn.department or (
            "Pharmacy Wallet"
            if txn.wallet_type == WalletType.PHARMACY
            else "Hospital Wallet"
        )

        if txn.type == TransactionType.CREDIT:
            total_collection += amount
            if payment_method == "CASH":
                cash_collection += amount
            else:
                digital_collection += amount

            dept_bucket = ensure_department(txn_department)
            if payment_method == "CASH":
                dept_bucket["cash"] += amount
            else:
                dept_bucket["digital"] += amount
            dept_bucket["total"] += amount

            billing_center_totals[center_name] = (
                billing_center_totals.get(center_name, 0.0) + amount
            )

            if provider_name in billing_user_names:
                user_bucket = ensure_user(provider_name)
                user_bucket["total_collection"] = (
                    float(user_bucket["total_collection"]) + amount
                )
                user_bucket["transactions"] = int(user_bucket["transactions"]) + 1

        if txn_date >= trend_start:
            label = _bucket_label(txn_date, trend_key)
            if label in range_index:
                if txn.type == TransactionType.CREDIT:
                    trend_overview["wallet_credit"][range_index[label]] += amount
                else:
                    trend_overview["wallet_debit"][range_index[label]] += amount

        live_transactions.append(
            {
                "id": txn.id,
                "name": patient_name,
                "subtitle": f"{txn_department} · {txn.description}",
                "amount": amount,
                "method": payment_method,
                "time": txn.time,
                "type": txn.type.value,
                "wallet_type": txn.wallet_type.value,
                "date": _safe_iso(txn.date),
                "reference_number": txn.reference_number,
                "provider": provider_name,
            }
        )

    for prescription, patient in pharmacy_rows:
        issued_at = prescription.issued_at
        if not issued_at:
            continue

        medications = list(getattr(prescription, "medications", []) or [])
        amount = 0.0

        if issued_at >= trend_start:
            label = _bucket_label(issued_at, trend_key)
            if label in range_index:
                trend_overview["pharmacy"][range_index[label]] += amount

        live_transactions.append(
            {
                "id": prescription.id,
                "name": patient.name if patient else "Unknown Patient",
                "subtitle": f"Pharmacy Issue · {prescription.prescription_id or prescription.id}",
                "amount": amount,
                "method": "PHARMACY",
                "time": issued_at.strftime("%H:%M"),
                "type": "ISSUED",
                "wallet_type": "PHARMACY",
                "date": _safe_iso(issued_at),
                "reference_number": prescription.prescription_id,
                "provider": prescription.doctor,
                "medication_count": len(medications),
            }
        )

    for record, patient in case_record_rows:
        amount = _to_float(record.price)
        if amount <= 0:
            continue

        department_name = record.department or "Forms"
        if (
            department
            and department != "All Departments"
            and department_name != department
        ):
            continue

        dept_bucket = ensure_department(department_name)
        dept_bucket["digital"] += amount
        dept_bucket["total"] += amount
        total_collection += amount
        digital_collection += amount

        billing_center_totals[department_name] = (
            billing_center_totals.get(department_name, 0.0) + amount
        )

        record_timestamp = record.last_modified_at or parsed_start
        if record_timestamp >= trend_start:
            label = _bucket_label(record_timestamp, trend_key)
            if label in range_index:
                trend_overview["forms"][range_index[label]] += amount

        live_transactions.append(
            {
                "id": record.id,
                "name": patient.name if patient else "Unknown Patient",
                "subtitle": f"Paid Form · {record.procedure or 'Case Record'}",
                "amount": amount,
                "method": "FORM",
                "time": record_timestamp.strftime("%H:%M") if record_timestamp else "",
                "type": "DEBIT",
                "wallet_type": "HOSPITAL",
                "date": _safe_iso(record_timestamp),
                "reference_number": record.id,
                "provider": record.created_by_name,
            }
        )

    for report, patient in lab_rows:
        report_date = report.date
        if not report_date:
            continue

        if report_date >= trend_start:
            label = _bucket_label(report_date, trend_key)
            if label in range_index:
                trend_overview["labs"][range_index[label]] += 0.0

        live_transactions.append(
            {
                "id": report.id,
                "name": patient.name if patient else "Unknown Patient",
                "subtitle": f"Lab Order · {report.title or 'Investigation'}",
                "amount": 0.0,
                "method": "LAB",
                "time": report.time or report_date.strftime("%H:%M"),
                "type": "ORDER",
                "wallet_type": "HOSPITAL",
                "date": _safe_iso(report_date),
                "reference_number": getattr(report, "report_id", None),
                "provider": report.ordered_by,
            }
        )

    live_transactions = sorted(
        live_transactions,
        key=lambda item: item.get("date") or "",
        reverse=True,
    )[:25]

    billing_centers_payload = [
        {
            "id": name.lower().replace(" ", "-"),
            "name": name,
            "value": round(value, 2),
            "color": color,
        }
        for (name, value), color in zip(
            sorted(
                billing_center_totals.items(), key=lambda item: item[1], reverse=True
            )[:6],
            ["#4f8df7", "#ff3b30", "#9b51e0", "#34c759", "#f59e0b", "#14b8a6"],
        )
    ]

    collection_rows_payload = [
        {
            "id": name.lower().replace(" ", "-"),
            "department": name,
            "cash": round(values["cash"], 2),
            "card": round(values["digital"], 2),
            "total": round(values["total"], 2),
        }
        for name, values in sorted(
            department_totals.items(),
            key=lambda item: item[1]["total"],
            reverse=True,
        )
    ]

    users_payload = [
        {
            "id": name.lower().replace(" ", "-"),
            "name": str(values["name"]),
            "total_collection": round(float(values["total_collection"]), 2),
            "transactions": int(values["transactions"]),
            "status": str(values["status"]),
            "status_tone": "success"
            if float(values["total_collection"]) > 0
            else "warning",
        }
        for name, values in sorted(
            user_totals.items(),
            key=lambda item: float(item[1]["total_collection"]),
            reverse=True,
        )
    ]

    trend_payload = {
        trend_key: {
            "OVERVIEW": [
                {
                    "id": "wallet-credit",
                    "label": "Wallet Credit",
                    "color": "#16a34a",
                    "values": [
                        round(value, 2) for value in trend_overview["wallet_credit"]
                    ],
                },
                {
                    "id": "wallet-debit",
                    "label": "Wallet Debit",
                    "color": "#2563eb",
                    "values": [
                        round(value, 2) for value in trend_overview["wallet_debit"]
                    ],
                },
                {
                    "id": "pharmacy",
                    "label": "Pharmacy",
                    "color": "#8b5cf6",
                    "values": [round(value, 2) for value in trend_overview["pharmacy"]],
                },
            ],
            "DEPARTMENTS": [
                {
                    "id": "forms",
                    "label": "Paid Forms",
                    "color": "#f59e0b",
                    "values": [round(value, 2) for value in trend_overview["forms"]],
                },
                {
                    "id": "labs",
                    "label": "Labs",
                    "color": "#14b8a6",
                    "values": [round(value, 2) for value in trend_overview["labs"]],
                },
            ],
            "INVESTIGATIONS": [
                {
                    "id": "labs",
                    "label": "Lab Orders",
                    "color": "#2563eb",
                    "values": [round(value, 2) for value in trend_overview["labs"]],
                },
                {
                    "id": "pharmacy",
                    "label": "Pharmacy Issues",
                    "color": "#8b5cf6",
                    "values": [round(value, 2) for value in trend_overview["pharmacy"]],
                },
            ],
        }
    }

    return {
        "summary": {
            "total_collection": round(total_collection, 2),
            "cash": round(cash_collection, 2),
            "card_digital": round(digital_collection, 2),
        },
        "billing_centers": billing_centers_payload,
        "live_transactions": live_transactions,
        "collections": collection_rows_payload,
        "users": users_payload,
        "trend_labels": range_labels,
        "trends": trend_payload,
        "meta": {
            "start_date": parsed_start.date().isoformat(),
            "end_date": parsed_end.date().isoformat(),
            "branch": branch or "All Branches",
            "department": department or "All Departments",
            "billing_user_count": len(billing_users),
        },
    }
