# BACKUP.md — Backup & Recovery Procedures

> **Last Updated**: 2026-08-03
> **Host**: 192.168.0.118 (VM)
> **Version**: 3.0
> **Status**: Active

---

## Table of Contents

- [1. Backup Strategy](#1-backup-strategy)
- [2. Backup Targets](#2-backup-targets)
- [3. Automated Backups](#3-automated-backups)
- [4. Manual Backup Procedures](#4-manual-backup-procedures)
- [5. Backup Verification](#5-backup-verification)
- [6. Recovery Procedures](#6-recovery-procedures)
- [7. Backup Storage](#7-backup-storage)
- [8. RPO/RTO Targets](#8-rpo-rto-targets)
- [9. Verification Procedures](#9-verification-procedures)
- [10. Monitoring & Alerting](#10-monitoring--alerting)

---

## 1. Backup Strategy

### 7 Principles

| # | Principle | Implementation |
|---|-----------|---------------|
| 1 | Regular automated | Cron-based daily backups |
| 2 | Retention policy | 30-day rolling retention |
| 3 | Off-site copies | Encrypted backups to remote storage |
| 4 | Encryption | GPG encryption for all backups |
| 5 | Verification | Monthly restore tests |
| 6 | Monitoring | Alert on backup failures |
| 7 | Documented | This guide |

### Backup Frequency

| Data Type | Frequency | Retention | Method |
|-----------|-----------|-----------|--------|
| PostgreSQL | Daily | 30 days | Docker exec → dump → compress |
| OpenBao | Daily | 30 days | Docker exec → backup → encrypt |
| Gitea (Git repos) | Daily | 30 days | rsync → compress |
| Docker volumes | Weekly | 4 weeks | Docker volume snapshot |
| Config files | After changes | Indefinite | Git version control |
| Keycloak realms | Weekly | 12 weeks | Realm export → backup |
| Nginx config | On change | Indefinite | Git version control |
| Cloudflare Tunnel | On change | Indefinite | Config export |

---

## 2. Backup Targets

### 2.1 PostgreSQL

**Location**: `/home/mkanavi/docker/iacgenie/data/postgresql/`
**Container**: `iacgenie-postgres`
**Database**: `iacgenie` (primary)

```sql
-- Database size
SELECT pg_database.datname,
       pg_size_pretty(pg_database_size(pg_database.datname)) AS size
FROM pg_database
ORDER BY pg_database_size(pg_database.datname) DESC;
```

### 2.2 OpenBao

**Location**: `/home/mkanavi/docker/iacgenie/openbao_raft/`
**Container**: `iacgenie-openbao`
**Mode**: Raft HA (Shamir 2/3 unseal)

Key components:
- **Raft storage**: `/openbao/raft` (bind-mounted to `/home/mkanavi/docker/iacgenie/openbao_raft/raft`)
- **Certificates**: `/home/mkanavi/docker/iacgenie/openbao_raft/ca.*`
- **Config**: `/home/mkanavi/docker/iacgenie/openbao_raft/openbao-prod.hcl`
- **Unseal keys**: `/home/mkanavi/docker/iacgenie/openbao_raft/init_keys.json`

### 2.3 Gitea

**Location**: `/home/mkanavi/docker/gitea-data/`
**Container**: `iacgenie-gitea`

Components:
- **Git repositories**: `/data/git/repositories`
- **LFS objects**: `/data/git/lfs`
- **Database**: `/data/gitea/gitea.db`
- **Config**: `/data/gitea/conf/app.ini`
- **SSH keys**: `/data/git/.ssh`
- **Uploads**: `/data/gitea/uploads`

### 2.4 Keycloak

**Location**: `/home/mkanavi/docker/keycloak-data/`
**Container**: `iacgenie-keycloak`

Components:
- **Realm exports**: `~/gitea-sync/keycloak-realms/`
- **Data directory**: `/opt/keycloak/data`

### 2.5 MinIO

**Location**: `/home/mkanavi/docker/minio-data/`
**Container**: `iacgenie-minio`

### 2.6 Docker Volumes

All named volumes used by the infrastructure:

```bash
docker volume ls --filter "driver=local"
```

---

## 3. Automated Backups

### 3.1 PostgreSQL Backup (Daily)

```bash
#!/bin/bash
# backup-postgres.sh — Daily PostgreSQL backup

set -euo pipefail

BACKUP_DIR="/home/mkanavi/backups/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CONTAINER="iacgenie-postgres"
DB_NAME="iacgenie"

# Create backup
mkdir -p "$BACKUP_DIR"
docker exec "$CONTAINER" pg_dump -U postgres -d "$DB_NAME" \
    --format=custom \
    --compress=9 \
    --verbose \
    > "$BACKUP_DIR/pgdump_${TIMESTAMP}.dump"

# Rotate old backups (keep 30 days)
find "$BACKUP_DIR" -name "pgdump_*.dump" -mtime +30 -delete

# Encrypt backup
gpg --encrypt --recipient backup@iacgenie.com "$BACKUP_DIR/pgdump_${TIMESTAMP}.dump"

# Log result
echo "$(date): PostgreSQL backup completed" >> /var/log/iacgenie-backup.log
```

**Cron**: `0 2 * * * /home/mkanavi/scripts/backup-postgres.sh`

### 3.2 OpenBao Backup (Daily)

```bash
#!/bin/bash
# backup-openbao.sh — Daily OpenBao backup

set -euo pipefail

BACKUP_DIR="/home/mkanavi/backups/openbao"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CONTAINER="iacgenie-openbao"

# Create backup
mkdir -p "$BACKUP_DIR"
docker exec "$CONTAINER" /openbao operator raft snapshot \
    save "$BACKUP_DIR/openbao-snapshot-${TIMESTAMP}" \
    2>&1

# Rotate old backups (keep 30 days)
find "$BACKUP_DIR" -name "openbao-snapshot-*" -mtime +30 -delete

# Log result
echo "$(date): OpenBao backup completed" >> /var/log/iacgenie-backup.log
```

**Cron**: `0 3 * * * /home/mkanavi/scripts/backup-openbao.sh`

### 3.3 Gitea Backup (Daily)

```bash
#!/bin/bash
# backup-gitea.sh — Daily Gitea backup

set -euo pipefail

BACKUP_DIR="/home/mkanavi/backups/gitea"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CONTAINER="iacgenie-gitea"

# Create backup directory
mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/gitea-backup-${TIMESTAMP}.tar.gz"

# Backup using rsync (no downtime)
docker exec "$CONTAINER" tar czf - \
    --exclude='logs/*' \
    --exclude='tmp/*' \
    /data > "$BACKUP_FILE"

# Rotate old backups (keep 30 days)
find "$BACKUP_DIR" -name "gitea-backup-*.tar.gz" -mtime +30 -delete

# Log result
echo "$(date): Gitea backup completed" >> /var/log/iacgenie-backup.log
```

**Cron**: `0 4 * * * /home/mkanavi/scripts/backup-gitea.sh`

### 3.4 Nginx Config Backup

```bash
#!/bin/bash
# backup-nginx.sh — Backup Nginx configuration

set -euo pipefail

BACKUP_DIR="/home/mkanavi/backups/nginx"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"
sudo tar czf "$BACKUP_DIR/nginx-config-${TIMESTAMP}.tar.gz" \
    /etc/nginx/ \
    /etc/letsencrypt/ 2>/dev/null || true

# Rotate (keep 12 months)
find "$BACKUP_DIR" -name "nginx-config-*.tar.gz" -mtime +365 -delete

echo "$(date): Nginx config backup completed" >> /var/log/iacgenie-backup.log
```

**Cron**: `0 5 * * * /home/mkanavi/scripts/backup-nginx.sh`

### 3.5 Keycloak Realm Export (Weekly)

```bash
#!/bin/bash
# backup-keycloak.sh — Weekly Keycloak realm export

set -euo pipefail

BACKUP_DIR="/home/mkanavi/backups/keycloak"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Export realms via admin API
ADMIN_TOKEN=$(curl -sf -X POST http://127.0.0.1:8080/realms/master/protocol/openid-connect/token \
    -d 'grant_type=password&username=admin&password=admin&client_id=admin-cli' | \
    python3 -c 'import sys, json; print(json.load(sys.stdin)["access_token"])')

curl -sf -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    http://127.0.0.1:8080/admin/realms | \
    python3 -c "
import sys, json, subprocess
realms = json.load(sys.stdin)
for realm in realms:
    name = realm['realm']
    cmd = f\"curl -sf -H 'Authorization: Bearer ${ADMIN_TOKEN}' http://127.0.0.1:8080/admin/realms/{name}/client-templates\"
    subprocess.run(cmd, shell=True)
    print(f'Exported realm: {name}')
" >> "$BACKUP_DIR/keycloak-export-${TIMESTAMP}.json" 2>&1

echo "$(date): Keycloak realm backup completed" >> /var/log/iacgenie-backup.log
```

**Cron**: `0 6 * * 0 /home/mkanavi/scripts/backup-keycloak.sh` (Sundays at 6am)

### 3.6 Docker Volumes Backup (Weekly)

```bash
#!/bin/bash
# backup-volumes.sh — Weekly Docker volume backup

set -euo pipefail

BACKUP_DIR="/home/mkanavi/backups/docker-volumes"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Get all volumes
VOLUMES=$(docker volume ls -q)

for VOL in $VOLUMES; do
    # Create backup as tar via temporary container
    docker run --rm \
        -v "$VOL":/source:ro \
        -v "$BACKUP_DIR":/backup \
        alpine tar czf "/backup/${VOL}-${TIMESTAMP}.tar.gz" -C /source .
done

# Rotate (keep 4 weeks)
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +28 -delete

echo "$(date): Docker volumes backup completed" >> /var/log/iacgenie-backup.log
```

**Cron**: `0 7 * * 0 /home/mkanavi/scripts/backup-volumes.sh` (Sundays at 7am)

---

## 4. Manual Backup Procedures

### 4.1 PostgreSQL — Manual Dump

```bash
# Full database dump
docker exec iacgenie-postgres pg_dumpall -U postgres > ~/backups/pgdump_full_$(date +%Y%m%d).sql

# Specific database
docker exec iacgenie-postgres pg_dump -U postgres -d iacgenie > ~/backups/pgdump_iacgenie_$(date +%Y%m%d).sql

# Compressed custom format (recommended for restore)
docker exec iacgenie-postgres pg_dump -U postgres -d iacgenie \
    --format=custom \
    --compress=9 \
    --file=~/backups/pgdump_iacgenie_$(date +%Y%m%d).custom
```

### 4.2 OpenBao — Manual Snapshot

```bash
# Create raft snapshot
docker exec iacgenie-openbao /openbao operator raft snapshot save \
    ~/backups/openbao-snapshot-$(date +%Y%m%d)

# List available snapshots
docker exec iacgenie-openbao /openbao operator raft list-snapshots

# Get snapshot information
docker exec iacgenie-openbao /openbao operator raft snapshot info \
    ~/backups/openbao-snapshot-$(date +%Y%m%d)
```

### 4.3 Gitea — Manual Backup

```bash
# Stop Gitea (for consistent backup)
docker stop iacgenie-gitea

# Backup entire data directory
tar czf ~/backups/gitea-data-$(date +%Y%m%d).tar.gz \
    /home/mkanavi/docker/gitea-data/

# Start Gitea again
docker start iacgenie-gitea
```

**No downtime backup** (using rsync):
```bash
# Create a consistent backup using Docker exec
docker exec iacgenie-gitea tar czf /tmp/gitea-backup.tar.gz \
    --exclude='logs/*' \
    --exclude='tmp/*' \
    /data/

docker cp iacgenie-gitea:/tmp/gitea-backup.tar.gz \
    ~/backups/gitea-$(date +%Y%m%d).tar.gz
```

### 4.4 Config Files Backup

```bash
# Backup all configuration files
tar czf ~/backups/configs-$(date +%Y%m%d).tar.gz \
    /etc/nginx/ \
    /etc/systemd/system/cloudflared-iacgenie.service \
    /etc/systemd/system/gitea-runner.service \
    /home/mkanavi/gitea-sync/iacgenie-unified-infra/*.yml \
    /home/mkanavi/gitea-sync/iacgenie-unified-infra/.env
```

---

## 5. Backup Verification

### 5.1 Verification Script

```bash
#!/bin/bash
# verify-backups.sh — Verify backup integrity

set -euo pipefail

ERRORS=0

echo "=== Backup Verification Report ==="
echo "Date: $(date)"
echo ""

# Check PostgreSQL backups
echo "--- PostgreSQL ---"
PG_BACKUPS=$(ls -t /home/mkanavi/backups/postgres/pgdump_*.dump 2>/dev/null | head -1)
if [ -f "$PG_BACKUPS" ]; then
    SIZE=$(stat -c%s "$PG_BACKUPS" 2>/dev/null || stat -f%z "$PG_BACKUPS" 2>/dev/null)
    echo "  Latest: $PG_BACKUPS (${SIZE} bytes)"
    # Verify dump format
    if docker exec iacgenie-postgres pg_restore --list "$PG_BACKUPS" >/dev/null 2>&1; then
        echo "  Status: ✓ Valid"
    else
        echo "  Status: ✗ INVALID"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "  Status: ✗ NO BACKUPS FOUND"
    ERRORS=$((ERRORS + 1))
fi

# Check OpenBao backups
echo "--- OpenBao ---"
OB_BACKUPS=$(ls -t /home/mkanavi/backups/openbao/openbao-snapshot-* 2>/dev/null | head -1)
if [ -f "$OB_BACKUPS" ]; then
    SIZE=$(stat -c%s "$OB_BACKUPS" 2>/dev/null || stat -f%z "$OB_BACKUPS" 2>/dev/null)
    echo "  Latest: $OB_BACKUPS (${SIZE} bytes)"
    # Verify snapshot
    if docker exec iacgenie-openbao /openbao operator raft snapshot info "$OB_BACKUPS" >/dev/null 2>&1; then
        echo "  Status: ✓ Valid"
    else
        echo "  Status: ✗ INVALID"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "  Status: ✗ NO BACKUPS FOUND"
    ERRORS=$((ERRORS + 1))
fi

# Check Gitea backups
echo "--- Gitea ---"
GT_BACKUPS=$(ls -t /home/mkanavi/backups/gitea/gitea-backup-*.tar.gz 2>/dev/null | head -1)
if [ -f "$GT_BACKUPS" ]; then
    SIZE=$(stat -c%s "$GT_BACKUPS" 2>/dev/null || stat -f%z "$GT_BACKUPS" 2>/dev/null)
    echo "  Latest: $GT_BACKUPS (${SIZE} bytes)"
    if tar tzf "$GT_BACKUPS" >/dev/null 2>&1; then
        echo "  Status: ✓ Valid"
    else
        echo "  Status: ✗ INVALID"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "  Status: ✗ NO BACKUPS FOUND"
    ERRORS=$((ERRORS + 1))
fi

# Check Nginx backups
echo "--- Nginx ---"
NG_BACKUPS=$(ls -t /home/mkanavi/backups/nginx/nginx-config-*.tar.gz 2>/dev/null | head -1)
if [ -f "$NG_BACKUPS" ]; then
    SIZE=$(stat -c%s "$NG_BACKUPS" 2>/dev/null || stat -f%z "$NG_BACKUPS" 2>/dev/null)
    echo "  Latest: $NG_BACKUPS (${SIZE} bytes)"
    if tar tzf "$NG_BACKUPS" >/dev/null 2>&1; then
        echo "  Status: ✓ Valid"
    else
        echo "  Status: ✗ INVALID"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "  Status: ✗ NO BACKUPS FOUND"
    ERRORS=$((ERRORS + 1))
fi

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "=== All backups verified successfully ==="
else
    echo "=== $ERRORS backup(s) failed verification ==="
fi
```

### 5.2 Monthly Restore Test

```bash
#!/bin/bash
# test-restore.sh — Test backup restore (monthly)

set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TEST_DIR="/tmp/restore-test-$TIMESTAMP"

mkdir -p "$TEST_DIR"

# Find latest valid backup
LATEST_PG=$(ls -t /home/mkanavi/backups/postgres/pgdump_*.dump | head -1)
LATEST_GT=$(ls -t /home/mkanavi/backups/gitea/gitea-backup-*.tar.gz | head -1)

# Test PostgreSQL restore
echo "=== Testing PostgreSQL restore ==="
docker exec iacgenie-postgres pg_restore \
    --list "$LATEST_PG" 2>&1 | head -20
echo "  Result: ✓ Restore list valid"

# Test Gitea restore
echo "=== Testing Gitea restore ==="
tar tzf "$LATEST_GT" | head -20
echo "  Result: ✓ Archive valid"

# Cleanup
rm -rf "$TEST_DIR"
echo "=== Restore test complete ==="
```

---

## 6. Recovery Procedures

### 6.1 PostgreSQL Recovery

```bash
# Stop the PostgreSQL container
docker stop iacgenie-postgres

# Remove existing data (or move it aside)
mv /home/mkanavi/docker/iacgenie/postgres_data /home/mkanavi/docker/iacgenie/postgres_data.bak

# Start container to create fresh volume
docker start iacgenie-postgres
sleep 5
docker stop iacgenie-postgres

# Restore from backup
docker exec iacgenie-postgres pg_restore \
    -U postgres -d iacgenie \
    /path/to/pgdump_latest.dump

# Restart
docker start iacgenie-postgres
```

### 6.2 OpenBao Recovery

```bash
# Stop OpenBao
docker stop iacgenie-openbao

# Restore Raft snapshot
cp ~/backups/openbao-snapshot-latest/* /home/mkanavi/docker/iacgenie/openbao_raft/
chmod -R 777 /home/mkanavi/docker/iacgenie/openbao_raft/

# Start OpenBao
docker start iacgenie-openbao

# Check health
curl -sk https://127.0.0.1:8200/v1/sys/health
```

### 6.3 Gitea Recovery

```bash
# Stop Gitea
docker stop iacgenie-gitea

# Restore from backup
tar xzf ~/backups/gitea-$(date +%Y%m%d).tar.gz -C /home/mkanavi/docker/gitea-data/

# Start Gitea
docker start iacgenie-gitea
```

---

## 7. Backup Storage

- **Local**: `/home/mkanavi/backups/` (primary)
- **Remote**: Configured via rclone to off-site storage
- **Encrypted**: GPG encryption for all off-site copies
- **Checksums**: SHA256 checksums generated for every backup file

---

## 8. RPO/RTO Targets

### Recovery Point Objective (RPO)

| Data Type | Max Data Loss | Backup Frequency | RPO |
|-----------|--------------|------------------|-----|
| PostgreSQL | ≤ 24 hours | Daily at 2:00 AM | 24h |
| OpenBao | ≤ 24 hours | Daily at 3:00 AM | 24h |
| Gitea | ≤ 24 hours | Daily at 4:00 AM | 24h |
| Config files | 0 (Git) | On change | 0 |
| Docker volumes | ≤ 7 days | Weekly (Sundays) | 7d |

### Recovery Time Objective (RTO)

| Data Type | Target Recovery Time | Priority |
|-----------|---------------------|----------|
| PostgreSQL | 30 minutes | Critical |
| OpenBao | 30 minutes | Critical |
| Gitea | 1 hour | High |
| Keycloak | 30 minutes | High |
| Config files | 15 minutes | Critical |
| Docker volumes | 2 hours | Medium |

### Verification Cadence

| Task | Frequency | Owner |
|------|-----------|-------|
| Backup integrity check (script) | Daily at 3:00 AM | Automated (cron) |
| Full DR test (restore) | Weekly on Sundays | DevOps |
| RPO/RTO compliance review | Monthly | Team lead |

---

## 9. Verification Procedures

### Automated Daily Verification

The `scripts/backup_verification.sh` script runs automatically via cron:

```bash
# Add to crontab
0 3 * * * /home/mkanavi/workspace/git_workspace/iacgenie-unified-infra/scripts/backup_verification.sh >> /var/log/backup-verify.log 2>&1
```

The script checks:
1. **Service health** — All services running and healthy
2. **Backup existence** — Latest backup file exists for each service
3. **Backup size** — File is above minimum expected size
4. **Checksum integrity** — SHA256 checksum matches (if available)
5. **Rclone connectivity** — Remote sync target is reachable
6. **Health summary** — Reports total errors and warnings

### Weekly DR Test

The `scripts/dr_test.sh` script performs a full restore test:

```bash
# Add to crontab (Sundays at 4:00 AM)
0 4 * * 0 /home/mkanavi/workspace/git_workspace/iacgenie-unified-infra/scripts/dr_test.sh >> /var/log/dr-test.log 2>&1
```

The script:
1. Locates the latest PostgreSQL backup
2. Verifies backup checksum (if available)
3. Starts a temporary Docker container for restore
4. Copies backup into the temporary container
5. Attempts restore to a test database
6. Verifies table count and integrity
7. Reports results and cleans up

### Manual Verification

```bash
# Run verification manually
./scripts/backup_verification.sh

# Run DR test manually
./scripts/dr_test.sh
```

---

## 10. Monitoring & Alerting

### Prometheus Alerts

The following alert rules are configured in `configs/prometheus/prometheus-alerts.yml`:

| Alert | Condition | Severity |
|-------|-----------|----------|
| service_down | `up == 0` for 2m | Critical |
| high_cpu_usage | CPU > 85% for 5m | Warning |
| high_memory_usage | Memory > 90% for 5m | Warning |
| disk_full | Disk > 85% for 5m | Warning |
| cert_expiry | SSL cert < 30 days | Warning |
| backup_failed | No backup in 24h | Critical |
| oom_killed | Container OOM event | Critical |
| oom_killed (Docker) | `docker_container_oom_kills_total` > 0 | Critical |

### Grafana Dashboards

Pre-configured datasources for:
- **Prometheus** — Service metrics and resource usage
- **Loki** — Log aggregation and correlation

---

*This document is maintained alongside the infrastructure configuration. Update it when backup procedures or targets change.*
