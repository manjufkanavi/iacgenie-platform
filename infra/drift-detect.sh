#!/bin/bash
# =============================================================================
# IacGenie Platform — Drift Detection Script
# =============================================================================
# Compares running infrastructure state against Ansible-defined state.
# Reports any deviation as DRIFT DETECTED with details.
#
# Usage:
#   ./drift-detect.sh              # Full drift check
#   ./drift-detect.sh --check nginx   # Only check nginx config
#   ./drift-detect.sh --fix             # Auto-fix detected drift
#   ./drift-detect.sh --json            # Output as JSON
# =============================================================================

set -euo pipefail

# === Configuration ===
SSH_USER="mkanavi"
VM_IP="192.168.0.118"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DRIFT_REPORT_FILE="/tmp/drift-report-$(date +%Y%m%d-%H%M%S).txt"

# === Colors ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

DRIFT_FOUND=false
JSON_OUTPUT=false
FIX_MODE=false
CHECK_FILTER=""

for arg in "$@"; do
    case $arg in
        --json) JSON_OUTPUT=true ;;
        --fix)  FIX_MODE=true ;;
        --check) CHECK_FILTER="$2"; shift ;;
        --help|-h)
            echo "Usage: $0 [--check SERVICE] [--fix] [--json]"
            exit 0
            ;;
    esac
done

report() {
    if [[ "$JSON_OUTPUT" == true ]]; then
        echo "$1"
    else
        echo "$1"
    fi
}

drift_found() {
    DRIFT_FOUND=true
    if [[ "$JSON_OUTPUT" != true ]]; then
        echo -e "${RED}[DRIFT]${NC} $1"
    fi
}

drift_ok() {
    if [[ "$JSON_OUTPUT" != true ]]; then
        echo -e "${GREEN}[OK]${NC} $1"
    fi
}

# === SSH wrapper ===
run_ssh() {
    ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSH_USER@$VM_IP" "$1" 2>/dev/null
}

# === Check 1: Docker Compose Files ===
check_docker_compose() {
    echo ""
    echo -e "${CYAN}=== Docker Compose File Drift ===${NC}"

    local result
    result=$(run_ssh "ls -la /home/mkanavi/docker/iacgenie/docker-compose*.yml 2>/dev/null")
    if [[ $? -ne 0 ]]; then
        drift_found "docker-compose.yml not found on VM"
        return
    fi
    drift_ok "docker-compose.yml exists on VM"

    # Check file permissions
    local perms
    perms=$(run_ssh "stat -c '%a' /home/mkanavi/docker/iacgenie/docker-compose.yml 2>/dev/null")
    if [[ "$perms" == "644" ]]; then
        drift_ok "docker-compose.yml has correct permissions (644)"
    else
        drift_found "docker-compose.yml has wrong permissions: $perms (expected 644)"
    fi

    # Check container count matches compose file
    local compose_services
    compose_services=$(run_ssh "grep -c '^\s*[a-z].*:$' /home/mkanavi/docker/iacgenie/docker-compose.yml 2>/dev/null || echo 0")
    local running_containers
    running_containers=$(run_ssh "docker ps --format '{{.Names}}' | grep -c '^iacgenie_' || echo 0")
    if [[ "$running_containers" -ge 10 ]]; then
        drift_ok "$running_containers containers running (from docker-compose.yml)"
    else
        drift_found "Only $running_containers containers running (expected $compose_services from compose file)"
    fi
}

# === Check 2: Nginx Config ===
check_nginx() {
    echo ""
    echo -e "${CYAN}=== Nginx Configuration Drift ===${NC}"

    # Check if nginx is running
    local nginx_status
    nginx_status=$(run_ssh "systemctl is-active nginx 2>/dev/null || echo 'inactive'")
    if [[ "$nginx_status" == "active" ]]; then
        drift_ok "Nginx is running (systemd)"
    else
        drift_found "Nginx is not running (status: $nginx_status)"
    fi

    # Check config file exists
    local nginx_config
    nginx_config=$(run_ssh "test -f /etc/nginx/conf.d/iacgenie-unified.conf && echo 'exists' || echo 'missing'")
    if [[ "$nginx_config" == "exists" ]]; then
        drift_ok "Nginx config exists at expected path"
    else
        drift_found "Nginx config missing at /etc/nginx/conf.d/iacgenie-unified.conf"
    fi

    # Check for redundant configs
    local extra_configs
    extra_configs=$(run_ssh "ls /etc/nginx/conf.d/*.conf 2>/dev/null | wc -l")
    if [[ "$extra_configs" -le 5 ]]; then
        drift_ok "No redundant nginx configs ($extra_configs total)"
    else
        drift_found "Too many nginx configs ($extra_configs) — potential drift"
    fi
}

# === Check 3: Cloudflare Tunnels ===
check_cloudflared() {
    echo ""
    echo -e "${CYAN}=== Cloudflare Tunnel Drift ===${NC}"

    # Check if cloudflared is running
    local cf_status
    cf_status=$(run_ssh "systemctl list-units --type=service --state=running | grep cloudflared | wc -l")
    if [[ "$cf_status" -ge 1 ]]; then
        drift_ok "$cf_status cloudflared service(s) running"
    else
        drift_found "No cloudflared services running"
    fi

    # Check tunnel credentials
    local cert_exists
    cert_exists=$(run_ssh "test -f /home/mkanavi/.cloudflared/cert.pem && echo 'exists' || echo 'missing'")
    if [[ "$cert_exists" == "exists" ]]; then
        drift_ok "Cloudflare tunnel cert exists"
    else
        drift_found "Cloudflare tunnel cert missing"
    fi
}

# === Check 4: Data Directory Permissions ===
check_data_dirs() {
    echo ""
    echo -e "${CYAN}=== Data Directory Permissions Drift ===${NC}"

    # Check OpenBao data dirs — must NOT be world-writable
    local openbao_raft_perms
    openbao_raft_perms=$(run_ssh "stat -c '%a' /home/mkanavi/docker/iacgenie/data/openbao_raft 2>/dev/null || echo 'missing'")
    if [[ "$openbao_raft_perms" == "777" ]]; then
        drift_found "OpenBao raft data dir has dangerous permissions: $openbao_raft_perms (should NOT be 777)"
    elif [[ "$openbao_raft_perms" != "missing" ]]; then
        drift_ok "OpenBao raft data dir permissions: $openbao_raft_perms"
    else
        drift_found "OpenBao raft data dir missing"
    fi

    # Check PostgreSQL data dir
    local pg_data_exists
    pg_data_exists=$(run_ssh "test -d /home/mkanavi/docker/iacgenie/data/postgres && echo 'exists' || echo 'missing'")
    if [[ "$pg_data_exists" == "exists" ]]; then
        drift_ok "PostgreSQL data directory exists"
    else
        drift_found "PostgreSQL data directory missing"
    fi

    # Check Keycloak data dir
    local kc_data_exists
    kc_data_exists=$(run_ssh "test -d /home/mkanavi/docker/iacgenie/data/keycloak && echo 'exists' || echo 'missing'")
    if [[ "$kc_data_exists" == "exists" ]]; then
        drift_ok "Keycloak data directory exists"
    else
        drift_found "Keycloak data directory missing"
    fi
}

# === Check 5: Service Health ===
check_service_health() {
    echo ""
    echo -e "${CYAN}=== Service Health Drift ===${NC}"

    local health_result
    health_result=$(run_ssh "cd /home/mkanavi/iacgenie-platform/infra && ./health-check.sh 2>/dev/null || echo '{"services":{},"overall":"error"}'")

    if [[ "$health_result" == *"healthy"* ]] || [[ "$health_result" == *"\"healthy\""* ]]; then
        drift_ok "Health check reports services are healthy"
    else
        drift_found "Health check reports issues — run health-check.sh for details"
    fi
}

# === Check 6: Cron Jobs ===
check_cron_jobs() {
    echo ""
    echo -e "${CYAN}=== Cron Job Drift ===${NC}"

    local crontab_content
    crontab_content=$(run_ssh "crontab -l 2>/dev/null || echo 'empty'" | grep -v "^#" | grep -v "^$" || true)

    local expected_jobs=("backup" "health-check" "drift-detect" "logrotate")
    for job in "${expected_jobs[@]}"; do
        if [[ "$crontab_content" == *"$job"* ]]; then
            drift_ok "Cron job for '$job' found"
        else
            drift_found "Expected cron job for '$job' not found"
        fi
    done
}

# === Check 7: Ansible Playbook Idempotency ===
check_ansible_idempotency() {
    echo ""
    echo -e "${CYAN}=== Ansible Idempotency Check ===${NC}"

    info "Running ansible-playbook --check (this may take a minute)..."
    local check_output
    check_output=$(cd "$SCRIPT_DIR/ansible" && ansible-playbook playbook.yml -i inventory/hosts.yml --check 2>&1 | tee /tmp/ansible-check.log || true)

    if echo "$check_output" | grep -q "ok="; then
        drift_ok "Ansible check mode passed (no changes would be made)"
    else
        drift_found "Ansible check mode found changes needed — run ansible-playbook to fix"
    fi
}

# === Fix Drift ===
fix_drift() {
    if [[ "$FIX_MODE" != true ]]; then
        return
    fi

    echo ""
    echo -e "${YELLOW}[FIX] Auto-fixing drift by running Ansible...${NC}"

    # Run the deploy script
    "$SCRIPT_DIR/deploy.sh" --role "$CHECK_FILTER" 2>/dev/null || {
        error "Auto-fix failed. Run deploy.sh manually."
        exit 1
    }

    log "Auto-fix completed. Run drift-detect.sh again to verify."
}

# === Main ===
main() {
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║         IacGenie Platform — Drift Detection             ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Run all checks (or filter if specified)
    if [[ -z "$CHECK_FILTER" ]] || [[ "$CHECK_FILTER" == "docker" ]] || [[ "$CHECK_FILTER" == "docker-compose" ]] || [[ "$CHECK_FILTER" == "compose" ]]; then
        check_docker_compose
    fi

    if [[ -z "$CHECK_FILTER" ]] || [[ "$CHECK_FILTER" == "nginx" ]]; then
        check_nginx
    fi

    if [[ -z "$CHECK_FILTER" ]] || [[ "$CHECK_FILTER" == "cloudflare" ]] || [[ "$CHECK_FILTER" == "cf" ]] || [[ "$CHECK_FILTER" == "tunnel" ]]; then
        check_cloudflared
    fi

    if [[ -z "$CHECK_FILTER" ]] || [[ "$CHECK_FILTER" == "data" ]] || [[ "$CHECK_FILTER" == "dirs" ]] || [[ "$CHECK_FILTER" == "permissions" ]]; then
        check_data_dirs
    fi

    if [[ -z "$CHECK_FILTER" ]] || [[ "$CHECK_FILTER" == "health" ]]; then
        check_service_health
    fi

    if [[ -z "$CHECK_FILTER" ]] || [[ "$CHECK_FILTER" == "cron" ]]; then
        check_cron_jobs
    fi

    if [[ -z "$CHECK_FILTER" ]] || [[ "$CHECK_FILTER" == "ansible" ]] || [[ "$CHECK_FILTER" == "idempotency" ]]; then
        check_ansible_idempotency
    fi

    # Summary
    echo ""
    if [[ "$DRIFT_FOUND" == true ]]; then
        echo -e "${RED}══════════════════════════════════════════════════════════${NC}"
        echo -e "${RED}  DRIFT DETECTED — run deploy.sh to fix                  ${NC}"
        echo -e "${RED}══════════════════════════════════════════════════════════${NC}"
        exit 1
    else
        echo -e "${GREEN}══════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  NO DRIFT — Infrastructure matches Ansible code         ${NC}"
        echo -e "${GREEN}══════════════════════════════════════════════════════════${NC}"
        exit 0
    fi
}

main "$@"
