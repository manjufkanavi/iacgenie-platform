#!/bin/bash
# setup-keycloak-clients.sh — Create Keycloak realm, clients, and users for LightSerp
# Run after Keycloak is fully started: ssh newvm 'bash -s' < setup-keycloak-clients.sh
#
# This script uses Keycloak Admin REST API to configure the lightserp realm

set -e

KC_ADMIN="admin"
KC_ADMIN_PASSWORD="Keyclo4k!2026"
KC_URL="http://127.0.0.1:8085"

echo "=========================================="
echo "  LightSerp Keycloak Client Setup"
echo "=========================================="

# Get admin token
echo ""
echo "[1/5] Authenticating with Keycloak admin..."
TOKEN_RESPONSE=

ADMIN_TOKEN=

if [ -z "" ]; then
    echo "  ❌ Failed to authenticate. Check credentials."
    exit 1
fi
echo "  ✓ Authenticated"

# Create realm
echo ""
echo "[2/5] Creating 'lightserp' realm..."
REALM_RESPONSE=

REALM_ID=lightserp
echo "  ✓ Realm 'lightserp' created/exists"

# Create WebUI client (OpenID Connect, public)
echo ""
echo "[3/5] Creating 'lightserp-webui' client..."
WEBUI_RESPONSE=

WEBUI_CLIENT_SECRET=NEEDS_MANUAL_CREATION

if [ -z "" ] || [ "" = "NEEDS_MANUAL_CREATION" ]; then
    echo "  ⚠️ Client created but secret not available via API."
    echo "    Get it from: Keycloak Admin → lightserp realm → Clients → lightserp-webui"
    WEBUI_CLIENT_SECRET="MANUAL_CHECK_IN_ADMIN_UI"
fi

echo "  ✓ lightserp-webui client created"
echo "    Client Secret: ..."

# Create API client (OpenID Connect, confidential)
echo ""
echo "[4/5] Creating 'lightserp-api' client..."
API_RESPONSE=

API_CLIENT_SECRET=MANUAL_CHECK

echo "  ✓ lightserp-api client created"
echo "    Client Secret: ..."

# ---- Summary ----
echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "  Keycloak URL:      http://127.0.0.1:8085/realms/lightserp"
echo "  OIDC Discovery:    http://127.0.0.1:8085/realms/lightserp/.well-known/openid-configuration"
echo ""
echo "  lightserp-webui:"
echo "    Secret: ..."
echo "    Type:  Public (SPA)"
echo ""
echo "  lightserp-api:"
echo "    Secret: ..."
echo "    Type:  Confidential"
echo ""
echo "  ⚠️  Next steps:"
echo "    1. Update nginx.conf with Keycloak proxy rules"
echo "    2. Update docker-compose with Keycloak env vars"
echo "    3. Deploy updated code to VM"
echo "    4. Rebuild and restart containers"