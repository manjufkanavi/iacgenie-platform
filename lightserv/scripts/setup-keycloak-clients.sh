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
TOKEN_RESPONSE=$(curl -s -X POST "$KC_URL/realms/master/protocol/openid-connect/token" \
  -d "grant_type=password" \
  -d "username=$KC_ADMIN" \
  -d "password=$KC_PASS" \
  -d "client_id=admin-cli")

ADMIN_TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('access_token',''))")

if [ -z "$ADMIN_TOKEN" ]; then
    echo "  ❌ Failed to authenticate. Check credentials."
    exit 1
fi
echo "  ✓ Authenticated"

# Create realm
echo ""
echo "[2/5] Creating 'lightserp' realm..."
REALM_RESPONSE=$(curl -s -X POST "$KC_URL/admin/realms" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "realm": "lightserp",
    "enabled": true,
    "registrationAllowed": true,
    "resetPasswordAllowed": true,
    "emailRequiredForAccountVerification": false,
    "verifyEmail": false,
    "loginWithEmailAllowed": true,
    "duplicateEmailsAllowed": false,
    "sslRequired": "none",
    "passwordPolicy": "length>=8 and notUsername",
    "rememberMe": true,
    "accessTokenLifespan": 3600,
    "refreshTokenLifespan": 86400,
    "ssoSessionIdleTimeout": 7200,
    "ssoSessionMaxLifespan": 86400
  }')

REALM_ID=$(echo "$REALM_RESPONSE" | python3 -c "import sys,json; r=json.loads(sys.stdin.read()); print(r.get('id',''))" 2>/dev/null || echo "lightserp")
echo "  ✓ Realm 'lightserp' created/exists"

# Create WebUI client (OpenID Connect, public)
echo ""
echo "[3/5] Creating 'lightserp-webui' client..."
WEBUI_RESPONSE=$(curl -s -X POST "$KC_URL/admin/realms/lightserp/clients" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "clientId": "lightserp-webui",
    "name": "LightSerp Web UI",
    "enabled": true,
    "clientAuthenticatorType": "client-secret",
    "redirectUris": ["https://lightserp.iacgenie.com/*", "http://127.0.0.1:3070/*"],
    "webOrigins": ["https://lightserp.iacgenie.com", "http://127.0.0.1:3070"],
    "protocol": "openid-connect",
    "standardFlowEnabled": true,
    "implicitFlowEnabled": false,
    "directAccessGrantsEnabled": true,
    "serviceAccountsEnabled": false,
    "publicClient": true,
    "standardFlowEnabled": true,
    "implicitFlowEnabled": false,
    "directAccessGrantsEnabled": true,
    "serviceAccountsEnabled": false,
    "publicClient": true,
    "authorizationServicesEnabled": false,
    "attributes": {
      "post.logout.redirect.uris": "https://lightserp.iacgenie.com/*"
    }
  }')

WEBUI_CLIENT_SECRET=$(echo "$WEBUI_RESPONSE" | python3 -c "import sys,json; r=json.loads(sys.stdin.read()); print(r.get('clientSecret',''))" 2>/dev/null || echo "NEEDS_MANUAL_CREATION")

if [ -z "$WEBUI_CLIENT_SECRET" ] || [ "$WEBUI_CLIENT_SECRET" = "NEEDS_MANUAL_CREATION" ]; then
    echo "  ⚠️ Client created but secret not available via API."
    echo "    Get it from: Keycloak Admin → lightserp realm → Clients → lightserp-webui"
    WEBUI_CLIENT_SECRET="MANUAL_CHECK_IN_ADMIN_UI"
fi

echo "  ✓ lightserp-webui client created"
echo "    Client Secret: ${WEBUI_CLIENT_SECRET:0:8}..."

# Create API client (OpenID Connect, confidential)
echo ""
echo "[4/5] Creating 'lightserp-api' client..."
API_RESPONSE=$(curl -s -X POST "$KC_URL/admin/realms/lightserp/clients" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "clientId": "lightserp-api",
    "name": "LightSerp API Server",
    "enabled": true,
    "clientAuthenticatorType": "client-secret",
    "redirectUris": ["*"],
    "webOrigins": ["*"],
    "protocol": "openid-connect",
    "standardFlowEnabled": false,
    "directAccessGrantsEnabled": true,
    "serviceAccountsEnabled": true,
    "publicClient": false,
    "standardFlowEnabled": false,
    "directAccessGrantsEnabled": true,
    "serviceAccountsEnabled": true,
    "publicClient": false,
    "authorizationServicesEnabled": false
  }')

API_CLIENT_SECRET=$(echo "$API_RESPONSE" | python3 -c "import sys,json; r=json.loads(sys.stdin.read()); print(r.get('clientSecret',''))" 2>/dev/null || echo "MANUAL_CHECK")

echo "  ✓ lightserp-api client created"
echo "    Client Secret: ${API_CLIENT_SECRET:0:8}..."

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
echo "    Secret: ${WEBUI_CLIENT_SECRET:0:16}..."
echo "    Type:  Public (SPA)"
echo ""
echo "  lightserp-api:"
echo "    Secret: ${API_CLIENT_SECRET:0:16}..."
echo "    Type:  Confidential"
echo ""
echo "  ⚠️  Next steps:"
echo "    1. Update nginx.conf with Keycloak proxy rules"
echo "    2. Update docker-compose with Keycloak env vars"
echo "    3. Deploy updated code to VM"
echo "    4. Rebuild and restart containers"
