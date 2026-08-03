#!/bin/bash
set -e

KC_ADMIN="admin"
KC_ADMIN_PASSWORD="Keyclo4k!2026"
KC_URL="http://127.0.0.1:8085"

echo "=========================================="
echo "  LightSerp Keycloak Setup"
echo "=========================================="

# Get admin token
echo ""
echo "[1/5] Authenticating with Keycloak admin..."
TOKEN_RESPONSE=

ADMIN_TOKEN=

if [ -z "" ]; then
    echo "  FAILED to authenticate. Check credentials."
    echo "  Response: "
    exit 1
fi
echo "  OK Authenticated"

# Create realm
echo ""
echo "[2/5] Creating 'lightserp' realm..."
REALM_RESPONSE=

REALM_ID=lightserp
echo "  OK Realm 'lightserp' created/exists (id: )"

# Create WebUI client
echo ""
echo "[3/5] Creating 'lightserp-webui' client..."
WEBUI_RESPONSE=

WEBUI_SECRET=NONE
echo "  OK lightserp-webui client created"
echo "    Secret: ..."

# Create API client
echo ""
echo "[4/5] Creating 'lightserp-api' client..."
API_RESPONSE=

API_SECRET=NONE
echo "  OK lightserp-api client created"
echo "    Secret: ..."

# Create a test user
echo ""
echo "[5/5] Creating test user 'admin'..."
USER_RESPONSE=

echo "  OK User 'admin' created"
echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "  Keycloak URL:      http://127.0.0.1:8085/realms/lightserp"
echo "  OIDC Discovery:    http://127.0.0.1:8085/realms/lightserp/.well-known/openid-configuration"
echo ""
echo "  Admin Login:       admin / Keyclo4k!2026"
echo "  lightserp-webui:   Public client"
echo "    Secret: ..."
echo "  lightserp-api:     Confidential client"
echo "    Secret: ..."
echo ""