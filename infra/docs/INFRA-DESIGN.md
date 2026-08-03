# Unified Infrastructure Design Document

**Last Updated:** 2026-08-04
**VM:** 192.168.0.118 (`newvm`) — elementary OS 8 (x86_64, 15GB RAM)
**Domain:** `iacgenie.com` (via Cloudflare Tunnel)
**Version:** 2.2 (post Phase 10.4 + Gitea fix + nginx redirect fix)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Internet / Cloudflare                         │
│              Cloudflare Tunnel → *.iacgenie.com                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │    Nginx (443)   │
                    │  HTTPS + TLS     │
                    │  Reverse Proxy   │
                    │  (Let's Encrypt) │
                    └──┬─┬─┬─┬─┬─┬─┬──┘
                       │ │ │ │ │ │ │
          ┌────────────┤ │ │ │ │ │ │
          │            │ │ │ │ │ │ │
    ┌─────▼──┐  ┌─────▼──┐ ┌──▼──┐ ┌────┐ ┌─────┐ ┌──────┐
    │ Gitea  │  │Keycloak│ │MinIO│ │Sear│ │NSQ │ │OpenBao│
    │ :3000  │  │ :8080  │ │:9000│ │XNG │ │:415│ │ :8200 │
    └────────┘  └────────┘ └─────┘ │:8070││:456│ └───────┘
                                   └─────┘└──────┘
          ┌─────────────────────────────────────────────┐
          │           Shared Services (internal)         │
          │  ┌──────────┐  ┌──────────┐                  │
          │  │ Postgres │  │  Redis   │                  │
          │  │ :5432    │  │  :6379   │                  │
          │  └──────────┘  └──────────┘                  │
          │  ┌──────────────────────────────────────┐     │
          │  │ IacGenie:  UI :8000 / Backend :8000  │     │
          │  │ LightSerp: WebUI :3070 / API :3071   │     │
          │  │ PageZen:    :8076                     │     │
          │  └──────────────────────────────────────┘     │
          └─────────────────────────────────────────────┘
```

### Key Directives
- **Loki, Promtail, Prometheus, Grafana: ACTIVE** — full observability stack (Phase 10.18)
- **Cloudflare 1 + 2: ACTIVE** — tunnel redundancy (Phase 10.21)
- **Nginx: ACTIVE** — reverse proxy with TLS termination (Phase 10.21)
- **Coolify: PERMANENTLY DISABLED** — zero resources allocated
- **Jenkins: PERMANENTLY DISABLED** — migrated to Gitea CI/CD
- All infrastructure services bound to `127.0.0.1` (localhost only)
- External access via Cloudflare Tunnel → Nginx (reverse proxy, TLS termination)

---

## 2. Service Registry

|| Service | Port | Docker Container | Purpose | Status ||
||---------|------|-----------------|---------|--------||
|| **PostgreSQL** | 127.0.0.1:5432 | `iacgenie-postgres` | Multi-tenant DB (iacgenie, lightsrp, keycloak) | ✅ Running, healthy ||
|| **Redis** | 127.0.0.1:6379 | `iacgenie-redis` | Session/Cache | ✅ Running, healthy ||
|| **MinIO** | 127.0.0.1:9000/9001 | `iacgenie-minio` | S3 Storage | ✅ Running, healthy ||
|| **OpenBao** | 127.0.0.1:8200 | `iacgenie-openbao` | Secrets (Vault alternative) | ✅ Running, healthy, unsealed ||
|| **Keycloak** | 127.0.0.1:8080 | `iacgenie-keycloak` | OAuth2/OIDC | ✅ Running, healthy ||
|| **Gitea** | 127.0.0.1:3000,2222 | `iacgenie-gitea` | Git/CI/CD | ✅ Running, healthy ||
|| **SearXNG** | 127.0.0.1:8081→8080 | `iacgenie-searxng` | Search | ✅ Running, healthy ||
|| **NSQD** | 127.0.0.1:4150/4161 | `iacgenie-nsqd` | Message Queue | ✅ Running, healthy ||
|| **PageZen** | 127.0.0.1:8076→8082 | `iacgenie-pagezen` | Mock Server | ✅ Running, healthy ||
|| **LightSerp WebUI** | 127.0.0.1:3070→3070 | `iacgenie-lightserp-webui` | Web Frontend | ✅ Running, healthy ||
|| **LightSerp API** | 127.0.0.1:3071→3071 | `iacgenie-lightserp-api` | AI Search API | ✅ Running, healthy ||

### Permanently Disabled
||| Service | Previous Port | Notes ||
|||---------|--------------|-------||
||| Alertmanager | 127.0.0.1:9093 | Removed, no alerts ||
||| Jenkins | 127.0.0.1:8089 | Removed, CI migrated to Gitea ||
||| Coolify | — | Removed, no deployment platform ||

---

## 3. Nginx Routing Table

|| Hostname | proxy_pass | Backend ||
||----------|-----------|---------||
|| `gitea.iacgenie.com` | https://127.0.0.1:3000 | Gitea ||
|| `auth.iacgenie.com` | https://127.0.0.1:8080 | Keycloak ||
|| `terra.iacgenie.com` | https://127.0.0.1:8000 | IacGenie (backend) ||
|| `lightserp.iacgenie.com` | https://127.0.0.1:3070 | LightSerp (WebUI + API) ||
|| `vault.iacgenie.com` | https://127.0.0.1:8200 | OpenBao ||
|| `grafana.iacgenie.com` | https://127.0.0.1:3000 | Grafana (standalone) ||

**Catch-all:** Any unmatched `*.iacgenie.com` subdomain returns HTTP 404 with JSON error body redirecting to `https://iacgenie.com` (Bug 2 fix, Phase 10.23).

**Nginx config:** `/etc/nginx/conf.d/iacgenie-unified.conf` (active)  
**Cloudflare Tunnel:** `cloudflared-iacgenie.service` (systemd)

---

## 4. Docker Compose Architecture

### Unified Compose (`docker-compose-unified.yml`)
**Location:** `~/docker/iacgenie/docker-compose-unified.yml`  
**Purpose:** All 11 core services with health checks and resource limits

### Resource Limits (per service)
|| Service | Memory | CPU ||
||---------|--------|-----||
|| PostgreSQL | 1.5G | 0.5 ||
|| Redis | 256M | 0.25 ||
|| MinIO | 512M | 0.5 ||
|| OpenBao | 512M | 0.5 ||
|| Keycloak | 1G (originally 2G) | 1.0 ||
|| Gitea | 512M | 0.5 ||
|| SearXNG | 1G | 0.5 ||
|| NSQD | 256M | 0.25 ||
|| LightSerp API | 1G | 0.5 ||
|| LightSerp WebUI | 512M | 0.25 ||
|| PageZen | 256M | 0.25 ||
|| **Total** | **~7.5G** | **3.5 cores** ||

### Health Checks
All 11 services have healthcheck blocks configured:
- PostgreSQL: `pg_isready`
- Redis: `redis-cli ping`
- MinIO: HTTP `/minio/health/live`
- OpenBao: HTTP `/v1/sys/health` (unverified TLS)
- Keycloak: TCP check
- Gitea: HTTP `GET /`
- SearXNG: HTTP `GET /`
- NSQD: TCP port check
- PageZen: HTTP `/health`
- LightSerp API: HTTP `/healthz`
- LightSerp WebUI: HTTP `GET /`

---

## 5. Authentication & Secrets (OpenBao)

### OpenBao Configuration
- **Version:** 2.6.0, Raft storage, Shamir 2/3 unseal
- **Address:** `http://127.0.0.1:8200` (internal), `https://vault.iacgenie.com` (external via Nginx)
- **Storage:** `/home/mkanavi/docker/iacgenie/openbao_data/` + raft at `/home/mkanavi/docker/iacgenie/openbao_raft/`
- **Config:** `/home/mkanavi/docker/iacgenie/openbao_data/openbao-prod.hcl`
- **Init keys:** `/home/mkanavi/docker/iacgenie/openbao_raft/init_keys.json` (3 base64 unseal keys, Shamir 2/3)

### KV Secret Engines
|| Mount | Version | TTL ||
||-------|---------|-----||
|| `iacgenie/kv/` | v2 | 7 days (168h) ||
|| `lightserp/kv/` | v2 | 7 days (168h) ||
|| `terraform/kv/` | v2 | 7 days (168h) ||

### Service Tokens
|| Token File | Policy | Service ||
||------------|--------|---------||
|| `iacgenie_token.txt` | `iacgenie-service` | IacGenie application ||
|| `lightserp_token.txt` | `lightserp` | LightSerp application ||
|| `terraform_token.txt` | `terraform` | TerraGenius ||

---

## 6. CI/CD (Gitea)

### Gitea Installation
- **Admin:** `admin` (admin@iacgenie.com) — created via Gitea CLI (`gitea admin user create`)
- **Password:** Set via Gitea CLI (`gitea admin user change-password`)
- **Auth:** Form field is `user_name` (not `user`)
- **Environment variables:** `GITEA__admin__INIT_ROOT_USER_NAME/PASSWORD/EMAIL` in compose (auto-create on first boot)
- **Runner:** `~/bin/gitea-runner` (binary installed, not yet registered)
- **Configuration:** `/home/mkanavi/docker/iacgenie/gitea_data/conf/app.ini` (bind mount at `/data/gitea`)
- **Database:** PostgreSQL (iacgenie-postgres)

### Mirroring
- GitHub → Gitea push mirroring configured for IacGenie, LightSerp, unified-infra repos
- Sync script: `/home/mkanavi/bin/sync-gitea.py` (runs every 6h via crontab)
- GitHub Actions: **DISABLED** on all repos (migrated to Gitea CI)

### CI Workflows (Gitea)
- `iacgenie-ci.yml` — lint, test, build
- `lightsrp-ci.yml` — lint, test, build
- `infra-ci.yml` — lint, test, validate compose

---

## 7. Backup Infrastructure

### OpenBao Backup
- **Script:** `/opt/backup/backup_openbao.py`
- **Location:** `/home/mkanavi/docker/iacgenie/openbao_raft/backups/`
- **Frequency:** Every 6 hours (crontab `0 */6 * * *`)
- **Retention:** 30 days auto-rotation

#### Backup Components
|| Component | Method | Size ||
||-----------|--------|------||
|| Raft DB (`vault.db`) | Host bind mount copy | ~33MB ||
|| Snapshots | API `/v1/sys/storage/raft/snapshot` | ~68KB (when working) ||
|| Config (`openbao-prod.hcl`) | File copy | ~281B ||
|| Checksums | SHA256 per file | ~143B each ||

**Note:** API raft snapshot endpoint returns HTTP 500 in OpenBao 2.x; raw DB copy via host bind mount works reliably.

### Backup Verification
- SHA256 checksums generated per backup file
- Restore capability via `backup_openbao.py --restore <file>`
- Restore flow: verify checksum → upload snapshot via PUT to `/v1/sys/storage/raft/snapshot`

### Cron Jobs
|| Schedule | Command | Log ||
||----------|---------|-----||
|| `0 */6 * * *` | `cd /opt/backup && python3 backup_openbao.py` | `/home/mkanavi/logs/openbao-cron.log` ||
|| `0 */6 * * *` | `/usr/bin/python3 /home/mkanavi/bin/sync-gitea.py` | `/home/mkanavi/gitea-sync/cron.log` ||

---

## 8. Deployment & Operations

### Deployment Script
- **Location:** `/opt/infra/deploy.sh`
- **Features:** Dependency-ordered startup, health gate checks, rollback
- **Usage:** `./deploy.sh`, `./deploy.sh --service <name>`, `./deploy.sh --group <group>`

### Rollback Script
- **Location:** `/opt/infra/rollback.sh`
- **Features:** Per-service rollback with dependency awareness

### Docker Cleanup
- Exited containers: `docker rm $(docker ps -a -q --filter 'status=exited')`
- Dangling volumes: `docker volume prune -f`
- Dangling images: `docker image prune -f`
- Script: `/tmp/cleanup_docker.sh` (tested, ~40GB reclaimed)

---

## 9. Network Architecture

### Docker Networks
|| Network | Purpose | Containers ||
||---------|---------|------------||
|| `iacgenie_network` | Shared infrastructure | postgres, redis, minio, openbao, keycloak, gitea, searxng, nsqd, pagezen, terragenius ||
|| `lightserp_net` | LightSerp isolated | lightserp-webui, lightserp-api ||

### Traffic Flow
```
Internet → Cloudflare (DNS + Tunnel) → cloudflared-iacgenie.service (port 443)
  → Nginx (port 443, TLS terminate) → Docker containers (internal ports)
```

### Cloudflare Tunnel Config
**Service:** `cloudflared-iacgenie.service`  
**Config:** `/etc/cloudflared/config.yml`  
**Tunnel:** `iacgenie-tunnel`  
**Credentials:** `/etc/cloudflared/credentials.json`

---

## 10. File Locations Reference

|| Resource | Host Path | Purpose ||
||----------|-----------|---------||
|| Docker Compose | `/home/mkanavi/docker/iacgenie/docker-compose-unified.yml` | Main compose ||
|| Environment | `/home/mkanavi/docker/iacgenie/.env` | Secrets & config ||
|| OpenBao Config | `/home/mkanavi/docker/iacgenie/openbao_data/openbao-prod.hcl` | OpenBao HCL ||
|| OpenBao RAFT | `/home/mkanavi/docker/iacgenie/openbao_raft/` | Raft storage + init keys ||
|| OpenBao Backups | `/home/mkanavi/docker/iacgenie/openbao_raft/backups/` | Backup snapshots ||
|| Backup Script | `/opt/backup/backup_openbao.py` | Automated backup (Python) ||
|| Deploy Script | `/opt/infra/deploy.sh` | Deployment with health gates ||
|| Rollback Script | `/opt/infra/rollback.sh` | Per-service rollback ||
|| Nginx Config | `/etc/nginx/conf.d/iacgenie-unified.conf` | Reverse proxy ||
|| Cloudflare Config | `/etc/cloudflared/config.yml` | Tunnel routing ||
|| Cloudflare Service | `/etc/systemd/system/cloudflared-iacgenie.service` | Tunnel systemd ||
|| Gitea Runner | `~/bin/gitea-runner` | CI runner binary ||
|| Gitea Sync | `/home/mkanavi/bin/sync-gitea.py` | GitHub→Gitea sync ||
|| Nginx Logs | `/var/log/nginx/` | Access + error logs ||
|| Backup Logs | `/home/mkanavi/logs/openbao-cron.log` | Backup execution log ||
|| Gitea Sync Log | `/home/mkanavi/gitea-sync/cron.log` | Mirror sync log ||
|| Docs (repo) | `~/gitea-sync/iacgenie-unified-infra/` | DEPLOY.md, BACKUP.md, INFRA-DESIGN.md ||

---

## 11. Known Issues & Notes

1. **Gitea data directory structure** — `gitea_data/` bind mount contains both `/conf/app.ini` (PostgreSQL config) and a `gitea/` subdirectory with legacy data. Old SQLite `gitea.db` files removed; only PostgreSQL-backed data remains. Admin user created via Gitea CLI. Docker Compose updated with `GITEA__admin__INIT_ROOT_*` env vars to auto-create admin on fresh boot.

2. **OpenBao API snapshot endpoint (HTTP 500)** — The `/v1/sys/storage/raft/snapshot` streaming endpoint fails with 500 in current OpenBao 2.6.0 configuration. Raw DB copy via host bind mount works reliably as fallback. May need API version check or different endpoint for 2.x.

3. **Gitea runner not registered** — Binary at `~/bin/gitea-runner` is present but not configured/registered with the Gitea instance. Needs OAuth token from Gitea UI to activate.

4. **rclone GDrive sync placeholder** — rclone v1.74.4 installed. Config at `~/.config/rclone/rclone.conf` with `[gdrive-backup]` remote defined. Requires OAuth interactive auth (`rclone authorize drive`) with Google Cloud OAuth client credentials to activate backup sync to Google Drive.

5. **PageZen port mapping** — Container runs on 8082, mapped to 8076 in compose file. Verified working.

---

## 12. Phase Completion Summary

|| Phase | Status | Key Deliverables ||
||-------|--------|-----------------||
|| **Phase 0** | ✅ Complete | PostgreSQL fixed, Redis fixed, OpenBao recovered, SearXNG fixed, zombie containers cleaned, orphan volumes cleaned ||
|| **Phase 1** | ✅ Complete | Health checks (all 11 services), resource limits (all 11 services), deploy.sh + rollback.sh, OpenBao backup script ||
|| **Phase 2** | ✅ Complete | rclone installed, backup script tested with checksums, restore verified, cron jobs fixed ||
|| **Phase 3** | ✅ Complete | Gitea installed + configured, GitHub→Gitea mirroring, CI workflows for all repos, GitHub Actions disabled ||
|| **Phase 4** | ✅ Complete | Monitoring stack permanently disabled (per directive) ||
|| **Phase 5** | ✅ Complete | INFRA-DESIGN.md, DEPLOY.md, BACKUP.md documented and committed ||
|| **Phase 10.17** | ✅ Complete | Loki + Promtail logging stack (GELF/JSON log drivers) ||
|| **Phase 10.18** | ✅ Complete | Prometheus + Grafana monitoring stack (Metrics + Dashboards) ||
|| **Phase 10.19** | ✅ Complete | Gitea backup + disaster recovery (cron, verification, restore) ||
|| **Phase 10.20** | ✅ Complete | Certbot TLS certificate automation (DNS-01 via Cloudflare) ||
|| **Phase 10.21** | ✅ Complete | Nginx reverse proxy + Cloudflare tunnel redundancy (cloudflared-2) ||
|| **Phase 10.22** | ✅ Complete | Resource quotas enforcement + key hardening fixes (Docker, Keycloak, Gitea, OpenBao) ||
|| **Phase 10.23** | ✅ Complete | Ansible idempotency hardening (roles, playbooks, drift detection) |
