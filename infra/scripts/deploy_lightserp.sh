#!/bin/bash
# =============================================================================
# deploy_lightserp.sh — Build & Deploy LightSerp to VM
# =============================================================================
# Usage: ./deploy_lightserp.sh
#
# Steps:
#   1. Validate prerequisites (Node.js, Docker)
#   2. Build API and WebUI Docker images on VM
#   3. Deploy containers with correct port mappings
#   4. Verify endpoints
#
# IMPORTANT: Uses existing VM infrastructure (postgres, redis, keycloak, etc.)
# Replaces: iacgenie_lightserp_api, iacgenie_lightserp_webui containers
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../" && pwd)"

VM_HOST="mkanavi@192.168.0.118"
VM_DIR="/home/mkanavi/iacgenie-platform"
LIGHTSERP_DIR="$REPO_ROOT/lightserv"
WEBUI_DIR="$LIGHTSERP_DIR/webui"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}   $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}   $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}   $*"; exit 1; }
step()  { echo -e "${BLUE}[STEP]${NC}   $*"; }

# ── 1. Validate prerequisites ───────────────────────────────────────────────

step "Validating prerequisites..."

command -v docker >/dev/null 2>&1 || fail "Docker not found. Please install Docker."
command -v node >/dev/null 2>&1 || fail "Node.js not found. Please install Node.js."
command -v npm >/dev/null 2>&1 || fail "npm not found."
command -v ssh >/dev/null 2>&1 || fail "SSH not found."

info "Docker:  $(docker --version 2>/dev/null || echo 'available')"
info "Node:    $(node --version 2>/dev/null || echo 'available')"
info "npm:     $(npm --version 2>/dev/null || echo 'available')"

# Check VM connectivity
info "Testing VM connectivity..."
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$VM_HOST" "echo 'VM reachable'" || fail "Cannot reach VM at $VM_HOST"
info "VM connectivity OK"

# ── 2. Sync LightSerp source to VM ──────────────────────────────────────────

step "Syncing LightSerp source to VM..."

# Sync API source (Dockerfile + src/)
rsync -avz \
    --exclude='node_modules' --exclude='__pycache__' --exclude='.git' \
    --exclude='*.pyc' --exclude='*.egg-info' \
    --exclude='infra/' --exclude='research/' --exclude='docs/' \
    "$LIGHTSERP_DIR/src/" "$VM_HOST:$VM_DIR/lightserv/src/" \
    "$LIGHTSERP_DIR/Dockerfile" "$VM_HOST:$VM_DIR/lightserv/Dockerfile" \
    "$LIGHTSERP_DIR/package.json" "$VM_HOST:$VM_DIR/lightserv/package.json" \
    "$LIGHTSERP_DIR/package-lock.json" "$VM_HOST:$VM_DIR/lightserv/package-lock.json" 2>/dev/null || true

info "API source synced"

# Sync WebUI source
rsync -avz \
    --exclude='node_modules' --exclude='.next' --exclude='.git' \
    --exclude='dist/' --exclude='*.egg-info' \
    "$WEBUI_DIR/" "$VM_HOST:$VM_DIR/lightserv/webui/"

info "WebUI source synced"

# ── 3. Build and deploy on VM ───────────────────────────────────────────────

step "Building and deploying on VM..."

ssh "$VM_HOST" <<'REMOTE_BUILD'
set -e

VM_DIR="/home/mkanavi/iacgenie-platform"

# ── Build API image ───────────────────────────────────────────────────────
echo "Building LightSerp API image..."
cd "$VM_DIR/lightserv"
docker build --platform linux/amd64 -t lightserp-api . || {
    echo "ERROR: API build failed"
    exit 1
}
echo "✅ API image built"

# ── Build WebUI image ─────────────────────────────────────────────────────
echo "Building LightSerp WebUI image..."
cd "$VM_DIR/lightserv/webui"
docker build --platform linux/amd64 -t lightserp-webui . || {
    echo "ERROR: WebUI build failed"
    exit 1
}
echo "✅ WebUI image built"

# ── Stop existing containers ──────────────────────────────────────────────
echo "Stopping existing LightSerp containers..."
docker stop iacgenie_lightserp_api 2>/dev/null && docker rm iacgenie_lightserp_api 2>/dev/null || true
docker stop iacgenie_lightserp_webui 2>/dev/null && docker rm iacgenie_lightserp_webui 2>/dev/null || true

# ── Start API on port 8000 ────────────────────────────────────────────────
echo "Starting LightSerp API (port 8000)..."
docker run -d \
    --name iacgenie_lightserp_api \
    --restart unless-stopped \
    --network iacgenie_network \
    -p 127.0.0.1:8000:3000 \
    -e NODE_ENV=production \
    -e PORT=3000 \
    lightserp-api || {
    echo "ERROR: Failed to start API container"
    exit 1
}
echo "✅ API container started"

# ── Start WebUI on port 3070 ──────────────────────────────────────────────
echo "Starting LightSerp WebUI (port 3070)..."
docker run -d \
    --name iacgenie_lightserp_webui \
    --restart unless-stopped \
    --network iacgenie_network \
    -p 127.0.0.1:3070:3070 \
    -e NODE_ENV=production \
    -e PORT=3070 \
    -e API_URL=http://iacgenie_lightserp_api:3000 \
    -e NEXT_PUBLIC_API_URL=https://lightserp.iacgenie.com \
    lightserp-webui || {
    echo "ERROR: Failed to start WebUI container"
    exit 1
}
echo "✅ WebUI container started"

# ── Wait and verify ───────────────────────────────────────────────────────
echo ""
echo "Waiting for containers to start..."
sleep 10

echo ""
echo "==========================================="
echo "  LightSerp Containers"
echo "==========================================="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "iacgenie_lightserp" || echo "  No LightSerp containers found"
echo ""
REMOTE_BUILD

info "Deployment complete"

# ── 4. Verify endpoints ────────────────────────────────────────────────────

step "Verifying endpoints..."

check_endpoint() {
    local url="$1"
    local desc="$2"
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>&1 || echo "000")
    case "$status" in
        200|301|302) echo "  ✅ $desc → $status" ;;
        000)         echo "  ❌ $desc → connection refused" ;;
        *)           echo "  ⚠️  $desc → $status" ;;
    esac
}

sleep 3
echo ""
check_endpoint "https://lightserp.iacgenie.com/" "lightserp.iacgenie.com (WebUI)"
check_endpoint "https://api.iacgenie.com/" "api.iacgenie.com (API)"
echo ""

echo ""
echo "==========================================="
echo "  LightSerp Deployment Complete!"
echo "==========================================="
echo ""
echo "  lightserp.iacgenie.com  → WebUI (via nginx:3070)"
echo "  api.iacgenie.com        → API    (via nginx:8000)"
echo "==========================================="
