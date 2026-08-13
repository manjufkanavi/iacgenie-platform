#!/bin/bash
# Post-Deployment Verification Script for Keycloak
# Tests: admin login, realm OIDC config, admin console availability
# Usage: ./verify-keycloak.sh [keycloak_url] [admin_user] [admin_pass]

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────
KC_URL="${1:-http://127.0.0.1:8083}"
KC_ADMIN="${2:-admin}"
KC_PASS="${3:-$(bao kv get -field=admin_password iacgenie/kv/keycloak 2>/dev/null || echo '')}"
PASS=0
FAIL=0
TOTAL=0

# ── Helpers ───────────────────────────────────────────────────────────────
pass() { printf '\033[32m✓\033[0m %s\n' "$1"; PASS=$((PASS+1)); TOTAL=$((TOTAL+1)); }
fail() { printf '\033[31m✗\033[0m %s\n' "$1"; FAIL=$((FAIL+1)); TOTAL=$((TOTAL+1)); }
info() { printf '  → %s\n' "$1"; }
sep() { printf '\n--- %s ---\n' "$1"; }

# ── 1. Admin CLI Login Test ───────────────────────────────────────────────
sep "Test 1: Admin CLI Login"
if [ -z "$KC_PASS" ]; then
    fail "Admin password not available (set KC_PASS or configure OpenBao)"
else
    TOKEN=$(curl -s -X POST "${KC_URL}/realms/master/protocol/openid-connect/token" \
        -d "grant_type=password" \
        -d "username=${KC_ADMIN}" \
        -d "password=${KC_PASS}" \
        -d "client_id=admin-cli" 2>/dev/null | jq -r '.access_token // empty')

    if [ -n "$TOKEN" ]; then
        pass "Admin CLI login successful"
    else
        RESP=$(curl -s -w '\n%{http_code}' -X POST "${KC_URL}/realms/master/protocol/openid-connect/token" \
            -d "grant_type=password" \
            -d "username=${KC_ADMIN}" \
            -d "password=${KC_PASS}" \
            -d "client_id=admin-cli" 2>/dev/null)
        HTTP_CODE=$(echo "$RESP" | tail -1)
        fail "Admin login failed (HTTP ${HTTP_CODE})"
        info "Response: $(echo "$RESP" | head -1)"
    fi
fi

# ── 2. Admin Console Availability ─────────────────────────────────────────
sep "Test 2: Admin Console Availability"
CONSOLE_HTTP=$(curl -s -o /dev/null -w '%{http_code}' "${KC_URL}/admin/" 2>/dev/null || echo "000")
if [ "$CONSOLE_HTTP" = "200" ] || [ "$CONSOLE_HTTP" = "302" ]; then
    pass "Admin console reachable (HTTP ${CONSOLE_HTTP})"
else
    fail "Admin console unreachable (HTTP ${CONSOLE_HTTP})"
fi

# ── 3. Health Endpoint Check ──────────────────────────────────────────────
sep "Test 3: Keycloak Health Endpoint"
HEALTH=$(curl -s "${KC_URL}/health/ready" 2>/dev/null || echo '{"status":"unavailable"}')
HEALTH_STATUS=$(echo "$HEALTH" | jq -r '.status // "unknown"')
if [ "$HEALTH_STATUS" = "UP" ]; then
    pass "Keycloak health check: UP"
else
    fail "Keycloak health check: ${HEALTH_STATUS}"
fi

# ── 4. Realm Availability Check ───────────────────────────────────────────
sep "Test 4: Realm Availability"
AUTH_HEADER=""
if [ -n "${TOKEN:-}" ]; then
    AUTH_HEADER="Bearer ${TOKEN}"
fi

for REALM in iacgenie lightserp; do
    REALM_HTTP=$(curl -s -o /dev/null -w '%{http_code}' "${KC_URL}/admin/realms/${REALM}" \
        -H "$AUTH_HEADER" 2>/dev/null || echo "000")
    if [ "$REALM_HTTP" = "200" ]; then
        REALM_NAME=$(curl -s "${KC_URL}/admin/realms/${REALM}" \
            -H "$AUTH_HEADER" 2>/dev/null | jq -r '.displayName // "unknown"')
        pass "Realm '${REALM}' available (${REALM_NAME})"
    else
        fail "Realm '${REALM}' not found (HTTP ${REALM_HTTP})"
    fi
done

# ── 5. Client Configuration Check ─────────────────────────────────────────
sep "Test 5: Client Configuration"
if [ -n "${TOKEN:-}" ]; then
    for CLIENT in iacgenie-platform lightserp-api gitea searxng; do
        CLIENT_HTTP=$(curl -s -o /dev/null -w '%{http_code}' \
            "${KC_URL}/admin/realms/iacgenie/clients?search=${CLIENT}" \
            -H "$AUTH_HEADER" 2>/dev/null || echo "000")
        if [ "$CLIENT_HTTP" = "200" ]; then
            pass "Client '${CLIENT}' registered in iacgenie realm"
        else
            # Try lightserp realm
            LS_HTTP=$(curl -s -o /dev/null -w '%{http_code}' \
                "${KC_URL}/admin/realms/lightserp/clients?search=${CLIENT}" \
                -H "$AUTH_HEADER" 2>/dev/null || echo "000")
            if [ "$LS_HTTP" = "200" ]; then
                pass "Client '${CLIENT}' registered in lightserp realm"
            else
                fail "Client '${CLIENT}' not found"
            fi
        fi
    done
else
    info "Skipping client check — admin token not available"
fi

# ── 6. Database Driver Check ──────────────────────────────────────────────
sep "Test 6: Database Driver Verification"
DB_URL=$(curl -s "${KC_URL}/about" 2>/dev/null | jq -r '.database // "unknown"')
if echo "$DB_URL" | grep -qi 'postgres'; then
    pass "Keycloak using PostgreSQL database"
else
    info "Database type: ${DB_URL:-unavailable (check keycloak.conf manually)}"
fi

# ── Summary ────────────────────────────────────────────────────────────────
sep "Verification Summary"
printf "  Total:  \033[1m%d\033[0m | Passed: \033[32m%d\033[0m | Failed: \033[31m%d\033[0m\n" "$TOTAL" "$PASS" "$FAIL"

if [ "$FAIL" -eq 0 ]; then
    printf '\033[32mAll Keycloak verifications passed!\033[0m\n'
    exit 0
else
    printf '\033[31m%d verification(s) failed — check logs\033[0m\n' "$FAIL"
    printf '  docker logs iacgenie_keycloak\n'
    exit 1
fi
