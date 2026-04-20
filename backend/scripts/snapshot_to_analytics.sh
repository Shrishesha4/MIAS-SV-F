#!/usr/bin/env bash
# snapshot_to_analytics.sh — Phase 1 snapshot pipeline
#
# Dumps the primary OLTP database and restores it into the analytics
# Postgres instance. Then applies post-load optimisations (indexes,
# materialized views, metadata).
#
# Usage:
#   ./scripts/snapshot_to_analytics.sh
#
# Environment variables (with defaults for local dev):
#   PRIMARY_DB_HOST, PRIMARY_DB_PORT, PRIMARY_DB_USER, PRIMARY_DB_NAME
#   ANALYTICS_DB_HOST, ANALYTICS_DB_PORT, ANALYTICS_DB_USER, ANALYTICS_DB_NAME
#   PGPASSWORD (or use .pgpass / PGPASSFILE)
#   RETENTION_DAYS  — keep N days of snapshots (default 7)

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────

PRIMARY_DB_HOST="${PRIMARY_DB_HOST:-localhost}"
PRIMARY_DB_PORT="${PRIMARY_DB_PORT:-5434}"
PRIMARY_DB_USER="${PRIMARY_DB_USER:-mias}"
PRIMARY_DB_NAME="${PRIMARY_DB_NAME:-mias_mp}"

ANALYTICS_DB_HOST="${ANALYTICS_DB_HOST:-localhost}"
ANALYTICS_DB_PORT="${ANALYTICS_DB_PORT:-5434}"
ANALYTICS_DB_USER="${ANALYTICS_DB_USER:-mias}"
ANALYTICS_DB_NAME="${ANALYTICS_DB_NAME:-mias_analytics}"

RETENTION_DAYS="${RETENTION_DAYS:-7}"
DUMP_DIR="/tmp/mias_snapshot_$(date +%Y%m%d_%H%M%S)"
JOBS=4
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ── Step 1: Dump primary ────────────────────────────────────────────

log "Dumping primary DB ${PRIMARY_DB_NAME}..."
pg_dump \
  --host="$PRIMARY_DB_HOST" \
  --port="$PRIMARY_DB_PORT" \
  --username="$PRIMARY_DB_USER" \
  --dbname="$PRIMARY_DB_NAME" \
  --format=directory \
  --jobs="$JOBS" \
  --no-owner \
  --no-acl \
  --schema=public \
  --file="$DUMP_DIR"

log "Dump complete → $DUMP_DIR"

# ── Step 2: Drop + recreate analytics DB ─────────────────────────────

log "Recreating analytics DB ${ANALYTICS_DB_NAME}..."
psql \
  --host="$ANALYTICS_DB_HOST" \
  --port="$ANALYTICS_DB_PORT" \
  --username="$ANALYTICS_DB_USER" \
  --dbname=postgres \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${ANALYTICS_DB_NAME}' AND pid <> pg_backend_pid();" \
  -c "DROP DATABASE IF EXISTS ${ANALYTICS_DB_NAME};" \
  -c "CREATE DATABASE ${ANALYTICS_DB_NAME};"

# ── Step 3: Restore into analytics ──────────────────────────────────

log "Restoring into analytics DB..."
pg_restore \
  --host="$ANALYTICS_DB_HOST" \
  --port="$ANALYTICS_DB_PORT" \
  --username="$ANALYTICS_DB_USER" \
  --dbname="$ANALYTICS_DB_NAME" \
  --jobs="$JOBS" \
  --no-owner \
  --no-acl \
  "$DUMP_DIR" || true  # pg_restore returns non-zero on warnings

# ── Step 4: Post-load SQL (indexes, views, metadata) ────────────────

log "Running post-load optimisations..."
psql \
  --host="$ANALYTICS_DB_HOST" \
  --port="$ANALYTICS_DB_PORT" \
  --username="$ANALYTICS_DB_USER" \
  --dbname="$ANALYTICS_DB_NAME" \
  <<'SQL'

-- ── Snapshot metadata table ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mrd_snapshot_meta (
    id SERIAL PRIMARY KEY,
    snapshot_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    source_db VARCHAR NOT NULL,
    status VARCHAR DEFAULT 'complete'
);
INSERT INTO mrd_snapshot_meta (source_db) VALUES ('PRIMARY_DB_NAME_PLACEHOLDER');

-- ── BRIN indexes on time columns (space-efficient for append-only) ──
CREATE INDEX CONCURRENTLY IF NOT EXISTS brin_medical_records_date
    ON medical_records USING brin (date);
CREATE INDEX CONCURRENTLY IF NOT EXISTS brin_prescriptions_date
    ON prescriptions USING brin (date);
CREATE INDEX CONCURRENTLY IF NOT EXISTS brin_reports_date
    ON reports USING brin (date);
CREATE INDEX CONCURRENTLY IF NOT EXISTS brin_admissions_admission_date
    ON admissions USING brin (admission_date);
CREATE INDEX CONCURRENTLY IF NOT EXISTS brin_vitals_recorded_at
    ON vitals USING brin (recorded_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS brin_wallet_transactions_date
    ON wallet_transactions USING brin (date);

-- ── Covering indexes for MRD query patterns ─────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_mrd_records_patient_date
    ON medical_records (patient_id, date DESC) INCLUDE (id, type, department);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_mrd_prescriptions_patient_date
    ON prescriptions (patient_id, date DESC) INCLUDE (id, department, status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_mrd_reports_patient_date
    ON reports (patient_id, date DESC) INCLUDE (id, type, department, status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_mrd_admissions_patient_date
    ON admissions (patient_id, admission_date DESC) INCLUDE (id, department, status);

-- ── Materialized views for common MRD reports ───────────────────────

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_patient_record_counts AS
SELECT
    patient_id,
    EXTRACT(YEAR FROM date)::int AS year,
    EXTRACT(MONTH FROM date)::int AS month,
    type::text AS record_type,
    COUNT(*) AS count
FROM medical_records
GROUP BY patient_id, year, month, type;

CREATE UNIQUE INDEX IF NOT EXISTS ux_mv_patient_record_counts
    ON mv_patient_record_counts (patient_id, year, month, record_type);


CREATE MATERIALIZED VIEW IF NOT EXISTS mv_department_activity AS
SELECT
    department,
    EXTRACT(YEAR FROM date)::int AS year,
    EXTRACT(MONTH FROM date)::int AS month,
    type::text AS record_type,
    COUNT(*) AS count
FROM medical_records
GROUP BY department, year, month, type;

CREATE UNIQUE INDEX IF NOT EXISTS ux_mv_department_activity
    ON mv_department_activity (department, year, month, record_type);


CREATE MATERIALIZED VIEW IF NOT EXISTS mv_prescription_volume AS
SELECT
    EXTRACT(YEAR FROM p.date)::int AS year,
    EXTRACT(MONTH FROM p.date)::int AS month,
    pm.name AS medication_name,
    COUNT(*) AS count
FROM prescriptions p
JOIN prescription_medications pm ON pm.prescription_id = p.id
GROUP BY year, month, pm.name;

CREATE UNIQUE INDEX IF NOT EXISTS ux_mv_prescription_volume
    ON mv_prescription_volume (year, month, medication_name);

-- ── Refresh materialized views ──────────────────────────────────────
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_patient_record_counts;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_department_activity;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_prescription_volume;

SQL

# Replace placeholder with actual DB name
psql \
  --host="$ANALYTICS_DB_HOST" \
  --port="$ANALYTICS_DB_PORT" \
  --username="$ANALYTICS_DB_USER" \
  --dbname="$ANALYTICS_DB_NAME" \
  -c "UPDATE mrd_snapshot_meta SET source_db = '${PRIMARY_DB_NAME}' WHERE source_db = 'PRIMARY_DB_NAME_PLACEHOLDER';"

# ── Step 5: Update Redis snapshot version ────────────────────────────

if command -v redis-cli &>/dev/null; then
  REDIS_URL="${REDIS_URL:-redis://localhost:6381}"
  redis-cli -u "$REDIS_URL" SET "mrd:snapshot_version" "$TIMESTAMP" EX 172800 >/dev/null 2>&1 || true
  log "Updated Redis snapshot version to $TIMESTAMP"
fi

# ── Step 6: Cleanup ─────────────────────────────────────────────────

rm -rf "$DUMP_DIR"
log "Snapshot pipeline complete at $TIMESTAMP"
