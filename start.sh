#!/usr/bin/env bash
# =============================================================================
#  MIAS Start Script
#  Usage:
#    ./start.sh                  — interactive
#    ./start.sh local            — start local dev stack
#    ./start.sh prod             — start production stack
#    ./start.sh local stop       — stop local stack
#    ./start.sh prod logs        — tail production logs
# =============================================================================
set -euo pipefail

# ── colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

ok()   { echo -e "${GREEN}  ✓ $*${NC}"; }
info() { echo -e "${CYAN}  → $*${NC}"; }
warn() { echo -e "${YELLOW}  ⚠ $*${NC}"; }
err()  { echo -e "${RED}  ✗ $*${NC}" >&2; }
hdr()  { echo -e "\n${BOLD}${BLUE}$*${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

COMPOSE_PROD="docker compose --env-file .env.production -f docker-compose.yml"
COMPOSE_LOCAL="docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.local.yml"

# ── helpers ───────────────────────────────────────────────────────────────────
require_docker() {
    if ! command -v docker &>/dev/null; then
        err "Docker not found. Install Docker Desktop and try again."
        exit 1
    fi
    if ! docker info &>/dev/null; then
        err "Docker daemon not running. Start Docker Desktop and try again."
        exit 1
    fi
}

wait_healthy() {
    local service=$1 compose_cmd=$2 max_wait=${3:-60}
    local elapsed=0
    info "Waiting for ${service} to be healthy…"
    while true; do
        status=$(eval "$compose_cmd ps --format json $service 2>/dev/null" \
            | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Health','') if isinstance(d,dict) else d[0].get('Health',''))" 2>/dev/null || echo "")
        [[ "$status" == "healthy" ]] && { ok "${service} healthy"; return 0; }
        [[ $elapsed -ge $max_wait ]] && { err "${service} did not become healthy in ${max_wait}s"; return 1; }
        sleep 3; (( elapsed+=3 ))
        echo -ne "    ${elapsed}s / ${max_wait}s\r"
    done
}

check_env_file() {
    local env_file=".env.${1}"
    if [[ ! -f "$env_file" ]]; then
        warn "${env_file} not found — compose variable defaults will be used."
        warn "Edit ${env_file} to override secrets and settings."
    else
        ok "Using ${env_file}"
    fi
}

print_banner() {
    echo -e "${BOLD}"
    echo "  ╔══════════════════════════════════════════╗"
    echo "  ║          MIAS — Saveetha Medical         ║"
    echo "  ║          Start / Stop Manager            ║"
    echo "  ╚══════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_endpoints() {
    local env=$1
    hdr "Services running:"
    echo -e "  ${BOLD}API (via Nginx)${NC}   →  http://localhost:8001/api/v1"
    echo -e "  ${BOLD}API (direct)${NC}      →  http://localhost:8000/api/v1"
    echo -e "  ${BOLD}API docs${NC}          →  http://localhost:8000/docs"
    echo -e "  ${BOLD}PostgreSQL${NC}        →  localhost:5432"
    echo -e "  ${BOLD}Redis${NC}             →  localhost:6379"
    if [[ "$env" == "local" ]]; then
        echo -e "  ${BOLD}Frontend (Vite)${NC}   →  http://localhost:5173"
    fi
    echo ""
    echo -e "  ${YELLOW}Default credentials:${NC}"
    echo -e "    admin/admin  |  d1/d1 (faculty)  |  s1/s1 (student)  |  p1/p1 (patient)"
    echo ""
}

# ── actions ───────────────────────────────────────────────────────────────────
do_start() {
    local env=$1 compose_cmd=$2

    hdr "Starting MIAS ($env)"
    check_env_file "$env"

    info "Pulling latest base images…"
    eval "$compose_cmd pull db redis pgbouncer nginx" 2>&1 | grep -E "Pulled|already" || true

    info "Building backend image…"
    eval "$compose_cmd build --parallel backend backend-worker"
    ok "Images built"

    info "Starting infrastructure (db → redis → pgbouncer)…"
    eval "$compose_cmd up -d db redis"
    wait_healthy "db" "$compose_cmd" 30

    eval "$compose_cmd up -d pgbouncer"
    wait_healthy "pgbouncer" "$compose_cmd" 60

    info "Starting backend (runs Alembic migrations on first boot)…"
    eval "$compose_cmd up -d backend"
    wait_healthy "backend" "$compose_cmd" 90

    info "Starting background worker…"
    eval "$compose_cmd up -d backend-worker"

    info "Starting nginx…"
    eval "$compose_cmd up -d nginx"
    ok "All backend services up"

    # Verify API reachable
    info "Checking API health…"
    local attempts=0
    until curl -sf http://localhost:8000/health >/dev/null 2>&1; do
        (( attempts++ ))
        [[ $attempts -ge 10 ]] && { err "API health check failed. Run: $compose_cmd logs backend"; exit 1; }
        sleep 2
    done
    ok "API is healthy → http://localhost:8000/health"

    print_endpoints "$env"
}

do_start_frontend() {
    hdr "Starting frontend dev server"
    if [[ ! -d "mias-client/node_modules" ]]; then
        info "Installing npm dependencies…"
        (cd mias-client && npm install --silent)
        ok "npm install done"
    fi
    info "Starting Vite dev server in background…"
    (cd mias-client && npm run dev > /tmp/mias-vite.log 2>&1 &)
    sleep 3
    if curl -sf http://localhost:5173 >/dev/null 2>&1; then
        ok "Frontend → http://localhost:5173"
    else
        warn "Vite may still be starting. Log: /tmp/mias-vite.log"
    fi
}

do_stop() {
    local env=$1 compose_cmd=$2
    hdr "Stopping MIAS ($env)"
    eval "$compose_cmd down"
    ok "All services stopped"
}

do_restart() {
    local env=$1 compose_cmd=$2
    do_stop "$env" "$compose_cmd"
    do_start "$env" "$compose_cmd"
}

do_rebuild() {
    local env=$1 compose_cmd=$2
    hdr "Rebuilding MIAS ($env)"
    eval "$compose_cmd down"
    eval "$compose_cmd build --no-cache --parallel backend backend-worker"
    do_start "$env" "$compose_cmd"
}

do_logs() {
    local compose_cmd=$1
    eval "$compose_cmd logs -f --tail=100"
}

do_status() {
    local compose_cmd=$1
    eval "$compose_cmd ps"
}

do_seed() {
    local compose_cmd=$1
    hdr "Seeding database"
    warn "This will DROP and recreate all tables with mock data!"
    read -rp "  Continue? [y/N]: " confirm </dev/tty
    [[ "$(echo "$confirm" | tr '[:upper:]' '[:lower:]')" == "y" ]] || { info "Aborted."; return; }
    eval "$compose_cmd exec backend python scripts/seed.py"
    ok "Database seeded"
}

do_reset_db() {
    local compose_cmd=$1
    hdr "Resetting database"
    err "WARNING: This deletes ALL data permanently."
    read -rp "  Type RESET to confirm: " confirm </dev/tty
    [[ "$confirm" == "RESET" ]] || { info "Aborted."; return; }
    eval "$compose_cmd down -v"
    ok "Volumes removed — DB will be fresh on next start"
}

# ── menus ─────────────────────────────────────────────────────────────────────
select_env() {
    hdr "Select environment" >/dev/tty
    echo "  1) Local dev  (MacBook Air — low resources, Vite frontend)" >/dev/tty
    echo "  2) Production (20-core / 64GB — full tuning, no frontend)"  >/dev/tty
    echo "" >/dev/tty
    local choice
    read -rp "  Choice [1/2]: " choice </dev/tty
    case "$choice" in
        1) echo "local" ;;
        2) echo "prod" ;;
        *) err "Invalid choice" >/dev/tty; exit 1 ;;
    esac
}

select_action() {
    local env=$1
    hdr "Select action  (env: $env)" >/dev/tty
    echo "  1) Start"                           >/dev/tty
    echo "  2) Stop"                            >/dev/tty
    echo "  3) Restart"                         >/dev/tty
    echo "  4) Rebuild & start  (clears cache)" >/dev/tty
    echo "  5) Logs  (tail all)"                >/dev/tty
    echo "  6) Status"                          >/dev/tty
    echo "  7) Seed database  ⚠ destructive"    >/dev/tty
    echo "  8) Reset database + volumes  ⚠ DELETES ALL DATA" >/dev/tty
    echo "" >/dev/tty
    local choice
    read -rp "  Choice [1-8]: " choice </dev/tty
    case "$choice" in
        1) echo "start" ;;
        2) echo "stop" ;;
        3) echo "restart" ;;
        4) echo "rebuild" ;;
        5) echo "logs" ;;
        6) echo "status" ;;
        7) echo "seed" ;;
        8) echo "reset" ;;
        *) err "Invalid choice" >/dev/tty; exit 1 ;;
    esac
}

# ── entry point ───────────────────────────────────────────────────────────────
main() {
    print_banner
    require_docker

    # Parse positional args
    local env="${1:-}"
    local action="${2:-}"

    # Resolve env
    if [[ -z "$env" ]]; then
        env=$(select_env)
    fi
    case "$env" in
        local|dev|l)   env="local";  compose_cmd="$COMPOSE_LOCAL" ;;
        prod|p)         env="prod";   compose_cmd="$COMPOSE_PROD"  ;;
        *)              err "Unknown env '$env'. Use: local | prod"; exit 1 ;;
    esac

    # Resolve action
    if [[ -z "$action" ]]; then
        action=$(select_action "$env")
    fi

    case "$action" in
        start)
            do_start "$env" "$compose_cmd"
            if [[ "$env" == "local" ]]; then
                read -rp "  Start frontend dev server (Vite)? [Y/n]: " fe </dev/tty
                [[ "${fe,,}" != "n" ]] && do_start_frontend
            fi
            ;;
        stop)    do_stop "$env" "$compose_cmd" ;;
        restart) do_restart "$env" "$compose_cmd" ;;
        rebuild) do_rebuild "$env" "$compose_cmd" ;;
        logs)    do_logs "$compose_cmd" ;;
        status)  do_status "$compose_cmd" ;;
        seed)    do_seed "$compose_cmd" ;;
        reset)   do_reset_db "$compose_cmd" ;;
        *)       err "Unknown action '$action'"; exit 1 ;;
    esac
}

main "$@"
