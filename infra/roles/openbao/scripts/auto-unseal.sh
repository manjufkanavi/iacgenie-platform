#!/bin/bash
# Auto-unseal OpenBao on boot
# Reads unseal keys from init_keys.json and unseals the OpenBao container
set -euo pipefail

KEYS_FILE="/home/mkanavi/docker/iacgenie/init_keys.json"
CONTAINER="iacgenie_openbao"
BAO_ADDR="http://127.0.0.1:8200"
LOG_FILE="/home/mkanavi/docker/iacgenie/openbao_logs/auto-unseal.log"
MAX_RETRIES=5
RETRY_DELAY=10

log() {
    echo "$(date -u +'%Y-%m-%dT%H:%M:%SZ') - $1" | tee -a "$LOG_FILE"
}

wait_for_openbao() {
    log "Waiting for OpenBao container to be ready..."
    for i in $(seq 1 30); do
        if docker ps | grep -q "$CONTAINER"; then
            sleep 5
            log "OpenBao container is running."
            return 0
        fi
        sleep 2
    done
    log "ERROR: OpenBao container not ready after 60 seconds."
    return 1
}

check_unsealed() {
    local status
    status=$(curl -sf http://127.0.0.1:8200/v1/sys/health 2>/dev/null || echo "")
    if echo "$status" | grep -q '"sealed":false'; then
        log "OpenBao is already unsealed. Nothing to do."
        return 0
    fi
    return 1
}

unseal_openbao() {
    local keys
    keys=$(python3 -c "import json; d=json.load(open('$KEYS_FILE')); print('\n'.join(d.get('unseal_keys_b64', d.get('keys_b64', []))))")
    if [ -z "$keys" ]; then
        log "ERROR: No unseal keys found in $KEYS_FILE"
        return 1
    fi
    local key_count=0
    local unsealed=false
    while IFS= read -r key; do
        [ -z "$key" ] && continue
        key_count=$((key_count + 1))
        log "Submitting unseal key $key_count..."
        local result
        result=$(docker exec -e BAO_ADDR="$BAO_ADDR" "$CONTAINER" bao operator unseal "$key" 2>&1)
        echo "$result" >> "$LOG_FILE"
        if echo "$result" | grep -q 'Sealed.*false'; then
            log "SUCCESS: OpenBao unsealed with key $key_count"
            unsealed=true
            break
        elif echo "$result" | grep -q 'Sealed.*true'; then
            log "Progress: $(echo "$result" | grep 'Unseal Progress' || echo 'unknown')"
        else
            log "WARNING: Key $key_count failed: $(echo "$result" | tail -3)"
        fi
    done <<< "$keys"
    if [ "$unsealed" = true ]; then
        return 0
    else
        log "ERROR: Failed to unseal OpenBao after trying all $key_count keys."
        return 1
    fi
}

main() {
    mkdir -p "$(dirname "$LOG_FILE")"
    log "=== OpenBao Auto-Unseal Started ==="
    wait_for_openbao || exit 1
    if check_unsealed; then
        exit 0
    fi
    local attempt=0
    while [ $attempt -lt $MAX_RETRIES ]; do
        attempt=$((attempt + 1))
        log "Unseal attempt $attempt/$MAX_RETRIES..."
        if unseal_openbao; then
            exit 0
        fi
        log "Retrying in ${RETRY_DELAY}s..."
        sleep "$RETRY_DELAY"
    done
    log "ERROR: All $MAX_RETRIES unseal attempts failed."
    exit 1
}

main "$@"
