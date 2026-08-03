#!/bin/bash
# =============================================================================
# OpenBao Audit Configuration
# =============================================================================
# This script configures audit logging in OpenBao once it's running.
# It's designed to be run via `docker exec` against the running openbao container.
#
# Usage:
#   ./openbao-enable-audit.sh
#
# Prerequisites:
#   - OpenBao must be running (dev or production mode)
#   - OPENBAO_ADDR and OPENBAO_TOKEN must be set
# =============================================================================

set -euo pipefail

OPENBAO_ADDR="${OPENBAO_ADDR:-http://127.0.0.1:8200}"
OPENBAO_TOKEN="${OPENBAO_TOKEN:-}"

if [ -z "$OPENBAO_TOKEN" ]; then
  # Try to load from .env
  if [ -f "../.env" ]; then
    OPENBAO_TOKEN=$(grep '^OPENBAO_TOKEN=' ../.env | head -1 | cut -d= -f2- | sed "s/^['\"]//;s/['\"]$//")
  fi
fi

if [ -z "$OPENBAO_TOKEN" ]; then
  echo "ERROR: OPENBAO_TOKEN is not set. Set it in .env or as an environment variable."
  exit 1
fi

echo "==> Configuring OpenBao audit logging..."

# Enable file-based audit (writes to disk)
echo "[1/3] Enabling file-based audit logging..."
curl -s -X POST \
  -H "X-Vault-Token: $OPENBAO_TOKEN" \
  -H "Content-Type: application/json" \
  "${OPENBAO_ADDR}/v1/sys/audit/file" \
  -d '{
    "type": "file",
    "options": {
      "file_path": "/openbao/data/audit.log",
      "mode": 0600
    }
  }' && echo " OK" || echo " WARN: Already enabled or failed"

# Enable syslog audit for real-time log forwarding
echo "[2/3] Enabling syslog audit for log forwarding..."
curl -s -X POST \
  -H "X-Vault-Token: $OPENBAO_TOKEN" \
  -H "Content-Type: application/json" \
  "${OPENBAO_ADDR}/v1/sys/audit/syslog" \
  -d '{
    "type": "syslog",
    "options": {
      "syslog_address": "udp://127.0.0.1:514",
      "syslog_format": "json",
      "syslog_facility": "local0"
    }
  }' && echo " OK (syslog)" || echo " SKIPPED (syslog not available)"

# Enable wrapper key audit (encrypt audit log data)
echo "[3/3] Setting audit log encryption wrapper (key rotation)..."
curl -s -X POST \
  -H "X-Vault-Token: $OPENBAO_TOKEN" \
  "${OPENBAO_ADDR}/v1/sys/config/audit-response-handling" \
  -d '{"audit_response_wrapper": true}' \
  > /dev/null 2>&1 && echo " OK" || echo " WARN"

echo ""
echo "==> OpenBao audit logging configured."
echo "    File audit: /openbao/data/audit.log"
echo "    Syslog:     udp://127.0.0.1:514 (local0)"
echo ""
echo "    To view audit logs:"
echo "      docker exec iacgenie-openbao cat /openbao/data/audit.log"
echo "      journalctl -f -f -t openbao -p info"
