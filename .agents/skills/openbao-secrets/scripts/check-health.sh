#!/usr/bin/env bash
# Check OpenBao health, seal status, and active token count
set -euo pipefail
BAO_ADDR="${OPENBAO_ADDR:-http://127.0.0.1:8200}"
echo "==> Checking OpenBao at $BAO_ADDR"
curl -sf "$BAO_ADDR/v1/sys/health" | python3 -m json.tool
echo
echo "==> Seal status:"
curl -sf "$BAO_ADDR/v1/sys/seal-status" | python3 -m json.tool 2>/dev/null || echo "  (requires authentication)"
