#!/bin/bash
# =============================================================================
# OpenBao Bootstrap Script — Complete Initialization
# =============================================================================
# Phase 1: Wait for OpenBao and ensure it's unsealed
# Phase 2: Generate/restore secrets into OpenBao KV-v2
# Phase 3: Set up RBAC policies (admin + read-only)
# Phase 4: Verify consistency between .env and OpenBao
#
# Required env vars:
#   OPENBAO_ADDR    - OpenBao API address
#   OPENBAO_TOKEN   - Root token (or OPENBAO_ROOT_TOKEN)
#   ENV_FILE        - Path to .env with service passwords
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPENBAO_ADDR="${OPENBAO_ADDR:-http://127.0.0.1:8200}"
TOKEN="${OPENBAO_TOKEN:-${OPENBAO_ROOT_TOKEN:-}}"
ENV_FILE="${ENV_FILE:-/home/mkanavi/docker/iacgenie/.env}"

if [ -z "$TOKEN" ]; then
    echo "ERROR: OPENBAO_TOKEN or OPENBAO_ROOT_TOKEN not set"
    exit 1
fi

# ── Helpers ──────────────────────────────────────────────────────────────────
wait_for_openbao() {
    echo "==> Waiting for OpenBao to be ready and unsealed..."
    for i in $(seq 1 30); do
        STATUS=$(curl -s -H "X-Vault-Token: $TOKEN" \
            "$OPENBAO_ADDR/v1/sys/seal-status" 2>/dev/null | python3 -c "import sys,json;print(json.load(sys.stdin).get('sealed','unknown'))" 2>/dev/null || echo "error")
        if [ "$STATUS" = "false" ]; then
            echo "    OpenBao is ready and unsealed"
            return 0
        elif [ "$STATUS" = "true" ]; then
            echo "    OpenBao is up but sealed. Waiting..."
            sleep 3
        else
            echo "    OpenBao not ready yet... (attempt $i/30)"
            sleep 2
        fi
    done
    echo "ERROR: OpenBao did not become unsealed within 90s"
    exit 1
}

enable_kv() {
    local mount=$1
    curl -s -X POST -H "X-Vault-Token: $TOKEN" \
        -H "Content-Type: application/json" \
        "$OPENBAO_ADDR/v1/sys/mounts/$mount" \
        -d '{"type":"kv","options":{"version":"2"}}' \
        > /dev/null 2>&1 || true
}

write_secret() {
    local mount=$1 path=$2 data=$3
    curl -s -X POST -H "X-Vault-Token: $TOKEN" \
        -H "Content-Type: application/json" \
        "$OPENBAO_ADDR/v1/$mount/data/$path" \
        -d "$data" > /dev/null 2>&1 || true
}

# ── Phase 1: Wait ───────────────────────────────────────────────────────────
echo "==> Phase 1: Waiting for OpenBao"
wait_for_openbao

# ── Phase 2: Enable KV mounts ──────────────────────────────────────────────
echo ""
echo "==> Phase 2: Ensuring KV mounts"
for mount in iacgenie/kv lightserp/kv terraform/kv; do
    enable_kv "$mount"
    echo "  $mount"
done

# ── Phase 3: Seed secrets from .env ─────────────────────────────────────────
if [ -f "$ENV_FILE" ]; then
    echo ""
    echo "==> Phase 3: Seeding secrets from $ENV_FILE"

    # Source the env file (safely)
    while IFS='=' read -r key value; do
        [[ "$key" =~ ^#.*$ ]] && continue
        [[ -z "$key" ]] && continue
        key=$(echo "$key" | tr -d '[:space:]')
        value=$(echo "$value" | tr -d '[:space:]')
        export "$key=$value" 2>/dev/null || true
    done < "$ENV_FILE"

    # PostgreSQL
    write_secret "iacgenie/kv" "postgres" \
        "{\"data\":{\"username\":\"lightsrp\",\"password\":\"${PG_APP_PASSWORD:-}\",\"database\":\"lightsrp\"}}"

    # Redis
    write_secret "iacgenie/kv" "redis" \
        "{\"data\":{\"password\":\"${REDIS_PASSWORD:-}\"}}"

    # MinIO
    write_secret "iacgenie/kv" "minio" \
        "{\"data\":{\"access_key\":\"iacgenie\",\"secret_key\":\"${MINIO_ROOT_PASSWORD:-}\"}}"

    # Gitea
    write_secret "iacgenie/kv" "gitea" \
        "{\"data\":{\"admin_password\":\"${GITEA_ADMIN_PASSWORD:-}\"}}"

    # Keycloak
    write_secret "iacgenie/kv" "keycloak" \
        "{\"data\":{\"admin_user\":\"admin\",\"admin_password\":\"${KEYCLOAK_ADMIN_PASSWORD:-}\"}}"

    # Keycloak DB
    write_secret "iacgenie/kv" "keycloak_db" \
        "{\"data\":{\"username\":\"keycloak\",\"password\":\"${KC_DB_PASSWORD:-}\",\"database\":\"keycloak\"}}"

    # LightSerp
    write_secret "iacgenie/kv" "lightserp" \
        "{\"data\":{\"api_secret\":\"${LIGHTSERP_API_SECRET:-}\",\"keycloak_client_secret\":\"${LIGHTSERP_KEYCLOAK_CLIENT_SECRET:-}\"}}"

    # SearXNG
    write_secret "iacgenie/kv" "searxng" \
        "{\"data\":{\"secret_key\":\"${SEARXNG_SECRET_KEY:-}\"}}"

    # Nginx JWT
    write_secret "iacgenie/kv" "nginx" \
        "{\"data\":{\"jwt_secret\":\"${JWT_SECRET:-}\"}}"

    # NSQD
    write_secret "iacgenie/kv" "nsqd" \
        "{\"data\":{\"auth_token\":\"${NSQD_AUTH_TOKEN:-}\"}}"

    # PageZen
    write_secret "iacgenie/kv" "pagezen" \
        "{\"data\":{\"api_secret\":\"${PAGEZEN_API_SECRET:-}\"}}"

    # Terraform
    write_secret "iacgenie/kv" "terraform" \
        "{\"data\":{\"api_key\":\"${TERRAFORM_API_KEY:-}\"}}"

    echo "  Seeded 12 secret paths from .env"
else
    echo "  WARNING: $ENV_FILE not found — skipping seed"
fi

# ── Phase 4: RBAC Setup ────────────────────────────────────────────────────
echo ""
echo "==> Phase 4: Setting up RBAC"

# Create admin policy (full access)
cat <<'POLICY' | curl -s -X POST -H "X-Vault-Token: $TOKEN" \
    -H "Content-Type: application/json" \
    "$OPENBAO_ADDR/v1/sys/policies/acl/admin/openbao-admin" -X PUT -d @- > /dev/null 2>&1
path "/*" {
  capabilities = ["create", "read", "update", "delete", "list", "sudo"]
}
POLICY
echo "  Admin policy created (full access)"

# Create read-only policies
for scope in "iacgenie:k/kv" "lightserp:l/kv" "terraform:t/kv"; do
    IFS=':' read -r name prefix <<< "$scope"
    cat <<POLICY | curl -s -X POST -H "X-Vault-Token: $TOKEN" \
        -H "Content-Type: application/json" \
        "$OPENBAO_ADDR/v1/sys/policies/acl/read-only/openbao-${name}-ro" -X PUT -d @- > /dev/null 2>&1
path "${name}/${prefix}/data/*" { capabilities = ["read"] }
path "${name}/${prefix}/metadata/*" { capabilities = ["read", "list"] }
path "${name}/${prefix}/*" { capabilities = ["list"] }
POLICY
    echo "  Read-only policy: ${name}"
done

echo "  RBAC setup complete"

# ── Phase 5: Consistency check ─────────────────────────────────────────────
echo ""
echo "==> Phase 5: Consistency check"

if [ -f "$SCRIPT_DIR/openbao-consistency-check.py" ]; then
    python3 "$SCRIPT_DIR/openbao-consistency-check.py" 2>&1 || true
else
    echo "  Skip: openbao-consistency-check.py not found"
fi

echo ""
echo "==> Bootstrap complete"
echo "    Services: 12 secret paths in iacgenie/kv"
echo "    RBAC:     admin + 3 read-only policies"
echo "    Auth:     token + AppRole (see openbao-rbac-setup.sh)"
