#!/bin/bash
# rollback.sh — Rollback deployed services on IacGenie unified infrastructure
#
# Usage:
#   ./rollback.sh                  # Rollback all services to last known-good state
#   ./rollback.sh <service>        # Rollback a single service
#   ./rollback.sh --all            # Rollback ALL services including core infra
#
# COMPOSE_FILE env var or default: same as deploy.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="/var/log/iacgenie"
TIMESTAMP=$(date +%Y%m%dT%H%M%SZ)
LOG_FILE="${LOG_DIR}/rollback-${TIMESTAMP}.log"
LOCK_FILE="/tmp/iacgenie-rollback.lock"

COMPOSE_FILE="${COMPOSE_FILE:-/home/mkanavi/workspace/git_workspace/iacgenie-unified-infra/docker-compose-unified.yml}"
LIGHTSERP_COMPOSE="${LIGHTSERP_COMPOSE:-/home/mkanavi/workspace/git_workspace/iacgenie-unified-infra/docker-compose-lightsrp.yml}"

ACTION="${1:-service}"
TARGET="${2:-}"
ALL_MODE=""

if [ "$ACTION" = "--all" ]; then
    ALL_MODE=true
    ACTION="service"
elif [ "$ACTION" = "service" ] && [ -z "$TARGET" ]; then
    TARGET=""
fi

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
            error "Another rollback is running (PID $pid). Aborting."
            exit 1
        else
            rm -f "$LOCK_FILE"
        fi
    fi
}

acquire_lock() {
    echo $$ > "$LOCK_FILE"
}

release_lock() {
    rm -f "$LOCK_FILE"
}

rollback_one() {
    local service="$1"
    local compose="$2"

    log "Rolling back $service..."

    # 1. Stop the service
    log "  Stopping $service..."
    docker compose -f "$compose" stop "$service" 2>/dev/null || true

    # 2. Remove containers (keeps images)
    log "  Removing containers for $service..."
    docker compose -f "$compose" rm -f "$service" 2>/dev/null || true

    # 3. Re-deploy from compose file
    log "  Re-deploying $service..."
    if docker compose -f "$compose" up -d "$service" 2>&1 | tee -a "$LOG_FILE"; then
        log "  $service rolled back successfully."
    else
        error "  Failed to re-deploy $service."
        return 1
    fi
}

status_report() {
    log ""
    log "═══════════════════════════════════════════════════"
    log "  ROLLBACK STATUS REPORT"
    log "═══════════════════════════════════════════════════"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>&1 | tee -a "$LOG_FILE"
    log "═══════════════════════════════════════════════════"
}

main() {
    mkdir -p "$LOG_DIR"
    check_lock
    acquire_lock
    trap release_lock EXIT

    log "═══════════════════════════════════════════════════"
    log "  IacGenie Rollback — ${TIMESTAMP}"
    log "═══════════════════════════════════════════════════"

    if [ -n "$TARGET" ] && [ "$ALL_MODE" != true ]; then
        # Single service rollback
        rollback_one "$TARGET" "$COMPOSE_FILE"
    elif [ "$ALL_MODE" = true ]; then
        # Rollback everything
        local services=()
        for f in "$COMPOSE_FILE" "$LIGHTSERP_COMPOSE"; do
            if [ -f "$f" ]; then
                while IFS= read -r svc; do
                    services+=("$svc")
                done < <(docker compose -f "$f" ps --services 2>/dev/null)
            fi
        done

        if [ ${#services[@]} -eq 0 ]; then
            error "No services found to rollback."
            exit 1
        fi

        log "Found ${#services[@]} services to rollback."

        # Rollback core services first (reverse dependency order)
        local core_services=("pagezen" "lightserp-webui" "lightserp-api" "nsqd" "searxng" "gitea" "keycloak" "openbao" "minio" "redis" "postgres")
        for svc in "${core_services[@]}"; do
            if [[ " ${services[*]} " =~ " ${svc} " ]]; then
                rollback_one "$svc" "$COMPOSE_FILE"
            fi
        done

        # Rollback app services
        local app_services=("pagezen" "lightserp-webui" "lightserp-api")
        for svc in "${app_services[@]}"; do
            if [[ " ${services[*]} " =~ " ${svc} " ]]; then
                rollback_one "$svc" "$LIGHTSERP_COMPOSE"
            fi
        done
    else
        # No target — just roll back app services (lightserp + pagezen)
        log "No service specified. Rolling back app services..."

        for svc in pagezen lightserp-webui lightserp-api; do
            docker compose -f "$LIGHTSERP_COMPOSE" stop "$svc" 2>/dev/null || true
            docker compose -f "$LIGHTSERP_COMPOSE" rm -f "$svc" 2>/dev/null || true
            docker compose -f "$LIGHTSERP_COMPOSE" up -d "$svc" 2>&1 | tee -a "$LOG_FILE" || true
        done
    fi

    status_report
    log "Rollback completed."
}

main "$@"
