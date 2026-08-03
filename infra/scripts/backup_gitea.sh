#!/bin/bash
# Gitea Backup Script
# Backs up repositories, config, and database to /home/mkanavi/backups/gitea/
# Should be run daily via cron (e.g., 0 3 * * *)

set -euo pipefail

# Configuration
BACKUP_ROOT="/home/mkanavi/backups/gitea"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"
DOCKER_COMPOSE_FILE="/home/mkanavi/docker/iacgenie/docker-compose-newvm.yml"
CONTAINER_NAME="iacgenie-gitea"

# Create backup directory
mkdir -p "${BACKUP_DIR}"

echo "=== Gitea Backup Started at $(date) ==="
echo "Backup directory: ${BACKUP_DIR}"

# Step 1: Stop Gitea container to ensure data consistency
echo "Stopping Gitea container..."
docker -f "${DOCKER_COMPOSE_FILE}" stop gitea
docker -f "${DOCKER_COMPOSE_FILE}" rm -f gitea

# Step 2: Backup the entire data directory
echo "Backing up data directory..."
cp -a /home/mkanavi/docker/iacgenie/gitea_data/data "${BACKUP_DIR}/data"

# Step 3: Backup config directory
echo "Backing up config directory..."
cp -a /home/mkanavi/docker/iacgenie/gitea_data/config "${BACKUP_DIR}/config"

# Step 4: Calculate and log sizes
DATA_SIZE=$(du -sh "${BACKUP_DIR}/data" | cut -f1)
CONFIG_SIZE=$(du -sh "${BACKUP_DIR}/config" | cut -f1)
TOTAL_SIZE=$(du -sh "${BACKUP_DIR}" | cut -f1)

echo "Backup completed:"
echo "  Data: ${DATA_SIZE}"
echo "  Config: ${CONFIG_SIZE}"
echo "  Total: ${TOTAL_SIZE}"

# Step 5: Start Gitea container again
echo "Starting Gitea container..."
docker -f "${DOCKER_COMPOSE_FILE}" up -d gitea

# Step 6: Wait for Gitea to be ready
echo "Waiting for Gitea to be ready..."
for i in {1..30}; do
    if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3000 | grep -q "200"; then
        echo "Gitea is back up!"
        break
    fi
    sleep 2
done

# Step 7: Cleanup old backups (keep last 7 days)
echo "Cleaning up old backups (keeping last 7 days)..."
find "${BACKUP_ROOT}" -maxdepth 1 -type d -mtime +7 -exec rm -rf {} + 2>/dev/null || true

echo "=== Gitea Backup Completed at $(date) ==="
echo "Backup saved to: ${BACKUP_DIR}"
ls -la "${BACKUP_DIR}/"
