#!/bin/bash
# =============================================================================
# run_local.sh — Run LightSerp Locally (with unified infra)
# =============================================================================
# Usage: ./run_local.sh [up|down|restart|logs]
#
# Runs LightSerp services locally via Docker Compose alongside unified infra:
#   - LightSerp API (FastAPI/Node, port 3001)
#   - PageZen (scraper, port 8076)
#
# Shared infrastructure (from docker-compose-unified.yml):
#   - PostgreSQL, Redis, SearXNG, NSQD, MinIO, Keycloak, OpenBao
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}   $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}   $*"; }

case "${1:-up}" in
    up)
        info "Starting LightSerp locally..."
        info "API:      http://localhost:3001"
        info "PageZen:  http://localhost:8076"
        info "Note: Requires docker-compose-unified.yml running first"
        docker compose -f "$COMPOSE_FILE" up -d
        sleep 3
        info "Logs: docker compose -f $COMPOSE_FILE logs -f"
        ;;
    down)
        info "Stopping LightSerp locally..."
        docker compose -f "$COMPOSE_FILE" down
        ;;
    restart)
        docker compose -f "$COMPOSE_FILE" restart
        ;;
    logs)
        docker compose -f "$COMPOSE_FILE" logs -f
        ;;
    *)
        echo "Usage: $0 [up|down|restart|logs]"
        exit 1
        ;;
esac
