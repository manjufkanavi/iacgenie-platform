#!/usr/bin/env bash
# Read a secret from OpenBao KV-v2
# Usage: ./read-secret.sh <mount>/<path>  e.g. iacgenie/kv/postgres
set -euo pipefail
if [ $# -lt 1 ]; then echo "Usage: $0 <mount/path>"; exit 1; fi
BAO_ADDR="${OPENBAO_ADDR:-http://127.0.0.1:8200}"
BAO_TOKEN="${OPENBAO_TOKEN:?OPENBAO_TOKEN required}"
SECRET_PATH="$1"
# Split mount from path for KV-v2 data endpoint
MOUNT="${SECRET_PATH%%/*}/${SECRET_PATH#*/}"
echo "==> Reading $SECRET_PATH from $BAO_ADDR"
curl -sf -H "X-Vault-Token: $BAO_TOKEN" "$BAO_ADDR/v1/$SECRET_PATH" | python3 -m json.tool
