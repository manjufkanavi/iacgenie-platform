#!/bin/bash
# =============================================================================
# backup_verification.sh — Backup & DR Verification Script
# Phase 10.19: Backup & DR Verification
#
# Checks:
#   1. All service health status
#   2. Backup files exist and are non-empty
#   3. rclone sync connectivity
#   4. Backup file integrity (SHA256 checksums)
#   5. Logs all results
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_DIR="${COMPOSE_DIR:-/home/mkanavi/docker/iacgenie}"
LOG_FILE="/var/log/iacgenie-backup-verification.log"
COMPOSE_FILE="${COMPOSE_DIR}/docker-compose-unified.yml"
BACKUP_BASE="/home/mkanavi/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ERRORS=0
WARNINGS=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    local level="$1"
    shift
    local msg="$*"
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${ts} [${level}] ${msg}" | tee -a "$LOG_FILE"
}

info()  { log "INFO"  "$*"; }
warn()  { log "WARN"  "$*"; WARNINGS=$((WARNINGS + 1)); }
error() { log "ERROR" "$*"; ERRORS=$((ERRORS + 1)); }
ok()    { log "OK"    "$*"; }

# ── Report Header ────────────────────────────────────────────────────────────
info "================================================================="
info "  Backup Verification Report — ${TIMESTAMP}"
info "================================================================="

# ── 1. Service Health Check ─────────────────────────────────────────────────
info "--- Service Health Check ---"
HEALTHY=0
UNHEALTHY=0

declare -A SERVICES=(
    [postgres]="iacgenie-postgres"
    [redis]="iacgenie-redis"
    [minio]="iacgenie-minio"
    [openbao]="iacgenie-openbao"
    [keycloak]="iacgenie-keycloak"
    [gitea]="iacgenie-gitea"
    [searxng]="iacgenie-searxng"
    [lightserp-api]="iacgenie-lightserp-api"
    [lightserp-webui]="iacgenie-lightserp-webui"
    [lightserp-pagezen]="iacgenie-pagezen"
    [nginx]="iacgenie-nginx"
    [cloudflared]="iacgenie-cloudflared"
)

for svc in "${!SERVICES[@]}"; do
    container="${SERVICES[$svc]}"
    status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "not_found")

    if [ "$status" = "healthy" ]; then
        ok "Service ${svc} (${container}): healthy"
        HEALTHY=$((HEALTHY + 1))
    elif [ "$status" = "not_found" ] || [ "$status" = "noHealthcheck" ]; then
        info "Service ${svc} (${container}): ${status}"
    else
        warn "Service ${svc} (${container}): ${status} (expected: healthy)"
        UNHEALTHY=$((UNHEALTHY + 1))
    fi
done

info "Health summary: ${HEALTHY} healthy, ${UNHEALTHY} unhealthy/unknown"

# ── 2. Backup File Existence & Size ─────────────────────────────────────────
info "--- Backup File Verification ---"

check_backup() {
    local label="$1"
    local dir="$2"
    local pattern="$3"
    local min_size="${4:-100}"  # minimum expected file size in bytes

    if [ ! -d "$dir" ]; then
        error "Backup directory missing: ${dir}"
        return
    fi

    local latest
    latest=$(find "$dir" -name "$pattern" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)

    if [ -z "$latest" ] || [ ! -f "$latest" ]; then
        error "No backups found in ${dir} matching ${pattern}"
        return
    fi

    local size
    size=$(stat -c%s "$latest" 2>/dev/null || stat -f%z "$latest" 2>/dev/null || echo 0)

    if [ "$size" -ge "$min_size" ]; then
        ok "${label}: ${latest} (${size} bytes) — size OK"
    else
        warn "${label}: ${latest} (${size} bytes) — size below minimum (${min_size} bytes)"
    fi

    # Check checksum if available
    local checksum_file="${latest}.sha256"
    if [ -f "$checksum_file" ]; then
        if sha256sum -c "$checksum_file" --quiet 2>/dev/null; then
            ok "${label}: checksum verification passed"
        else
            error "${label}: checksum verification FAILED"
        fi
    else
        warn "${label}: no checksum file found (${checksum_file})"
    fi
}

check_backup "PostgreSQL"  "${BACKUP_BASE}/postgres"  "pgdump_*.dump"        1024
check_backup "OpenBao"     "${BACKUP_BASE}/openbao"   "openbao-snapshot-*"   1024
check_backup "Gitea"       "${BACKUP_BASE}/gitea"     "gitea-backup-*.tar.gz" 1024
check_backup "Nginx"       "${BACKUP_BASE}/nginx"     "nginx-config-*.tar.gz" 100
check_backup "Keycloak"    "${BACKUP_BASE}/keycloak"  "keycloak-export-*.json" 100
check_backup "Docker Volumes" "${BACKUP_BASE}/docker-volumes" "*.tar.gz" 1024

# ── 3. Rclone Sync Connectivity ─────────────────────────────────────────────
info "--- Rclone Sync Connectivity ---"

if command -v rclone &>/dev/null; then
    if [ -f "$HOME/.config/rclone/rclone.conf" ]; then
        # Try listing the remote config name (default: remote)
        REMOTE=$(grep -oP '^\[\K[^\]]+' "$HOME/.config/rclone/rclone.conf" | head -1)
        if [ -n "$REMOTE" ]; then
            if rclone ls "$REMOTE:/" --max-depth 0 --log-level ERROR 2>/dev/null; then
                ok "rclone connectivity to ${REMOTE}: OK"
            else
                warn "rclone connectivity to ${REMOTE}: FAILED"
            fi
        else
            warn "No rclone remote configured in $HOME/.config/rclone/rclone.conf"
        fi
    else
        warn "rclone config not found at $HOME/.config/rclone/rclone.conf"
    fi
else
    warn "rclone command not found — skipping rclone connectivity check"
fi

# ── 4. Backup Integrity Summary ─────────────────────────────────────────────
info "--- Integrity Check Summary ---"

# Check all checksum files in backup directory
INTEGRITY_OK=0
INTEGRITY_FAIL=0

if [ -d "$BACKUP_BASE" ]; then
    while IFS= read -r -d '' checksum_file; do
        if sha256sum -c "$checksum_file" --quiet 2>/dev/null; then
            INTEGRITY_OK=$((INTEGRITY_OK + 1))
        else
            error "Checksum verification failed: $(basename "$checksum_file")"
            INTEGRITY_FAIL=$((INTEGRITY_FAIL + 1))
        fi
    done < <(find "$BACKUP_BASE" -name "*.sha256" -print0 2>/dev/null)
fi

info "Checksum integrity: ${INTEGRITY_OK} passed, ${INTEGRITY_FAIL} failed"

# ── 5. Final Summary ────────────────────────────────────────────────────────
info "================================================================="
info "  Verification Summary"
info "================================================================="
info "  Errors:      ${ERRORS}"
info "  Warnings:    ${WARNINGS}"
info "  Healthy:     ${HEALTHY} services"
info "  Unhealthy:   ${UNHEALTHY} services"
info "  Checksums:   ${INTEGRITY_OK} OK / ${INTEGRITY_FAIL} failed"
info "================================================================="

if [ $ERRORS -eq 0 ]; then
    info "  STATUS: ALL CHECKS PASSED"
else
    info "  STATUS: ${ERRORS} ERROR(S) DETECTED"
    exit 1
fi
