"""Automatic notification scheduler.

Creates scheduled notifications for:
- Medication reminders (based on active prescriptions)
- Appointment reminders (day before and 1 hour before)
- Follow-up reminders
- Vital check reminders for assigned students
"""
import asyncio
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.prescription import Prescription, PrescriptionStatus
from app.models.notification import PatientNotification, ScheduledNotification
from app.models.patient import Patient, Appointment
from app.models.student import StudentPatientAssignment, StudentNotification
from app.models.faculty import FacultyNotification


async def create_medication_reminders():
    """Create medication reminder notifications for patients with active prescriptions."""
    async with AsyncSessionLocal() as db:
        # Get all active prescriptions
        result = await db.execute(
            select(Prescription)
            .options(selectinload(Prescription.medications))
            .where(Prescription.status == PrescriptionStatus.ACTIVE)
        )
        prescriptions = result.scalars().all()

        now = datetime.utcnow()
        count = 0

        for rx in prescriptions:
            for med in rx.medications:
                # Check if we already created a reminder in last 6 hours
                existing = await db.execute(
                    select(PatientNotification)
                    .where(PatientNotification.patient_id == rx.patient_id)
                    .where(PatientNotification.type == "MEDICATION_REMINDER")
                    .where(PatientNotification.created_at >= now - timedelta(hours=6))
                    .where(PatientNotification.title.contains(med.name))
                )
                if existing.scalar_one_or_none():
                    continue

                # Create reminder
                notif = PatientNotification(
                    id=str(uuid.uuid4()),
                    patient_id=rx.patient_id,
                    title=f"Time to take {med.name}",
                    message=f"Take {med.name} {med.dosage} - {med.frequency}. {med.instructions or ''}".strip(),
                    type="MEDICATION_REMINDER",
                )
                db.add(notif)
                count += 1

        await db.commit()
        return count


async def create_appointment_reminders():
    """Create reminder notifications for upcoming appointments."""
    async with AsyncSessionLocal() as db:
        now = datetime.utcnow()
        tomorrow = now + timedelta(hours=24)

        # Find appointments in the next 24 hours
        result = await db.execute(
            select(Appointment)
            .where(
                and_(
                    Appointment.date >= now,
                    Appointment.date <= tomorrow,
                    Appointment.status == "Scheduled",
                )
            )
        )
        appointments = result.scalars().all()

        count = 0
        for appt in appointments:
            # Check if reminder already sent
            existing = await db.execute(
                select(PatientNotification)
                .where(PatientNotification.patient_id == appt.patient_id)
                .where(PatientNotification.type == "APPOINTMENT_REMINDER")
                .where(PatientNotification.created_at >= now - timedelta(hours=12))
            )
            if existing.scalar_one_or_none():
                continue

            time_until = appt.date - now
            hours_until = int(time_until.total_seconds() / 3600)

            notif = PatientNotification(
                id=str(uuid.uuid4()),
                patient_id=appt.patient_id,
                title="Upcoming Appointment",
                message=f"You have an appointment with {appt.doctor} ({appt.department}) "
                        f"{'tomorrow' if hours_until > 12 else f'in {hours_until} hours'} "
                        f"at {appt.time}.",
                type="APPOINTMENT_REMINDER",
            )
            db.add(notif)
            count += 1

            # Also notify assigned students
            student_result = await db.execute(
                select(StudentPatientAssignment.student_id)
                .where(StudentPatientAssignment.patient_id == appt.patient_id)
                .where(StudentPatientAssignment.status == "Active")
            )
            for (student_id,) in student_result.all():
                patient_result = await db.execute(
                    select(Patient.name).where(Patient.id == appt.patient_id)
                )
                patient_name = patient_result.scalar_one_or_none() or "Patient"

                student_notif = StudentNotification(
                    id=str(uuid.uuid4()),
                    student_id=student_id,
                    title="Patient Appointment",
                    message=f"Your patient {patient_name} has an appointment with "
                            f"{appt.doctor} {'tomorrow' if hours_until > 12 else f'in {hours_until} hours'}.",
                    type="APPOINTMENT",
                )
                db.add(student_notif)

        await db.commit()
        return count


async def create_vital_check_reminders():
    """Remind students to check vitals for their assigned patients daily."""
    async with AsyncSessionLocal() as db:
        now = datetime.utcnow()

        # Get all active student-patient assignments
        result = await db.execute(
            select(StudentPatientAssignment)
            .options(selectinload(StudentPatientAssignment.patient))
            .where(StudentPatientAssignment.status == "Active")
        )
        assignments = result.scalars().all()

        count = 0
        for assignment in assignments:
            if not assignment.patient:
                continue

            # Check if reminder already sent today
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            existing = await db.execute(
                select(StudentNotification)
                .where(StudentNotification.student_id == assignment.student_id)
                .where(StudentNotification.type == "VITAL_CHECK")
                .where(StudentNotification.created_at >= today_start)
            )
            if existing.scalar_one_or_none():
                continue

            notif = StudentNotification(
                id=str(uuid.uuid4()),
                student_id=assignment.student_id,
                title="Vital Signs Check",
                message=f"Don't forget to check and record vitals for {assignment.patient.name} today.",
                type="VITAL_CHECK",
            )
            db.add(notif)
            count += 1

        await db.commit()
        return count


async def process_scheduled_notifications():
    """Process any due scheduled notifications."""
    async with AsyncSessionLocal() as db:
        now = datetime.utcnow()
        result = await db.execute(
            select(ScheduledNotification)
            .where(
                and_(
                    ScheduledNotification.is_active == 1,
                    ScheduledNotification.next_run_at <= now,
                )
            )
        )
        scheduled = result.scalars().all()

        count = 0
        for sched in scheduled:
            # Create the actual notification
            if sched.target_role == "PATIENT" and sched.patient_id:
                notif = PatientNotification(
                    id=str(uuid.uuid4()),
                    patient_id=sched.patient_id,
                    title=sched.title,
                    message=sched.message,
                    type=sched.notification_type,
                )
                db.add(notif)
            elif sched.target_role == "STUDENT" and sched.target_id:
                notif = StudentNotification(
                    id=str(uuid.uuid4()),
                    student_id=sched.target_id,
                    title=sched.title,
                    message=sched.message,
                    type=sched.notification_type,
                )
                db.add(notif)
            elif sched.target_role == "FACULTY" and sched.target_id:
                notif = FacultyNotification(
                    id=str(uuid.uuid4()),
                    faculty_id=sched.target_id,
                    title=sched.title,
                    message=sched.message,
                    type=sched.notification_type,
                )
                db.add(notif)

            sched.last_run_at = now
            count += 1

            # Calculate next run
            if sched.frequency == "DAILY":
                sched.next_run_at = now + timedelta(days=1)
            elif sched.frequency == "TWICE_DAILY":
                sched.next_run_at = now + timedelta(hours=12)
            elif sched.frequency == "WEEKLY":
                sched.next_run_at = now + timedelta(weeks=1)
            elif sched.frequency == "ONCE":
                sched.is_active = 0
            else:
                sched.next_run_at = now + timedelta(days=1)

        await db.commit()
        return count


async def run_notification_scheduler():
    """Background task that runs all notification jobs periodically."""
    while True:
        try:
            med_count = await create_medication_reminders()
            appt_count = await create_appointment_reminders()
            vital_count = await create_vital_check_reminders()
            sched_count = await process_scheduled_notifications()

            if any([med_count, appt_count, vital_count, sched_count]):
                print(
                    f"[Notification Scheduler] Created: "
                    f"{med_count} medication, {appt_count} appointment, "
                    f"{vital_count} vital, {sched_count} scheduled notifications"
                )
        except Exception as e:
            print(f"[Notification Scheduler] Error: {e}")

        # Run every 30 minutes
        await asyncio.sleep(1800)
