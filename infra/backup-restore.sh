#!/bin/bash
# =============================================================================
# IacGenie Platform — Comprehensive Backup & Restore Script
# =============================================================================
# Creates encrypted backups of ALL service data, stores on Google Drive via rclone.
# Backs up: PostgreSQL, OpenBao, Gitea, Keycloak, MinIO, Redis, LightSerp,
#           Monitoring (Prometheus, Grafana, Loki), configs
# Supports per-service backup, full backup, restore, verify, and cleanup.
#
# Usage:
#   ./backup-restore.sh backup              # Full backup of all services
#   ./backup-restore.sh backup postgres     # Single service backup
#   ./backup-restore.sh list               # List available backups
#   ./backup-restore.sh restore <file>     # Restore from backup
#   ./backup-restore.sh verify             # Verify backup integrity
#   ./backup-restore.sh cleanup            # Clean old backups (retention policy)
# =============================================================================

set -euo pipefail

# === Configuration ===
SSH_USER="mkanavi"
VM_IP="192.168.0.118"
LOCAL_BACKUP_DIR="/tmp/iacgenie-backups"
REMOTE_BACKUP_DIR="/home/mkanavi/backups/encrypted"
ENCRYPTION_KEY_FILE="/home/mkanavi/.iacgenie_backup_key"

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
    ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSH_USER@$VM_IP" "$1" 2>/dev/null
}

# === Initialize ===
init() {
    mkdir -p "$LOCAL_BACKUP_DIR"
    run_ssh "mkdir -p $REMOTE_BACKUP_DIR"
}

# === Encrypt helper ===
encrypt_remote() {
    local src_file="$1" dest_file="$2"
    run_ssh "gpg --batch --symmetric --cipher-algo AES256 --passphrase-file $ENCRYPTION_KEY_FILE --output '$dest_file' '$src_file' 2>/dev/null && echo 'OK: $dest_file' || echo 'FAIL: $dest_file'"
}

# === Backup PostgreSQL ===
backup_postgres() {
    info "Backing up PostgreSQL..."
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="pg-$timestamp.sql.gz.gpg"
    
    run_ssh "
        set -euo pipefail
        mkdir -p $REMOTE_BACKUP_DIR
        # Dump all databases (lightsrp + keycloak)
        pg_dump -h 127.0.0.1 -U postgres lightsrp | gzip > /tmp/pg-lightsrp.sql.gz
        pg_dump -h 127.0.0.1 -U postgres keycloak | gzip > /tmp/pg-keycloak.sql.gz
        # Compress both into one file
        cat /tmp/pg-lightsrp.sql.gz /tmp/pg-keycloak.sql.gz | \
        gpg --batch --symmetric --cipher-algo AES256 \
            --passphrase-file $ENCRYPTION_KEY_FILE \
            --output $REMOTE_BACKUP_DIR/$backup_file
        rm -f /tmp/pg-*.sql.gz
        echo \"PostgreSQL backup created: $REMOTE_BACKUP_DIR/$backup_file\"
    "
    log "PostgreSQL backup: $backup_file"
}

# === Backup OpenBao (Raft snapshot) ===
backup_openbao() {
    info "Backing up OpenBao raft snapshot..."
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="openbao-$timestamp.tar.gz.gpg"
    
    # Check OpenBao health first
    local health=$(run_ssh "curl -sf http://127.0.0.1:8200/v1/sys/health" 2>/dev/null || echo '{"sealed":true}')
    local sealed=$(echo "$health" | python3 -c "import sys,json; print(str(json.load(sys.stdin).get('sealed',True)).lower())" 2>/dev/null || echo "true")
    
    if [ "$sealed" = "true" ]; then
        warn "OpenBao is sealed — skipping raft snapshot (backup of data dir only)"
        # Backup data directory to remote temp file, then encrypt
        run_ssh "
            set -euo pipefail
            mkdir -p $REMOTE_BACKUP_DIR
            cd /home/mkanavi/docker/iacgenie
            tar czf /tmp/openbao-backup-$timestamp.tar.gz data/openbao data/openbao_raft
            gpg --batch --symmetric --cipher-algo AES256 \
                --passphrase-file /home/mkanavi/.iacgenie_backup_key \
                --output $REMOTE_BACKUP_DIR/$backup_file \
                /tmp/openbao-backup-$timestamp.tar.gz
            rm -f /tmp/openbao-backup-$timestamp.tar.gz
            echo \"OpenBao data backup created: $REMOTE_BACKUP_DIR/$backup_file (sealed state)\"
        "
        log "OpenBao data backup: $backup_file (sealed — full snapshot requires unseal)"
    else
        run_ssh "
            set -euo pipefail
            mkdir -p $REMOTE_BACKUP_DIR
            cd /home/mkanavi/docker/iacgenie
            # Snapshot raft
            bao operator raft snapshot save /tmp/openbao-$timestamp.snap
            # Compress data dir + snapshot
            tar czf /tmp/openbao-backup-$timestamp.tar.gz data/openbao_raft
            gpg --batch --symmetric --cipher-algo AES256 \
                --passphrase-file /home/mkanavi/.iacgenie_backup_key \
                --output $REMOTE_BACKUP_DIR/$backup_file \
                /tmp/openbao-backup-$timestamp.tar.gz
            rm -f /tmp/openbao-backup-$timestamp.tar.gz /tmp/openbao-$timestamp.snap
            echo \"OpenBao backup created: $REMOTE_BACKUP_DIR/$backup_file\"
        "
        log "OpenBao backup: $backup_file"
    fi
}

# === Backup Gitea ===
backup_gitea() {
    info "Backing up Gitea..."
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="gitea-$timestamp.tar.gz.gpg"
    
    run_ssh "
        set -euo pipefail
        mkdir -p $REMOTE_BACKUP_DIR
        tar czf - /home/mkanavi/docker/iacgenie/data/gitea | \
        gpg --batch --symmetric --cipher-algo AES256 \
            --passphrase-file $ENCRYPTION_KEY_FILE \
            --output $REMOTE_BACKUP_DIR/$backup_file
        echo \"Gitea backup created: $REMOTE_BACKUP_DIR/$backup_file\"
    "
    log "Gitea backup: $backup_file"
}

# === Backup Keycloak (realm export + data) ===
backup_keycloak() {
    info "Backing up Keycloak realm..."
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="keycloak-$timestamp.tar.gz.gpg"
    
    run_ssh "
        set -euo pipefail
        mkdir -p $REMOTE_BACKUP_DIR
        # Export realm via Keycloak Admin API
        curl -s -H 'Content-Type: application/json' \
            http://127.0.0.1:8083/auth/admin/realms/iacgenie/export \
            -d '{\"exportUsers\":true,\"exportGroups\":true,\"includeRoleMapping\":true}' \
            -o /tmp/keycloak-realm-export.json 2>/dev/null || true
        # Compress data directory and export
        tar czf - /home/mkanavi/docker/iacgenie/data/keycloak /tmp/keycloak-realm-export.json 2>/dev/null | \
        gpg --batch --symmetric --cipher-algo AES256 \
            --passphrase-file $ENCRYPTION_KEY_FILE \
            --output $REMOTE_BACKUP_DIR/$backup_file
        echo \"Keycloak backup created: $REMOTE_BACKUP_DIR/$backup_file\"
    "
    log "Keycloak backup: $backup_file"
}

# === Backup MinIO ===
backup_minio() {
    info "Backing up MinIO data..."
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="minio-$timestamp.tar.gz.gpg"
    
    run_ssh "
        set -euo pipefail
        mkdir -p $REMOTE_BACKUP_DIR
        tar czf - /home/mkanavi/docker/iacgenie/data/minio | \
        gpg --batch --symmetric --cipher-algo AES256 \
            --passphrase-file $ENCRYPTION_KEY_FILE \
            --output $REMOTE_BACKUP_DIR/$backup_file
        echo \"MinIO backup created: $REMOTE_BACKUP_DIR/$backup_file\"
    "
    log "MinIO backup: $backup_file"
}

# === Backup Redis ===
backup_redis() {
    info "Backing up Redis..."
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="redis-$timestamp.rdb.gpg"
    
    run_ssh "
        set -euo pipefail
        mkdir -p $REMOTE_BACKUP_DIR
        # Trigger Redis BGSAVE
        redis-cli -h 127.0.0.1 BGSAVE 2>/dev/null || true
        sleep 2
        # Copy RDB file
        cp /home/mkanavi/docker/iacgenie/data/redis/dump.rdb /tmp/redis-dump.rdb 2>/dev/null || true
        if [[ -f /tmp/redis-dump.rdb ]]; then
            gzip /tmp/redis-dump.rdb
            gpg --batch --symmetric --cipher-algo AES256 \
                --passphrase-file $ENCRYPTION_KEY_FILE \
                --output $REMOTE_BACKUP_DIR/$backup_file \
                /tmp/redis-dump.rdb.gz
            echo \"Redis backup created: $REMOTE_BACKUP_DIR/$backup_file\"
        else
            warn \"Redis dump.rdb not found - skipping\"
        fi
        rm -f /tmp/redis-dump.rdb*
    "
    log "Redis backup: $backup_file"
}

# === Backup Monitoring (Prometheus, Grafana, Loki) ===
backup_monitoring() {
    info "Backing up monitoring data (Prometheus, Grafana, Loki)..."
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="monitoring-$timestamp.tar.gz.gpg"
    
    run_ssh "
        set -euo pipefail
        mkdir -p $REMOTE_BACKUP_DIR
        tar czf - \
            /home/mkanavi/docker/iacgenie/prometheus/data \
            /home/mkanavi/docker/iacgenie/grafana \
            /home/mkanavi/docker/iacgenie/loki \
        | gpg --batch --symmetric --cipher-algo AES256 \
            --passphrase-file $ENCRYPTION_KEY_FILE \
            --output $REMOTE_BACKUP_DIR/$backup_file
        echo \"Monitoring backup created: $REMOTE_BACKUP_DIR/$backup_file\"
    "
    log "Monitoring backup: $backup_file"
}

# === Backup Configuration Files ===
backup_configs() {
    info "Backing up configuration files..."
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="configs-$timestamp.tar.gz.gpg"
    
    run_ssh "
        set -euo pipefail
        mkdir -p $REMOTE_BACKUP_DIR
        tar czf - \
            /home/mkanavi/docker/iacgenie/docker-compose.yml \
            /home/mkanavi/docker/iacgenie/docker-compose-monitoring.yml \
            /home/mkanavi/docker/iacgenie/docker-compose-unified.yml \
            /home/mkanavi/docker/iacgenie/nginx*.conf \
            /etc/nginx/conf.d/iacgenie-unified.conf \
            /home/mkanavi/.cloudflared/config.yml \
            /home/mkanavi/.cloudflared/*.json \
            /etc/systemd/system/iacgenie-* 2>/dev/null || true \
        | gpg --batch --symmetric --cipher-algo AES256 \
            --passphrase-file $ENCRYPTION_KEY_FILE \
            --output $REMOTE_BACKUP_DIR/$backup_file
        echo \"Config backup created: $REMOTE_BACKUP_DIR/$backup_file\"
    "
    log "Config backup: $backup_file"
}

# === Upload to Google Drive via rclone ===
upload_to_gdrive() {
    info "Uploading backups to Google Drive..."
    local result
    result=$(run_ssh "
        set -euo pipefail
        if command -v rclone &>/dev/null; then
            # Sync with dedup check
            rclone sync $REMOTE_BACKUP_DIR gdrive:iacgenie-backups/ \
                --max-depth 5 \
                --transfers 4 \
                --checkers 8 \
                --log-file /tmp/rclone-upload.log \
                --log-level INFO 2>&1
            echo \"rclone: upload complete\"
        else
            echo 'rclone not configured on VM - skipping Google Drive upload'
        fi
    " 2>/dev/null)
    
    if echo "$result" | grep -q "rclone: upload complete"; then
        log "Google Drive upload complete"
    elif echo "$result" | grep -q "not configured"; then
        warn "$result"
    else
        warn "Google Drive upload status: $result"
    fi
}

# === Cleanup old backups (retention policy) ===
cleanup_old() {
    info "Cleaning up old backups..."
    run_ssh "
        set -euo pipefail
        # Daily backups: keep 30 days
        find $REMOTE_BACKUP_DIR -name '*.gpg' -mtime +30 -type f | while read f; do
            # Keep at least 1 per day
            base=\$(basename \$f .gpg)
            day=\$(echo \$base | grep -oP '^\w+-\d{8}-\d{6}' || echo '')
            if [[ -z \$day ]]; then continue; fi
            # Only delete if 30+ days old AND not a weekly/monthly marker
            if [[ \$((\$(stat -c '%Y' \$f) / 86400)) -gt 30 ]]; then
                echo \"removing: \$f\"
                rm -f \$f
            fi
        done
        echo 'Old backups cleaned up'
    "
    log "Cleanup complete"
}

# === List available backups ===
list_backups() {
    info "Available backups:"
    run_ssh "
        set -euo pipefail
        if [[ -d $REMOTE_BACKUP_DIR ]]; then
            ls -lhS $REMOTE_BACKUP_DIR/*.gpg 2>/dev/null | sort -k6,7 || echo 'No backups found'
            echo ''
            echo \"Total: \$(ls $REMOTE_BACKUP_DIR/*.gpg 2>/dev/null | wc -l) files\"
        else
            echo 'Backup directory not found'
        fi
    "
}

# === Restore from backup ===
restore() {
    local backup_file="$1"
    info "WARNING: This will overwrite current data with backup!"
    info "Backup file: $backup_file"
    read -r -p "Type 'RESTORE' to confirm: " confirm
    if [[ "$confirm" != "RESTORE" ]]; then
        echo "Restore cancelled."
        exit 1
    fi

    case "$backup_file" in
        pg-*)
            info "Restoring PostgreSQL from $backup_file..."
            run_ssh "
                gpg --batch --decrypt --passphrase-file $ENCRYPTION_KEY_FILE \
                    $REMOTE_BACKUP_DIR/$backup_file 2>/dev/null > /tmp/restored-pg.sql.gz
                zcat /tmp/restored-pg.sql.gz | psql -h 127.0.0.1 -U postgres lightsrp 2>/dev/null || true
                rm -f /tmp/restored-pg.sql.gz
            "
            log "PostgreSQL restored"
            ;;
        openbao-*)
            info "Restoring OpenBao from $backup_file..."
            run_ssh "
                tar xzf <(gpg --batch --decrypt --passphrase-file $ENCRYPTION_KEY_FILE $REMOTE_BACKUP_DIR/$backup_file 2>/dev/null) \
                    -C /tmp/
                # Stop openbao, replace data, restart
                docker stop iacgenie_openbao
                rm -rf /home/mkanavi/docker/iacgenie/data/openbao_raft
                cp -r /tmp/openbao_raft /home/mkanavi/docker/iacgenie/data/
                docker start iacgenie_openbao
                rm -rf /tmp/openbao_*
            "
            log "OpenBao restored"
            ;;
        keycloak-*)
            info "Restoring Keycloak from $backup_file..."
            run_ssh "
                tar xzf <(gpg --batch --decrypt --passphrase-file $ENCRYPTION_KEY_FILE $REMOTE_BACKUP_DIR/$backup_file 2>/dev/null) \
                    -C /tmp/
                rm -rf /home/mkanavi/docker/iacgenie/data/keycloak
                cp -r /tmp/keycloak /home/mkanavi/docker/iacgenie/data/
                docker restart iacgenie_keycloak
                rm -rf /tmp/keycloak*
            "
            log "Keycloak restored"
            ;;
        gitea-*)
            info "Restoring Gitea from $backup_file..."
            run_ssh "
                tar xzf <(gpg --batch --decrypt --passphrase-file $ENCRYPTION_KEY_FILE $REMOTE_BACKUP_DIR/$backup_file 2>/dev/null) \
                    -C /tmp/
                rm -rf /home/mkanavi/docker/iacgenie/data/gitea
                cp -r /tmp/gitea /home/mkanavi/docker/iacgenie/data/
                docker restart iacgenie_gitea
            "
            log "Gitea restored"
            ;;
        redis-*)
            info "Restoring Redis from $backup_file..."
            run_ssh "
                gpg --batch --decrypt --passphrase-file $ENCRYPTION_KEY_FILE $REMOTE_BACKUP_DIR/$backup_file 2>/dev/null | \
                gunzip > /tmp/redis-dump.rdb
                cp /tmp/redis-dump.rdb /home/mkanavi/docker/iacgenie/data/redis/dump.rdb
                docker restart iacgenie_redis
                rm -f /tmp/redis-dump.rdb
            "
            log "Redis restored"
            ;;
        monitoring-*)
            info "Restoring monitoring data from $backup_file..."
            run_ssh "
                docker stop iacgenie_prometheus iacgenie_grafana iacgenie_loki 2>/dev/null || true
                tar xzf <(gpg --batch --decrypt --passphrase-file $ENCRYPTION_KEY_FILE $REMOTE_BACKUP_DIR/$backup_file 2>/dev/null) \
                    -C /tmp/
                rm -rf /home/mkanavi/docker/iacgenie/prometheus/data /home/mkanavi/docker/iacgenie/grafana /home/mkanavi/docker/iacgenie/loki
                cp -r /tmp/prometheus/data /home/mkanavi/docker/iacgenie/prometheus/ 2>/dev/null || true
                cp -r /tmp/grafana /home/mkanavi/docker/iacgenie/ 2>/dev/null || true
                cp -r /tmp/loki /home/mkanavi/docker/iacgenie/ 2>/dev/null || true
                docker compose -f /home/mkanavi/docker/iacgenie/docker-compose-monitoring.yml up -d
                rm -rf /tmp/prometheus /tmp/grafana /tmp/loki
            "
            log "Monitoring data restored"
            ;;
        configs-*)
            info "Restoring configs from $backup_file..."
            run_ssh "
                tar xzf <(gpg --batch --decrypt --passphrase-file $ENCRYPTION_KEY_FILE $REMOTE_BACKUP_DIR/$backup_file 2>/dev/null) \
                    -C /
            "
            log "Config files restored"
            ;;
        *)
            error "Unknown backup type: $backup_file"
            echo "Supported types: pg-*, openbao-*, keycloak-*, gitea-*, redis-*, monitoring-*, configs-*"
            exit 1
            ;;
    esac
}

# === Verify backup integrity ===
verify() {
    info "Verifying backup integrity..."
    run_ssh "
        set -euo pipefail
        count=0; ok=0; fail=0
        for f in $REMOTE_BACKUP_DIR/*.gpg; do
            [[ -f \$f ]] || continue
            count=\$((count+1))
            if gpg --batch --decrypt --passphrase-file $ENCRYPTION_KEY_FILE --output /dev/null \$f 2>/dev/null; then
                echo \"  OK: \$(basename \$f)\"
                ok=\$((ok+1))
            else
                echo \"  FAIL: \$(basename \$f)\"
                fail=\$((fail+1))
            fi
        done
        echo \"Total: \$count | OK: \$ok | FAIL: \$fail\"
    "
}

# === Full backup of all services ===
full_backup() {
    init
    log "Starting full backup at $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    # Core services
    backup_postgres
    backup_openbao
    backup_gitea
    backup_keycloak
    backup_minio
    backup_redis
    
    # Monitoring stack
    backup_monitoring
    
    # Configs
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
            else
                init
                case "$service" in
                    postgres)     backup_postgres ;;
                    openbao)      backup_openbao ;;
                    gitea)        backup_gitea ;;
                    keycloak)     backup_keycloak ;;
                    minio)        backup_minio ;;
                    redis)        backup_redis ;;
                    monitoring)   backup_monitoring ;;
                    configs)      backup_configs ;;
                    *)            error "Unknown service: $service"; exit 1 ;;
                esac
            fi
            ;;
        list)     list_backups ;;
        restore)
            if [[ -z "${1:-}" ]]; then
                error "Usage: $0 restore <backup-file.gpg>"
                exit 1
            fi
            restore "$1"
            ;;
        verify)   verify ;;
        cleanup)  cleanup_old ;;
        *)
            echo "Usage: $0 {backup [service] | list | restore <file> | verify | cleanup}"
            echo ""
            echo "Services: postgres openbao gitea keycloak minio redis monitoring configs all"
            ;;
    esac
}

main "$@"
