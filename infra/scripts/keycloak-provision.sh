#!/bin/bash
# Keycloak Provisioning Script
# Creates lightserp realm and clients, enforces admin-only model
# Uses the Keycloak Admin REST API directly (no ansible dependency)
set -euo pipefail

KC_URL="http://127.0.0.1:8083"
KC_ADMIN_USER="admin"
KC_ADMIN_PASS="hAaIa219fq5VzAP81SDyNuBV"
MASTER_REALM="master"
IACGENIE_REALM="iacgenie"
LIGHTSERP_REALM="lightserp"

# Get admin access token
get_admin_token() {
    curl -s -X POST "${KC_URL}/realms/${MASTER_REALM}/protocol/openid-connect/token" \
        -d "grant_type=password" \
        -d "username=${KC_ADMIN_USER}" \
        -d "password=${KC_ADMIN_PASS}" \
        -d "client_id=admin-cli" | jq -r .access_token
}

ADMIN_TOKEN=$(get_admin_token)
echo "Authenticated as ${KC_ADMIN_USER}"

# =============================================================================
# Create lightserp realm
# =============================================================================
if curl -s -o /dev/null -w "%{http_code}" "http://${KC_URL}/admin/realms/lightserp" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" | grep -q "200"; then
    echo "Realm '${LIGHTSERP_REALM}' already exists, skipping creation"
else
    echo "Creating realm '${LIGHTSERP_REALM}'..."
    curl -s -X POST "http://${KC_URL}/admin/realms" \
        -H "Authorization: Bearer ${ADMIN_TOKEN}" \
        -H "Content-Type: application/json" \
        -d '{
            "realm": "lightserp",
            "displayName": "LightSerp Platform",
            "enabled": true,
            "registrationAllowed": false,
            "registrationEmailAsUsername": false,
            "rememberMe": true,
            "loginWithEmailAllowed": true,
            "duplicateEmailsAllowed": false,
            "resetPasswordAllowed": true,
            "sslRequired": "external",
            "passwordPolicy": "length(8) and notUsername and uppercase(1) and digits(1)",
            "browserFlow": "registration",
            "directGrantFlow": "direct grant",
            "resetCredentialsFlow": "reset credentials",
            "clientAuthenticationFlow": "clients",
            "roles": {
                "realm": [
                    {"name": "platform-admin", "description": "Full platform administrator"},
                    {"name": "project-admin", "description": "Project-level administrator"},
                    {"name": "project-member", "description": "Project read-only member"},
                    {"name": "openbao-admin", "description": "OpenBao admin access"},
                    {"name": "openbao-service-read", "description": "OpenBao read-only service token"}
                ]
            },
            "attributes": {
                "clientAuthorization PoliciesEnabled": "true",
                "standardFlowEnabled": "true",
                "implicitFlowEnabled": "false",
                "adminPermissionsEnabled": "true"
            }
        }' 2>&1 | jq .
fi

# Get lightserp realm ID
LIGHTSERP_REALM_ID=$(curl -s "http://${KC_URL}/admin/realms/lightserp" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" | jq -r .id)

echo "LightSerp realm ID: ${LIGHTSERP_REALM_ID}"

# =============================================================================
# Create LightSerp clients in lightserp realm
# =============================================================================

# Client: lightserp-webui
echo "Creating client 'lightserp-webui'..."
WEBUI_CLIENT_ID=$(curl -s "http://${KC_URL}/admin/realms/lightserp/clients?search=lightserp-webui" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" | jq -r '.[0].clientId // empty')

if [ -z "${WEBUI_CLIENT_ID:-}" ]; then
    WEBUI_RESP=$(curl -s -X POST "http://${KC_URL}/admin/realms/lightserp/clients" \
        -H "Authorization: Bearer ${ADMIN_TOKEN}" \
        -H "Content-Type: application/json" \
        -d '{
            "clientId": "lightserp-webui",
            "name": "LightSerp WebUI",
            "enabled": true,
            "clientAuthenticatorType": "client-secret",
            "redirectUris": [
                "https://lightserp.iacgenie.com/*",
                "https://app.iacgenie.com/*"
            ],
            "webOrigins": [
                "https://lightserp.iacgenie.com",
                "https://app.iacgenie.com"
            ],
            "standardFlowEnabled": true,
            "directAccessGrantsEnabled": false,
            "serviceAccountsEnabled": false,
            "consentRequired": false,
            "protocol": "openid-connect",
            "defaultClientScopes": ["web-origins", "role_list", "profile", "email"],
            "attributes": {
                "post.logout.redirect.uris": "+"
            }
        }' 2>&1)
    echo "Response: ${WEBUI_RESP}"
else
    echo "Client 'lightserp-webui' already exists, skipping"
fi

# Client: lightserp-api
echo "Creating client 'lightserp-api'..."
API_CLIENT_ID=$(curl -s "http://${KC_URL}/admin/realms/lightserp/clients?search=lightserp-api" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" | jq -r '.[0].clientId // empty')

if [ -z "${API_CLIENT_ID:-}" ]; then
    API_RESP=$(curl -s -X POST "http://${KC_URL}/admin/realms/lightserp/clients" \
        -H "Authorization: Bearer ${ADMIN_TOKEN}" \
        -H "Content-Type: application/json" \
        -d '{
            "clientId": "lightserp-api",
            "name": "LightSerp API",
            "enabled": true,
            "clientAuthenticatorType": "client-secret",
            "redirectUris": [
                "https://api.iacgenie.com/*"
            ],
            "webOrigins": [
                "https://api.iacgenie.com",
                "+"
            ],
            "standardFlowEnabled": true,
            "directAccessGrantsEnabled": true,
            "serviceAccountsEnabled": true,
            "consentRequired": false,
            "protocol": "openid-connect",
            "defaultClientScopes": ["web-origins", "role_list"],
            "attributes": {
                "jwt.press_claims": "true"
            }
        }' 2>&1)
    echo "Response: ${API_RESP}"
else
    echo "Client 'lightserp-api' already exists, skipping"
fi

# Client: openbao-oidc (for OpenBao OIDC auth)
echo "Creating client 'openbao-oidc'..."
OAIDC_CLIENT_ID=$(curl -s "http://${KC_URL}/admin/realms/lightserp/clients?search=openbao-oidc" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" | jq -r '.[0].clientId // empty')

if [ -z "${OAIDC_CLIENT_ID:-}" ]; then
    OAIDC_RESP=$(curl -s -X POST "http://${KC_URL}/admin/realms/lightserp/clients" \
        -H "Authorization: Bearer ${ADMIN_TOKEN}" \
        -H "Content-Type: application/json" \
        -d '{
            "clientId": "openbao-oidc",
            "name": "OpenBao OIDC",
            "enabled": true,
            "clientAuthenticatorType": "client-secret",
            "redirectUris": [
                "https://vault.iacgenie.com/*"
            ],
            "webOrigins": [
                "https://vault.iacgenie.com"
            ],
            "standardFlowEnabled": true,
            "directAccessGrantsEnabled": false,
            "serviceAccountsEnabled": true,
            "consentRequired": false,
            "protocol": "openid-connect",
            "defaultClientScopes": ["web-origins", "role_list"],
            "attributes": {}
        }' 2>&1)
    echo "Response: ${OAIDC_RESP}"
else
    echo "Client 'openbao-oidc' already exists, skipping"
fi

# =============================================================================
# Create admin user in lightserp realm
# =============================================================================
echo "Creating admin user in lightserp realm..."
ADMIN_CREATED=$(curl -s -X POST "http://${KC_URL}/admin/realms/lightserp/users" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
        "username": "admin",
        "enabled": true,
        "email": "admin@iacgenie.com",
        "emailVerified": true,
        "firstName": "Platform",
        "lastName": "Admin",
        "credentials": [
            {"type": "password", "value": "hAaIa219fq5VzAP81SDyNuBV", "temporary": false}
        ],
        "realmRoles": ["platform-admin", "openbao-admin"]
    }' 2>&1)
echo "Admin user response: ${ADMIN_CREATED}"

# =============================================================================
# Register clients in iacgenie realm (if not already done)
# =============================================================================
echo "Registering clients in iacgenie realm..."

for CLIENT in \
    '{
        "clientId": "iacgenie-platform",
        "name": "IacGenie Admin Dashboard",
        "enabled": true,
        "clientAuthenticatorType": "client-secret",
        "redirectUris": ["https://admin.iacgenie.com/*", "https://iacgenie.com/*"],
        "webOrigins": ["https://admin.iacgenie.com", "https://iacgenie.com"],
        "standardFlowEnabled": true,
        "directAccessGrantsEnabled": false,
        "serviceAccountsEnabled": true,
        "consentRequired": false,
        "protocol": "openid-connect",
        "defaultClientScopes": ["web-origins", "role_list"]
    }' \
    '{
        "clientId": "gitea",
        "name": "Gitea SSO",
        "enabled": true,
        "clientAuthenticatorType": "client-secret",
        "redirectUris": ["https://gitea.iacgenie.com/user/oauth2/gitea"],
        "webOrigins": ["https://gitea.iacgenie.com"],
        "standardFlowEnabled": true,
        "directAccessGrantsEnabled": false,
        "serviceAccountsEnabled": false,
        "consentRequired": false,
        "protocol": "openid-connect",
        "defaultClientScopes": ["web-origins", "role_list"]
    }' \
    '{
        "clientId": "searxng",
        "name": "SearXNG Search",
        "enabled": true,
        "clientAuthenticatorType": "client-secret",
        "redirectUris": ["https://search.iacgenie.com/*"],
        "webOrigins": ["https://search.iacgenie.com"],
        "standardFlowEnabled": true,
        "directAccessGrantsEnabled": false,
        "serviceAccountsEnabled": false,
        "consentRequired": false,
        "protocol": "openid-connect",
        "defaultClientScopes": ["web-origins", "role_list"]
    }'; do

    CLIENT_ID=$(echo "$CLIENT" | jq -r .clientId)
    EXISTING=$(curl -s "http://${KC_URL}/admin/realms/iacgenie/clients?search=${CLIENT_ID}" \
        -H "Authorization: Bearer ${ADMIN_TOKEN}" | jq ".[0].clientId // empty")

    if [ -z "${EXISTING:-}" ]; then
        echo "  Registering client: ${CLIENT_ID}"
        curl -s -X POST "http://${KC_URL}/admin/realms/iacgenie/clients" \
            -H "Authorization: Bearer ${ADMIN_TOKEN}" \
            -H "Content-Type: application/json" \
            -d "${CLIENT}" 2>&1 | jq .
    else
        echo "  Client '${CLIENT_ID}' already exists, skipping"
    fi
done

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "=== Keycloak Provisioning Summary ==="
echo "Realms: master, iacgenie, lightserp"
echo ""
echo "iacgenie realm clients: iacgenie-platform, gitea, searxng"
echo "lightserp realm clients: lightserp-webui, lightserp-api, openbao-oidc"
echo ""
echo "Admin user created: admin@iacgenie.com (password from .env)"
echo "Roles: platform-admin, project-admin, project-member, openbao-admin, openbao-service-read"
echo ""
echo "Next: Deploy OpenBao OIDC auth method using these client credentials"
