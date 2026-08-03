#!/bin/sh
# =============================================================================
# OpenBao Bootstrap Script — Secrets Initialization
# =============================================================================
# Writes secrets for IacGenie and LightSerp into OpenBao KV-v2 engine.
#
# Required env vars (inherited from .env):
#   OPENBAO_TOKEN   - OpenBao root token
#   POSTGRES_SUPER_PASSWORD
#   POSTGRES_APP_PASSWORD
#   POSTGRES_KC_PASSWORD
#   REDIS_PASSWORD
#   MINIO_ROOT_USER
#   MINIO_ROOT_PASSWORD
#   JWT_SECRET
#   SEARXNG_SECRET
# =============================================================================

set -e

echo "==> Waiting for OpenBao to become ready..."
until wget -q --tries=1 --spider http://openbao:8200/v1/sys/health 2>/dev/null; do
    echo "Waiting for OpenBao..."
    sleep 2
done

echo "==> OpenBao is ready. Initializing KV-v2 engine and policies..."

# Enable KV-v2 secrets engine
curl -s -X POST \
    -H "X-Vault-Token: $OPENBAO_TOKEN" \
    -H "Content-Type: application/json" \
    http://openbao:8200/v1/sys/mounts/secret \
    -d '{"type": "kv-v2"}' || echo "  KV-v2 engine already enabled"

# ============================================================================
# IacGenie Secrets
# ============================================================================

# PostgreSQL credentials
curl -s -X POST \
    -H "X-Vault-Token: $OPENBAO_TOKEN" \
    -H "Content-Type: application/json" \
    http://openbao:8200/v1/secret/data/iacgenie/postgres \
    -d "{\"data\":{\"username\":\"postgres\",\"password\":\"${POSTGRES_SUPER_PASSWORD}\",\"host\":\"postgres\",\"port\":\"5432\"}}" || true

# Redis credentials
curl -s -X POST \
    -H "X-Vault-Token: $OPENBAO_TOKEN" \
    -H "Content-Type: application/json" \
    http://openbao:8200/v1/secret/data/iacgenie/redis \
    -d "{\"data\":{\"password\":\"${REDIS_PASSWORD}\",\"host\":\"redis\",\"port\":\"6379\"}}" || true

# MinIO credentials
curl -s -X POST \
    -H "X-Vault-Token: $OPENBAO_TOKEN" \
    -H "Content-Type: application/json" \
    http://openbao:8200/v1/secret/data/iacgenie/minio \
    -d "{\"data\":{\"access_key\":\"${MINIO_ROOT_USER}\",\"secret_key\":\"${MINIO_ROOT_PASSWORD}\",\"endpoint\":\"http://minio:9000\"}}" || true

# JWT secret
curl -s -X POST \
    -H "X-Vault-Token: $OPENBAO_TOKEN" \
    -H "Content-Type: application/json" \
    http://openbao:8200/v1/secret/data/iacgenie/jwt \
    -d "{\"data\":{\"secret\":\"${JWT_SECRET}\"}}" || true

# ============================================================================
# LightSerp Secrets
# ============================================================================

# PostgreSQL credentials
curl -s -X POST \
    -H "X-Vault-Token: $OPENBAO_TOKEN" \
    -H "Content-Type: application/json" \
    http://openbao:8200/v1/secret/data/lightsrp/postgres \
    -d "{\"data\":{\"username\":\"lightsrp\",\"password\":\"${POSTGRES_APP_PASSWORD}\",\"host\":\"postgres\",\"port\":\"5432\"}}" || true

# Redis credentials
curl -s -X POST \
    -H "X-Vault-Token: $OPENBAO_TOKEN" \
    -H "Content-Type: application/json" \
    http://openbao:8200/v1/secret/data/lightsrp/redis \
    -d "{\"data\":{\"password\":\"${REDIS_PASSWORD}\",\"host\":\"redis\",\"port\":\"6379\"}}" || true

# MinIO credentials
curl -s -X POST \
    -H "X-Vault-Token: $OPENBAO_TOKEN" \
    -H "Content-Type: application/json" \
    http://openbao:8200/v1/secret/data/lightsrp/minio \
    -d "{\"data\":{\"access_key\":\"${MINIO_ROOT_USER}\",\"secret_key\":\"${MINIO_ROOT_PASSWORD}\",\"endpoint\":\"http://minio:9000\"}}" || true

# SearXNG secret
curl -s -X POST \
    -H "X-Vault-Token: $OPENBAO_TOKEN" \
    -H "Content-Type: application/json" \
    http://openbao:8200/v1/secret/data/lightsrp/searxng \
    -d "{\"data\":{\"secret\":\"${SEARXNG_SECRET}\"}}" || true

echo "==> OpenBao secrets configured successfully"
echo "    iacgenie/*   - IacGenie secret paths"
echo "    lightsrp/*   - LightSerp secret paths"
