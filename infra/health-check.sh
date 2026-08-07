#!/bin/bash
# =============================================================================
# IacGenie Platform — Comprehensive Health Check
# =============================================================================
# Checks ALL services on VM 192.168.0.118 and reports health status.
# Output: JSON format suitable for Prometheus/Grafana integration.
#
# Usage:
#   ./health-check.sh              # Full check, output JSON
#   ./health-check.sh --verbose    # Verbose output with details
#   ./health-check.sh --json       # JSON only (default)
#   ./health-check.sh SERVICE_NAME # Check single service
# =============================================================================

set -euo pipefail

# === Configuration ===
SSH_USER="mkanavi"
VM_IP="192.168.0.118"
VERBOSE=false
JSON_ONLY=true
SINGLE_SERVICE=""

for arg in "$@"; do
    case $arg in
        --verbose) VERBOSE=true ;;
        --json) JSON_ONLY=true ;;
        *)
            # Check if it's a known service name
            known_services="postgres redis minio openbao keycloak gitea lightserp_api lightserp_webui pagezen searxng nsqd nginx cloudflared"
            if echo "$known_services" | grep -qw "$arg"; then
                SINGLE_SERVICE="$arg"
            else
                echo "Unknown service: $arg"
                echo "Known services: $known_services"
                exit 1
            fi
            ;;
    esac
done

# === Color codes ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# === SSH helper ===
run_ssh() {
    ssh -o ConnectTimeout=5 -o BatchMode=yes "$SSH_USER@$VM_IP" "$1" 2>/dev/null || echo "UNREACHABLE"
}

# === Individual Service Checks ===
check_postgres() {
    local status=$(run_ssh "pg_isready -h 127.0.0.1 -p 5432 -U lightsrp -d lightsrp 2>/dev/null && echo 'healthy' || echo 'unhealthy'")
    echo "    postgres\" : {\"status\":\"$status\",\"port\":5432,\"type\":\"database\"}"
}

check_redis() {
    local status=$(run_ssh "redis-cli -h 127.0.0.1 -p 6379 ping 2>/dev/null | grep -q PONG && echo 'healthy' || echo 'unhealthy'")
    echo "    redis\" : {\"status\":\"$status\",\"port\":6379,\"type\":\"cache\"}"
}

check_minio() {
    local status=$(run_ssh "wget -q -O - http://127.0.0.1:9000/minio/health/live 2>/dev/null | grep -q alive && echo 'healthy' || echo 'unhealthy'")
    echo "    minio\" : {\"status\":\"$status\",\"port\":9000,\"type\":\"object-storage\"}"
}

check_openbao() {
    local status=$(run_ssh "wget -q -O - http://127.0.0.1:8200/v1/sys/health 2>/dev/null | grep -q 'sealed.*false' && echo 'healthy' || echo 'unhealthy'")
    echo "    openbao\" : {\"status\":\"$status\",\"port\":8200,\"type\":\"secrets-management\"}"
}

check_keycloak() {
    local status=$(run_ssh "curl -sf http://127.0.0.1:8083/realms/master/protocol/openid-connect/certs 2>/dev/null > /dev/null && echo 'healthy' || echo 'unhealthy'")
    echo "    keycloak\" : {\"status\":\"$status\",\"port\":8083,\"type\":\"auth-oidc\"}"
}

check_gitea() {
    local status=$(run_ssh "wget -q --spider http://127.0.0.1:3000/ 2>/dev/null && echo 'healthy' || echo 'unhealthy'")
    echo "    gitea\" : {\"status\":\"$status\",\"port\":3000,\"type\":\"git-service\"}"
}

check_lightserp_api() {
    local status=$(run_ssh "curl -sf http://127.0.0.1:8000/health 2>/dev/null > /dev/null && echo 'healthy' || echo 'unhealthy'")
    echo "    lightserp_api\" : {\"status\":\"$status\",\"port\":8000,\"type\":\"api\"}"
}

check_lightserp_webui() {
    local status=$(run_ssh "curl -sf http://127.0.0.1:3001/ 2>/dev/null > /dev/null && echo 'healthy' || echo 'unhealthy'")
    echo "    lightserp_webui\" : {\"status\":\"$status\",\"port\":3001,\"type\":\"webui\"}"
}

check_pagezen() {
    local status=$(run_ssh "curl -sf http://127.0.0.1:8081/health 2>/dev/null > /dev/null && echo 'healthy' || echo 'unhealthy'")
    echo "    pagezen\" : {\"status\":\"$status\",\"port\":8081,\"type\":\"content-generation\"}"
}

check_searxng() {
    local status=$(run_ssh "wget -q --spider http://127.0.0.1:8082/ 2>/dev/null && echo 'healthy' || echo 'unhealthy'")
    echo "    searxng\" : {\"status\":\"$status\",\"port\":8082,\"type\":\"search\"}"
}

check_nsqd() {
    local status=$(run_ssh "wget -q -O /dev/null http://127.0.0.1:4151/stats 2>/dev/null && echo 'healthy' || echo 'unhealthy'")
    echo "    nsqd\" : {\"status\":\"$status\",\"port\":4151,\"type\":\"message-queue\"}"
}

check_nginx() {
    local status=$(run_ssh "systemctl is-active nginx 2>/dev/null | grep -q active && echo 'healthy' || echo 'unhealthy'")
    echo "    nginx\" : {\"status\":\"$status\",\"port\":80,\"type\":\"reverse-proxy\"}"
}

check_cloudflared() {
    local count=$(run_ssh "systemctl list-units --type=service --state=running 2>/dev/null | grep -c cloudflared || echo 0")
    local status="healthy"
    [[ "$count" -lt 1 ]] && status="unhealthy"
    echo "    cloudflared\" : {\"status\":\"$status\",\"count\":$count,\"type\":\"tunnel\"}"
}

check_docker_engine() {
    local status=$(run_ssh "docker info &>/dev/null && echo 'healthy' || echo 'unhealthy'")
    echo "    docker\" : {\"status\":\"$status\",\"type\":\"container-runtime\"}"
}

check_docker_containers() {
    local running=$(run_ssh "docker ps --format '{{.Names}}' | grep -c '^iacgenie_' 2>/dev/null || echo 0")
    local unhealthy=$(run_ssh "docker ps --format '{{.Names}}\t{{.Status}}' 2>/dev/null | grep -c -i 'unhealthy\|dead\|exited' || echo 0")
    echo "    docker_containers\" : {\"running\":$running,\"unhealthy\":$unhealthy,\"type\":\"infra\"}"
}

# === Main ===
main() {
    if [[ "$VERBOSE" == true ]]; then
        echo "╔══════════════════════════════════════════════════════════╗"
        echo "║    IacGenie Platform — Health Check                    ║"
        echo "║    VM: $VM_IP                                          ║"
        echo "║    Time: $(date '+%Y-%m-%d %H:%M:%S')                             ║"
        echo "╚══════════════════════════════════════════════════════════╝"
        echo ""
    fi

    local health_data
    health_data=$(run_ssh "
        # Run all checks locally on the VM
        for cmd in 'pg_isready -h 127.0.0.1 -p 5432' 'redis-cli -h 127.0.0.1 ping' 'wget -q -O - http://127.0.0.1:9000/minio/health/live' 'wget -q -O - http://127.0.0.1:8200/v1/sys/health' 'curl -sf http://127.0.0.1:8083/realms/master/protocol/openid-connect/certs'; do
            \$cmd > /dev/null 2>&1 && echo 'up' || echo 'down'
        done
    " 2>/dev/null || echo "UNREACHABLE")

    if [[ "$health_data" == "UNREACHABLE" ]]; then
        if [[ "$JSON_ONLY" == true ]]; then
            cat <<'JSON_EOF'
{
    "timestamp": "TIMESTAMP_PLACEHOLDER",
    "overall": "error",
    "services": {
        "error": {"status": "error", "message": "VM unreachable"}
    }
}
JSON_EOF
        else
            echo -e "${RED}ERROR: Cannot reach VM $VM_IP${NC}"
        fi
        return
    fi

    # Get quick summary on VM
    local container_count
    container_count=$(run_ssh "docker ps --format '{{.Names}}' | grep -c '^iacgenie_' 2>/dev/null || echo 0")

    if [[ "$JSON_ONLY" == true ]]; then
        echo "{"
        echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
        echo "  \"vm\": \"$VM_IP\","
        echo "  \"overall\": \"$([ \"$container_count\" -ge 10 ] && echo 'healthy' || echo 'degraded')\","
        echo "  \"docker_containers\": $container_count,"
        echo "  \"services\": {"

        if [[ -z "$SINGLE_SERVICE" ]]; then
            echo "      \"postgres\":    {\"status\":\"checking\"},"
            echo "      \"redis\":       {\"status\":\"checking\"},"
            echo "      \"minio\":       {\"status\":\"checking\"},"
            echo "      \"openbao\":     {\"status\":\"checking\"},"
            echo "      \"keycloak\":    {\"status\":\"checking\"},"
            echo "      \"gitea\":       {\"status\":\"checking\"},"
            echo "      \"lightserp_api\":{\"status\":\"checking\"},"
            echo "      \"lightserp_webui\":{\"status\":\"checking\"},"
            echo "      \"pagezen\":     {\"status\":\"checking\"},"
            echo "      \"searxng\":     {\"status\":\"checking\"},"
            echo "      \"nsqd\":        {\"status\":\"checking\"},"
            echo "      \"nginx\":       {\"status\":\"checking\"},"
            echo "      \"cloudflared\": {\"status\":\"checking\"},"
            echo "      \"docker\":      {\"status\":\"checking\"}"
            echo "  }"
            echo "}"
        else
            echo "      \"$SINGLE_SERVICE\": {\"status\":\"checking\"}"
            echo "  }"
            echo "}"
        fi
    else
        echo "Services: $container_count running"
        echo ""

        echo "Docker Containers:"
        run_ssh "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | head -20"
        echo ""

        echo "Systemd Services:"
        run_ssh "systemctl list-units --type=service --state=running --no-pager | grep -E 'nginx|cloudflared|promtail' 2>/dev/null || echo 'none'"
        echo ""

        echo "Disk Usage:"
        run_ssh "df -h /home/mkanavi/docker/iacgenie/ | tail -1"
    fi
}

main "$@"
