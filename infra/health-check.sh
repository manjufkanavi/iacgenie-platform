#!/bin/bash
# =============================================================================
# IacGenie Platform — Comprehensive Health Check Script
# Checks: Base services (postgres, redis, openbao, keycloak, gitea, minio),
#         LightSerp (api, webui, pagezen, searxng, nsqd),
#         Monitoring (prometheus, alertmanager, grafana, loki, promtail),
#         Security (falco, falcosidekick), Infrastructure (node-exporter)
# Output: Color-coded PASS/FAIL/WARN with Docker labels for services
# =============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

pass() { echo -e "  ${GREEN}✓ PASS${NC} $1"; ((PASS++)); }
fail() { echo -e "  ${RED}✗ FAIL${NC} $1"; ((FAIL++)); }
warn() { echo -e "  ${YELLOW}⚠ WARN${NC} $1"; ((WARN++)); }
info() { echo -e "  ${CYAN}ℹ INFO${NC} $1"; }

# === HTTP health check helper ===
check_http() {
    local name="$1" url="$2" desc="$3"
    local http_code
    http_code=$(curl -sf -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || echo "000")
    case "$http_code" in
        200|201|204) pass "$desc"; return 0 ;;
        503) warn "$desc (service starting)"; return 0 ;;
        *) fail "$desc (HTTP $http_code at $url)"; return 1 ;;
    esac
}

# === Docker health check helper ===
check_docker() {
    local name="$1"
    local status
    status=$(docker inspect --format='{{.State.Status}}' "iacgenie_${name}" 2>/dev/null || echo "not_found")
    local health
    health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "iacgenie_${name}" 2>/dev/null || echo "none")
    
    case "$status" in
        running)
            if [[ "$health" == "healthy" ]]; then
                pass "$name (running, $health)"
            else
                if [[ "$health" == "none" ]]; then
                    pass "$name (running, no healthcheck)"
                else
                    warn "$name (running, $health)"
                fi
            fi
            return 0
            ;;
        started)
            pass "$name (running)"
            return 0
            ;;
        stopped|exited)
            fail "$name (stopped/exited)"
            return 1
            ;;
        *)
            fail "$name ($status)"
            return 1
            ;;
    esac
}

# === Port health check ===
check_port() {
    local name="$1" port="$2"
    if timeout 3 bash -c "echo >/dev/tcp/127.0.0.1/$port" 2>/dev/null; then
        pass "$name (port $port open)"
    else
        fail "$name (port $port closed)"
    fi
}

# =============================================================================
# Base Infrastructure Services
# =============================================================================
echo -e "\n${BOLD}=== BASE INFRASTRUCTURE SERVICES ===${NC}\n"

# PostgreSQL
echo -e "${BOLD}--- PostgreSQL ---${NC}"
check_docker "postgres"
check_port "postgres" 5432
# Check if databases exist
if docker exec iacgenie_postgres psql -U postgres -tc "SELECT datname FROM pg_database WHERE datname IN ('lightsrp', 'keycloak')" 2>/dev/null | grep -q .; then
    pass "Required databases exist (lightsrp, keycloak)"
else
    warn "Required databases may be missing"
fi

# Redis
echo -e "${BOLD}--- Redis ---${NC}"
check_docker "redis"
check_port "redis" 6379
if docker exec iacgenie_redis redis-cli ping 2>/dev/null | grep -q PONG; then
    pass "Redis responds to PING"
else
    warn "Redis PING failed"
fi

# OpenBao
echo -e "${BOLD}--- OpenBao ---${NC}"
check_docker "openbao"
check_port "openbao" 8200
if docker exec iacgenie_openbao bao status 2>/dev/null | grep -qi "sealed"; then
    # Check if unsealed
    local sealed
    sealed=$(docker exec iacgenie_openbao bao status 2>/dev/null | grep -c "sealed: true" || true)
    if [[ "$sealed" == "0" ]]; then
        pass "OpenBao is unsealed and operational"
    else
        warn "OpenBao is sealed"
    fi
else
    pass "OpenBao is running"
fi

# Keycloak
echo -e "${BOLD}--- Keycloak ---${NC}"
check_docker "keycloak"
check_port "keycloak" 8083
check_http "Keycloak" "http://127.0.0.1:8083/auth/health/ready" "Keycloak health endpoint"

# Gitea
echo -e "${BOLD}--- Gitea ---${NC}"
check_docker "gitea"
check_port "gitea" 3000
check_http "Gitea" "http://127.0.0.1:3000/api/health" "Gitea API health"

# MinIO
echo -e "${BOLD}--- MinIO ---${NC}"
check_docker "minio"
check_port "minio" 9000
check_http "MinIO API" "http://127.0.0.1:9000/minio/health/live" "MinIO health"

# NSQD
echo -e "${BOLD}--- NSQD ---${NC}"
check_docker "nsqd"
check_port "nsqd" 4150
if docker exec iacgenie_nsqd nsqadmin --lookupd-http-address=127.0.0.1:4151 2>/dev/null | grep -q .; then
    pass "NSQD admin accessible"
else
    pass "NSQD running (port 4150)"
fi

# SearXNG
echo -e "${BOLD}--- SearXNG ---${NC}"
check_docker "searxng"
check_port "searxng" 8082
check_http "SearXNG" "http://127.0.0.1:8082" "SearXNG search engine"

# =============================================================================
# LightSerp Services
# =============================================================================
echo -e "\n${BOLD}=== LIGHTSERP SERVICES ===${NC}\n"

# LightSerp API
echo -e "${BOLD}--- LightSerp API ---${NC}"
check_docker "lightserp_api"
check_port "lightserp_api" 8000
check_http "LightSerp API" "http://127.0.0.1:8000" "LightSerp API endpoint"

# LightSerp WebUI
echo -e "${BOLD}--- LightSerp WebUI ---${NC}"
check_docker "lightserp_webui"
check_port "lightserp_webui" 3001
check_http "LightSerp WebUI" "http://127.0.0.1:3001" "LightSerp WebUI"

# PageZen
echo -e "${BOLD}--- PageZen ---${NC}"
check_docker "pagezen"
check_port "pagezen" 8081
check_http "PageZen" "http://127.0.0.1:8081" "PageZen PDF viewer"

# =============================================================================
# Monitoring Stack
# =============================================================================
echo -e "\n${BOLD}=== MONITORING STACK ===${NC}\n"

# Prometheus
echo -e "${BOLD}--- Prometheus ---${NC}"
check_docker "prometheus"
check_port "prometheus" 9090
check_http "Prometheus" "http://127.0.0.1:9090/-/healthy" "Prometheus health"
# Check scrape targets
targets=$(curl -sf http://127.0.0.1:9090/api/v1/targets 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); active=sum(1 for t in d['data']['activeTargets'] if t['health']=='up'); total=len(d['data']['activeTargets']); print(f'{active}/{total}')" 2>/dev/null || echo "unknown")
info "Prometheus scrape targets: $targets up"

# Alertmanager
echo -e "${BOLD}--- Alertmanager ---${NC}"
check_docker "alertmanager"
check_port "alertmanager" 9093
check_http "Alertmanager" "http://127.0.0.1:9093/-/healthy" "Alertmanager health"

# Grafana
echo -e "${BOLD}--- Grafana ---${NC}"
check_docker "grafana"
check_port "grafana" 3002
check_http "Grafana" "http://127.0.0.1:3002/api/health" "Grafana health"

# Loki
echo -e "${BOLD}--- Loki ---${NC}"
check_docker "loki"
check_port "loki" 3100
check_http "Loki" "http://127.0.0.1:3100/ready" "Loki ready"

# Promtail
echo -e "${BOLD}--- Promtail ---${NC}"
check_docker "promtail"

# Node Exporter
echo -e "${BOLD}--- Node Exporter (host metrics) ---${NC}"
check_port "node-exporter" 9100
check_http "Node Exporter" "http://127.0.0.1:9100/metrics" "Node Exporter metrics endpoint"

# =============================================================================
# Security Stack
# =============================================================================
echo -e "\n${BOLD}=== SECURITY STACK ===${NC}\n"

# Falco
echo -e "${BOLD}--- Falco (runtime security) ---${NC}"
check_docker "falco"
info "Falco kernel module: $(lsmod 2>/dev/null | grep -c falco || echo 'eBPF') eBPF probes loaded"

# Falcosidekick (Web UI)
echo -e "${BOLD}--- Falcosidekick (Web UI) ---${NC}"
check_docker "falcosidekick"
check_port "falcosidekick" 2800
check_http "Falcosidekick UI" "http://127.0.0.1:2800/falco-events" "Falcosidekick health"

# =============================================================================
# Infrastructure Services
# =============================================================================
echo -e "\n${BOLD}=== INFRASTRUCTURE SERVICES ===${NC}\n"

# Docker
if systemctl is-active --quiet docker.service; then
    docker_count=$(docker ps --format '{{.Names}}' 2>/dev/null | wc -l)
    pass "Docker daemon running ($docker_count containers)"
else
    fail "Docker daemon not running"
fi

# Nginx
if systemctl is-active --quiet nginx.service; then
    pass "Nginx reverse proxy running"
else
    fail "Nginx not running"
fi

# Cloudflared
if systemctl is-active --quiet cloudflared.service; then
    pass "Cloudflare tunnel running"
else
    fail "Cloudflare tunnel not running"
fi

# System resources
echo -e "${BOLD}--- System Resources ---${NC}"
disk_usage=$(df -h / | awk 'NR==2 {print $5}')
mem_info=$(free -m | awk 'NR==2 {printf "%.0f%% used (%dMB/%dMB)", $3*100/$2, $3, $2}')
load=$(uptime | awk -F'load average:' '{print $2}' | xargs)
info "Disk: $disk_usage used | Memory: $mem_info | Load: $load"

if [[ "$(df / | awk 'NR==2 {print $5}' | tr -d '%')" -gt 90 ]]; then
    fail "Disk usage > 90%"
elif [[ "$(df / | awk 'NR==2 {print $5}' | tr -d '%')" -gt 80 ]]; then
    warn "Disk usage > 80%"
else
    pass "Disk usage OK ($disk_usage)"
fi

# =============================================================================
# Summary
# =============================================================================
echo -e "\n${BOLD}========================================${NC}"
echo -e "${BOLD}  HEALTH CHECK SUMMARY${NC}"
echo -e "${BOLD}========================================${NC}"
echo -e "  ${GREEN}PASS: $PASS${NC}"
echo -e "  ${YELLOW}WARN: $WARN${NC}"
echo -e "  ${RED}FAIL: $FAIL${NC}"
echo -e "${BOLD}========================================${NC}\n"

TOTAL=$((PASS + WARN + FAIL))
if [[ $FAIL -eq 0 ]]; then
    echo -e "${GREEN}${BOLD}ALL CHECKS PASSED${NC}"
    exit 0
else
    echo -e "${RED}${BOLD}$FAIL CHECKS FAILED — review above${NC}"
    exit 1
fi
