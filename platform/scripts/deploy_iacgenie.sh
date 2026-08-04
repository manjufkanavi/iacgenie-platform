#!/bin/bash
# =============================================================================
# deploy_iacgenie.sh — Build & Deploy IacGenie Platform
# =============================================================================
# Usage: ./deploy_iacgenie.sh [--push|--vm-only]
#
# This script:
#   1. Validates prerequisites (Node.js, Docker, Python, SSH)
#   2. Builds IacGenie backend Docker image
#   3. Builds IacGenie frontend Docker image
#   4. Pushes images to registry OR deploys directly to VM
#   5. Deploys both containers on the VM
#
# Options:
#   --push     Build, push to registry, then deploy on VM
#   --vm-only  Skip build/push, just deploy pre-built images on VM
#   (default)  Build and deploy to VM directly (no push)
# =============================================================================

set -euo pipefail

# ── Configuration ───────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VM_HOST="${IACGENIE_VM_HOST:-mkanavi@192.168.0.118}"
VM_SSH_KEY="${IACGENIE_VM_SSH_KEY:-}"
IMAGE_TAG="${IACGENIE_IMAGE_TAG:-latest}"

FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_DIR="$PROJECT_ROOT/backend"

IMAGE_FRONTEND="iacgenie-frontend:${IMAGE_TAG}"
IMAGE_BACKEND="iacgenie-backend:${IMAGE_TAG}"

# ── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}   $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}   $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}   $*" && exit 1; }
step()  { echo -e "${BLUE}[STEP]${NC}   $*"; }

# ── Parse arguments ─────────────────────────────────────────────────────────
MODE="build-deploy"
for arg in "$@"; do
    case $arg in
        --push)    MODE="push-deploy";;
        --vm-only) MODE="vm-only";;
        *)         echo "Unknown option: $arg"; exit 1;;
    esac
done

# ── Prerequisite checks ─────────────────────────────────────────────────────
check_cmd() {
    if ! command -v "$1" &>/dev/null; then
        fail "Required command not found: $1. Please install it."
    fi
}

step "Validating prerequisites..."
check_cmd docker
check_cmd node
check_cmd npm
if [ "$MODE" != "vm-only" ]; then
    check_cmd ssh
    check_cmd scp
fi

info "Docker:  $(docker --version)"
info "Node:    $(node --version)"
info "npm:     $(npm --version)"

# ── SSH helper ──────────────────────────────────────────────────────────────
ssh_cmd() {
    local cmd="$1"
    if [ -n "$VM_SSH_KEY" ]; then
        ssh -i "$VM_SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=30 "$VM_HOST" "$cmd"
    else
        ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 "$VM_HOST" "$cmd"
    fi
}

scp_cmd() {
    if [ -n "$VM_SSH_KEY" ]; then
        scp -i "$VM_SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=30 "$@"
    else
        scp -o StrictHostKeyChecking=no -o ConnectTimeout=30 "$@"
    fi
}

# ── Build Frontend ──────────────────────────────────────────────────────────
build_frontend() {
    step "Building IacGenie frontend..."
    cd "$FRONTEND_DIR"
    
    # Install dependencies
    if [ -f package-lock.json ]; then
        npm ci 2>/dev/null || npm install
    else
        npm install
    fi
    
    # Build
    info "Building Vite app..."
    if [ -f vite.config.ts ]; then
        npx vite build
    elif [ -f vite.config.js ]; then
        npx vite build
    else
        fail "No vite.config.ts or vite.config.js found in frontend/"
    fi
    
    if [ ! -d dist ]; then
        fail "Frontend build failed — dist/ directory not found"
    fi
    
    info "Frontend built successfully → dist/"
    cd "$SCRIPT_DIR"
}

# ── Build Backend ───────────────────────────────────────────────────────────
build_backend() {
    step "Building IacGenie backend..."
    cd "$BACKEND_DIR"
    
    info "Building Docker image: $IMAGE_BACKEND"
    docker build -t "$IMAGE_BACKEND" .
    
    info "Backend image built successfully: $(docker images --format '{{.Size}}' "$IMAGE_BACKEND" | head -1)"
    cd "$SCRIPT_DIR"
}

# ── Push images to registry ─────────────────────────────────────────────────
push_images() {
    step "Pushing images to registry..."
    
    # For GHCR (or any registry — modify as needed)
    local REGISTRY="${REGISTRY:-ghcr.io/manjufkanavi/iacgenie-platform}"
    local FRONTEND_REMOTE="${REGISTRY}/frontend:${IMAGE_TAG}"
    local BACKEND_REMOTE="${REGISTRY}/backend:${IMAGE_TAG}"
    
    # Tag and push frontend
    docker tag "$IMAGE_FRONTEND" "$FRONTEND_REMOTE"
    docker push "$FRONTEND_REMOTE" || warn "Failed to push frontend image"
    
    # Tag and push backend
    docker tag "$IMAGE_BACKEND" "$BACKEND_REMOTE"
    docker push "$BACKEND_REMOTE" || warn "Failed to push backend image"
    
    info "Images pushed to $REGISTRY"
}

# ── Deploy on VM ────────────────────────────────────────────────────────────
deploy_vm() {
    step "Deploying to VM ($VM_HOST)..."
    
    # Create deploy directory on VM
    ssh_cmd "mkdir -p /home/mkanavi/docker/iacgenie/iacgenie-deploy"
    
    # Build context tarballs
    if [ "$MODE" = "vm-only" ]; then
        info "VM-only mode: using existing backend image on VM"
    else
        # Copy frontend build artifacts to VM
        info "Copying frontend build to VM..."
        scp_cmd -r "$FRONTEND_DIR/dist/" "${VM_HOST}:/home/mkanavi/docker/iacgenie/iacgenie-deploy/frontend-dist/"
        
        # Copy Dockerfile to VM
        scp_cmd "$FRONTEND_DIR/Dockerfile" "${VM_HOST}:/home/mkanavi/docker/iacgenie/iacgenie-deploy/frontend-Dockerfile"
        scp_cmd "$FRONTEND_DIR/nginx.conf" "${VM_HOST}:/home/mkanavi/docker/iacgenie/iacgenie-deploy/frontend-nginx.conf"
        
        # Build backend image on VM
        info "Building backend image on VM..."
        scp_cmd -r "$BACKEND_DIR/" "${VM_HOST}:/home/mkanavi/docker/iacgenie/iacgenie-deploy/backend/"
        scp_cmd "$BACKEND_DIR/Dockerfile" "${VM_HOST}:/home/mkanavi/docker/iacgenie/iacgenie-deploy/backend-Dockerfile"
        
        ssh_cmd "cd /home/mkanavi/docker/iacgenie/iacgenie-deploy/backend && \
                  docker build -t $IMAGE_BACKEND . && \
                  rm -rf /home/mkanavi/docker/iacgenie/iacgenie-deploy/backend"
        
        # Build frontend image on VM
        ssh_cmd "cd /home/mkanavi/docker/iacgenie/iacgenie-deploy && \
                  docker build -t $IMAGE_FRONTEND -f frontend-Dockerfile . && \
                  rm -rf /home/mkanavi/docker/iacgenie/iacgenie-deploy"
    fi
    
    # Stop old containers if running
    ssh_cmd "docker stop iacgenie-frontend 2>/dev/null; docker rm iacgenie-frontend 2>/dev/null || true"
    ssh_cmd "docker stop iacgenie-backend 2>/dev/null; docker rm iacgenie-backend 2>/dev/null || true"
    
    # Start IacGenie backend (port 8001)
    info "Starting IacGenie backend on port 8001..."
    ssh_cmd "docker run -d \
        --name iacgenie-backend \
        --restart unless-stopped \
        --network iacgenie_network \
        -p 127.0.0.1:8001:8000 \
        -e DATABASE_PROVIDER=postgres \
        -e POSTGRES_HOST=iacgenie-postgres \
        -e POSTGRES_PORT=5432 \
        -e POSTGRES_DATABASE=iacgenie \
        -e POSTGRES_USER=postgres \
        -e POSTGRES_PASSWORD=\${POSTGRES_SUPER_PASSWORD} \
        -e HOST=0.0.0.0 \
        -e PORT=8000 \
        $IMAGE_BACKEND"
    
    # Start IacGenie frontend (nginx, port 3001)
    info "Starting IacGenie frontend on port 3001..."
    ssh_cmd "docker run -d \
        --name iacgenie-frontend \
        --restart unless-stopped \
        --network iacgenie_network \
        -p 127.0.0.1:3001:80 \
        -e VITE_API_BASE_URL=https://api.iacgenie.com \
        $IMAGE_FRONTEND"
    
    # Wait for containers
    info "Waiting for containers to start..."
    sleep 5
    
    # Check health
    local backend_status=$(ssh_cmd "docker inspect --format='{{.State.Health.Status}}' iacgenie-backend 2>/dev/null || echo 'starting'")
    local frontend_status=$(ssh_cmd "docker inspect --format='{{.State.Status}}' iacgenie-frontend 2>/dev/null || echo 'starting'")
    
    info "Backend: $backend_status"
    info "Frontend: $frontend_status"
    
    # Test connectivity
    info "Testing frontend..."
    local http_code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3001/ 2>/dev/null || echo "000")
    if [ "$http_code" = "200" ]; then
        info "✓ Frontend responding (HTTP $http_code)"
    else
        warn "Frontend HTTP code: $http_code (may need more startup time)"
    fi
    
    info "Testing backend..."
    local api_code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/api/health 2>/dev/null || echo "000")
    if [ "$api_code" = "200" ]; then
        info "✓ Backend responding (HTTP $api_code)"
    else
        warn "Backend HTTP code: $api_code (may need more startup time)"
    fi
    
    info ""
    info "========================================================="
    info "  IacGenie Platform Deployed!"
    info "========================================================="
    info "  Frontend:  http://127.0.0.1:3001 (platform.iacgenie.com)"
    info "  Backend:   http://127.0.0.1:8001 (iacgenie-api.iacgenie.com)"
    info "  Containers: iacgenie-frontend, iacgenie-backend"
    info "  Image Tag:  $IMAGE_TAG"
    info "========================================================="
    echo ""
}

# ── Main ────────────────────────────────────────────────────────────────────
case "$MODE" in
    build-deploy)
        build_frontend
        build_backend
        deploy_vm
        ;;
    push-deploy)
        build_frontend
        build_backend
        push_images
        deploy_vm
        ;;
    vm-only)
        deploy_vm
        ;;
esac
