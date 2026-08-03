# Deployment & Backup Guide

## Overview

IacGenie unified infrastructure runs on VM `192.168.0.118` (15GB RAM, Ubuntu). All services managed via Docker Compose with dependency-ordered startup, health check gates, and automated backups.

---

## Quick Start

### Start All Services

```bash
# Full dependency-ordered deployment (postgres → redis → minio → openbao → keycloak → gitea → searxng → nsqd → app services)
/opt/infra/deploy.sh up
```

### Restart a Specific Service

```bash
/opt/infra/deploy.sh restart postgres
/opt/infra/deploy.sh restart lightserp-api
```

### Force Recreate (apply config changes)

```bash
/opt/infra/deploy.sh force-recreate       # All services
/opt/infra/deploy.sh force-recreate nginx  # Single service
```

### Rollback

```bash
# Rollback a single service
/opt/infra/rollback.sh postgres

# Rollback all app services
/opt/infra/rollback.sh

# Rollback everything
/opt/infra/rollback.sh --all
```

---

## Service Dependency Order

```
Tier 1 (Core)  → postgres
Tier 1 (Core)  → redis
Tier 1 (Core)  → minio
Tier 1 (Core)  → openbao
Tier 1 (Core)  → keycloak
Tier 1 (Core)  → gitea
Tier 1 (Core)  → searxng
Tier 1 (Core)  → nsqd
Tier 2 (App)   → lightserp-api    (depends on: postgres, redis, minio, openbao)
Tier 2 (App)   → lightserp-webui  (depends on: lightserp-api)
Tier 2 (App)   → pagezen          (depends on: lightserp-api)
```

The deploy script starts services in this order automatically, waiting for each to pass its health gate before proceeding.

---

## Health Checks

Each service has a dedicated health check endpoint:

| Service       | Endpoint                              | Port |
|---------------|---------------------------------------|------|
| PostgreSQL    | `http://127.0.0.1:5432`              | 5432 |
| Redis         | `http://127.0.0.1:6379`              | 6379 |
| MinIO         | `http://127.0.0.1:9001/.../health`   | 9001 |
| OpenBao       | `http://127.0.0.1:8200/v1/sys/health`| 8200 |
| Keycloak      | `http://127.0.0.1:8080/auth/...`     | 8080 |
| Gitea         | `http://127.0.0.1:3000/api/healthz`   | 3000 |
| SearXNG       | `http://127.0.0.1:8081/search`       | 8081 |
| NSQD          | `http://127.0.0.1:4161/nsqstat`      | 4161 |
| LightSerp API | `http://127.0.0.1:3071/health`       | 3071 |
| LightSerp Web | `http://127.0.0.1:3070/health`       | 3070 |
| PageZen       | `http://127.0.0.1:8076/health`       | 8076 |

Health checks run with 30 retry attempts (2s interval = ~60s max wait).

---

## Backup System

### OpenBao Backup

**Script:** `/opt/backup/openbao-backup.sh`
**Python helper:** `/opt/backup/backup_openbao.py`
**Cron:** `0 */6 * * *` (every 6 hours)
**Logs:** `/home/mkanavi/logs/openbao-cron.log`

Backup flow:
1. Health check (reject if OpenBao is sealed)
2. Trigger raft snapshot (manual mode)
3. Copy `raft.db` to backup directory
4. Copy existing snapshots
5. Full tar backup of raft data directory
6. Retention: 7 days (auto-cleanup)

**Manual trigger:**
```bash
/home/mkanavi/docker/iacgenie/scripts/openbao-backup.sh manual
```

### Backup Locations

| Item                     | Path                                           |
|--------------------------|------------------------------------------------|
| Raft data                | `/home/mkanavi/docker/iacgenie/openbao_raft/` |
| Recent snapshots         | `/home/mkanavi/docker/iacgenie/openbao_raft/backups/` |
| Full backups (7-day)     | `/home/mkanavi/backups/openbao/`              |
| Backup script            | `/opt/backup/openbao-backup.sh`               |
| Python backup helper     | `/opt/backup/backup_openbao.py`               |
| Backup logs              | `/home/mkanavi/logs/openbao-*.log`            |

---

## File Locations

| Item                     | Path                                           |
|--------------------------|------------------------------------------------|
| Compose (main)           | `/home/mkanavi/workspace/git_workspace/iacgenie-unified-infra/docker-compose-unified.yml` |
| Compose (LightSerp)      | `.../docker-compose-lightsrp.yml`              |
| Deploy script            | `/opt/infra/deploy.sh`                         |
| Rollback script          | `/opt/infra/rollback.sh`                       |
| OpenBao backup           | `/opt/backup/openbao-backup.sh`                |
| OpenBao Python backup    | `/opt/backup/backup_openbao.py`                |
| Deploy logs              | `/var/log/iacgenie/`                           |
| Deployment lock          | `/tmp/iacgenie-deploy.lock`                    |

---

## Resource Limits

All services have memory+C上大CPU limits defined in `docker-compose-unified.yml`:

| Service       | Memory | CPU  |
|---------------|--------|------|
| PostgreSQL    | 1.5G   | 0.5  |
| Redis         | 256M   | 0.25 |
| MinIO         | 512M   | 0.5  |
| OpenBao       | 512M   | 0.5  |
| Keycloak      | 1G     | 1.0  |
| Gitea         | 512M   | 0.5  |
| SearXNG       | 512M   | 0.5  |
| NSQD          | 256M   | 0.25 |
| LightSerp API | 1G     | 0.5  |
| LightSerp Web | 512M   | 0.25 |
| PageZen       | 256M   | 0.25 |

**Total allocated:** ~6.5G of 15GB available.

---

## Troubleshooting

### Deployment stuck at health check
```bash
# Check which service is failing
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -v healthy

# Check service logs
docker logs iacgenie-<service> --tail 50
```

### Another deployment running
```bash
# Check lock file
cat /tmp/iacgenie-deploy.lock

# Force remove (only if process is dead)
sudo rm /tmp/iacgenie-deploy.lock
```

### OpenBao sealed — can't backup
```bash
# Check health
curl -k https://127.0.0.1:8200/v1/sys/health

# If sealed, need to unseal manually
/opt/backup/openbao-backup.sh
# Exit code 2 = sealed, cannot backup
```

---

## Phase 1 Tasks Completed

| Task                                    | Status |
|-----------------------------------------|--------|
| PHASE 1.1: Set backup directory structure | ✅ Done |
| PHASE 1.2: Set resource limits on Docker services | ✅ Done |
| PHASE 1.3: Create deployment script with health gates | ✅ Done |
| PHASE 1.4: Write OpenBao backup script (Raft snapshot) | ✅ Done |
| PHASE 1.5: Create Docker health check script | ✅ Done |
