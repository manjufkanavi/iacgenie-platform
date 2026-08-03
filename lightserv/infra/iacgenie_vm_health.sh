#!/usr/bin/env bash
# =============================================================================
# iacgenie_vm_health.sh — Infrastructure Health Check for iacgenie VM
# =============================================================================
# Purpose: Check health of iacgenie infrastructure services on the remote VM
#          (192.168.0.118) and auto-fix recoverable issues.
#
# Runs FROM macOS (local machine) against remote Linux VM.
#
# Prerequisites:
#   - ssh with key-based auth to mkanavi@192.168.0.118
#   - curl installed (macOS ships with it)
#   - ping installed (macOS BSD syntax)
#
# SSH Key: ~/.ssh/newvm_key (key-based auth, no password for SSH itself)
#
# Usage:
#   ./iacgenie_vm_health.sh                    # Quick check with auto-fix
#   ./iacgenie_vm_health.sh --verbose          # Show detailed output
#   ./iacgenie_vm_health.sh --no-fix           # Check only, no auto-fix
#   ./iacgenie_vm_health.sh --check ping ssh   # Run only specified checks
#
# To add a new check:
#   1. Write check_<name>() that sets CHECK_STATUS=0 or CHECK_STATUS=1
#   2. Write fix_<name>() if the check is auto-fixable
#   3. Append "name" to the CHECKS array below
#   4. (Optional) Append "name" to the AUTO_FIXABLE array below
#
# =============================================================================

# ---------------------------------------------------------------------------
# Error handling: NO set -e. We collect errors and continue through all
# checks. A single failing check must NOT abort the script.
# ---------------------------------------------------------------------------
set -uo pipefail

# ---------------------------------------------------------------------------
# Configuration — tweak these to match your environment
# ---------------------------------------------------------------------------
VM_IP="192.168.0.118"
SSH_USER="mkanavi"
SSH_KEY="${HOME}/.ssh/newvm_key"
SSH_OPTS="-i ${SSH_KEY} -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ServerAliveInterval=5"

# Service paths on VM
COMPOSE_FILE="/home/${SSH_USER}/docker/iacgenie/docker-compose-newvm.yml"
COMPOSE_DIR="/home/${SSH_USER}/docker/iacgenie"
CLOUDFLARED_SERVICE="cloudflared-tunnel"

# Gitea config
GITEA_CONTAINER="iacgenie-gitea"
GITEA_INTERNAL="http://127.0.0.1:3000"
GITEA_API_HEALTH="${GITEA_INTERNAL}/api/v1/healthz"
GITEA_RUNNER_SERVICE="gitea-runner"
GITEA_RUNNER_BINARY="/home/${SSH_USER}/gitea-runner/gitea-runner"

# Wait timeouts (seconds)
TUNNEL_WAIT_TIMEOUT=30
GITEA_WAIT_TIMEOUT=60
GITEA_WAIT_INTERVAL=3

# ---------------------------------------------------------------------------
# Colors and log helpers — matches setup_local_cicd.sh style
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[  OK  ]${NC} $*"; }
fix()   { echo -e "${YELLOW}[  FIX  ]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }
skip()  { echo -e "${CYAN}[ SKIP ]${NC} $*"; }
bold()  { echo -e "${BOLD}$*${NC}"; }

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FILE="/tmp/iacgenie_vm_health.log"
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
VERBOSE=false
AUTO_FIX=true
HAS_SPECIFIC_CHECKS=false
SPECIFIC_CHECKS=()

# Validate specific check names against known checks
VALID_CHECKS="ping ssh tunnel gitea runner postgres redis minio"
IN_CHECK_MODE=false
for arg in "$@"; do
    if [[ "$arg" == "--check" ]]; then
        IN_CHECK_MODE=true
        continue
    fi
    if $IN_CHECK_MODE; then
        for vc in $VALID_CHECKS; do
            if [[ "$arg" == "$vc" ]]; then
                SPECIFIC_CHECKS+=("$arg")
                HAS_SPECIFIC_CHECKS=true
                break
            fi
        done
        continue
    fi
    if [[ "$arg" == "--verbose" || "$arg" == "-v" ]]; then
        VERBOSE=true
        continue
    fi
    if [[ "$arg" == "--no-fix" ]]; then
        AUTO_FIX=false
        continue
    fi
done

# ---------------------------------------------------------------------------
# Remote command helpers
# ---------------------------------------------------------------------------

# Run a command on the remote VM via SSH (key-based auth).
vm_run() {
    ssh ${SSH_OPTS} ${SSH_USER}@${VM_IP} "$1"
}

# Run a command with sudo on the remote VM.
# Requires passwordless sudo configured on the VM.
vm_sudo() {
    ssh ${SSH_OPTS} ${SSH_USER}@${VM_IP} "sudo $1"
}

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

# Try ping to the VM (macOS compatible BSD syntax).
try_ping() {
    if command -v ping &>/dev/null; then
        ping -c 3 -W 2 ${VM_IP} &>/dev/null
        return $?
    fi
    return 1
}

# Try SSH key-based auth to the VM.
try_ssh() {
    ssh ${SSH_OPTS} ${SSH_USER}@${VM_IP} "echo ok" &>/dev/null 2>&1
    return $?
}

# Wait for a systemd service to become active.
# Usage: wait_for_service "cloudflared-tunnel" 30
wait_for_service() {
    local service="$1"
    local timeout="${2:-30}"
    local elapsed=0

    while [[ $elapsed -lt $timeout ]]; do
        if vm_sudo "systemctl is-active --quiet ${service}" 2>/dev/null; then
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    return 1
}

# Wait for a Gitea container to become healthy via HTTP endpoint.
wait_for_gitea() {
    local timeout=${GITEA_WAIT_TIMEOUT}
    local elapsed=0

    while [[ $elapsed -lt $timeout ]]; do
        local http_code
        http_code=$(vm_run "curl -s -o /dev/null -w '%{http_code}' --max-time 5 ${GITEA_API_HEALTH}" 2>/dev/null || echo "000")
        if [[ "$http_code" == "200" ]]; then
            return 0
        fi
        sleep ${GITEA_WAIT_INTERVAL}
        elapsed=$((elapsed + GITEA_WAIT_INTERVAL))
    done
    return 1
}

# ---------------------------------------------------------------------------
# Check functions
# Each sets CHECK_STATUS=0 (pass) or CHECK_STATUS=1 (fail),
# CHECK_FIXABLE (whether auto-fix exists), CHECK_FIXED (whether fix succeeded).
# ---------------------------------------------------------------------------

check_ping() {
    CHECK_NAME="ping"
    CHECK_STATUS=1
    CHECK_FIXABLE=false
    CHECK_FIXED=false

    bold "--- Ping (VM Reachability) ---"

    if try_ping; then
        ok "VM ${VM_IP} is reachable (ICMP OK)"
        CHECK_STATUS=0
        log "PING: reachable"
    else
        error "VM ${VM_IP} is NOT reachable (ICMP failed)"
        CHECK_STATUS=1
        CHECK_FIXABLE=false
        log "PING: unreachable"
    fi
}

check_ssh() {
    CHECK_NAME="ssh"
    CHECK_STATUS=1
    CHECK_FIXABLE=false
    CHECK_FIXED=false

    bold "--- SSH (Key-Based Auth) ---"

    if try_ssh; then
        local hostname
        hostname=$(vm_run "hostname" 2>/dev/null || echo "unknown")
        ok "SSH key auth works (hostname: ${hostname})"
        CHECK_STATUS=0
        log "SSH: auth OK, hostname=${hostname}"
    else
        error "SSH key auth to ${SSH_USER}@${VM_IP} FAILED"
        CHECK_STATUS=1
        CHECK_FIXABLE=false
        log "SSH: authentication failed"
    fi
}

check_tunnel() {
    CHECK_NAME="tunnel"
    CHECK_STATUS=1
    CHECK_FIXABLE=true
    CHECK_FIXED=false

    bold "--- Cloudflared Tunnel ---"

    local status
    status=$(vm_sudo "systemctl is-active ${CLOUDFLARED_SERVICE}" 2>/dev/null || echo "unknown")

    if [[ "$status" == "active" ]]; then
        ok "cloudflared-tunnel service is active"
        CHECK_STATUS=0
        log "TUNNEL: active"
    else
        error "cloudflared-tunnel service is NOT active (status: ${status})"
        CHECK_STATUS=1
        log "TUNNEL: inactive (status=${status})"
    fi
}

check_gitea() {
    CHECK_NAME="gitea"
    CHECK_STATUS=1
    CHECK_FIXABLE=true
    CHECK_FIXED=false

    bold "--- Gitea (Git + CI/CD) ---"

    # Check container status
    local container_status
    container_status=$(vm_run "docker inspect --format='{{.State.Status}}' ${GITEA_CONTAINER}" 2>/dev/null || echo "not found")

    if [[ "$container_status" == "running" ]]; then
        ok "Gitea container is running"
    else
        error "Gitea container status: ${container_status}"
        CHECK_STATUS=1
        log "GITEA: container status=${container_status}"
        echo ""
        return
    fi

    # Check API health
    local http_code
    http_code=$(vm_run "curl -s -o /dev/null -w '%{http_code}' --max-time 10 ${GITEA_API_HEALTH}" 2>/dev/null || echo "000")

    if [[ "$http_code" == "200" ]]; then
        ok "Gitea API responding (HTTP ${http_code})"
        CHECK_STATUS=0
        log "GITEA: healthy (HTTP ${http_code})"
    else
        error "Gitea API NOT responding (HTTP ${http_code})"
        CHECK_STATUS=1
        log "GITEA: unhealthy (HTTP ${http_code})"
    fi
}

check_runner() {
    CHECK_NAME="runner"
    CHECK_STATUS=1
    CHECK_FIXABLE=true
    CHECK_FIXED=false

    bold "--- Gitea Actions Runner ---"

    local status
    status=$(vm_sudo "systemctl is-active ${GITEA_RUNNER_SERVICE}" 2>/dev/null || echo "unknown")

    if [[ "$status" == "active" ]]; then
        ok "Gitea runner systemd service is active"
        # Check runner process health
        local uptime
        uptime=$(vm_sudo "systemctl show --property=ActiveEnterTimestamp ${GITEA_RUNNER_SERVICE}" 2>/dev/null | cut -d= -f2)
        ok "Runner uptime: ${uptime}"
        CHECK_STATUS=0
        log "RUNNER: active (started ${uptime})"
    else
        error "Gitea runner systemd service is NOT active (status: ${status})"
        CHECK_STATUS=1
        log "RUNNER: inactive (status=${status})"
    fi
}

check_postgres() {
    CHECK_NAME="postgres"
    CHECK_STATUS=1
    CHECK_FIXABLE=true
    CHECK_FIXED=false

    bold "--- PostgreSQL ---"

    local status
    status=$(vm_run "docker exec iacgenie-postgres-1 pg_isready -U postgres 2>&1" 2>/dev/null || echo "not ready")

    if echo "$status" | grep -q "accepting connections"; then
        ok "PostgreSQL is accepting connections"
        CHECK_STATUS=0
        log "POSTGRES: healthy"
    else
        error "PostgreSQL is NOT ready: ${status}"
        CHECK_STATUS=1
        log "POSTGRES: unhealthy"
    fi
}

check_redis() {
    CHECK_NAME="redis"
    CHECK_STATUS=1
    CHECK_FIXABLE=true
    CHECK_FIXED=false

    bold "--- Redis ---"

    local status
    status=$(vm_run "docker exec iacgenie-redis-1 redis-cli -a \$(grep REDIS_PASSWORD ${COMPOSE_DIR}/.env | cut -d= -f2) ping 2>&1" 2>/dev/null || echo "not ready")

    if echo "$status" | grep -q "PONG"; then
        ok "Redis is responding (PONG)"
        CHECK_STATUS=0
        log "REDIS: healthy"
    else
        # Fallback: try without password for local check
        status=$(vm_run "docker exec iacgenie-redis-1 redis-cli ping 2>&1" 2>/dev/null || echo "not ready")
        if echo "$status" | grep -q "PONG"; then
            ok "Redis is responding (PONG)"
            CHECK_STATUS=0
            log "REDIS: healthy"
        else
            error "Redis is NOT responding: ${status}"
            CHECK_STATUS=1
            log "REDIS: unhealthy"
        fi
    fi
}

check_minio() {
    CHECK_NAME="minio"
    CHECK_STATUS=1
    CHECK_FIXABLE=true
    CHECK_FIXED=false

    bold "--- MinIO ---"

    local http_code
    http_code=$(vm_run "curl -s -o /dev/null -w '%{http_code}' --max-time 10 http://127.0.0.1:9000/minio/health/live" 2>/dev/null || echo "000")

    if [[ "$http_code" == "200" ]]; then
        ok "MinIO health endpoint responding (HTTP ${http_code})"
        CHECK_STATUS=0
        log "MINIO: healthy"
    else
        error "MinIO health endpoint NOT responding (HTTP ${http_code})"
        CHECK_STATUS=1
        log "MINIO: unhealthy"
    fi
}

# ---------------------------------------------------------------------------
# Fix functions
# Each sets CHECK_FIXED=true on success.
# ---------------------------------------------------------------------------

fix_tunnel() {
    bold "  [FIX] Restarting cloudflared-tunnel..."
    fix "Restarting systemd service: ${CLOUDFLARED_SERVICE}"

    if vm_sudo "systemctl restart ${CLOUDFLARED_SERVICE}" 2>/dev/null; then
        ok "Restart command succeeded. Waiting for service to become active..."
        if wait_for_service "${CLOUDFLARED_SERVICE}" ${TUNNEL_WAIT_TIMEOUT}; then
            ok "cloudflared-tunnel is now active"
            CHECK_FIXED=true
            log "FIX_TUNNEL: restart OK, service active"
            return 0
        else
            error "cloudflared-tunnel did NOT become active after ${TUNNEL_WAIT_TIMEOUT}s"
            log "FIX_TUNNEL: service did not become active"
            return 1
        fi
    else
        error "Failed to restart cloudflared-tunnel"
        log "FIX_TUNNEL: restart command failed"
        return 1
    fi
}

fix_gitea() {
    bold "  [FIX] Restarting Gitea container..."
    fix "Running: docker compose -f ${COMPOSE_FILE} up -d gitea in ${COMPOSE_DIR}"

    if vm_run "cd ${COMPOSE_DIR} && docker compose -f ${COMPOSE_FILE} up -d gitea" 2>/dev/null; then
        ok "Compose command succeeded. Waiting for Gitea to be healthy..."
        if wait_for_gitea; then
            ok "Gitea is now healthy"
            CHECK_FIXED=true
            log "FIX_GITEA: container restarted and healthy"
            return 0
        else
            error "Gitea did NOT become healthy after ${GITEA_WAIT_TIMEOUT}s"
            log "FIX_GITEA: container restarted but not healthy within timeout"
            return 1
        fi
    else
        error "Failed to start Gitea via docker compose"
        log "FIX_GITEA: docker compose command failed"
        return 1
    fi
}

fix_runner() {
    bold "  [FIX] Restarting Gitea runner service..."
    fix "Running: sudo systemctl restart ${GITEA_RUNNER_SERVICE}"

    if vm_sudo "systemctl restart ${GITEA_RUNNER_SERVICE}" 2>/dev/null; then
        ok "Restart command succeeded. Waiting for runner to become active..."
        if wait_for_service "${GITEA_RUNNER_SERVICE}" 30; then
            ok "Gitea runner is now active"
            CHECK_FIXED=true
            log "FIX_RUNNER: restart OK, service active"
            return 0
        else
            error "Gitea runner did NOT become active after 30s"
            log "FIX_RUNNER: service did not become active"
            return 1
        fi
    else
        error "Failed to restart Gitea runner"
        log "FIX_RUNNER: restart command failed"
        return 1
    fi
}

fix_postgres() {
    bold "  [FIX] Restarting PostgreSQL container..."
    fix "Running: docker compose up -d postgres"

    if vm_run "cd ${COMPOSE_DIR} && docker compose -f ${COMPOSE_FILE} up -d postgres" 2>/dev/null; then
        ok "Restart command succeeded. Waiting for PostgreSQL to be ready..."
        local elapsed=0
        while [[ $elapsed -lt 30 ]]; do
            local status
            status=$(vm_run "docker exec iacgenie-postgres-1 pg_isready -U postgres 2>&1" 2>/dev/null || echo "not ready")
            if echo "$status" | grep -q "accepting connections"; then
                ok "PostgreSQL is now accepting connections"
                CHECK_FIXED=true
                log "FIX_POSTGRES: healthy after restart"
                return 0
            fi
            sleep 3
            elapsed=$((elapsed + 3))
        done
        error "PostgreSQL did NOT become ready within 30s"
        return 1
    else
        error "Failed to restart PostgreSQL"
        log "FIX_POSTGRES: docker compose command failed"
        return 1
    fi
}

fix_redis() {
    bold "  [FIX] Restarting Redis container..."
    fix "Running: docker compose up -d redis"

    if vm_run "cd ${COMPOSE_DIR} && docker compose -f ${COMPOSE_FILE} up -d redis" 2>/dev/null; then
        ok "Restart command succeeded. Waiting for Redis..."
        local elapsed=0
        while [[ $elapsed -lt 20 ]]; do
            local status
            status=$(vm_run "docker exec iacgenie-redis-1 redis-cli ping 2>&1" 2>/dev/null || echo "not ready")
            if echo "$status" | grep -q "PONG"; then
                ok "Redis is now responding (PONG)"
                CHECK_FIXED=true
                log "FIX_REDIS: healthy after restart"
                return 0
            fi
            sleep 2
            elapsed=$((elapsed + 2))
        done
        error "Redis did NOT become ready within 20s"
        return 1
    else
        error "Failed to restart Redis"
        log "FIX_REDIS: docker compose command failed"
        return 1
    fi
}

fix_minio() {
    bold "  [FIX] Restarting MinIO container..."
    fix "Running: docker compose up -d minio"

    if vm_run "cd ${COMPOSE_DIR} && docker compose -f ${COMPOSE_FILE} up -d minio" 2>/dev/null; then
        ok "Restart command succeeded. Waiting for MinIO..."
        local elapsed=0
        while [[ $elapsed -lt 30 ]]; do
            local http_code
            http_code=$(vm_run "curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:9000/minio/health/live" 2>/dev/null || echo "000")
            if [[ "$http_code" == "200" ]]; then
                ok "MinIO is now healthy"
                CHECK_FIXED=true
                log "FIX_MINIO: healthy after restart"
                return 0
            fi
            sleep 3
            elapsed=$((elapsed + 3))
        done
        error "MinIO did NOT become healthy within 30s"
        return 1
    else
        error "Failed to restart MinIO"
        log "FIX_MINIO: docker compose command failed"
        return 1
    fi
}

# ---------------------------------------------------------------------------
# Arrays of checks and fixable checks
# Add or remove check names here to control what gets checked.
# ---------------------------------------------------------------------------

# Default checks — modify to add/remove which checks run by default.
CHECKS=(
    ping
    ssh
    tunnel
    gitea
    runner
)

# Checks that have auto-fix functions. Not listed = manual intervention only.
AUTO_FIXABLE=(
    tunnel
    gitea
    runner
    postgres
    redis
    minio
)

# ---------------------------------------------------------------------------
# Dispatcher helpers
# ---------------------------------------------------------------------------

get_check_function() { echo "check_$1"; }
get_fix_function()   { echo "fix_$1"; }

is_fixable() {
    local name="$1"
    for fn in "${AUTO_FIXABLE[@]}"; do
        [[ "$fn" == "$name" ]] && return 0
    done
    return 1
}

# ---------------------------------------------------------------------------
# Run a single check, then fix if needed
# ---------------------------------------------------------------------------
run_check() {
    local check_name="$1"
    local check_func
    check_func=$(get_check_function "$check_name")

    # Reset per-check state
    CHECK_NAME="$check_name"
    CHECK_STATUS=1
    CHECK_FIXABLE=false
    CHECK_FIXED=false

    if ! type "$check_func" &>/dev/null; then
        error "Check function '${check_func}' not defined. Skipping."
        return 1
    fi

    $check_func

    # Record result
    CHECK_RESULTS["${check_name}_status"]=$CHECK_STATUS
    CHECK_RESULTS["${check_name}_fixable"]=$([ "$CHECK_FIXABLE" = "true" ] && echo 1 || echo 0)
    CHECK_RESULTS["${check_name}_fixed"]=$([ "$CHECK_FIXED" = "true" ] && echo 1 || echo 0)

    # Attempt fix if failed, fixable, and auto-fix enabled
    if [[ $CHECK_STATUS -ne 0 ]] && is_fixable "$check_name" && $AUTO_FIX; then
        local fix_func
        fix_func=$(get_fix_function "$check_name")

        if type "$fix_func" &>/dev/null; then
            $fix_func
            CHECK_RESULTS["${check_name}_fixed"]=$([ "$CHECK_FIXED" = "true" ] && echo 1 || echo 0)
        else
            error "No fix function defined for '${check_name}'. Manual intervention required."
        fi
    fi
}

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
main() {
    echo "=============================================================="
    echo "  IacGenie VM Health Check"
    echo "  VM: ${SSH_USER}@${VM_IP}"
    echo "  $(date '+%Y-%m-%d %H:%M:%S %Z')"
    echo "=============================================================="
    echo ""

    declare -A CHECK_RESULTS

    local total_checks=0
    local passed_checks=0
    local failed_checks=0
    local fixed_checks=0

    # Use specific checks if provided, otherwise use default CHECKS array
    local checks_to_run=("${CHECKS[@]}")
    if $HAS_SPECIFIC_CHECKS; then
        checks_to_run=("${SPECIFIC_CHECKS[@]}")
    fi

    for check_name in "${checks_to_run[@]}"; do
        total_checks=$((total_checks + 1))
        run_check "$check_name"

        local status=${CHECK_RESULTS["${check_name}_status"]}
        if [[ $status -eq 0 ]]; then
            passed_checks=$((passed_checks + 1))
        else
            failed_checks=$((failed_checks + 1))
            local fixed=${CHECK_RESULTS["${check_name}_fixed"]}
            [[ $fixed -eq 1 ]] && fixed_checks=$((fixed_checks + 1))
        fi
    done

    # Summary
    echo ""
    echo "=============================================================="
    echo "  Summary"
    echo "=============================================================="
    echo -e "  Total checks : ${BOLD}${total_checks}${NC}"
    echo -e "  Passed       : ${GREEN}${passed_checks}${NC}"
    echo -e "  Failed       : ${RED}${failed_checks}${NC}"
    [[ $fixed_checks -gt 0 ]] && echo -e "  Auto-fixed   : ${YELLOW}${fixed_checks}${NC}"
    echo "=============================================================="

    if [[ $failed_checks -eq 0 ]]; then
        echo ""
        ok "All checks passed! Infrastructure is healthy."
        echo ""
    else
        local remaining=$((failed_checks - fixed_checks))
        if [[ $remaining -gt 0 ]]; then
            echo ""
            error "${remaining} issue(s) could not be auto-fixed. Manual intervention required."
            echo "  Log file: ${LOG_FILE}"
            echo ""
        else
            echo ""
            ok "All failures were auto-fixed. Infrastructure is now healthy."
            echo "  Log file: ${LOG_FILE}"
            echo ""
        fi
    fi

    # Per-check detail lines
    echo "  Per-check details:"
    for check_name in "${checks_to_run[@]}"; do
        local status=${CHECK_RESULTS["${check_name}_status"]}
        local fixable=${CHECK_RESULTS["${check_name}_fixable"]}
        local fixed=${CHECK_RESULTS["${check_name}_fixed"]}

        if [[ $status -eq 0 ]]; then
            echo -e "    [PASS] ${check_name}"
        elif [[ $fixable -eq 1 ]]; then
            if [[ $fixed -eq 1 ]]; then
                echo -e "    [FIXED] ${check_name} (auto-fixed)"
            else
                echo -e "    [FAIL]  ${check_name} (fixable but fix failed)"
            fi
        else
            echo -e "    [FAIL]  ${check_name} (not auto-fixable)"
        fi
    done
    echo ""

    log "SUMMARY: total=${total_checks} passed=${passed_checks} failed=${failed_checks} fixed=${fixed_checks}"
    exit $failed_checks
}

# Run main only when executed directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
