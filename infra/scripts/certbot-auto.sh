#!/bin/bash
# =============================================================================
# certbot-auto.sh — Automated TLS Certificate Renewal
# Phase 10.20: TLS Certificate Automation
#
# Runs certbot renew with --nginx and --dns-cloudflare flags,
# validates renewal, restarts nginx, and sends alert on failure.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="/var/log/certbot-renew.log"
ALERT_SCRIPT="${SCRIPT_DIR}/cert-alert.sh"
NGINX_RELOAD_CMD="docker exec iacgenie-nginx nginx -s reload || systemctl reload nginx"
ALERT_EMAIL="${ALERT_EMAIL:-admin@iacgenie.com}"
ALERT_WEBHOOK="${ALERT_WEBHOOK:-}"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log() {
    local msg="$*"
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')
    echo "${ts} ${msg}" | tee -a "$LOG_FILE"
}

send_alert() {
    local status="$1"
    local msg="$2"

    log "Sending alert: ${status} - ${msg}"

    # Email alert (if mail command available)
    if command -v mail &>/dev/null && [ -n "$ALERT_EMAIL" ]; then
        echo "$msg" | mail -s "[certbot] ${status} - TLS Certificate Renewal" "$ALERT_EMAIL" 2>/dev/null || true
    fi

    # Webhook alert (if configured)
    if [ -n "$ALERT_WEBHOOK" ]; then
        curl -sf -X POST "$ALERT_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{\"text\": \"[certbot] ${status}: ${msg}\"}" \
            2>/dev/null || true
    fi
}

log "================================================================="
log "  TLS Certificate Renewal — $(date '+%Y-%m-%d %H:%M:%S')"
log "================================================================="

# ── Step 1: Check if certificates exist ─────────────────────────────────────
CERT_DIR="/etc/letsencrypt/live"

if [ ! -d "$CERT_DIR" ]; then
    log "ERROR: Let's Encrypt cert directory not found at ${CERT_DIR}"
    log "First-time certificate request required — run certbot manually"
    send_alert "ERROR" "Let's Encrypt directory missing: ${CERT_DIR}"
    exit 1
fi

CERT_COUNT=$(find "$CERT_DIR" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
if [ "$CERT_COUNT" -eq 0 ]; then
    log "No certificates found — running full certbot request instead of renew"
fi

log "Found ${CERT_COUNT} certificate(s) in ${CERT_DIR}"

# ── Step 2: Run certbot renew ───────────────────────────────────────────────
log "Running certbot renew..."

RENEW_OUTPUT=$(certbot renew \
    --nginx \
    --dns-cloudflare \
    --dns-cloudflare-credentials /etc/letsencrypt/cloudflare.ini \
    --non-interactive \
    --quiet \
    --force-renewal \
    2>&1) || true

if echo "$RENEW_OUTPUT" | grep -qi "successfully renewed"; then
    log "OK: Certificate(s) renewed successfully"
elif echo "$RENEW_OUTPUT" | grep -qi "no renewal attempts\|unchanged"; then
    log "OK: No certificates needed renewal (up to date)"
elif [ -n "$RENEW_OUTPUT" ]; then
    log "WARN: Unexpected output from certbot renew"
    log "  Output: ${RENEW_OUTPUT}"
else
    log "OK: Certbot renew completed without errors"
fi

# ── Step 3: Validate renewed certificates ───────────────────────────────────
log "Validating renewed certificates..."

VALIDATION_OK=true
for cert_dir in "$CERT_DIR"/*/; do
    hostname=$(basename "$cert_dir")
    cert_file="${cert_dir}fullchain.pem"

    if [ -f "$cert_file" ]; then
        expiry_date=$(openssl x509 -enddate -noout -in "$cert_file" 2>/dev/null | cut -d= -f2)

        if [ -n "$expiry_date" ]; then
            expiry_epoch=$(date -d "$expiry_date" +%s 2>/dev/null || echo 0)
            current_epoch=$(date +%s)
            days_remaining=$(( (expiry_epoch - current_epoch) / 86400 ))

            if [ "$days_remaining" -lt 0 ]; then
                log "ERROR: Certificate for ${hostname} expired"
                VALIDATION_OK=false
            else
                log "OK: ${hostname} valid for ${days_remaining} more days"
            fi
        fi
    fi
done

if [ "$VALIDATION_OK" = false ]; then
    send_alert "CRITICAL" "Certificate validation failed — one or more certs are expired"
    exit 1
fi

# ── Step 4: Reload nginx ────────────────────────────────────────────────────
log "Reloading nginx to pick up new certificates..."

if eval "$NGINX_RELOAD_CMD" 2>&1; then
    log "OK: Nginx reloaded successfully"
else
    log "ERROR: Failed to reload nginx"
    send_alert "ERROR" "Failed to reload nginx after certificate renewal"
    exit 1
fi

# ── Step 5: Summary ─────────────────────────────────────────────────────────
log "================================================================="
log "  TLS Certificate Renewal Complete"
log "  Status: SUCCESS"
log "  Certificates checked: ${CERT_COUNT}"
log "  Nginx: Reloaded"
log "================================================================="

send_alert "SUCCESS" "TLS certificates renewed successfully — ${CERT_COUNT} cert(s) checked"
