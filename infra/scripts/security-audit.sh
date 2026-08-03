#!/bin/bash
# =============================================================================
# Security Audit Script for Unified Infrastructure
# =============================================================================
# Scans the docker-compose configuration for common security issues.
#
# Usage:
#   bash security-audit.sh
#
# Output:
#   Color-coded report of findings (HIGH/MEDIUM/LOW/INFO)
# =============================================================================

set -euo pipefail

COMPOSE_FILE="$1"
if [ -z "$COMPOSE_FILE" ]; then
  COMPOSE_FILE="$(dirname "$0")/docker-compose-unified.yml"
fi

if [ ! -f "$COMPOSE_FILE" ]; then
  echo "ERROR: Compose file not found: $COMPOSE_FILE"
  exit 1
fi

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

HIGH=0
MED=0
LOW=0
INFO=0

pass() { echo -e "  ${GREEN}✅ PASS${NC}: $1"; }
warn() { echo -e "  ${YELLOW}⚠️  WARN${NC}: $1"; ((MED++)); }
fail() { echo -e "  ${RED}❌ FAIL${NC}: $1"; ((HIGH++)); }
note() { echo -e "  ${BLUE}ℹ️  NOTE${NC}: $1"; ((INFO++)); }

echo "============================================"
echo "  Unified Infrastructure Security Audit"
echo "  File: $COMPOSE_FILE"
echo "  Date: $(date)"
echo "============================================"
echo ""

# Check 1: Secrets in compose file
echo "[1] Secrets Management"
if grep -q '${' "$COMPOSE_FILE"; then
  pass "Secrets use environment variable references (${VAR})"
else
  fail "No environment variable references found in compose file"
fi

# Check 2: no-new-privileges
echo ""
echo "[2] Process Isolation"
if grep -q 'no-new-privileges' "$COMPOSE_FILE"; then
  pass "no-new-privileges is set for services"
else
  fail "no-new-privileges not set — containers may escalate privileges"
fi

# Check 3: Port bindings
echo ""
echo "[3] Port Exposure"
if grep -q 'internal: true' "$COMPOSE_FILE"; then
  pass "Internal-only network detected"
else
  warn "No internal-only network defined — all services may be externally accessible"
fi

# Count exposed ports
EXPOSED_PORTS=$(grep -c '^\s*- "' "$COMPOSE_FILE" 2>/dev/null || echo 0)
echo "  Found $EXPOSED_PORTS port mappings"
note "Verify all exposed ports are bound to 127.0.0.1"

# Check 4: Health checks
echo ""
echo "[4] Health Checks"
HC_COUNT=$(grep -c 'healthcheck' "$COMPOSE_FILE" 2>/dev/null || echo 0)
TOTAL_SERVICES=$(grep -c '^\s\+\w' "$COMPOSE_FILE" 2>/dev/null || echo 0)
if [ "$HC_COUNT" -gt 0 ]; then
  pass "$HC_COUNT services have health checks"
else
  fail "No health checks defined — cannot detect service failures"
fi

# Check 5: Read-only filesystems
echo ""
echo "[5] Filesystem Security"
if grep -q 'read_only: true' "$COMPOSE_FILE"; then
  pass "Read-only filesystem configured where possible"
else
  warn "No read_only filesystem — containers can write to root filesystem"
fi

# Check 6: Resource limits
echo ""
echo "[6] Resource Limits"
if grep -q 'limits:' "$COMPOSE_FILE"; then
  pass "Resource limits (memory/CPU) are configured"
else
  warn "No resource limits — a single service could consume all resources"
fi

# Check 7: Network isolation
echo ""
echo "[7] Network Isolation"
if grep -q 'internal: true' "$COMPOSE_FILE"; then
  pass "Internal network defined for shared services"
else
  fail "No internal network — shared services may be exposed"
fi

# Check 8: TLS readiness
echo ""
echo "[8] TLS/Encryption"
if [ -f "$(dirname "$COMPOSE_FILE")/generate-tls-certs.sh" ]; then
  pass "TLS certificate generation script found"
else
  warn "No TLS certificate generation script found"
fi

if [ -f "$(dirname "$COMPOSE_FILE")/certs/fullchain.pem" ]; then
  pass "TLS certificates exist in certs/"
else
  note "No TLS certificates yet — run generate-tls-certs.sh"
fi

# Check 9: Audit logging
echo ""
echo "[9] Audit Logging"
if [ -f "$(dirname "$COMPOSE_FILE")/openbao/openbao-enable-audit.sh" ]; then
  pass "OpenBao audit logging script found"
else
  warn "No OpenBao audit logging script"
fi

if [ -f "$(dirname "$COMPOSE_FILE")/postgres/audit-logging.conf" ]; then
  pass "PostgreSQL audit logging config found"
else
  warn "No PostgreSQL audit logging config"
fi

# Check 10: Secret rotation
echo ""
echo "[10] Secret Rotation"
if [ -f "$(dirname "$COMPOSE_FILE")/rotate-secrets.sh" ]; then
  pass "Secret rotation script found"
else
  warn "No secret rotation script — consider creating one"
fi

# Summary
echo ""
echo "============================================"
echo "  Audit Summary"
echo "============================================"
echo -e "  ${RED}❌ CRITICAL: $HIGH${NC}"
echo -e "  ${YELLOW}⚠️  WARNING: $MED${NC}"
echo -e "  ${BLUE}ℹ️  INFO: $INFO${NC}"
echo ""

if [ "$HIGH" -gt 0 ]; then
  echo "  STATUS: ${RED}FAILED — $HIGH critical issue(s) need fixing${NC}"
  exit 1
else
  echo "  STATUS: ${GREEN}PASSED${NC} — No critical issues found"
fi
