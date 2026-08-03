#!/bin/bash
# Generate strong secrets for IacGenie Raspberry Pi deployment
# Usage: bash infra/generate-secrets.sh
# Output: infra/services-secrets.md

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SECRETS_FILE="$SCRIPT_DIR/services-secrets.md"

echo "Generating secrets for Raspberry Pi deployment..."

cat > "$SECRETS_FILE" << 'HEADER'
# IacGenie Services Secrets — Raspberry Pi Deployment

> **DO NOT commit this file to git.** Add to `.gitignore` if necessary.
HEADER

# Add timestamp
echo "> Generated: $(date -u '+%Y-%m-%d')" >> "$SECRETS_FILE"
echo "> Environment: Raspberry Pi (aarch64, 8GB RAM)" >> "$SECRETS_FILE"
echo "" >> "$SECRETS_FILE"
echo "## Generated Secrets (Core Stack)" >> "$SECRETS_FILE"
echo "" >> "$SECRETS_FILE"
echo "| # | Service | Key | Value |" >> "$SECRETS_FILE"
echo "|---|---------|-----|-------|" >> "$SECRETS_FILE"

declare -A SERVICES
SERVICES=(
    ["POSTGRES_SUPER_PASSWORD"]="32"
    ["POSTGRES_APP_PASSWORD"]="32"
    ["POSTGRES_KC_PASSWORD"]="32"
    ["MINIO_ROOT_PASSWORD"]="32"
    ["OPENBAO_ROOT_TOKEN"]="32"
    ["OPENBAO_TOKEN"]="32"
    ["KEYCLOAK_ADMIN_PASSWORD"]="32"
    ["GRAFANA_ADMIN_PASSWORD"]="32"
    ["JWT_SECRET"]="64"
    ["REDIS_PASSWORD"]="32"
)

NUM=0
for key in "${!SERVICES[@]}"; do
    NUM=$((NUM + 1))
    length="${SERVICES[$key]}"
    value=$(python3 -c "import secrets; print(secrets.token_urlsafe($length))")
    echo "| $NUM | ${key%%_*} (${key#*_}) | \`$key\` | \`$value\` |" >> "$SECRETS_FILE"
    echo "  $key=***hidden*** (length: $length bytes)"
done

echo "" >> "$SECRETS_FILE"
echo "## External Secrets (Obtain Manually)" >> "$SECRETS_FILE"
echo "" >> "$SECRETS_FILE"
echo "| # | Service | Key | Where to Obtain |" >> "$SECRETS_FILE"
echo "|---|---------|-----|-----------------|" >> "$SECRETS_FILE"
echo '| 11 | Cloudflare Tunnel | `CLOUDFLARE_TUNNEL_TOKEN` | Cloudflare Zero Trust Dashboard → Networks → Access → Tunnels |' >> "$SECRETS_FILE"
echo '| 12 | SMTP (SMTP2GO) | `SMTP2GO_API_KEY` | SMTP2GO Dashboard → Settings → API Keys |' >> "$SECRETS_FILE"
echo '| 13 | Sentry | `SENTRY_DSN` | Sentry Dashboard → Project Settings → DSN |' >> "$SECRETS_FILE"
echo "" >> "$SECRETS_FILE"
echo "## Deferred Secrets (Phase 3b — ELK/Digger/Jaeger)" >> "$SECRETS_FILE"
echo "" >> "$SECRETS_FILE"
echo "| # | Service | Key | When to Generate |" >> "$SECRETS_FILE"
echo "|---|---------|-----|------------------|" >> "$SECRETS_FILE"
echo "| 14 | Elasticsearch | `ELASTIC_PASSWORD` | When adding ELK stack |" >> "$SECRETS_FILE"
echo "| 15 | Digger DB | `DIGGER_DB_PASSWORD` | When adding Digger |" >> "$SECRETS_FILE"
echo "| 16 | Alertmanager | `ALERTMANAGER_PASSWORD` | When adding alerting |" >> "$SECRETS_FILE"

echo ""
echo "Secrets written to: $SECRETS_FILE"
echo "WARNING: This file contains sensitive data. Do not commit to git."
