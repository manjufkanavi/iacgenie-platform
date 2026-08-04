#!/bin/bash
# =============================================================================
# deploy_lightserp.sh — Build & Deploy LightSerp
# =============================================================================
# Usage: ./deploy_lightserp.sh [--push|--vm-only]
#
# This script:
#   1. Validates prerequisites (Node.js, Docker, SSH)
#   2. Builds LightSerp API and WebUI Docker images
#   3. Pushes images to registry OR deploys directly to VM
#   4. Deploys both containers on the VM
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
VM_HOST="${LIGHTSERP_VM_HOST:-mkanavi@192.168.0.118}"
VM_SSH_KEY="${LIGHTSERP_VM_SSH_KEY:-}"
IMAGE_TAG="${LIGHTSERP_IMAGE_TAG:-latest}"

LIGHTSERP_DIR="$PROJECT_ROOT"
WEBUI_DIR="$PROJECT_ROOT/webui"

IMAGE_API="lightserp-lightserp-api:${IMAGE_TAG}"
IMAGE_WEBUI="lightserp-lightserp-webui:${IMAGE_TAG}"

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
    if [ -n "$VM_SSH_KEY" ]; then
        ssh -i "$VM_SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=30 "$VM_HOST" "$1"
    else
        ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 "$VM_HOST" "$1"
    fi
}

scp_cmd() {
    if [ -n "$VM_SSH_KEY" ]; then
        scp -i "$VM_SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=30 "$@"
    else
        scp -o StrictHostKeyChecking=no -o ConnectTimeout=30 "$@"
    fi
}

# ── Build API ───────────────────────────────────────────────────────────────
build_api() {
    step "Building LightSerp API..."
    cd "$LIGHTSERP_DIR"
    
    info "Building Docker image: $IMAGE_API"
    docker build -t "$IMAGE_API" -f Dockerfile .
    
    info "API image built successfully: $(docker images --format '{{.Size}}' "$IMAGE_API" | head -1)"
}

# ── Build WebUI ─────────────────────────────────────────────────────────────
build_webui() {
    step "Building LightSerp WebUI..."
    cd "$WEBUI_DIR"
    
    # Install dependencies
    if [ -f package-lock.json ]; then
        npm ci 2>/dev/null || npm install
    else
        npm install
    fi
    
    info "Building Next.js app..."
    npm run build
    
    if [ ! -d ".next/standalone" ]; then
        # Try without standalone if config doesn't support it
        info "No standalone output, building without..."
        npm run build:standalone 2>/dev/null || npm run build
    fi
    
    if [ ! -d ".next" ]; then
        fail "WebUI build failed — .next/ directory not found"
    fi
    
    info "WebUI built successfully → .next/"
    
    # Build Docker image
    info "Building Docker image: $IMAGE_WEBUI"
    docker build -t "$IMAGE_WEBUI" .
    
    info "WebUI image built successfully: $(docker images --format '{{.Size}}' "$IMAGE_WEBUI" | head -1)"
}

# ── Push images to registry ─────────────────────────────────────────────────
push_images() {
    step "Pushing images to registry..."
    
    local REGISTRY="${REGISTRY:-ghcr.io/manjufkanavi/iacgenie-platform}"
    
    docker tag "$IMAGE_API" "${REGISTRY}/api:${IMAGE_TAG}"
    docker push "${REGISTRY}/api:${IMAGE_TAG}" || warn "Failed to push API image"
    
    docker tag "$IMAGE_WEBUI" "${REGISTRY}/webui:${IMAGE_TAG}"
    docker push "${REGISTRY}/webui:${IMAGE_TAG}" || warn "Failed to push WebUI image"
    
    info "Images pushed to $REGISTRY"
}

# ── Deploy on VM ────────────────────────────────────────────────────────────
deploy_vm() {
    step "Deploying to VM ($VM_HOST)..."
    
    # Stop old containers
    info "Stopping existing LightSerp containers..."
    ssh_cmd "docker stop iacgenie_lightserp_webui 2>/dev/null; docker rm iacgenie_lightserp_webui 2>/dev/null || true"
    ssh_cmd "docker stop iacgenie_lightserp_api 2>/dev/null; docker rm iacgenie_lightserp_api 2>/dev/null || true"
    
    # Copy files to VM for building
    if [ "$MODE" = "vm-only" ]; then
        info "VM-only mode: images already on VM"
    else
        # Create deploy directory on VM
        ssh_cmd "mkdir -p /home/mkanavi/docker/iacgenie/lightsrp-deploy/webui /home/mkanavi/docker/iacgenie/lightsrp-deploy/api"
        
        # Copy WebUI source
        info "Copying WebUI source to VM..."
        scp_cmd -r "$WEBUI_DIR/." "${VM_HOST}:/home/mkanavi/docker/iacgenie/lightsrp-deploy/webui/"
        scp_cmd "$WEBUI_DIR/Dockerfile" "${VM_HOST}:/home/mkanavi/docker/iacgenie/lightsrp-deploy/webui-Dockerfile"
        
        # Copy API source
        info "Copying API source to VM..."
        scp_cmd -r "$LIGHTSERP_DIR/src/" "${VM_HOST}:/home/mkanavi/docker/iacgenie/lightsrp-deploy/api/src/"
        scp_cmd "$LIGHTSERP_DIR/Dockerfile" "${VM_HOST}:/home/mkanavi/docker/iacgenie/lightsrp-deploy/api-Dockerfile"
        scp_cmd -r "$LIGHTSERP_DIR/config/" "${VM_HOST}:/home/mkanavi/docker/iacgenie/lightsrp-deploy/api/config/" 2>/dev/null || true
        scp_cmd "$LIGHTSERP_DIR/package.json" "${VM_HOST}:/home/mkanavi/docker/iacgenie/lightsrp-deploy/api-package.json"
        scp_cmd "$LIGHTSERP_DIR/package-lock.json" "${VM_HOST}:/home/mkanavi/docker/iacgenie/lightsrp-deploy/api-package-lock.json" 2>/dev/null || true
        
        # Build API on VM
        info "Building API image on VM..."
        ssh_cmd "cd /home/mkanavi/docker/iacgenie/lightsrp-deploy/api && \
                  cp /home/mkanavi/docker/iacgenie/lightsrp-deploy/api-package.json . && \
                  cp /home/mkanavi/docker/iacgenie/lightsrp-deploy/api-package-lock.json . 2>/dev/null || true && \
                  cp /home/mkanavi/docker/iacgenie/lightsrp-deploy/api-Dockerfile Dockerfile && \
                  docker build -t $IMAGE_API . && \
                  rm -rf /home/mkanavi/docker/iacgenie/lightsrp-deploy/api"
        
        # Build WebUI on VM
        info "Building WebUI image on VM..."
        ssh_cmd "cd /home/mkanavi/docker/iacgenie/lightsrp-deploy/webui && \
                  cp /home/mkanavi/docker/iacgenie/lightsrp-deploy/webui-Dockerfile Dockerfile && \
                  docker build -t $IMAGE_WEBUI . && \
                  rm -rf /home/mkanavi/docker/iacgenie/lightsrp-deploy/webui"
        
        # Cleanup
        ssh_cmd "rm -f /home/mkanavi/docker/iacgenie/lightsrp-deploy/*-Dockerfile /home/mkanavi/docker/iacgenie/lightsrp-deploy/*-package*.json"
    fi
    
    # Start LightSerp API on port 8000 (unchanged)
    info "Starting LightSerp API on port 8000..."
    ssh_cmd "docker run -d \
        --name iacgenie_lightserp_api \
        --restart unless-stopped \
        --network iacgenie_network \
        -p 127.0.0.1:8000:3071 \
        --env-file /home/mkanavi/docker/iacgenie/.env \
        $IMAGE_API"
    
    # Start LightSerp WebUI on port 3070 (FIXED — was mapped to 3001)
    info "Starting LightSerp WebUI on port 3070..."
    ssh_cmd "docker run -d \
        --name iacgenie_lightserp_webui \
        --restart unless-stopped \
        --network iacgenie_network \
        -p 127.0.0.1:3070:3070 \
        -e NODE_ENV=production \
        -e PORT=3070 \
        -e API_URL=http://iacgenie_lightserp_api:3071 \
        -e NEXT_PUBLIC_API_URL=https://lightserp.iacgenie.com \
        $IMAGE_WEBUI"
    
    # Wait for containers
    info "Waiting for containers to start..."
    sleep 8
    
    # Check health
    local api_status=$(ssh_cmd "docker inspect --format='{{.State.Status}}' iacgenie_lightserp_api 2>/dev/null || echo 'unknown'")
    local webui_status=$(ssh_cmd "docker inspect --format='{{.State.Status}}' iacgenie_lightserp_webui 2>/dev/null || echo 'unknown'")
    
    info "API: $api_status"
    info "WebUI: $webui_status"
    
    # Test connectivity
    info "Testing API..."
    local api_code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/ 2>/dev/null || echo "000")
    if [ "$api_code" != "000" ]; then
        info "✓ API responding (HTTP $api_code)"
    else
        warn "API HTTP code: $api_code (may need more startup time)"
    fi
    
    info "Testing WebUI..."
    local webui_code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3070/ 2>/dev/null || echo "000")
    if [ "$webui_code" = "200" ]; then
        info "✓ WebUI responding (HTTP $webui_code)"
    else
        warn "WebUI HTTP code: $webui_code (may need more startup time)"
    fi
    
    info ""
    info "========================================================="
    info "  LightSerp Deployed!"
    info "========================================================="
    info "  API:     http://127.0.0.1:8000 (api.iacgenie.com)"
    info "  WebUI:   http://127.0.0.1:3070 (lightserp.iacgenie.com)"
    info "  Containers: iacgenie_lightserp_api, iacgenie_lightserp_webui"
    info "  Image Tag:  $IMAGE_TAG"
    info "========================================================="
    echo ""
}

# ── Main ────────────────────────────────────────────────────────────────────
case "$MODE" in
    build-deploy)
        build_api
        build_webui
        deploy_vm
        ;;
    push-deploy)
        build_api
        build_webui
        push_images
        deploy_vm
        ;;
    vm-only)
        deploy_vm
        ;;
esac
