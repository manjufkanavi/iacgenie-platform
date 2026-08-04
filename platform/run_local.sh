#!/bin/bash
# =============================================================================
# run_local.sh — Run IacGenie Platform Locally (all services)
# =============================================================================
# Usage: ./run_local.sh [up|down|restart|logs]
#
# Runs all IacGenie services locally via Docker Compose:
#   - PostgreSQL (shared with unified infra)
#   - Redis (shared with unified infra)
#   - Keycloak (shared with unified infra)
#   - IacGenie Backend (FastAPI, port 8000)
#   - IacGenie Frontend (Vite/React, port 5173)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose-local.yml"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}   $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}   $*"; }

case "${1:-up}" in
    up)
        info "Starting IacGenie Platform locally..."
        info "Backend:  http://localhost:8000"
        info "Frontend: http://localhost:5173"
        docker compose -f "$COMPOSE_FILE" up -d
        sleep 5
        info "Logs: docker compose -f $COMPOSE_FILE logs -f"
        ;;
    down)
        info "Stopping IacGenie Platform locally..."
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
