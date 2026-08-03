#!/bin/bash
set -euo pipefail

# IacGenie Platform Unified Deployment Script
# Usage: ./scripts/deploy.sh [--group <name>] [--backup] [--validate] [--dry-run]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/infra/docker-compose/docker-compose-unified.yml"

GROUP="${1:---group all}"
ACTION="deploy"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --group)
      GROUP="$2"
      shift 2
      ;;
    --backup)
      ACTION="backup"
      shift
      ;;
    --validate)
      ACTION="validate"
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--group <iacgenie|lightsrp|all>] [--backup] [--validate] [--dry-run]"
      exit 1
      ;;
  esac
done

case "$ACTION" in
  deploy)
    echo "=== Deploying IacGenie Platform ==="
    echo "Group: $GROUP"
    echo "Compose file: $COMPOSE_FILE"
    echo ""

    if [ "$DRY_RUN" = true ]; then
      echo "[DRY RUN] Would run:"
      echo "  cd $REPO_ROOT"
      echo "  docker compose -f $COMPOSE_FILE up -d"
      exit 0
    fi

    # Backup current state
    echo "[1/3] Backing up current state..."
    cp "$COMPOSE_FILE" "${COMPOSE_FILE}.bak.$(date +%Y%m%d%H%M%S)"
    echo "  ✅ Backup saved"

    # Deploy
    echo "[2/3] Deploying services..."
    cd "$REPO_ROOT"
    docker compose -f "$COMPOSE_FILE" up -d
    echo "  ✅ Services deployed"

    # Wait and verify
    echo "[3/3] Verifying services..."
    sleep 30
    docker compose -f "$COMPOSE_FILE" ps
    ;;

  backup)
    echo "=== Running Backups ==="
    cd "$REPO_ROOT"
    ansible-playbook "$REPO_ROOT/infra/ansible/playbooks/backup.yml"
    ;;

  validate)
    echo "=== Validating Deployment ==="
    cd "$REPO_ROOT"
    ansible-playbook "$REPO_ROOT/infra/ansible/playbooks/validate.yml"
    ;;

  *)
    echo "Unknown action: $ACTION"
    exit 1
    ;;
esac

echo ""
echo "=== Done ==="
