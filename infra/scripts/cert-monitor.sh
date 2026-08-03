#!/bin/bash
# =============================================================================
# cert-monitor.sh — TLS Certificate Expiry Monitor
# Phase 10.20: TLS Certificate Automation
#
# Checks expiry of all certificates in /etc/letsencrypt/live/,
# alerts if <30 days remaining, logs to syslog.
# =============================================================================

set -euo pipefail

CERT_DIR="/etc/letsencrypt/live"
ALERT_THRESHOLD=30  # days
ALERT_EMAIL="${ALERT_EMAIL:-admin@iacgenie.com}"
ALERT_WEBHOOK="${ALERT_WEBHOOK:-}"
SYSLOG_TAG="cert-monitor"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    logger -t "$SYSLOG_TAG" "$*" 2>/dev/null || echo "$(date '+%Y-%m-%d %H:%M:%S') $*"
}

send_alert() {
    local severity="$1"
    local msg="$2"

    # Email alert
    if command -v mail &>/dev/null && [ -n "$ALERT_EMAIL" ]; then
        echo "$msg" | mail -s "[cert-monitor] ${severity}: TLS Certificate Expiry Alert" "$ALERT_EMAIL" 2>/dev/null || true
    fi

    # Webhook alert
    if [ -n "$ALERT_WEBHOOK" ]; then
        curl -sf -X POST "$ALERT_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{\"text\": \"[cert-monitor] ${severity}: ${msg}\"}" \
            2>/dev/null || true
    fi
}

log "================================================================="
log "TLS Certificate Expiry Check — $(date '+%Y-%m-%d %H:%M:%S')"
log "================================================================="

if [ ! -d "$CERT_DIR" ]; then
    log "ERROR: Certificate directory ${CERT_DIR} not found"
    exit 1
fi

ALERTS=0
CHECKED=0

for cert_dir in "$CERT_DIR"/*/; do
    [ -d "$cert_dir" ] || continue

    hostname=$(basename "$cert_dir")
    cert_file="${cert_dir}fullchain.pem"
    CHECKED=$((CHECKED + 1))

    if [ ! -f "$cert_file" ]; then
        log "WARN: Certificate file not found: ${cert_file}"
        continue
    fi

    # Get expiry date
    expiry_date=$(openssl x509 -enddate -noout -in "$cert_file" 2>/dev/null | cut -d= -f2)
    if [ -z "$expiry_date" ]; then
        log "ERROR: Could not parse expiry date for ${hostname}"
        continue
    fi

    expiry_epoch=$(date -d "$expiry_date" +%s 2>/dev/null || echo 0)
    current_epoch=$(date +%s)
    days_remaining=$(( (expiry_epoch - current_epoch) / 86400 ))

    if [ "$days_remaining" -lt 0 ]; then
        log "CRITICAL: Certificate for ${hostname} has EXPIRED (${days_remaining} days ago)"
        send_alert "CRITICAL" "Certificate expired: ${hostname} (${days_remaining} days overdue)"
        ALERTS=$((ALERTS + 1))
    elif [ "$days_remaining" -lt "$ALERT_THRESHOLD" ]; then
        log "WARN: Certificate for ${hostname} expires in ${days_remaining} days (threshold: ${ALERT_THRESHOLD} days)"
        send_alert "WARNING" "Certificate expiring soon: ${hostname} (${days_remaining} days remaining)"
        ALERTS=$((ALERTS + 1))
    else
        log "OK: ${hostname} valid for ${days_remaining} more days"
    fi
done

log "================================================================="
log "Certificate Check Complete"
log "  Checked: ${CHECKED} certificates"
log "  Alerts:  ${ALERTS}"
log "  Threshold: ${ALERT_THRESHOLD} days"
log "================================================================="

if [ "$ALERTS" -gt 0 ]; then
    log "ALERTS: ${ALERTS} certificate(s) need attention"
    exit 1
fi

log "All certificates valid (>${ALERT_THRESHOLD} days remaining)"
