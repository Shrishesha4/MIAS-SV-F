"""add lab technician role, groups, and report workflow fields

Revision ID: 20260422_0036
Revises: 20260421_0035
Create Date: 2026-04-22
"""
from alembic import op


revision = "20260422_0036"
down_revision = "20260421_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'LAB_TECHNICIAN'")

	op.execute(
		"""
		CREATE TABLE IF NOT EXISTS lab_technician_groups (
		    id VARCHAR NOT NULL,
		    name VARCHAR NOT NULL,
		    description TEXT,
		    is_active BOOLEAN NOT NULL DEFAULT TRUE,
		    created_at TIMESTAMP,
		    updated_at TIMESTAMP,
		    PRIMARY KEY (id),
		    UNIQUE (name)
		)
		"""
	)
	op.execute(
		"CREATE INDEX IF NOT EXISTS ix_lab_technician_groups_name "
		"ON lab_technician_groups (name)"
	)

	op.execute(
		"""
		CREATE TABLE IF NOT EXISTS lab_technicians (
		    id VARCHAR NOT NULL,
		    technician_id VARCHAR NOT NULL,
		    user_id VARCHAR NOT NULL,
		    group_id VARCHAR,
		    active_lab_id VARCHAR,
		    name VARCHAR NOT NULL,
		    phone VARCHAR,
		    email VARCHAR,
		    photo VARCHAR,
		    department VARCHAR,
		    has_selected_lab INTEGER NOT NULL DEFAULT 0,
		    last_checked_in_at TIMESTAMP,
		    created_at TIMESTAMP,
		    updated_at TIMESTAMP,
		    PRIMARY KEY (id),
		    UNIQUE (technician_id),
		    UNIQUE (user_id),
		    FOREIGN KEY (user_id) REFERENCES users(id),
		    FOREIGN KEY (group_id) REFERENCES lab_technician_groups(id),
		    FOREIGN KEY (active_lab_id) REFERENCES labs(id)
		)
		"""
	)
	op.execute(
		"CREATE INDEX IF NOT EXISTS ix_lab_technicians_technician_id "
		"ON lab_technicians (technician_id)"
	)
	op.execute(
		"CREATE INDEX IF NOT EXISTS ix_lab_technicians_user_id "
		"ON lab_technicians (user_id)"
	)
	op.execute(
		"CREATE INDEX IF NOT EXISTS ix_lab_technicians_group_id "
		"ON lab_technicians (group_id)"
	)
	op.execute(
		"CREATE INDEX IF NOT EXISTS ix_lab_technicians_active_lab_id "
		"ON lab_technicians (active_lab_id)"
	)

	op.execute(
		"""
		CREATE TABLE IF NOT EXISTS lab_technician_group_labs (
		    group_id VARCHAR NOT NULL,
		    lab_id VARCHAR NOT NULL,
		    PRIMARY KEY (group_id, lab_id),
		    FOREIGN KEY (group_id) REFERENCES lab_technician_groups(id),
		    FOREIGN KEY (lab_id) REFERENCES labs(id)
		)
		"""
	)

	op.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS lab_id VARCHAR")
	op.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS accepted_by_user_id VARCHAR")
	op.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS accepted_at TIMESTAMP")
	op.execute(
		"ALTER TABLE reports ADD CONSTRAINT IF NOT EXISTS fk_reports_lab_id "
		"FOREIGN KEY (lab_id) REFERENCES labs(id)"
	)
	op.execute(
		"ALTER TABLE reports ADD CONSTRAINT IF NOT EXISTS fk_reports_accepted_by_user_id "
		"FOREIGN KEY (accepted_by_user_id) REFERENCES users(id)"
	)
	op.execute(
		"CREATE INDEX IF NOT EXISTS ix_reports_lab_id ON reports (lab_id)"
	)
	op.execute(
		"CREATE INDEX IF NOT EXISTS ix_reports_accepted_by_user_id ON reports (accepted_by_user_id)"
	)


def downgrade() -> None:
	op.execute("DROP INDEX IF EXISTS ix_reports_accepted_by_user_id")
	op.execute("DROP INDEX IF EXISTS ix_reports_lab_id")
	op.execute("ALTER TABLE reports DROP CONSTRAINT IF EXISTS fk_reports_accepted_by_user_id")
	op.execute("ALTER TABLE reports DROP CONSTRAINT IF EXISTS fk_reports_lab_id")
	op.execute("ALTER TABLE reports DROP COLUMN IF EXISTS accepted_at")
	op.execute("ALTER TABLE reports DROP COLUMN IF EXISTS accepted_by_user_id")
	op.execute("ALTER TABLE reports DROP COLUMN IF EXISTS lab_id")
	op.execute("DROP TABLE IF EXISTS lab_technician_group_labs")
	op.execute("DROP TABLE IF EXISTS lab_technicians")
	op.execute("DROP TABLE IF EXISTS lab_technician_groups")