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
TOKEN_RESPONSE=$(curl -s -X POST "$KC_URL/realms/master/protocol/openid-connect/token" \
  -d "grant_type=password" \
  -d "username=$KC_ADMIN" \
  -d "password=$KC_ADMIN_PASSWORD" \
  -d "client_id=admin-cli")

ADMIN_TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('access_token',''))")

if [ -z "$ADMIN_TOKEN" ]; then
    echo "  FAILED to authenticate. Check credentials."
    echo "  Response: $TOKEN_RESPONSE"
    exit 1
fi
echo "  OK Authenticated"

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
echo "  OK Realm 'lightserp' created/exists (id: $REALM_ID)"

# Create WebUI client
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
    "publicClient": true,
    "authorizationServicesEnabled": false,
    "attributes": {
      "post.logout.redirect.uris": "https://lightserp.iacgenie.com/*"
    }
  }')

WEBUI_SECRET=$(echo "$WEBUI_RESPONSE" | python3 -c "import sys,json; r=json.loads(sys.stdin.read()); print(r.get('clientSecret','NONE'))" 2>/dev/null || echo "NONE")
echo "  OK lightserp-webui client created"
echo "    Secret: ${WEBUI_SECRET:0:16}..."

# Create API client
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
    "standardFlowEnabled": true,
    "directAccessGrantsEnabled": true,
    "serviceAccountsEnabled": false,
    "publicClient": false,
    "authorizationServicesEnabled": false
  }')

API_SECRET=$(echo "$API_RESPONSE" | python3 -c "import sys,json; r=json.loads(sys.stdin.read()); print(r.get('clientSecret','NONE'))" 2>/dev/null || echo "NONE")
echo "  OK lightserp-api client created"
echo "    Secret: ${API_SECRET:0:16}..."

# Create a test user
echo ""
echo "[5/5] Creating test user 'admin'..."
USER_RESPONSE=$(curl -s -X POST "$KC_URL/admin/realms/lightserp/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@iacgenie.com",
    "enabled": true,
    "emailVerified": true,
    "credentials": [
      {"type": "password", "value": "Keyclo4k!2026", "temporary": false}
    ],
    "clientRoles": {
      "lightserp-api": ["admin"]
    }
  }')

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
echo "    Secret: ${WEBUI_SECRET:0:16}..."
echo "  lightserp-api:     Confidential client"
echo "    Secret: ${API_SECRET:0:16}..."
echo ""
