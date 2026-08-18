#!/bin/bash
# =============================================================================
# run_on_vm.sh — Deploy LightSerp to VM (using existing unified infra)
# =============================================================================
# Usage: ./run_on_vm.sh [deploy|logs|restart|status]
#
# Deploys only the LightSerp app containers to the VM.
# Uses existing unified infrastructure already running:
#   - PostgreSQL (iacgenie-postgres)
#   - Redis (iacgenie-redis)
#   - SearXNG (iacgenie-searxng)
#   - NSQD (iacgenie-nsqd)
#   - MinIO (iacgenie-minio)
#   - Keycloak (iacgenie-keycloak)
#   - OpenBao (iacgenie-openbao)
#
# After deployment:
#   - API:     api.iacgenie.com → port 8000
#   - WebUI:   lightserp.iacgenie.com → port 3070
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

VM_HOST="${LIGHTSERP_VM_HOST:-mkanavi@192.168.0.118}"
IMAGE_TAG="${LIGHTSERP_IMAGE_TAG:-latest}"

IMAGE_API="lightserp-lightserp-api:${IMAGE_TAG}"
IMAGE_WEBUI="lightserp-lightserp-webui:${IMAGE_TAG}"

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
        
        # Verify unified infrastructure is running
        step "Verifying unified infrastructure..."
        infra_ok=$(ssh_cmd "docker ps --format '{{.Names}}' | grep -c -E 'iacgenie-postgres|iacgenie-redis|iacgenie-searxng' || true")
        if [ "$infra_ok" -lt 3 ]; then
            fail "Unified infrastructure not running. Run deploy-unified.sh first."
        fi
        info "✓ Unified infrastructure running ($infra_ok/3 core services)"
        
        # Build API locally
        step "Building API image..."
        cd "$PROJECT_ROOT"
        docker build -t "$IMAGE_API" -f Dockerfile .
        info "✓ API image built: $(docker images --format '{{.Size}}' "$IMAGE_API" | head -1)"
        
        # Build WebUI locally
        step "Building WebUI image..."
        cd "$PROJECT_ROOT/webui"
        if [ -f package-lock.json ]; then
            npm ci 2>/dev/null || npm install
        else
            npm install
        fi
        npm run build
        docker build -t "$IMAGE_WEBUI" .
        info "✓ WebUI image built: $(docker images --format '{{.Size}}' "$IMAGE_WEBUI" | head -1)"
        
        # Transfer images to VM
        step "Transferring images to VM..."
        local_api_tar="/tmp/lightserp-api-${IMAGE_TAG}.tar"
        local_webui_tar="/tmp/lightserp-webui-${IMAGE_TAG}.tar"
        
        docker save "$IMAGE_API" -o "$local_api_tar"
        docker save "$IMAGE_WEBUI" -o "$local_webui_tar"
        
        scp_cmd "$local_api_tar" "${VM_HOST}:/tmp/"
        scp_cmd "$local_webui_tar" "${VM_HOST}:/tmp/"
        
        ssh_cmd "docker load -i /tmp/lightserp-api-${IMAGE_TAG}.tar && rm -f /tmp/lightserp-api-${IMAGE_TAG}.tar"
        ssh_cmd "docker load -i /tmp/lightserp-webui-${IMAGE_TAG}.tar && rm -f /tmp/lightserp-webui-${IMAGE_TAG}.tar"
        
        # Stop old containers
        step "Stopping old containers..."
        ssh_cmd "docker stop iacgenie_lightserp_webui 2>/dev/null; docker rm iacgenie_lightserp_webui 2>/dev/null || true"
        ssh_cmd "docker stop iacgenie_lightserp_api 2>/dev/null; docker rm iacgenie_lightserp_api 2>/dev/null || true"
        
        # Start API on port 8000
        step "Starting LightSerp API on port 8000..."
        ssh_cmd "docker run -d \
            --name iacgenie_lightserp_api \
            --restart unless-stopped \
            --network iacgenie_network \
            -p 127.0.0.1:8000:3071 \
            --env-file /home/mkanavi/docker/iacgenie/.env \
            $IMAGE_API"
        
        # Start WebUI on port 3070 (NOT 3001!)
        step "Starting LightSerp WebUI on port 3070..."
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
        
        # Wait and verify
        sleep 8
        step "Verifying deployment..."
        
        local api_code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/ 2>/dev/null || echo "000")
        local web_code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3070/ 2>/dev/null || echo "000")
        
        if [ "$api_code" != "000" ]; then
            info "✓ API responding (HTTP $api_code)"
        else
            warn "API not yet responding (HTTP $api_code) — still starting"
        fi
        
        if [ "$web_code" = "200" ]; then
            info "✓ WebUI responding (HTTP $web_code)"
        else
            warn "WebUI not yet responding (HTTP $web_code) — still starting"
        fi
        
        info ""
        info "========================================================="
        info "  LightSerp deployed to VM!"
        info "========================================================="
        info "  API:     api.iacgenie.com → :8000"
        info "  WebUI:   lightserp.iacgenie.com → :3070"
        info "  Logs:      ./run_on_vm.sh logs"
        info "  Status:    ./run_on_vm.sh status"
        info "========================================================="
        ;;
    
    logs)
        ssh_cmd "docker logs -f iacgenie_lightserp_api"
        ;;
    
    restart)
        ssh_cmd "docker restart iacgenie_lightserp_api iacgenie_lightserp_webui"
        info "Restarted both containers"
        ;;
    
    status)
        echo "=== LightSerp Containers ==="
        ssh_cmd "docker ps --filter 'name=iacgenie_lightserp' --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
        echo ""
        echo "=== Health Checks ==="
        local api_code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/ 2>/dev/null || echo "000")
        local web_code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3070/ 2>/dev/null || echo "000")
        info "API:     HTTP $api_code (port 8000)"
        info "WebUI:   HTTP $web_code (port 3070)"
        ;;
    
    *)
        echo "Usage: $0 [deploy|logs|restart|status]"
        exit 1
        ;;
esac
