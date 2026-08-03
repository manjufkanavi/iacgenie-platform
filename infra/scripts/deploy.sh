#!/bin/bash
# deploy.sh — Safe deployment script for IacGenie unified infrastructure
# Dependency-ordered start with health check gates, rollback capability, and status reporting.
#
# Usage:
#   ./deploy.sh [up|restart|force-recreate] [service] [compose-file]
#   Examples:
#     ./deploy.sh up                    # Start all services in order
#     ./deploy.sh restart postgres       # Restart single service
#     ./deploy.sh force-recreate         # Force recreate all services
#
# COMPOSE_FILE env var or default: /home/mkanavi/workspace/git_workspace/iacgenie-unified-infra/docker-compose-unified.yml

set -euo pipefail

# ─── Configuration ───────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="/var/log/iacgenie"
TIMESTAMP=$(date +%Y%m%dT%H%M%SZ)
LOG_FILE="${LOG_DIR}/deploy-${TIMESTAMP}.log"
LOCK_FILE="/tmp/iacgenie-deploy.lock"

COMPOSE_FILE="${COMPOSE_FILE:-/home/mkanavi/workspace/git_workspace/iacgenie-unified-infra/docker-compose-unified.yml}"
LIGHTSERP_COMPOSE="${LIGHTSERP_COMPOSE:-/home/mkanavi/workspace/git_workspace/iacgenie-unified-infra/docker-compose-lightsrp.yml}"

ACTION="${1:-up}"
TARGET_SERVICE="${2:-}"
FORCE_MODE=""
if [ "$ACTION" = "force-recreate" ]; then
    FORCE_MODE="--force-recreate"
    ACTION="up"
fi

# ─── Dependency Order ────────────────────────────────────────────────────────
# Core infrastructure services in startup order
CORE_SERVICES=(postgres redis minio openbao keycloak gitea searxng nsqd)
APP_SERVICES=(lightserp-api lightserp-webui pagezen)
ALL_SERVICES=("${CORE_SERVICES[@]}" "${APP_SERVICES[@]}")

# Health check endpoints per service
declare -A HEALTH_CHECKS=(
    [postgres]="http://127.0.0.1:5432"
    [redis]="http://127.0.0.1:6379"
    [minio]="http://127.0.0.1:9001/minio/health/live"
    [openbao]="http://127.0.0.1:8200/v1/sys/health"
    [keycloak]="http://127.0.0.1:8080/auth/realms/iacgenie"
    [gitea]="http://127.0.0.1:3000/api/healthz"
    [searxng]="http://127.0.0.1:8081/search?format=json&q=test"
    [nsqd]="http://127.0.0.1:4161/nsqstat"
    [lightserp-api]="http://127.0.0.1:3071/health"
    [lightserp-webui]="http://127.0.0.1:3070/health"
    [pagezen]="http://127.0.0.1:8076/health"
)

# ─── Functions ───────────────────────────────────────────────────────────────

log() {
    local msg="[$(date +%Y-%m-%dT%H:%M:%S)] $*"
    echo "$msg" | tee -a "$LOG_FILE"
}

error() {
    log "ERROR: $*"
}

check_lock() {
    if [ -f "$LOCK_FILE" ]; then
        local pid
        pid=$(cat "$LOCK_FILE" 2>/dev/null)
        if kill -0 "$pid" 2>/dev/null; then
            error "Another deployment is running (PID $pid). Aborting."
            exit 1
        else
            rm -f "$LOCK_FILE"
            log "Removed stale lock file."
        fi
    fi
}

acquire_lock() {
    echo $$ > "$LOCK_FILE"
}

release_lock() {
    rm -f "$LOCK_FILE"
}

wait_for_health() {
    local service="$1"
    local url="${HEALTH_CHECKS[$service]:-}"
    local max_retries=30
    local retry=0

    if [ -z "$url" ]; then
        log "  No health check configured for $service — skipping health gate."
        return 0
    fi

    log "  Waiting for $service to become healthy..."
    while [ $retry -lt $max_retries ]; do
        if curl -sf --max-time 5 "$url" >/dev/null 2>&1; then
            log "  $service is healthy."
            return 0
        fi
        sleep 2
        retry=$((retry + 1))
    done
    error "  $service failed health check after ${max_retries} attempts."
    return 1
}

start_service() {
    local service="$1"
    local compose="$2"

    log "Starting $service..."
    if docker compose -f "$compose" up -d "$service" 2>&1 | tee -a "$LOG_FILE"; then
        wait_for_health "$service" || {
            error "$service failed to become healthy. Rolling back..."
            rollback_service "$service" "$compose"
            return 1
        }
    else
        error "Failed to start $service."
        return 1
    fi
}

rollback_service() {
    local service="$1"
    log "Rolling back $service — stopping and removing..."
    docker compose -f "$COMPOSE_FILE" stop "$service" 2>/dev/null || true
    docker compose -f "$COMPOSE_FILE" rm -f "$service" 2>/dev/null || true
    docker compose -f "$COMPOSE_FILE" up -d "$service" 2>&1 | tee -a "$LOG_FILE"
}

restart_service() {
    local service="$1"
    local compose="$2"
    log "Restarting $service (force-recreate)..."
    docker compose -f "$compose" up -d --force-recreate "$service" 2>&1 | tee -a "$LOG_FILE"
    wait_for_health "$service" || {
        error "$service failed health check after restart."
        return 1
    }
}

status_report() {
    log ""
    log "═══════════════════════════════════════════════════"
    log "  DEPLOYMENT STATUS REPORT"
    log "═══════════════════════════════════════════════════"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>&1 | tee -a "$LOG_FILE"
    log "═══════════════════════════════════════════════════"
}

# ─── Main ────────────────────────────────────────────────────────────────────

main() {
    mkdir -p "$LOG_DIR"
    check_lock
    acquire_lock
    trap release_lock EXIT

    log "═══════════════════════════════════════════════════"
    log "  IacGenie Deployment — ${ACTION^^} — ${TIMESTAMP}"
    log "  Compose: ${COMPOSE_FILE}"
    log "═══════════════════════════════════════════════════"

    if [ -n "$TARGET_SERVICE" ]; then
        # Single service operation
        log "Targeting single service: ${TARGET_SERVICE}"
        if [ "$ACTION" = "restart" ] || [ "$ACTION" = "force-recreate" ]; then
            restart_service "$TARGET_SERVICE" "$COMPOSE_FILE"
        else
            start_service "$TARGET_SERVICE" "$COMPOSE_FILE"
        fi
    else
        # Dependency-ordered deployment
        log "--- Starting core services (dependency order) ---"
        local failed=()
        for svc in "${CORE_SERVICES[@]}"; do
            start_service "$svc" "$COMPOSE_FILE" || failed+=("$svc")
        done

        if [ ${#failed[@]} -gt 0 ]; then
            error "Core services failed: ${failed[*]}"
            log "Aborting app services deployment."
            status_report
            exit 1
        fi

        log "--- Starting app services ---"
        for svc in "${APP_SERVICES[@]}"; do
            start_service "$svc" "$LIGHTSERP_COMPOSE" || error "Failed to start $svc (continuing...)"
        done
    fi

    status_report
    log "Deployment ${ACTION} ${TARGET_SERVICE:+for ${TARGET_SERVICE}} completed."
}

main "$@"
