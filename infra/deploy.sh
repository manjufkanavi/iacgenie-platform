#!/bin/bash
# =============================================================================
# IacGenie Platform — Ansible Deployment Script
# =============================================================================
# Usage:
#   ./deploy.sh              # Full deployment
#   ./deploy.sh --check      # Dry run (check mode)
#   ./deploy.sh --diff       # Dry run with diffs
#   ./deploy.sh --role X     # Deploy only specific role
#   ./deploy.sh --services   # Only start/stop docker services
# =============================================================================

set -euo pipefail

# === Configuration ===
ANSIBLE_DIR="$(cd "$(dirname "$0")" && pwd)/ansible"
PLAYBOOK="$ANSIBLE_DIR/playbook.yml"
INVENTORY="$ANSIBLE_DIR/inventory/hosts.yml"
SSH_USER="mkanavi"
VM_IP="192.168.0.118"
REMOTE_SCRIPT_DIR="/home/mkanavi/iacgenie-platform/infra"

# === Colors ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[DEPLOY]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
info() { echo -e "${CYAN}[INFO]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# === Parse Arguments ===
CHECK_MODE=false
DIFF_MODE=false
SINGLE_ROLE=""
DEPLOY_SERVICES_ONLY=false

for arg in "$@"; do
    case $arg in
        --check)    CHECK_MODE=true ;;
        --diff)     CHECK_MODE=true; DIFF_MODE=true ;;
        --role)     SINGLE_ROLE="$2"; shift ;;
        --services) DEPLOY_SERVICES_ONLY=true ;;
        --help|-h)
            echo "Usage: $0 [--check] [--diff] [--role ROLE_NAME] [--services] [--help]"
            exit 0
            ;;
        *) error "Unknown argument: $arg"; exit 1 ;;
    esac
done

# === Pre-flight Checks ===
preflight() {
    info "Running pre-flight checks..."

    # Check Ansible is installed
    if ! command -v ansible-playbook &>/dev/null; then
        error "ansible-playbook not found. Install with: brew install ansible"
        exit 1
    fi

    # Check playbook exists
    if [[ ! -f "$PLAYBOOK" ]]; then
        error "Playbook not found: $PLAYBOOK"
        exit 1
    fi

    # Check inventory
    if [[ ! -f "$INVENTORY" ]]; then
        error "Inventory not found: $INVENTORY"
        exit 1
    fi

    # Check SSH connectivity
    if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$SSH_USER@$VM_IP" "echo ok" &>/dev/null; then
        error "Cannot reach VM at $VM_IP via SSH"
        exit 1
    fi

    info "Pre-flight checks passed"
}

# === Run Ansible Playbook ===
run_ansible() {
    info "Running Ansible deployment..."

    local args=()
    args+=("playbook.yml" "-i" "$INVENTORY")

    if [[ "$CHECK_MODE" == true ]]; then
        args+=("--check")
        if [[ "$DIFF_MODE" == true ]]; then
            args+=("--diff")
        fi
        info "Running in check mode (no changes will be made)"
    fi

    if [[ -n "$SINGLE_ROLE" ]]; then
        args+=("--tags" "$SINGLE_ROLE")
        info "Deploying only role: $SINGLE_ROLE"
    fi

    ansible-playbook "${args[@]}" --vault-password-file ~/.ansible_vault_password 2>&1

    if [[ $? -ne 0 ]]; then
        error "Ansible deployment failed"
        exit 1
    fi

    log "Ansible deployment completed successfully"
}

# === Deploy Services (docker compose) ===
deploy_services() {
    info "Deploying Docker services on VM..."

    ssh "$SSH_USER@$VM_IP" <<'REMOTE_EOF'
set -euo pipefail
cd /home/mkanavi/docker/iacgenie

# Ensure data directories have correct permissions
chmod 777 /home/mkanavi/docker/iacgenie/data/openbao /home/mkanavi/docker/iacgenie/data/openbao_raft 2>/dev/null || true

# Start all services
docker compose up -d

# Show status
echo ""
echo "=== Service Status ==="
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | head -20
REMOTE_EOF

    log "Docker services deployed"
}

# === Wait for Services to be Ready ===
wait_for_services() {
    info "Waiting for services to become healthy..."

    ssh "$SSH_USER@$VM_IP" <<'REMOTE_EOF'
set -euo pipefail
cd /home/mkanavi/iacgenie-platform/infra

# Wait for all services
timeout=300
elapsed=0
while [[ $elapsed -lt $timeout ]]; do
    status=$("./health-check.sh" 2>/dev/null | grep -o '"overall":"[^"]*"' || echo '"overall":"unknown"')
    if [[ "$status" == '"overall":"healthy"' ]]; then
        echo "All services healthy after ${elapsed}s"
        exit 0
    fi
    echo "Services not ready (elapsed: ${elapsed}s)..."
    sleep 10
    elapsed=$((elapsed + 10))
done

echo "TIMEOUT: Services not healthy after ${timeout}s"
exit 1
REMOTE_EOF

    if [[ $? -eq 0 ]]; then
        log "All services are healthy"
    else
        warn "Some services may not be healthy yet. Run health-check.sh for details."
    fi
}

# === Run Health Check ===
health_check() {
    info "Running post-deployment health check..."

    ssh "$SSH_USER@$VM_IP" <<'REMOTE_EOF'
cd /home/mkanavi/iacgenie-platform/infra
./health-check.sh
REMOTE_EOF
}

# === Run Drift Detection ===
drift_detect() {
    info "Running drift detection..."

    ssh "$SSH_USER@$VM_IP" <<'REMOTE_EOF'
cd /home/mkanavi/iacgenie-platform/infra
./drift-detect.sh
REMOTE_EOF
}

# === Main ===
main() {
    log "IacGenie Platform Deployment — $(date '+%Y-%m-%d %H:%M:%S')"
    log "Target: $SSH_USER@$VM_IP"
    echo ""

    if [[ "$DEPLOY_SERVICES_ONLY" == true ]]; then
        deploy_services
        wait_for_services
        return
    fi

    preflight

    if [[ "$CHECK_MODE" == true ]]; then
        # Check mode: just verify what would change
        run_ansible
        info "Check mode complete. Review changes above."
        exit 0
    fi

    run_ansible
    deploy_services
    wait_for_services
    health_check
    drift_detect

    echo ""
    log "=========================================="
    log "Deployment complete! $(date '+%Y-%m-%d %H:%M:%S')"
    log "=========================================="
    echo ""
    echo "Next steps:"
    echo "  - Check services: ssh $SSH_USER@$VM_IP 'docker ps'"
    echo "  - View logs:      ssh $SSH_USER@$VM_IP 'docker logs -f iacgenie_keycloak'"
    echo "  - Health check:   ssh $SSH_USER@$VM_IP '~/iacgenie-platform/infra/health-check.sh'"
}

main "$@"
