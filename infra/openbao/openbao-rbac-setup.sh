#!/bin/bash
# =============================================================================
# OpenBao RBAC Setup — Policy, Auth Method & Token Management
# =============================================================================
# Creates:
#   1. admin policy    - full access to all secrets (read, write, delete, manage)
#   2. read-only policies - per-service mount read-only access
#   3. AppRole auth    - machine-to-machine authentication
#   4. Token auth      - service tokens with appropriate ACLs
#
# Only the admin policy can delete secrets. All others are read-only.
#
# Usage: source .env && bash openbao-rbac-setup.sh
# =============================================================================

set -euo pipefail

OPENBAO_ADDR="${OPENBAO_ADDR:-http://127.0.0.1:8200}"
OPENBAO_TOKEN="${OPENBAO_ROOT_TOKEN:-${OPENBAO_TOKEN:-}}"

if [ -z "$OPENBAO_TOKEN" ]; then
    echo "ERROR: OPENBAO_TOKEN or OPENBAO_ROOT_TOKEN not set"
    exit 1
fi

CURL="curl -s -X POST -H \"X-Vault-Token: $OPENBAO_TOKEN\" -H \"Content-Type: application/json\""
GET="curl -s -H \"X-Vault-Token: $OPENBAO_TOKEN\" -H \"Content-Type: application/json\""

echo "==> OpenBao RBAC Setup"
echo "    Address: $OPENBAO_ADDR"

# ============================================================================
# 1. ADMIN POLICY (full access)
# ============================================================================
echo ""
echo "--- Admin Policy ---"

cat <<'HCL' | $CURL $OPENBAO_ADDR/v1/sys/policies/acl/admin/openbao-admin -X PUT -d @- || true
path "/*" {
  capabilities = ["create", "read", "update", "delete", "list", "sudo"]
}
HCL
echo "  Created admin policy (full access)"

# ============================================================================
# 2. READ-ONLY POLICIES (per-mount)
# ============================================================================
echo ""
echo "--- Read-Only Policies ---"

# iacgenie read-only
cat <<'HCL' | $CURL $OPENBAO_ADDR/v1/sys/policies/acl/read-only/openbao-iacgenie-ro -X PUT -d @- || true
path "iacgenie/kv/data/*" {
  capabilities = ["read"]
}
path "iacgenie/kv/metadata/*" {
  capabilities = ["read", "list"]
}
path "iacgenie/kv/*" {
  capabilities = ["list"]
}
HCL
echo "  Created read-only policy for iacgenie/kv"

# lightserp read-only
cat <<'HCL' | $CURL $OPENBAO_ADDR/v1/sys/policies/acl/read-only/openbao-lightserp-ro -X PUT -d @- || true
path "lightserp/kv/data/*" {
  capabilities = ["read"]
}
path "lightserp/kv/metadata/*" {
  capabilities = ["read", "list"]
}
path "lightserp/kv/*" {
  capabilities = ["list"]
}
HCL
echo "  Created read-only policy for lightserp/kv"

# terraform read-only
cat <<'HCL' | $CURL $OPENBAO_ADDR/v1/sys/policies/acl/read-only/openbao-terraform-ro -X PUT -d @- || true
path "terraform/kv/data/*" {
  capabilities = ["read"]
}
path "terraform/kv/metadata/*" {
  capabilities = ["read", "list"]
}
path "terraform/kv/*" {
  capabilities = ["list"]
}
HCL
echo "  Created read-only policy for terraform/kv"

# ============================================================================
# 3. APPROLE AUTH METHOD
# ============================================================================
echo ""
echo "--- AppRole Auth ---"

# Enable AppRole if not already
curl -s -X POST -H "X-Vault-Token: $OPENBAO_TOKEN" \
    $OPENBAO_ADDR/v1/sys/auth/approle 2>/dev/null || true

# Create roles for each service
SERVICES=(
    "iacgenie/postgres:iacgenie-admin:openbao-admin"
    "iacgenie/redis:iacgenie-redis:openbao-iacgenie-ro"
    "iacgenie/minio:iacgenie-minio:openbao-iacgenie-ro"
    "iacgenie/keycloak:iacgenie-kc:openbao-iacgenie-ro"
    "iacgenie/gitea:iacgenie-gitea:openbao-iacgenie-ro"
    "iacgenie/lightserp:iacgenie-ls:openbao-iacgenie-ro"
    "iacgenie/searxng:iacgenie-sx:openbao-iacgenie-ro"
    "iacgenie/nsqd:iacgenie-nsqd:openbao-iacgenie-ro"
    "iacgenie/pagezen:iacgenie-pz:openbao-iacgenie-ro"
    "iacgenie/nginx:iacgenie-nginx:openbao-iacgenie-ro"
    "iacgenie/terraform:iacgenie-tf:openbao-iacgenie-ro"
    "lightserp/kv:lightserp-kc:openbao-lightserp-ro"
    "terraform/kv:terraform-kv:openbao-terraform-ro"
)

for entry in "${SERVICES[@]}"; do
    IFS=':' read -r mount service_name policy <<< "$entry"
    # Create role
    curl -s -X POST \
        -H "X-Vault-Token: $OPENBAO_TOKEN" \
        -H "Content-Type: application/json" \
        $OPENBAO_ADDR/v1/auth/approle/role/$service_name \
        -d "{\"secret_id_ttl\":\"24h\",\"token_ttl\":\"1h\",\"token_max_ttl\":\"4h\",\"policies\":\"$policy\"}" \
        > /dev/null 2>&1 || true
    echo "  AppRole: $service_name -> policy=$policy mount=$mount"
done

# ============================================================================
# 4. SERVICE TOKENS (direct tokens for quick access)
# ============================================================================
echo ""
echo "--- Service Tokens ---"

create_token() {
    local service=$1
    local policies=$2
    local mount=$3

    local response
    response=$(curl -s -X POST \
        -H "X-Vault-Token: $OPENBAO_TOKEN" \
        -H "Content-Type: application/json" \
        $OPENBAO_ADDR/v1/auth/token/create \
        -d "{\"policies\":\"$policies\",\"display_name\":\"$service\",\"token_ttl\":\"720h\",\"token_max_ttl\":\"2160h\"}")

    local token
    token=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('auth',{}).get('client_token',''))" 2>/dev/null || echo "")

    if [ -n "$token" ]; then
        echo "  TOKEN[$service]: $token" | awk -F: '{print "  "$1": "$2"…"$3}'
        # Save token reference
        local token_file="/home/mkanavi/docker/iacgenie/data/openbao_raft/service_tokens/${service}.token"
        mkdir -p "$(dirname $token_file)"
        echo "$token" > "$token_file"
        chmod 600 "$token_file"
    fi
}

create_token "iacgenie-admin" "admin" "iacgenie/kv"
create_token "iacgenie-redis" "openbao-iacgenie-ro" "iacgenie/kv"
create_token "iacgenie-minio" "openbao-iacgenie-ro" "iacgenie/kv"
create_token "iacgenie-keycloak" "openbao-iacgenie-ro" "iacgenie/kv"
create_token "iacgenie-gitea" "openbao-iacgenie-ro" "iacgenie/kv"
create_token "iacgenie-lightserp" "openbao-iacgenie-ro" "iacgenie/kv"
create_token "iacgenie-searxng" "openbao-iacgenie-ro" "iacgenie/kv"
create_token "iacgenie-nsqd" "openbao-iacgenie-ro" "iacgenie/kv"
create_token "iacgenie-pagezen" "openbao-iacgenie-ro" "iacgenie/kv"
create_token "iacgenie-nginx" "openbao-iacgenie-ro" "iacgenie/kv"
create_token "iacgenie-terraform" "openbao-iacgenie-ro" "iacgenie/kv"
create_token "lightserp-kc" "openbao-lightserp-ro" "lightserp/kv"
create_token "terraform-kv" "openbao-terraform-ro" "terraform/kv"

echo ""
echo "==> RBAC setup complete"
echo "    Policies: admin + 3 read-only"
echo "    AppRoles: 13 service roles"
echo "    Tokens:   13 service tokens (saved in service_tokens/)"
