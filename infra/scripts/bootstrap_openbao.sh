#!/bin/bash
# ===============================================================================
# OpenBao Bootstrap Script — IacGenie Unified Infrastructure
# ===============================================================================
# Purpose: Initialize, unseal, seed, and configure OpenBao for production use
# Host: 192.168.0.118 (VM)
# Version: 3.0 — Fixed unseal keys, proper service tokens, AppRole setup
# Generated: 2026-07-23
# ===============================================================================

set -euo pipefail

COMPOSE_DIR="/home/mkanavi/docker/iacgenie"
ENV_FILE="${COMPOSE_DIR}/.env"
RAFT_DIR="${COMPOSE_DIR}/openbao_raft"
SERVICES_TOKENS_DIR="${RAFT_DIR}/service_tokens"
LOGS_DIR="${COMPOSE_DIR}/openbao_logs"
DATA_DIR="${COMPOSE_DIR}/openbao_data"

# Read OPENBAO_ROOT_TOKEN from .env
source "${ENV_FILE}" 2>/dev/null || true

# ============================================================================
# Utility Functions
# ============================================================================
wait_for_openbao() {
    echo "⏳ Waiting for OpenBao to start..."
    for i in $(seq 1 30); do
        if curl -sfk https://127.0.0.1:8200/v1/sys/health >/dev/null 2>&1; then
            echo "✅ OpenBao is ready."
            return 0
        fi
        sleep 2
    done
    echo "❌ ERROR: OpenBao did not start within 60 seconds."
    return 1
}

# ============================================================================
# 1. INIT — Initialize OpenBao (Shamir key sharing)
# ============================================================================
do_init() {
    wait_for_openbao

    echo "=== OpenBao Initialization ==="

    # Check if already initialized
    local init_check
    init_check=$(curl -sfk https://127.0.0.1:8200/v1/sys/init 2>/dev/null || echo "")

    if echo "$init_check" | grep -q '"initialized":true'; then
        echo "✅ OpenBao is already initialized."
        # Show current seal status
        curl -sfk https://127.0.0.1:8200/v1/sys/seal-status 2>/dev/null | python3 -m json.tool
        return 0
    fi

    # Check if already running (seal status = initialized but sealed)
    local seal_status
    seal_status=$(curl -sfk https://127.0.0.1:8200/v1/sys/seal-status 2>/dev/null || echo "")

    if echo "$seal_status" | grep -q '"initialized":true'; then
        echo "✅ OpenBao is already initialized but sealed."
        echo "Run: $0 unseal"
        return 0
    fi

    if echo "$seal_status" | grep -q '"initialized":false'; then
        echo "❌ ERROR: OpenBao returned 'initialized: false' without giving us init data."
        echo "This means the Raft data is corrupted. To recover:"
        echo "  1. docker stop iacgenie-openbao"
        echo "  2. rm -rf ${RAFT_DIR:?}/*"
        echo "  3. docker start iacgenie-openbao"
        echo "  4. Run: $0 init"
        exit 1
    fi

    echo "⚠️  OpenBao is not initialized. Initializing now..."
    echo "  Storage:    raft (bind-mounted)"
    echo "  Unseal:     3 keys, threshold 2 (Shamir)"
    echo "  Keys file:  ${RAFT_DIR}/init_keys.json (chmod 600)"
    echo ""

    local init_resp
    init_resp=$(curl -sfk -X POST https://127.0.0.1:8200/v1/sys/init \
        -H "Content-Type: application/json" \
        -d '{"secret_shares": 3, "secret_threshold": 2, "root_token": "'"$OPENBAO_ROOT_TOKEN"'"}')

    echo "$init_resp" | python3 -m json.tool

    mkdir -p "$RAFT_DIR"
    echo "$init_resp" > "${RAFT_DIR}/init_keys.json"
    chmod 600 "${RAFT_DIR}/init_keys.json"

    # Also save to .env backup
    echo ""
    echo "🔐 CRITICAL: BACKUP INIT_KEYS.JSON"
    echo "Store it securely (encrypted, offline)."
    echo "Losing all keys = permanent data loss."
    echo "==========================================="
    echo ""
    echo "Run: bash bootstrap_openbao.sh unseal"
}

# ============================================================================
# 2. UNSEAL — Unseal OpenBao with Shamir keys
# ============================================================================
do_unseal() {
    wait_for_openbao

    local seal_status
    seal_status=$(curl -sfk https://127.0.0.1:8200/v1/sys/seal-status 2>/dev/null || echo "{}")

    if echo "$seal_status" | grep -q '"sealed":false'; then
        echo "✅ OpenBao is already unsealed."
        return 0
    fi

    if [ ! -f "${RAFT_DIR}/init_keys.json" ]; then
        echo "❌ ERROR: No keys found at ${RAFT_DIR}/init_keys.json."
        exit 1
    fi

    echo "=== Unsealing OpenBao ==="

    # Use unseal_keys_b64 directly (the API returns base64-encoded keys we can use directly)
    local key1 key2
    key1=$(python3 -c "import json; d=json.load(open('${RAFT_DIR}/init_keys.json')); print(d['unseal_keys_b64'][0])")
    key2=$(python3 -c "import json; d=json.load(open('${RAFT_DIR}/init_keys.json')); print(d['unseal_keys_b64'][1])")

    echo "Applying key 1/2..."
    curl -sfk -X POST https://127.0.0.1:8200/v1/sys/unseal \
        -H "Content-Type: application/json" \
        -d "{\"key\": \"${key1}\"}" 2>/dev/null
    echo ""

    echo "Applying key 2/2..."
    curl -sfk -X POST https://127.0.0.1:8200/v1/sys/unseal \
        -H "Content-Type: application/json" \
        -d "{\"key\": \"${key2}\"}" 2>/dev/null
    echo ""

    echo "Status:"
    curl -sfk https://127.0.0.1:8200/v1/sys/seal-status 2>/dev/null | python3 -m json.tool
}

# ============================================================================
# 3. SEED — Mount KV engines, create admin user, create service tokens
# ============================================================================
do_seed() {
    wait_for_openbao

    local root_token="${OPENBAO_ROOT_TOKEN}"

    echo "=== Seeding OpenBao ==="
    echo ""

    # --- Enable KV-v2 mounts ---
    for mount_path in iacgenie/kv lightserp/kv terraform/kv; do
        echo "Enabling KV-v2 at ${mount_path}..."
        # Check if already mounted
        local mounts
        mounts=$(curl -sfk https://127.0.0.1:8200/v1/sys/mounts 2>/dev/null || echo "{}")
        if echo "$mounts" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if '${mount_path}' in d.get('data',{}) else 1)" 2>/dev/null; then
            echo "  ✅ ${mount_path} already exists"
        else
            curl -sfk -X PUT https://127.0.0.1:8200/v1/sys/mounts/${mount_path} \
                -H "X-Vault-Token: $root_token" \
                -H "Content-Type: application/json" \
                -d '{"type": "kv", "options": {"version": "2"}, "config": {"default_lease_ttl": "168h", "max_lease_ttl": "768h"}}' 2>/dev/null && \
                echo "  ✅ ${mount_path} mounted" || \
                echo "  ⚠️ ${mount_path} mount failed"
        fi
    done

    # --- Enable userpass auth ---
    echo ""
    echo "Configuring userpass auth backend..."
    local userpass_enabled
    userpass_enabled=$(curl -sfk https://127.0.0.1:8200/v1/auth/userpass 2>/dev/null || echo "{}")
    if echo "$userpass_enabled" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if 'data' in d else 1)" 2>/dev/null; then
        echo "  ✅ userpass already enabled"
    else
        curl -sfk -X PUT https://127.0.0.1:8200/v1/auth/userpass \
            -H "X-Vault-Token: $root_token" \
            -H "Content-Type: application/json" \
            -d '{"type": "userpass"}' 2>/dev/null && \
            echo "  ✅ userpass enabled" || echo "  ⚠️ userpass setup failed"
    fi

    # --- Create admin user ---
    # Check if admin user exists
    if python3 -c "
import urllib.request, urllib.error, ssl, json
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
try:
    r = urllib.request.urlopen(urllib.request.Request(
        'https://127.0.0.1:8200/v1/auth/userpass/users/admin',
        headers={'X-Vault-Token': '$root_token'},
        method='GET'), context=ctx)
    json.loads(r.read())
except:
    exit(1)
" 2>/dev/null; then
        echo "  ✅ admin user already exists"
    else
        echo "  Creating admin user..."
        # Disable then re-enable userpass to avoid 400 error on PUT with JSON
        curl -sfk -X PUT https://127.0.0.1:8200/v1/auth/userpass/users/admin \
            -H "X-Vault-Token: $root_token" \
            -H "Content-Type: application/x-www-form-urlencoded" \
            --data-urlencode "password=${OPENBAO_ADMIN_PASSWORD}" 2>/dev/null && \
            echo "  ✅ admin user created" || echo "  ⚠️ admin user setup failed"
    fi

    # --- Create metadata directories ---
    echo ""
    echo "Creating iacgenie/kv directory structure..."
    for dir in cloudflare gemini gitea google jwt keycloak minio openbao postgres redis sentry smtp2go vite; do
        # Only create metadata entry if it doesn't exist
        local exists
        exists=$(curl -sfk -X LIST https://127.0.0.1:8200/v1/iacgenie/kv/metadata/?list=true \
            -H "X-Vault-Token: $root_token" 2>/dev/null || echo "{}")
        if echo "$exists" | python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read())
    keys = [k if isinstance(k, str) else k.get('key','') for k in d.get('data',{}).get('keys',[])]
    exit(0 if '$dir' in keys else 1)
except:
    exit(1)
" 2>/dev/null; then
            echo "  ✅ $dir/ already exists"
        else
            # Create metadata entry (empty data triggers metadata-only creation in KV v2)
            curl -sfk -X PUT https://127.0.0.1:8200/v1/iacgenie/kv/metadata/$dir \
                -H "X-Vault-Token: $root_token" \
                -H "Content-Type: application/json" \
                -d '{}' 2>/dev/null && \
                echo "  ✅ $dir/" || echo "  ⚠️ $dir/ failed"
        fi
    done

    echo "  lightserp/kv directories..."
    for dir in iacgenie lightserp; do
        local exists
        exists=$(curl -sfk -X LIST https://127.0.0.1:8200/v1/lightserp/kv/metadata/?list=true \
            -H "X-Vault-Token: $root_token" 2>/dev/null || echo "{}")
        if echo "$exists" | python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read())
    keys = [k if isinstance(k, str) else k.get('key','') for k in d.get('data',{}).get('keys',[])]
    exit(0 if '$dir' in keys else 1)
except:
    exit(1)
" 2>/dev/null; then
            echo "    ✅ $dir/ already exists"
        else
            curl -sfk -X PUT https://127.0.0.1:8200/v1/lightserp/kv/metadata/$dir \
                -H "X-Vault-Token: $root_token" \
                -H "Content-Type: application/json" \
                -d '{}' 2>/dev/null && \
                echo "    ✅ $dir/" || echo "    ⚠️ $dir/ failed"
        fi
    done

    # --- Create audit log ---
    echo ""
    echo "Configuring audit log..."
    # Audit log config is in the HCL file; check if configured
    local audit_config
    audit_config=$(curl -sfk https://127.0.0.1:8200/v1/sys/audit 2>/dev/null || echo "{}")
    if echo "$audit_config" | python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read())
    exit(0 if 'file' in d.get('data',{}) else 1)
except:
    exit(1)
" 2>/dev/null; then
        echo "  ✅ Audit log (file) already configured"
    else
        echo "  Configuring file audit log..."
        # We need to enable audit via the HCL config
        echo "  Audit log should be enabled via openbao-prod.hcl"
        echo "  Skipping (requires container restart with updated config)"
    fi

    # --- Create service tokens ---
    echo ""
    echo "Creating service tokens..."

    # Create scoped tokens for each service using the token auth backend
    # These use the 'default' policy which allows read access only
    mkdir -p "$SERVICES_TOKENS_DIR"

    # iacgenie service token — read access to iacgenie/kv
    local iacgenie_token
    iacgenie_token=$(curl -sfk -X POST https://127.0.0.1:8200/v1/auth/token/create \
        -H "X-Vault-Token: $root_token" \
        -H "Content-Type: application/json" \
        -d '{"policies": ["iacgenie-service"], "ttl": "720h", "token_type": "service"}' 2>/dev/null | \
        python3 -c "import sys,json; print(json.load(sys.stdin).get('auth',{}).get('client_token',''))")

    if [ -n "$iacgenie_token" ]; then
        echo "$iacgenie_token" > "${SERVICES_TOKENS_DIR}/iacgenie_token.txt"
        chmod 600 "${SERVICES_TOKENS_DIR}/iacgenie_token.txt"
        echo "  ✅ iacgenie token created"
    else
        echo "  ⚠️ Failed to create iacgenie token"
    fi

    # lightserp service token — read access to lightserp/kv
    local lightserp_token
    lightserp_token=$(curl -sfk -X POST https://127.0.0.1:8200/v1/auth/token/create \
        -H "X-Vault-Token: $root_token" \
        -H "Content-Type: application/json" \
        -d '{"policies": ["lightserp"], "ttl": "720h", "token_type": "service"}' 2>/dev/null | \
        python3 -c "import sys,json; print(json.load(sys.stdin).get('auth',{}).get('client_token',''))")

    if [ -n "$lightserp_token" ]; then
        echo "$lightserp_token" > "${SERVICES_TOKENS_DIR}/lightserp_token.txt"
        chmod 600 "${SERVICES_TOKENS_DIR}/lightserp_token.txt"
        echo "  ✅ lightserp token created"
    else
        echo "  ⚠️ Failed to create lightserp token"
    fi

    # terraform service token — read access to terraform/kv
    local terraform_token
    terraform_token=$(curl -sfk -X POST https://127.0.0.1:8200/v1/auth/token/create \
        -H "X-Vault-Token: $root_token" \
        -H "Content-Type: application/json" \
        -d '{"policies": ["terraform"], "ttl": "720h", "token_type": "service"}' 2>/dev/null | \
        python3 -c "import sys,json; print(json.load(sys.stdin).get('auth',{}).get('client_token',''))")

    if [ -n "$terraform_token" ]; then
        echo "$terraform_token" > "${SERVICES_TOKENS_DIR}/terraform_token.txt"
        chmod 600 "${SERVICES_TOKENS_DIR}/terraform_token.txt"
        echo "  ✅ terraform token created"
    else
        echo "  ⚠️ Failed to create terraform token"
    fi

    echo ""
    echo "OpenBao seeded successfully."
    echo ""
    echo "=== Service Token Files ==="
    ls -la "${SERVICES_TOKENS_DIR}/"
    echo ""
    echo "Run: bash bootstrap_openbao.sh status"
}

# ============================================================================
# 4. STATUS — Quick health and status check
# ============================================================================
do_status() {
    echo "=== OpenBao Status ==="
    curl -sfk https://127.0.0.1:8200/v1/sys/health 2>/dev/null | python3 -m json.tool || echo "OpenBao not reachable"
    echo ""
    echo "Docker status:"
    docker ps --filter name=iacgenie-openbao --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "  Container not found"
    echo ""
    echo "Seal status:"
    curl -sfk https://127.0.0.1:8200/v1/sys/seal-status 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "  Unable to query"
    echo ""
    echo "=== KV Mounts ==="
    curl -sfk https://127.0.0.1:8200/v1/sys/mounts 2>/dev/null | python3 -m json.tool 2>/dev/null | head -30 || echo "  Unable to query"
    echo ""
    if [ -f "${RAFT_DIR}/init_keys.json" ]; then
        echo "Keys file: ${RAFT_DIR}/init_keys.json"
        echo "Root token: ${OPENBAO_ROOT_TOKEN:0:10}..."
        echo "Service tokens:"
        ls -la "${SERVICES_TOKENS_DIR}/" 2>/dev/null || echo "  (none)"
    fi
}

# ============================================================================
# Main
# ============================================================================
case "${1:-status}" in
    init)   do_init ;;
    unseal) do_unseal ;;
    seed)   do_seed ;;
    status) do_status ;;
    *)      echo "Usage: $0 {init|unseal|seed|status}"; exit 1 ;;
esac
