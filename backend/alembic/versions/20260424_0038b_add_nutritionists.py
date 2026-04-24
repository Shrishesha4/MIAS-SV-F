"""add nutritionists

Revision ID: 20260424_0038b
Revises: 20260423_0037
Create Date: 2026-04-24
"""

from alembic import op

revision = "20260424_0038b"
down_revision = "20260423_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'NUTRITIONIST'")

    op.execute(
        """
		CREATE TABLE IF NOT EXISTS nutritionists (
		    id VARCHAR NOT NULL,
		    nutritionist_id VARCHAR NOT NULL,
		    user_id VARCHAR NOT NULL,
		    clinic_id VARCHAR NOT NULL,
		    name VARCHAR NOT NULL,
		    phone VARCHAR,
		    email VARCHAR,
		    photo VARCHAR,
		    created_at TIMESTAMP,
		    updated_at TIMESTAMP,
		    PRIMARY KEY (id),
		    UNIQUE (nutritionist_id),
		    UNIQUE (user_id),
		    UNIQUE (clinic_id),
		    FOREIGN KEY (user_id) REFERENCES users(id),
		    FOREIGN KEY (clinic_id) REFERENCES clinics(id)
		)
		"""
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_nutritionists_nutritionist_id "
        "ON nutritionists (nutritionist_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_nutritionists_user_id ON nutritionists (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_nutritionists_clinic_id "
        "ON nutritionists (clinic_id)"
    )

    op.execute(
        """
		CREATE TABLE IF NOT EXISTS nutritionist_clinic_sessions (
		    id VARCHAR NOT NULL,
		    nutritionist_id VARCHAR NOT NULL,
		    clinic_id VARCHAR NOT NULL,
		    clinic_name VARCHAR NOT NULL,
		    department VARCHAR NOT NULL,
		    date TIMESTAMP NOT NULL,
		    status VARCHAR,
		    checked_in_at TIMESTAMP NOT NULL,
		    checked_out_at TIMESTAMP,
		    PRIMARY KEY (id),
		    FOREIGN KEY (nutritionist_id) REFERENCES nutritionists(id),
		    FOREIGN KEY (clinic_id) REFERENCES clinics(id)
		)
		"""
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_nutritionist_clinic_sessions_nutritionist_id "
        "ON nutritionist_clinic_sessions (nutritionist_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_nutritionist_clinic_sessions_clinic_id "
        "ON nutritionist_clinic_sessions (clinic_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_nutritionist_clinic_sessions_date "
        "ON nutritionist_clinic_sessions (date)"
    )

    op.execute(
        """
		CREATE TABLE IF NOT EXISTS nutritionist_notes (
		    id VARCHAR NOT NULL,
		    nutritionist_id VARCHAR NOT NULL,
		    patient_id VARCHAR NOT NULL,
		    clinic_id VARCHAR NOT NULL,
		    note_date DATE NOT NULL,
		    content TEXT NOT NULL,
		    created_at TIMESTAMP NOT NULL,
		    updated_at TIMESTAMP NOT NULL,
		    PRIMARY KEY (id),
		    CONSTRAINT uq_nutritionist_notes_daily UNIQUE (nutritionist_id, patient_id, note_date),
		    FOREIGN KEY (nutritionist_id) REFERENCES nutritionists(id),
		    FOREIGN KEY (patient_id) REFERENCES patients(id),
		    FOREIGN KEY (clinic_id) REFERENCES clinics(id)
		)
		"""
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_nutritionist_notes_nutritionist_id "
        "ON nutritionist_notes (nutritionist_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_nutritionist_notes_patient_id "
        "ON nutritionist_notes (patient_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_nutritionist_notes_clinic_id "
        "ON nutritionist_notes (clinic_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_nutritionist_notes_patient_date "
        "ON nutritionist_notes (patient_id, note_date)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS nutritionist_notes")
    op.execute("DROP TABLE IF EXISTS nutritionist_clinic_sessions")
    op.execute("DROP TABLE IF EXISTS nutritionists")
