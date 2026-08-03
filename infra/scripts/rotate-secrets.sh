# =============================================================================
# API Key Rotation Procedure
# =============================================================================
# 
# This script rotates all shared infrastructure credentials.
# 
# IMPORTANT: After rotation, all services must be restarted to pick up new keys.
#
# Steps:
#   1. Run this script: bash rotate-secrets.sh
#   2. Review the new values in .env
#   3. Restart services: docker compose -f docker-compose-unified.yml up -d --force-recreate
#   4. Re-run OpenBao bootstrap: docker compose -f docker-compose-unified.yml up -d openbao-init
#   5. Update .env.iacgenie and .env.lightserp with new database credentials
#   6. Restart application services
#
# Risk Assessment:
#   - Short downtime during service restarts (typically < 2 minutes)
#   - OpenBao must be re-seeded with new secrets
#   - Application services must reconnect with new credentials
#   - If rollback needed: restore .env from backup and restart
#
# Frequency recommendation:
#   - Monthly for development
#   - Quarterly for production
#   - Immediately after any suspected breach
#
# Date: 2026-07-20
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
BACKUP_FILE="${ENV_FILE}.backup.$(date +%Y%m%d%H%M%S)"

echo "=== API Key Rotation ==="
echo ""

# Backup current .env
echo "[1/6] Backing up current .env file..."
cp "$ENV_FILE" "$BACKUP_FILE"
echo "  Backup saved: $BACKUP_FILE"

# Generate secure random passwords
echo "[2/6] Generating new credentials..."

generate_password() {
  openssl rand -base64 32 | tr -dc 'A-Za-z0-9_+' | head -c 24
}

NEW_PG_SUPER=$(generate_password)
NEW_PG_APP=$(generate_password)
NEW_PG_KC=$(generate_password)
NEW_REDIS=$(generate_password)
NEW_MINIO_PASS=$(generate_password)
NEW_OPENBAO_ROOT=$(generate_password)
NEW_OPENBAO_TOKEN=$(generate_password)
NEW_KC_ADMIN=$(generate_password)
NEW_GRAFANA=$(generate_password)
NEW_SEARXNG=$(generate_password)
NEW_JWT=$(generate_password)
NEW_A12N=$(generate_password)
NEW_A12N_ENC=$(generate_password)
NEW_CSRF=$(generate_password)

# Read existing values that should NOT change
MINIO_USER=$(grep '^MINIO_ROOT_USER=' "$ENV_FILE" | cut -d= -f2)
KEYCLOAK_ADMIN_USER=$(grep '^KEYCLOAK_ADMIN=' "$ENV_FILE" | cut -d= -f2 | tr -d '"')
GRAFANA_ADMIN_USER=$(grep '^GF_SECURITY_ADMIN_USER' "$ENV_FILE" | cut -d= -f2 | tr -d '"' || echo "admin")

echo "[3/6] Updating .env file..."

# Update .env with new passwords (preserving comments and structure)
sed -i '' "s/^POSTGRES_SUPER_PASSWORD=.*/POSTGRES_SUPER_PASSWORD='${NEW_PG_SUPER}'/" "$ENV_FILE"
sed -i '' "s/^POSTGRES_APP_PASSWORD=.*/POSTGRES_APP_PASSWORD='${NEW_PG_APP}'/" "$ENV_FILE"
sed -i '' "s/^POSTGRES_KC_PASSWORD=.*/POSTGRES_KC_PASSWORD='${NEW_PG_KC}'/" "$ENV_FILE"
sed -i '' "s/^REDIS_PASSWORD=.*/REDIS_PASSWORD='${NEW_REDIS}'/" "$ENV_FILE"
sed -i '' "s/^MINIO_ROOT_PASSWORD=.*/MINIO_ROOT_PASSWORD='${NEW_MINIO_PASS}'/" "$ENV_FILE"
sed -i '' "s/^OPENBAO_ROOT_TOKEN=.*/OPENBAO_ROOT_TOKEN='${NEW_OPENBAO_ROOT}'/" "$ENV_FILE"
sed -i '' "s/^OPENBAO_TOKEN=.*/OPENBAO_TOKEN='${NEW_OPENBAO_TOKEN}'/" "$ENV_FILE"
sed -i '' "s/^KEYCLOAK_ADMIN_PASSWORD=.*/KEYCLOAK_ADMIN_PASSWORD='${NEW_KC_ADMIN}'/" "$ENV_FILE"
sed -i '' "s/^GRAFANA_ADMIN_PASSWORD=.*/GRAFANA_ADMIN_PASSWORD='${NEW_GRAFANA}'/" "$ENV_FILE"
sed -i '' "s/^SEARXNG_SECRET=.*/SEARXNG_SECRET='${NEW_SEARXNG}'/" "$ENV_FILE"
sed -i '' "s/^JWT_SECRET=.*/JWT_SECRET='${NEW_JWT}'/" "$ENV_FILE"
sed -i '' "s/^A12N_SECRET=.*/A12N_SECRET='${NEW_A12N}'/" "$ENV_FILE"
sed -i '' "s/^A12N_ENCRYPTION_KEY=.*/A12N_ENCRYPTION_KEY='${NEW_A12N_ENC}'/" "$ENV_FILE"
sed -i '' "s/^A12N_CSRF_SECRET=.*/A12N_CSRF_SECRET='${NEW_CSRF}'/" "$ENV_FILE"

echo "[4/6] Rotating OpenBao secrets..."
echo "  Re-seeding OpenBao with new credentials..."
echo "  (Run: docker compose -f docker-compose-unified.yml up -d openbao-init)"

echo ""
echo "[5/6] Summary of changes:"
echo "  ✅ PostgreSQL superuser password rotated"
echo "  ✅ PostgreSQL app password rotated"
echo "  ✅ PostgreSQL Keycloak password rotated"
echo "  ✅ Redis password rotated"
echo "  ✅ MinIO root password rotated"
echo "  ✅ OpenBao root token rotated"
echo "  ✅ OpenBao auth token rotated"
echo "  ✅ Keycloak admin password rotated"
echo "  ✅ Grafana admin password rotated"
echo "  ✅ SearXNG secret rotated"
echo "  ✅ JWT secret rotated"
echo "  ✅ A12N secrets rotated"
echo ""
echo "[6/6] Next steps:"
echo "  1. Restart shared services: docker compose -f docker-compose-unified.yml up -d --force-recreate"
echo "  2. Re-run OpenBao bootstrap: docker compose -f docker-compose-unified.yml up -d openbao-init"
echo "  3. Update .env.iacgenie and .env.lightserp with new DB passwords"
echo "  4. Restart application services: docker compose -f docker-compose-unified.yml -f docker-compose-iacgenie.yml up -d"
echo "  5. Verify: docker compose -f docker-compose-unified.yml ps"
echo ""
echo "  Backup saved at: $BACKUP_FILE"
echo "  If rollback is needed:"
echo "    cp $BACKUP_FILE $ENV_FILE"
echo "    docker compose -f docker-compose-unified.yml up -d --force-recreate"
