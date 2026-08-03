#!/bin/bash
# setup-keycloak.sh — Configure Keycloak for LightSerp on the VM
# Run: ssh newvm 'bash -s' < setup-keycloak.sh
#
# This script:
# 1. Creates keycloak database in PostgreSQL
# 2. Starts Keycloak with proper env vars
# 3. Creates the lightserp realm and clients

set -e

echo "=========================================="
echo "  LightSerp Keycloak Setup"
echo "=========================================="

# ---- 1. Create Keycloak database in PostgreSQL ----
echo ""
echo "[1/4] Creating Keycloak database in PostgreSQL..."
docker exec iacgenie-postgres-1 psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'keycloak'" 2>/dev/null | grep -q 1 && echo "  keycloak database already exists" || {
    docker exec iacgenie-postgres-1 psql -U postgres -c "CREATE DATABASE keycloak;"
    echo "  ✓ Created database keycloak"
}

# ---- 2. Generate secrets ----
echo ""
echo "[2/4] Generating secrets..."
export KEYCLOAK_ADMIN_PASSWORD=$(openssl rand -base64 24)
export KC_DB_PASSWORD=$(openssl rand -base64 24)

# Set Keycloak DB user password
docker exec iacgenie-postgres-1 psql -U postgres -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'keycloak') THEN CREATE USER keycloak WITH PASSWORD '$KC_DB_PASSWORD'; END IF; END \$\$;"
docker exec iacgenie-postgres-1 psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE keycloak TO keycloak;"

echo "  ✓ KEYCLOAK_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD:0:8}..."
echo "  ✓ KC_DB_PASSWORD: ${KC_DB_PASSWORD:0:8}..."
echo ""
echo "  ⚠️  Save these passwords — they are not recoverable!"
echo "     KEYCLOAK_ADMIN_PASSWORD=$KEYCLOAK_ADMIN_PASSWORD"
echo "     KC_DB_PASSWORD=$KC_DB_PASSWORD"

# ---- 3. Stop existing container if any ----
echo ""
echo "[3/4] Stopping existing Keycloak container..."
docker rm -f iacgenie-keycloak-1 2>/dev/null || true
echo "  ✓ Cleaned up old container"

# ---- 4. Start Keycloak ----
echo ""
echo "[4/4] Starting Keycloak..."
docker run -d \
  --name iacgenie-keycloak-1 \
  --restart unless-stopped \
  -p 8085:8080 \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD="$KEYCLOAK_ADMIN_PASSWORD" \
  -e KC_DB=postgres \
  -e KC_DB_URL=jdbc:postgresql://iacgenie-postgres-1:5432/keycloak \
  -e KC_DB_USERNAME=keycloak \
  -e KC_DB_PASSWORD="$KC_DB_PASSWORD" \
  -e KC_HOSTNAME=keycloak.iacgenie.com \
  -e KC_HTTP_RELATIVE_PATH=/ \
  -e KC_PROXY=edge \
  -e KC_DB_POOL_INITIAL_SIZE=2 \
  -e KC_DB_POOL_MAX_SIZE=10 \
  quay.io/keycloak/keycloak:26.0 \
  start --http-port=8080 --http-enabled=true

echo ""
echo "=========================================="
echo "  Keycloak is starting up (takes 30-60s)"
echo "=========================================="
echo ""
echo "  Admin UI:     http://127.0.0.1:8085/admin/"
echo "  Admin creds:  admin / $KEYCLOAK_ADMIN_PASSWORD"
echo ""
echo "  After it's ready, run:"
echo "    ssh newvm 'bash -s' < setup-keycloak-clients.sh"
echo ""
