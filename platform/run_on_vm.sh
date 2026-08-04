#!/bin/bash
# =============================================================================
# run_on_vm.sh — Deploy IacGenie Platform to VM (using existing infra)
# =============================================================================
# Usage: ./run_on_vm.sh [deploy|logs|restart|status]
#
# Deploys only the IacGenie app containers to the VM.
# Uses existing infrastructure services already running on VM:
#   - PostgreSQL (iacgenie-postgres)
#   - Redis (iacgenie-redis)
#   - Keycloak (iacgenie-keycloak)
#   - MinIO (iacgenie-minio)
#   - OpenBao (iacgenie-openbao)
#   - SearXNG (iacgenie-searxng)
#   - NSQD (iacgenie-nsqd)
#
# After deployment:
#   - Frontend: platform.iacgenie.com → port 3001
#   - Backend:  api.iacgenie.com → port 8001
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

VM_HOST="${IACGENIE_VM_HOST:-mkanavi@192.168.0.118}"
IMAGE_TAG="${IACGENIE_IMAGE_TAG:-latest}"

IMAGE_FRONTEND="iacgenie-frontend:${IMAGE_TAG}"
IMAGE_BACKEND="iacgenie-backend:${IMAGE_TAG}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}   $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}   $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}   $*" && exit 1; }
step()  { echo -e "${BLUE}[STEP]${NC}   $*"; }

ssh_cmd() {
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 "$VM_HOST" "$1"
}

scp_cmd() {
    scp -o StrictHostKeyChecking=no -o ConnectTimeout=30 "$@"
}

case "${1:-deploy}" in
    deploy)
        step "Checking prerequisites..."
        
        # Verify VM is reachable
        if ! ssh_cmd "echo 'connected'" &>/dev/null; then
            fail "Cannot reach VM at $VM_HOST. Check SSH config."
        fi
        info "✓ VM reachable at $VM_HOST"
        
        # Verify infrastructure is running
        step "Verifying infrastructure services..."
        infra_ok=$(ssh_cmd "docker ps --format '{{.Names}}' | grep -c -E 'iacgenie-postgres|iacgenie-redis|iacgenie-keycloak' || true")
        if [ "$infra_ok" -lt 3 ]; then
            warn "Some infrastructure services may be down. Run deploy-unified.sh first."
        else
            info "✓ Infrastructure services running ($infra_ok/3 core services)"
        fi
        
        # Build backend on local machine (has Docker)
        step "Building backend image..."
        cd "$PROJECT_ROOT/backend"
        docker build -t "$IMAGE_BACKEND" .
        info "✓ Backend image built: $(docker images --format '{{.Size}}' "$IMAGE_BACKEND" | head -1)"
        
        # Build frontend locally
        step "Building frontend image..."
        cd "$PROJECT_ROOT/frontend"
        
        # Install deps and build
        if [ -f package-lock.json ]; then
            npm ci 2>/dev/null || npm install
        else
            npm install
        fi
        npx vite build
        docker build -t "$IMAGE_FRONTEND" .
        info "✓ Frontend image built: $(docker images --format '{{.Size}}' "$IMAGE_FRONTEND" | head -1)"
        
        # Push images to VM via docker import (simplest method)
        step "Deploying images to VM..."
        
        # Save images as tarballs and transfer
        local_backend_tar="/tmp/iacgenie-backend-${IMAGE_TAG}.tar"
        local_frontend_tar="/tmp/iacgenie-frontend-${IMAGE_TAG}.tar"
        
        docker save "$IMAGE_BACKEND" -o "$local_backend_tar"
        docker save "$IMAGE_FRONTEND" -o "$local_frontend_tar"
        
        scp_cmd "$local_backend_tar" "${VM_HOST}:/tmp/"
        scp_cmd "$local_frontend_tar" "${VM_HOST}:/tmp/"
        
        # Load images on VM
        ssh_cmd "docker load -i /tmp/iacgenie-backend-${IMAGE_TAG}.tar && rm -f /tmp/iacgenie-backend-${IMAGE_TAG}.tar"
        ssh_cmd "docker load -i /tmp/iacgenie-frontend-${IMAGE_TAG}.tar && rm -f /tmp/iacgenie-frontend-${IMAGE_TAG}.tar"
        
        # Stop old containers
        ssh_cmd "docker stop iacgenie-frontend 2>/dev/null; docker rm iacgenie-frontend 2>/dev/null || true"
        ssh_cmd "docker stop iacgenie-backend 2>/dev/null; docker rm iacgenie-backend 2>/dev/null || true"
        
        # Start backend
        step "Starting IacGenie backend..."
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
            -e POSTGRES_PASSWORD=\${PO...ORD} \
            -e HOST=0.0.0.0 \
            -e PORT=8000 \
            $IMAGE_BACKEND"
        
        # Start frontend
        step "Starting IacGenie frontend..."
        ssh_cmd "docker run -d \
            --name iacgenie-frontend \
            --restart unless-stopped \
            --network iacgenie_network \
            -p 127.0.0.1:3001:80 \
            $IMAGE_FRONTEND"
        
        # Wait and verify
        sleep 8
        step "Verifying deployment..."
        
        local api_code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/api/health 2>/dev/null || echo "000")
        local web_code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3001/ 2>/dev/null || echo "000")
        
        if [ "$api_code" != "000" ]; then
            info "✓ Backend healthy (HTTP $api_code)"
        else
            warn "Backend not yet responding (HTTP $api_code) — still starting"
        fi
        
        if [ "$web_code" = "200" ]; then
            info "✓ Frontend healthy (HTTP $web_code)"
        else
            warn "Frontend not yet responding (HTTP $web_code) — still starting"
        fi
        
        info ""
        info "========================================================="
        info "  IacGenie Platform deployed to VM!"
        info "========================================================="
        info "  Frontend: platform.iacgenie.com → :3001"
        info "  Backend:  api.iacgenie.com → :8001"
        info "  View logs: ./run_on_vm.sh logs"
        info "  Check status: ./run_on_vm.sh status"
        info "========================================================="
        ;;
    
    logs)
        ssh_cmd "docker logs -f iacgenie-backend"
        ;;
    
    restart)
        ssh_cmd "docker restart iacgenie-backend iacgenie-frontend"
        info "Restarted both containers"
        ;;
    
    status)
        echo "=== Docker Containers ==="
        ssh_cmd "docker ps --filter 'name=iacgenie-(frontend|backend)' --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
        echo ""
        echo "=== Health Checks ==="
        local api_code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/api/health 2>/dev/null || echo "000")
        local web_code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3001/ 2>/dev/null || echo "000")
        info "Backend API: HTTP $api_code"
        info "Frontend:    HTTP $web_code"
        ;;
    
    *)
        echo "Usage: $0 [deploy|logs|restart|status]"
        exit 1
        ;;
esac
