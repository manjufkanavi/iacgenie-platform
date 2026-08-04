#!/bin/bash
# =============================================================================
# deploy_platform.sh — Build & Deploy IacGenie Platform to VM
# =============================================================================
# Usage: ./deploy_platform.sh
#
# Steps:
#   1. Validate prerequisites (Python, Docker, Node.js)
#   2. Sync platform/ directory to VM
#   3. Build backend image (Python 3.11 + all dependencies)
#   4. Build frontend image (Node 22 + Vite build + nginx)
#   5. Deploy containers on VM (reuses existing network & shared services)
#   6. Verify endpoints
#
# IMPORTANT: Reuses existing VM infrastructure:
#   - PostgreSQL (iacgenie_postgres on iacgenie-network)
#   - Redis (iacgenie_redis on iacgenie-network)
#   - MinIO, OpenBao, Keycloak, Gitea (all running)
#   - Docker network: iacgenie-network
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../" && pwd)"

VM_HOST="mkanavi@192.168.0.118"
VM_DIR="/home/mkanavi/iacgenie-platform"
PLATFORM_DIR="$REPO_ROOT/platform"
FRONTEND_DIR="$PLATFORM_DIR/frontend"
BACKEND_DIR="$PLATFORM_DIR/backend"

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
command -v python3 >/dev/null 2>&1 || fail "Python 3 not found."
command -v node >/dev/null 2>&1 || fail "Node.js not found."
command -v rsync >/dev/null 2>&1 || fail "rsync not found."

info "Docker:  $(docker --version 2>/dev/null || echo 'available')"
info "Python:  $(python3 --version 2>/dev/null || echo 'available')"
info "Node:    $(node --version 2>/dev/null || echo 'available')"

# Check VM connectivity
info "Testing VM connectivity..."
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$VM_HOST" "echo 'VM reachable'" || fail "Cannot reach VM at $VM_HOST"
info "VM connectivity OK"

# ── 2. Sync platform/ directory to VM ───────────────────────────────────────

step "Syncing platform/ directory to VM..."

rsync -avz \
    --exclude='node_modules' --exclude='__pycache__' --exclude='.git' \
    --exclude='*.pyc' --exclude='.next/' --exclude='dist/' \
    --exclude='.env' --exclude='.env.local' \
    --exclude='__pycache__/' --exclude='*.egg-info' \
    --exclude='migrations/' \
    "$PLATFORM_DIR/" "$VM_HOST:$VM_DIR/platform/"

info "Platform source synced to $VM_DIR/platform/"

# ── 3. Build images on VM ──────────────────────────────────────────────────

step "Building backend image..."

ssh "$VM_HOST" <<'REMOTE_BACKEND'
set -e

VM_DIR="/home/mkanavi/iacgenie-platform"

# Stop existing backend
docker stop iacgenie-backend 2>/dev/null && docker rm iacgenie-backend 2>/dev/null || true

# Build backend
echo "Building IacGenie Backend image..."
cd "$VM_DIR/platform/backend"
docker build --platform linux/amd64 -t iacgenie-backend . || {
    echo "ERROR: Backend build failed"
    exit 1
}
echo "✅ Backend image built: iacgenie-backend"
REMOTE_BACKEND

step "Building frontend image..."

ssh "$VM_HOST" <<'REMOTE_FRONTEND'
set -e

VM_DIR="/home/mkanavi/iacgenie-platform"

# Stop existing frontend
docker stop iacgenie-frontend 2>/dev/null && docker rm iacgenie-frontend 2>/dev/null || true

# Build frontend from platform/ context (with nginx.conf)
echo "Building IacGenie Frontend image..."
cd "$VM_DIR/platform"
docker build --platform linux/amd64 -t iacgenie-frontend -f frontend/Dockerfile . || {
    echo "ERROR: Frontend build failed"
    exit 1
}
echo "✅ Frontend image built: iacgenie-frontend"
REMOTE_FRONTEND

# ── 4. Deploy containers ───────────────────────────────────────────────────

step "Deploying containers..."

ssh "$VM_HOST" <<'REMOTE_DEPLOY'
set -e

echo "Starting IacGenie Backend..."
docker run -d \
    --name iacgenie-backend \
    --restart unless-stopped \
    --network iacgenie-network \
    -p 8002:8000 \
    -e DATABASE_PROVIDER=postgres \
    -e POSTGRES_HOST=iacgenie_postgres \
    -e POSTGRES_PORT=5432 \
    -e POSTGRES_DATABASE=iacgenie \
    -e POSTGRES_USER=iacgenie_user \
    -e REDIS_HOST=iacgenie_redis \
    -e REDIS_PORT=6379 \
    -e HOST=0.0.0.0 \
    -e PORT=8000 \
    -e OPENBAO_ADDR=http://127.0.0.1:8200 \
    -e MINIO_ENDPOINT=http://127.0.0.1:9000 \
    -e MINIO_ACCESS_KEY=minioadmin \
    -e GITEA_HOST=http://127.0.0.1:3000 \
    -e GITEA_USER=mkanavi \
    --restart unless-stopped \
    iacgenie-backend || {
    echo "ERROR: Failed to start backend"
    exit 1
}
echo "✅ Backend started"

echo "Starting IacGenie Frontend..."
docker run -d \
    --name iacgenie-frontend \
    --restart unless-stopped \
    --network iacgenie-network \
    -p 3001:80 \
    -e NEXT_PUBLIC_API_URL=https://iacgenie.iacgenie.com \
    -e API_BASE_URL=https://iacgenie.iacgenie.com \
    iacgenie-frontend || {
    echo "ERROR: Failed to start frontend"
    exit 1
}
echo "✅ Frontend started"

# Wait for containers
echo ""
echo "Waiting for containers to start..."
sleep 12

echo ""
echo "==========================================="
echo "  IacGenie Platform Containers"
echo "==========================================="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "iacgenie-(backend|frontend)" || echo "  No platform containers found"
echo ""
echo "Container details:"
echo "  Backend: iacgenie-backend   (port 8002 → 8000)"
echo "  Frontend: iacgenie-frontend (port 3001 → 80)"
echo "==========================================="
REMOTE_DEPLOY

# ── 5. Verify endpoints ────────────────────────────────────────────────────

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

echo ""
sleep 3
echo "Endpoint checks:"
check_endpoint "https://platform.iacgenie.com/" "platform.iacgenie.com (Frontend)"
check_endpoint "https://iacgenie.iacgenie.com/" "iacgenie.iacgenie.com (Backend)"
check_endpoint "https://lightserp.iacgenie.com/" "lightserp.iacgenie.com (LightSerp WebUI)"
echo ""

# ── 6. Summary ──────────────────────────────────────────────────────────────

echo ""
echo "==========================================="
echo "  IacGenie Platform Deployment Complete!"
echo "==========================================="
echo ""
echo "  platform.iacgenie.com   → IacGenie Frontend  (nginx:3001)"
echo "  iacgenie.iacgenie.com   → IacGenie Backend   (nginx:8002)"
echo "  lightserp.iacgenie.com  → LightSerp WebUI    (nginx:3070)"
echo "==========================================="
