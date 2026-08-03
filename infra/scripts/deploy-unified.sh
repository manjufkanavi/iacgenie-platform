#!/bin/bash
# =============================================================================
# deploy-unified.sh — Bootstrap the unified infrastructure stack
# =============================================================================
# Usage: ./deploy-unified.sh
#
# This script:
#   1. Validates the docker-compose config
#   2. Starts the shared services
#   3. Waits for health checks
#   4. Verifies backups before/after deployment
#   5. Optionally starts IacGenie and LightSerp
#
# ── Suggested Crontab ──────────────────────────────────────────────────────
# Daily backup verification at 3:00 AM:
#   0 3 * * * /opt/scripts/backup_verification.sh >> /var/log/backup-verify.log 2>&1
# Weekly full DR test on Sundays at 4:00 AM:
#   0 4 * * 0 /opt/scripts/dr_test.sh >> /var/log/dr-test.log 2>&1
# ───────────────────────────────────────────────────────────────────────────
#
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

UNIFIED="docker compose -f docker-compose-unified.yml"
IACGENIE="docker compose -f docker-compose-iacgenie.yml"
LIGHTSRP="docker compose -f docker-compose-lightsrp.yml"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}   $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}   $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}   $*" && exit 1; }

# ── Backup Verification Functions ───────────────────────────────────────────
pre_deploy_backup_verify() {
    info "Running pre-deployment backup verification..."
    local script="${SCRIPT_DIR}/scripts/backup_verification.sh"
    if [ -f "$script" ] && [ -x "$script" ]; then
        if "$script" 2>&1 | tail -5; then
            info "Pre-deployment backup verification passed"
        else
            warn "Backup verification found issues — proceeding with caution"
        fi
    else
        warn "Backup verification script not found or not executable: $script"
    fi
}

post_deploy_backup_verify() {
    info "Running post-deployment backup verification..."
    local script="${SCRIPT_DIR}/scripts/backup_verification.sh"
    if [ -f "$script" ] && [ -x "$script" ]; then
        if "$script" 2>&1 | tail -5; then
            info "Post-deployment backup verification passed"
        else
            warn "Post-deployment backup verification found issues"
        fi
    else
        warn "Backup verification script not found or not executable: $script"
    fi
}

# ── Pre-flight ───────────────────────────────────────────────────────────────
info "Validating docker-compose config..."
$UNIFIED config > /dev/null || fail "Docker compose config validation failed"
info "Config validation passed"

# ── Pre-deploy backup verification ──────────────────────────────────────────
pre_deploy_backup_verify

# ── Cleanup existing stack ───────────────────────────────────────────────────
if $UNIFIED ps --format '{{.Name}}' 2>/dev/null | head -1 >/dev/null 2>&1; then
    warn "Existing stack detected. Performing graceful shutdown..."
    $UNIFIED down --remove-orphans
    $IACGENIE down --remove-orphans 2>/dev/null || true
    $LIGHTSRP down --remove-orphans 2>/dev/null || true
fi

# ── Start unified infrastructure ─────────────────────────────────────────────
info "Starting unified infrastructure..."
$UNIFIED up -d postgres redis minio openbao keycloak searxng pagezen nsqd
$UNIFIED up -d minio-init openbao-init

# Wait for core services
echo ""
info "Waiting for core services to become healthy..."

wait_for() {
    local service=$1
    local max=120
    local count=0
    while [ $count -lt $max ]; do
        if docker inspect --format='{{.State.Health.Status}}' "$(docker compose -f docker-compose-unified.yml ps -q $service 2>/dev/null | head -1)" 2>/dev/null | grep -q "healthy"; then
            info "${service} is healthy"
            return 0
        fi
        sleep 2
        count=$((count + 2))
    done
    warn "${service} did not report healthy within ${max}s (may still be starting)"
}

wait_for postgres
wait_for redis
wait_for minio
wait_for openbao
wait_for keycloak

# ── Start per-project services ───────────────────────────────────────────────
echo ""
info "Starting IacGenie and LightSerp services..."
$IACGENIE up -d 2>/dev/null || warn "IacGenie compose failed to start"
$LIGHTSRP up -d 2>/dev/null || warn "LightSerp compose failed to start"

# ── Post-deploy backup verification ─────────────────────────────────────────
post_deploy_backup_verify

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
info "==============================================================="
info "  UNIFIED INFRASTRUCTURE — Deployment Complete"
info "==============================================================="
echo ""
info "PostgreSQL:    127.0.0.1:5432"
info "Redis:         127.0.0.1:6379"
info "MinIO:         http://127.0.0.1:9000  (console: 9001)"
info "OpenBao:       http://127.0.0.1:8200  (dev mode)"
info "Keycloak:      http://127.0.0.1:8080  (admin: admin / admin-admin)"
info "SearXNG:       http://127.0.0.1:8070"
info "Prometheus:    http://127.0.0.1:9090"
info "Grafana:       http://127.0.0.1:3000"
info "Loki:          http://127.0.0.1:3100"
info "Nginx:         https://127.0.0.1:443"
echo ""
info "Run '$UNIFIED ps' to check all services"
info "Run '$UNIFIED logs -f' to view logs"
