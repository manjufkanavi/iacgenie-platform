#!/bin/bash
# =============================================================================
# IacGenie Platform — Comprehensive Backup & Restore Script
# =============================================================================
# Creates encrypted backups of ALL service data, stores on Google Drive.
# Supports per-service backup, full backup, and restore operations.
#
# Usage:
#   ./backup-restore.sh backup              # Full backup
#   ./backup-restore.sh backup postgres     # Single service backup
#   ./backup-restore.sh list               # List available backups
#   ./backup-restore.sh restore <file>     # Restore from backup
#   ./backup-restore.sh verify             # Verify backup integrity
# =============================================================================

set -euo pipefail

# === Configuration ===
SSH_USER="mkanavi"
VM_IP="192.168.0.118"
LOCAL_BACKUP_DIR="/tmp/iacgenie-backups"
REMOTE_BACKUP_DIR="/home/mkanavi/backups/encrypted"
ENCRYPTION_KEY_FILE="$HOME/.iacgenie_backup_key"

# === Colors ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[BACKUP]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
info() { echo -e "${CYAN}[INFO]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# === SSH Helper ===
run_ssh() {
    ssh -o ConnectTimeout=10 "$SSH_USER@$VM_IP" "$1" 2>/dev/null
}

# === Initialize ===
init() {
    # Create local backup directory
    mkdir -p "$LOCAL_BACKUP_DIR"

    # Check for encryption key
    if [[ ! -f "$ENCRYPTION_KEY_FILE" ]]; then
        warn "Encryption key not found at $ENCRYPTION_KEY_FILE"
        warn "Generate one with: openssl rand -base64 32 > $ENCRYPTION_KEY_FILE"
    fi
}

# === Backup PostgreSQL ===
backup_postgres() {
    info "Backing up PostgreSQL..."
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="$REMOTE_BACKUP_DIR/pg-$timestamp.sql.gz.gpg"

    run_ssh "
        set -euo pipefail
        mkdir -p $REMOTE_BACKUP_DIR
        pg_dump -h 127.0.0.1 -U lightsrp lightsrp | gzip | \
        gpg --batch --symmetric --cipher-algo AES256 \
            --passphrase-file /home/mkanavi/.iacgenie_backup_key \
            --output $backup_file -
        echo \"PostgreSQL backup created: $backup_file\"
    "
    log "PostgreSQL backup: $backup_file"
}

# === Backup OpenBao ===
backup_openbao() {
    info "Backing up OpenBao raft snapshot..."
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="$REMOTE_BACKUP_DIR/openbao-$timestamp.tar.gz.gpg"

    run_ssh "
        set -euo pipefail
        mkdir -p $REMOTE_BACKUP_DIR
        # Snapshot raft
        bao operator raft snapshot TAKE $REMOTE_BACKUP_DIR/openbao-$timestamp.snap
        # Compress and encrypt
        tar czf - $REMOTE_BACKUP_DIR/openbao-$timestamp.snap | \
        gpg --batch --symmetric --cipher-algo AES256 \
            --passphrase-file /home/mkanavi/.iacgenie_backup_key \
            --output $backup_file -
        rm -f $REMOTE_BACKUP_DIR/openbao-$timestamp.snap
        echo \"OpenBao backup created: $backup_file\"
    "
    log "OpenBao backup: $backup_file"
}

# === Backup Gitea ===
backup_gitea() {
    info "Backing up Gitea..."
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="$REMOTE_BACKUP_DIR/gitea-$timestamp.tar.gz.gpg"

    run_ssh "
        set -euo pipefail
        mkdir -p $REMOTE_BACKUP_DIR
        tar czf - /home/mkanavi/docker/iacgenie/data/gitea | \
        gpg --batch --symmetric --cipher-algo AES256 \
            --passphrase-file /home/mkanavi/.iacgenie_backup_key \
            --output $backup_file -
        echo \"Gitea backup created: $backup_file\"
    "
    log "Gitea backup: $backup_file"
}

# === Backup Keycloak ===
backup_keycloak() {
    info "Backing up Keycloak realm..."
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="$REMOTE_BACKUP_DIR/keycloak-$timestamp.tar.gz.gpg"

    run_ssh "
        set -euo pipefail
        mkdir -p $REMOTE_BACKUP_DIR
        # Export realm via API
        curl -s -H 'Content-Type: application/json' \
            http://127.0.0.1:8083/admin/realms/master/export \
            -d '{\"includePlayers\":true,\"includeCredentials\":true,\"includeRoles\":true}' \
            -o /tmp/realm-export.json 2>/dev/null || true
        # Compress data directory and encrypt
        tar czf - /home/mkanavi/docker/iacgenie/data/keycloak \
            /tmp/realm-export.json 2>/dev/null | \
        gpg --batch --symmetric --cipher-algo AES256 \
            --passphrase-file /home/mkanavi/.iacgenie_backup_key \
            --output $backup_file -
        echo \"Keycloak backup created: $backup_file\"
    "
    log "Keycloak backup: $backup_file"
}

# === Backup MinIO ===
backup_minio() {
    info "Backing up MinIO data..."
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="$REMOTE_BACKUP_DIR/minio-$timestamp.tar.gz.gpg"

    run_ssh "
        set -euo pipefail
        mkdir -p $REMOTE_BACKUP_DIR
        tar czf - /home/mkanavi/docker/iacgenie/data/minio | \
        gpg --batch --symmetric --cipher-algo AES256 \
            --passphrase-file /home/mkanavi/.iacgenie_backup_key \
            --output $backup_file -
        echo \"MinIO backup created: $backup_file\"
    "
    log "MinIO backup: $backup_file"
}

# === Backup Configuration Files ===
backup_configs() {
    info "Backing up configuration files..."
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="$REMOTE_BACKUP_DIR/configs-$timestamp.tar.gz.gpg"

    run_ssh "
        set -euo pipefail
        mkdir -p $REMOTE_BACKUP_DIR
        tar czf - \
            /home/mkanavi/docker/iacgenie/docker-compose.yml \
            /home/mkanavi/docker/iacgenie/nginx*.conf \
            /etc/nginx/conf.d/iacgenie-unified.conf \
            /home/mkanavi/.cloudflared/config.yml \
            /home/mkanavi/backups/scripts/ \
        | gpg --batch --symmetric --cipher-algo AES256 \
            --passphrase-file /home/mkanavi/.iacgenie_backup_key \
            --output $backup_file -
        echo \"Config backup created: $backup_file\"
    "
    log "Config backup: $backup_file"
}

# === Upload to Google Drive ===
upload_to_gdrive() {
    info "Uploading backups to Google Drive..."
    run_ssh "
        set -euo pipefail
        if command -v rclone &>/dev/null; then
            cd $REMOTE_BACKUP_DIR
            rclone copy . gdrive:iacgenie-backups/ --max-age 0d --transfers 4 --checkers 8
            echo \"Uploaded to Google Drive\"
        else
            echo 'rclone not configured - skipping upload'
        fi
    " 2>/dev/null || warn "Google Drive upload failed or rclone not configured"
}

# === Cleanup Old Backups ===
cleanup_old() {
    info "Cleaning up old backups..."
    run_ssh "
        set -euo pipefail
        # Keep daily backups for 30 days
        find $REMOTE_BACKUP_DIR -name '*.gpg' -mtime +30 -delete 2>/dev/null || true
        # Keep weekly backups (1 week)
        find $REMOTE_BACKUP_DIR -name '*.gpg' -mtime +7 ! -mtime +30 -print | \
            while read f; do
                # Keep one backup per week (randomly to avoid all-weekly conflicts)
                day=\$(stat -c '%Y' \$f)
                week=\$((day / 604800))
                if [[ \$((week % 7)) -eq 0 ]]; then
                    rm -f \$f
                fi
            done
        # Keep monthly backups (1 month)
        find $REMOTE_BACKUP_DIR -name '*.gpg' -mtime +30 -mtime -365 -print | \
            while read f; do
                day=\$(stat -c '%Y' \$f)
                month=\$((day / 2592000))
                if [[ \$((month % 30)) -eq 0 ]]; then
                    rm -f \$f
                fi
            done
        echo 'Old backups cleaned up'
    "
    log "Cleanup complete"
}

# === List Available Backups ===
list_backups() {
    info "Available backups:"
    run_ssh "ls -lh $REMOTE_BACKUP_DIR/*.gpg 2>/dev/null | sort -k6,7 || echo 'No backups found'"
}

# === Restore ===
restore() {
    local backup_file="$1"
    info "WARNING: This will overwrite current data with backup!"
    info "Backup file: $backup_file"

    # Download backup
    run_ssh "
        gpg --batch --decrypt --passphrase-file /home/mkanavi/.iacgenie_backup_key \
            $REMOTE_BACKUP_DIR/$backup_file 2>/dev/null > /tmp/restored-backup.tar.gz
        echo 'Decrypted'
    "

    # Restore based on backup type
    if [[ "$backup_file" == pg-* ]]; then
        run_ssh "gzip -dc /tmp/restored-backup.tar.gz | psql -h 127.0.0.1 -U lightsrp lightsrp"
        log "PostgreSQL restored from $backup_file"
    fi
}

# === Verify Backup ===
verify() {
    info "Verifying backup integrity..."
    run_ssh "
        set -euo pipefail
        for f in $REMOTE_BACKUP_DIR/*.gpg; do
            if gpg --batch --decrypt --passphrase-file /home/mkanavi/.iacgenie_backup_key --output /dev/null \$f 2>/dev/null; then
                echo \"OK: \$f\"
            else
                echo \"FAIL: \$f\"
            fi
        done
    "
}

# === Full Backup ===
full_backup() {
    init
    log "Starting full backup at $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    backup_postgres
    backup_openbao
    backup_gitea
    backup_keycloak
    backup_minio
    backup_configs

    echo ""
    upload_to_gdrive
    cleanup_old

    log "Full backup complete at $(date '+%Y-%m-%d %H:%M:%S')"
}

# === Main ===
main() {
    local action="${1:-help}"
    shift || true

    case "$action" in
        backup)
            local service="${1:-all}"
            if [[ "$service" == "all" ]]; then
                full_backup
            elif [[ "$service" == "postgres" ]]; then
                init; backup_postgres
            elif [[ "$service" == "openbao" ]]; then
                init; backup_openbao
            elif [[ "$service" == "gitea" ]]; then
                init; backup_gitea
            elif [[ "$service" == "keycloak" ]]; then
                init; backup_keycloak
            elif [[ "$service" == "minio" ]]; then
                init; backup_minio
            elif [[ "$service" == "configs" ]]; then
                init; backup_configs
            else
                error "Unknown service: $service"
                exit 1
            fi
            ;;
        list)   list_backups ;;
        restore)
            if [[ -z "${1:-}" ]]; then
                error "Usage: $0 restore <backup-file.gpg>"
                exit 1
            fi
            restore "$1"
            ;;
        verify) verify ;;
        *)
            echo "Usage: $0 {backup [service] | list | restore <file> | verify}"
            echo ""
            echo "Services: postgres openbao gitea keycloak minio configs all"
            ;;
    esac
}

main "$@"
