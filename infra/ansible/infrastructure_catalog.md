# IacGenie Platform — Full Infrastructure Configuration Report
## Generated from: /Users/manjunathkanavi/iacgenie-platform/infra/ansible

---

## 1. Architecture Overview

The platform consists of **17 Docker services** deployed via docker-compose, orchestrated by Ansible
roles on a single Debian VM (192.168.0.118). Nginx acts as a reverse proxy on the host, and
Cloudflare Tunnel provides external access.

```
User → Cloudflare Edge → Cloudflare Tunnel → Nginx (host:80/443) → Docker Containers
```

**Docker Networks (3):**
| Network | Purpose | Services |
|---------|---------|----------|
| `iacgenie-frontend` | Nginx-exposed services | nginx, cloudflared, lightserp-webui, searxng, pagezen, grafana |
| `iacgenie-backend` | Databases, cache, object storage, auth | postgres, redis, minio, openbao, keycloak, gitea, loki, prometheus |
| `iacgenie-messaging` | Pub/sub | nsqd, lightserp-api |

---

## 2. Services Catalogued

### 2.1 PostgreSQL 15

| Property | Value |
|----------|-------|
| **Image** | `postgres:15-alpine` |
| **Container** | `iacgenie_postgres` |
| **Ports** | `127.0.0.1:5432:5432` |
| **Volumes** | `/home/mkanavi/docker/iacgenie/data/postgres:/var/lib/postgresql/data` |
| **Environment** | `POSTGRES_USER=lightsrp`, `POSTGRES_DB=lightsrp`, `POSTGRES_PASSWORD=${PG_ROOT_PASSWORD}` |
| **Secret Source** | OpenBao KV → `PG_ROOT_PASSWORD` |
| **Health Check** | `pg_isready -U lightsrp -d lightsrp` (30s interval, 10s timeout, 3 retries) |
| **Resource Limits** | 2GB memory, 0.75 CPU |
| **Networks** | `iacgenie-backend` |
| **Depends On** | — |

**PostgreSQL-specific defaults** (`roles/postgresql/defaults/main.yml`):
- `pg_version: "15"`, `pg_port: 5432`
- `pg_max_connections: 200`, `pg_shared_buffers: 256MB`
- `pg_backrest_bucket: iacgenie-backups`

---

### 2.2 Redis 7

| Property | Value |
|----------|-------|
| **Image** | `redis:7-alpine` |
| **Container** | `iacgenie_redis` |
| **Ports** | `127.0.0.1:6379:6379` |
| **Volumes** | `/home/mkanavi/docker/iacgenie/data/redis:/data` |
| **Command** | `redis-server --appendonly yes --maxmemory 512m --maxmemory-policy allkeys-lru` |
| **Environment** | `REDIS_PASSWORD=${REDIS_PASSWORD}` (from .env.j2) |
| **Secret Source** | OpenBao KV |
| **Health Check** | `redis-cli ping` (30s interval, 10s timeout, 3 retries) |
| **Resource Limits** | 512MB memory, 0.25 CPU |
| **Networks** | `iacgenie-backend` |

**Redis-specific defaults**:
- `redis_version: "7"`, `redis_port: 6379`
- `redis_maxmemory: 2gb` (default, but compose overrides to 512m via service_memory_defaults)
- `redis_aof_enabled: "yes"`

---

### 2.3 MinIO

| Property | Value |
|----------|-------|
| **Image** | `minio/minio:latest` (pinned for reproducibility) |
| **Container** | `iacgenie_minio` |
| **Ports** | `127.0.0.1:9000:9000` (API), `127.0.0.1:9001:9001` (Console via nginx) |
| **Volumes** | `/home/mkanavi/docker/iacgenie/data/minio:/data` |
| **Command** | `server /data --console-address ":9001"` |
| **Environment** | `MINIO_ROOT_USER={{ minio_root_user }}`, `MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD}` |
| **Secret Source** | `minio_root_password` from OpenBao KV; `minio_root_user=iacgenie` (default) |
| **Health Check** | `mc ready local` (30s interval, 10s timeout, 3 retries) |
| **Resource Limits** | 4GB memory, 0.5 CPU |
| **Networks** | `iacgenie-backend` |

**Buckets**: `iacgenie/artifacts`, `iacgenie/logs`, `iacgenie/plans`, `iacgenie/outputs`, `lightsrp/artifacts`, `lightsrp/logs`

**MinIO Console Proxy** (separate nginx:1.27-alpine container `iacgenie_minio_console_proxy`):
- Exposes `127.0.0.1:9001:9001` on `iacgenie-frontend` network
- Mounted config: `./minio-nginx.conf:/etc/nginx/conf.d/default.conf:ro`

---

### 2.4 OpenBao 2.6.0

| Property | Value |
|----------|-------|
| **Image** | `openbao/openbao:2.6.0` |
| **Container** | `iacgenie_openbao` |
| **Ports** | `127.0.0.1:8200:8200` (API), `127.0.0.1:8201:8201` (Cluster) |
| **Volumes** | `/home/mkanavi/docker/iacgenie/data/openbao:/openbao/storage`, `/home/mkanavi/docker/iacgenie/data/openbao_raft:/openbao/raft`, `/etc/letsencrypt:/etc/letsencrypt` |
| **User** | `0:0` (root) |
| **Command** | `bao server -config=/openbao/storage/openbao-prod.hcl` |
| **Environment** | `OPENBAO_ADDR`, `OPENBAO_CLUSTER_ADDR`, `OPENBAO_UI=true`, `OPENBAO_STORAGE_TYPE=raft`, `OPENBAO_STORAGE_PATH=/openbao/storage`, `OPENBAO_LOG_LEVEL=info`, `OPENBAO_ROOT_TOKEN` (secret) |
| **Secret Source** | `OPENBAO_ROOT_TOKEN` from OpenBao init_keys.json |
| **Health Check** | `wget -q -O /dev/null http://127.0.0.1:8200/v1/sys/health` (30s/10s/3) |
| **Resource Limits** | 1GB memory, 0.5 CPU |
| **Networks** | `iacgenie-backend` |
| **Auth** | Self-managed — root token-based, KV mount at `iacgenie/kv` |

**OpenBao Role Purpose**: Central secret management for the entire platform. Seeds KV data, manages root/admin tokens.

---

### 2.5 Keycloak 26.0

| Property | Value |
|----------|-------|
| **Image** | `quay.io/keycloak/keycloak:26.0` |
| **Container** | `iacgenie_keycloak` |
| **Ports** | `127.0.0.1:8083:8080` |
| **Volumes** | `/home/mkanavi/docker/iacgenie/data/keycloak:/opt/keycloak/data` |
| **Command** | `start --http-enabled=true --http-port=8080 --db-url-host=postgres --db-url-port=5432 --db-url-database=keycloak --db-username=keycloak --db-password=${KC_DB_PASSWORD} --hostname=https://auth.iacgenie.com --hostname-admin=https://auth.iacgenie.com` |
| **Environment** | `KC_BOOTSTRAP_ADMIN_USERNAME=${KEYCLOAK_ADMIN_USER}`, `KC_BOOTSTRAP_ADMIN_PASSWORD=${KEYCLOAK_ADMIN_PASSWORD}`, `KC_DB_PASSWORD=${KC_DB_PASSWORD}`, `KC_DB_HOST`, `KC_DB_PORT`, `KC_DB_NAME` |
| **Secrets** | `KEYCLOAK_ADMIN_PASSWORD`, `KC_DB_PASSWORD` from OpenBao KV |
| **Health Check** | `exec 6<>/dev/tcp/127.0.0.1/8080` (30s/10s/3) |
| **Resource Limits** | 2GB memory, 1.0 CPU |
| **Networks** | `iacgenie-backend` |
| **Depends On** | postgres |

**Keycloak Realm Config** (`roles/keycloak_realm/defaults/main.yml`):
- **Realm**: `iacgenie` (registration disabled)
- **Realm Roles**: `platform-admin`, `project-admin`, `project-member` (with `offline_access` default)
- **Clients**:
  - `iacgenie-platform` (Admin Dashboard) — service accounts, `https://admin.iacgenie.com/*`
  - `lightserp-api` (LightSerp API) — direct access grants, `https://lightserp.iacgenie.com/*`
  - `gitea` (Gitea SSO) — `https://git.iacgenie.com/user/oauth2/gitea`
  - `searxng` (Search) — `https://search.iacgenie.com/*`
- **Client Scopes**: `project-info` (OIDC mapper for `project_ids` claim)

---

### 2.6 Gitea 1.23.4

| Property | Value |
|----------|-------|
| **Image** | `gitea/gitea:1.23.4-rootless` |
| **Container** | `iacgenie_gitea` |
| **Ports** | `127.0.0.1:3000:3000` (HTTP), `127.0.0.1:2222:2222` (SSH) |
| **Volumes** | `/home/mkanavi/docker/iacgenie/data/gitea:/var/lib/gitea`, `/home/mkanavi/docker/iacgenie/data/gitea:/etc/gitea` |
| **Database** | PostgreSQL (same cluster, separate DB) |
| **Environment** | Multiple `GITEA__*` config keys for DB, SMTP, admin, security |
| **Secrets** | `GITEA_ADMIN_PASSWORD`, `GITEA_DB_PASSWORD` from OpenBao |
| **Health Check** | `exec 6<>/dev/tcp/127.0.0.1/3000` (30s/10s/3) |
| **Resource Limits** | 1GB memory, 0.5 CPU |
| **Networks** | `iacgenie-backend` |
| **Depends On** | postgres |

**Security Hardening** (Phase 10.9):
- Registration disabled (`GITEA__security__DISABLE_REGISTRATION=true`)
- 2FA enforced (`GITEA__security__DEFAULT_ENABLE_2FA=true`)
- Gravatar disabled, CAPTCHA enabled
- Min password length: 12
- Session lifetime: 86400s (24h)

**SMTP**: `mail.smtp2go.com:2525` (credentials from OpenBao)

**RBAC Mapping** (`roles/gitea_orgs/defaults/main.yml`):
- `platform-admin` → `maintainers` team
- `project-admin` → `maintainers` team
- `project-member` → `developers` team

**Project Orgs**: `iacgenie-project` (2 repos), `terragenius` (1 repo)

---

### 2.7 LightSerp API

| Property | Value |
|----------|-------|
| **Image** | `lightserp-lightserp-api:latest` (local/build) |
| **Container** | `iacgenie_lightserp_api` |
| **Ports** | `127.0.0.1:8000:3000` |
| **Volumes** | None (image-based) |
| **Networks** | `iacgenie-frontend`, `iacgenie-backend`, `iacgenie-messaging` |
| **Depends On** | postgres, minio, nsqd, searxng |
| **Resource Limits** | 512MB memory, 1.0 CPU |

**Environment Variables**:
| Variable | Value |
|----------|-------|
| `LOGTIDE_URL` | `http://localhost:4318/v1/traces` |
| `MINIO_ENDPOINT` | `minio:9000` |
| `MINIO_ACCESS_KEY` | `${MINIO_ROOT_USER}` |
| `MINIO_SECRET_KEY` | `${MINIO_ROOT_PASSWORD}` (OpenBao) |
| `NSQD_ADDR` | `nsqd:4150` |
| `LIGHTSERP_PAGEZEN_API` | `http://pagezen:8082` |
| `SEARXNG_URL` | `http://searxng:8080` |
| `LIGHTSERP_S3_BASE` | `iacgenie-lightserp` |
| `LIGHTSERP_ALLOW_INSECURE` | `true` |
| `REDIS_URL` | `redis://:${REDIS_PASSWORD}@redis:6379/0` |
| `LIGHTSERP_API_SECRET` | `${LIGHTSERP_API_SECRET}` (OpenBao) |
| `LIGHTSERP_DATABASE_URL` | `${LIGHTSERP_DATABASE_URL}` (OpenBao) |
| `LIGHTSERP_KEYCLOAK_CLIENT_SECRET` | `${LIGHTSERP_KEYCLOAK_CLIENT_SECRET}` (OpenBao) |

**Authentication**: OIDC via Keycloak (`LIGHTSERP_KEYCLOAK_CLIENT_SECRET`), API key via `LIGHTSERP_API_SECRET`

---

### 2.8 LightSerp WebUI

| Property | Value |
|----------|-------|
| **Image** | `lightserp-lightserp-webui:latest` (local/build) |
| **Container** | `iacgenie_lightserp_webui` |
| **Ports** | `127.0.0.1:3001:3070` |
| **Volumes** | None |
| **Networks** | `iacgenie-frontend` |
| **Depends On** | lightserp-api |
| **Resource Limits** | 512MB memory (shared with API) |

**Note**: Served via nginx at `app.iacgenie.com` and `lightserp.iacgenie.com`

---

### 2.9 SearXNG

| Property | Value |
|----------|-------|
| **Image** | `searxng/searxng:latest` |
| **Container** | `iacgenie_searxng` |
| **Ports** | `127.0.0.1:8082:8080` |
| **Volumes** | None |
| **Environment** | `SEARXNG_SECRET=${SEARXNG_SECRET_KEY}`, `SEARXNG_BASE_URL=http://search.iacgenie.com` |
| **Secret Source** | `SEARXNG_SECRET_KEY` from OpenBao |
| **Health Check** | `wget --spider -q http://127.0.0.1:8080/` (30s/10s/3) |
| **Resource Limits** | 512MB memory |
| **Networks** | `iacgenie-frontend` |

---

### 2.10 NSQD

| Property | Value |
|----------|-------|
| **Image** | `nsqio/nsq:latest` |
| **Container** | `iacgenie_nsqd` |
| **Ports** | `127.0.0.1:4150:4150` (TCP), `127.0.0.1:4151:4151` (HTTP API) |
| **Volumes** | `/home/mkanavi/docker/iacgenie/data/nsqd:/nsq/data` |
| **Command** | `nsqd --data-path=/nsq/data` |
| **Environment** | `NSQD_DATA_PATH=/nsq/data` |
| **Health Check** | `exec 6<>/dev/tcp/127.0.0.1/4150` (30s/10s/3) |
| **Resource Limits** | 256MB memory |
| **Networks** | `iacgenie-messaging` |

---

### 2.11 PageZen

| Property | Value |
|----------|-------|
| **Image** | `lightserp-pagezen:latest` (local/build) |
| **Container** | `iacgenie_pagezen` |
| **Ports** | `127.0.0.1:8081:8082` |
| **Volumes** | None |
| **Environment** | `LIGHTSERP_API_URL=http://lightserp-api:8000`, `LIGHTSERP_API_SECRET=${LIGHTSERP_API_SECRET}` |
| **Secret Source** | `LIGHTSERP_API_SECRET` from OpenBao |
| **Depends On** | lightserp-api |
| **Resource Limits** | 512MB memory |
| **Networks** | `iacgenie-frontend` |

**Note**: Served via nginx at `page.iacgenie.com`

---

### 2.12 Nginx (Host-Level)

| Property | Value |
|----------|-------|
| **Type** | Host-level systemd service (NOT Docker) |
| **Config** | `/etc/nginx/nginx.conf` + `/etc/nginx/conf.d/iacgenie.conf` |
| **Ports** | 80 (HTTP), 443 (HTTPS) |
| **Template** | `roles/nginx/templates/reverse-proxy.conf.j2` |

**Domains Proxied**:
| Domain | Proxy Target | Port |
|--------|-------------|------|
| `auth.iacgenie.com` | Keycloak | 127.0.0.1:8083 |
| `search.iacgenie.com` | SearXNG | 127.0.0.1:8082 |
| `api.iacgenie.com` | LightSerp API | 127.0.0.1:8000 |
| `app.iacgenie.com` | LightSerp WebUI | 127.0.0.1:3001 |
| `git.iacgenie.com` | Gitea | 127.0.0.1:3000 |
| `page.iacgenie.com` | PageZen | 127.0.0.1:8081 |
| `platform.iacgenie.com` | LightSerp WebUI | 127.0.0.1:3001 |
| `lightserp.iacgenie.com` | LightSerp WebUI | 127.0.0.1:3001 |

**Rate Limiting**:
| Zone | Rate |
|------|------|
| `general` | 10r/s (burst 20) |
| `auth` | 3r/m (burst 3-5) |
| `api` | 30r/s (burst 30) |

**Security Headers**: HSTS (365d), X-Frame-Options (SAMEORIGIN/DENY), X-Content-Type (nosniff), X-XSS, Referrer-Policy, CSP, Permissions-Policy, COEP/COOP/CORP

**TLS**: Let's Encrypt wildcards (`/etc/letsencrypt/live/iacgenie.com/`) — TLSv1.2/1.3, strong cipher suite

**Additional nginx configs**:
- `admin-gateway.conf` (admin.iacgenie.com → JWT middleware)
- `jwt-rbac-proxy.conf` (RBAC enforcement via JWT middleware)

---

### 2.13 Cloudflare Tunnel

| Property | Value |
|----------|-------|
| **Binary** | `cloudflared` v2025.6.0 (host-level systemd) |
| **Tunnel Name** | `iacgenie-tunnel` |
| **Credentials** | `/etc/cloudflared/iacgenie-tunnel.json` |
| **Origin Cert** | `/home/mkanavi/.cloudflared/cert.pem` |
| **Metrics** | `0.0.0.0:12345` |
| **Config** | `/etc/cloudflared/config.yml` |
| **Service** | `/etc/systemd/system/cloudflared.service` |

**Ingress Rules**:
- `*.iacgenie.com` → `http://127.0.0.1:80` (nginx reverse proxy)
- `status.tcp:8080` → health check

---

### 2.14 Monitoring Stack (Optional)

| Property | Value |
|----------|-------|
| **Components** | Prometheus, Grafana, cAdvisor |
| **Enabled By** | `monitoring_enabled` (defaults: netdata=true, prometheus=false, grafana=false) |
| **Config** | `docker-compose.monitoring.yml` |
| **Network** | `monitoring` (separate) |

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| prometheus | `prom/prometheus:latest` | `127.0.0.1:9090` | Metrics collection |
| grafana | `grafana/grafana:latest` | `127.0.0.1:3001` | Dashboards |
| cadvisor | `gcr.io/cadvisor/cadvisor:latest` | `127.0.0.1:8080` | Container metrics |

**Scrape Targets**: Prometheus (localhost:9090), Docker (localhost:9323), cAdvisor, Nginx (exporter:9113)

---

### 2.15 Logging Stack (Loki + Promtail)

| Property | Value |
|----------|-------|
| **Image (Loki)** | `grafana/loki:2.9.0` |
| **Image (Promtail)** | `grafana/promtail:2.9.0` |
| **Container** | `iacgenie-loki`, `iacgenie-promtail` |
| **Loki Port** | `127.0.0.1:3100:3100` |
| **Data Dir** | `/home/mkanavi/docker/iacgenie/loki/data` |
| **Retention** | 10GB storage, 720h (30 days) |
| **Promtail** | Ships `/var/lib/docker/containers/*.log` and `/home/mkanavi/docker/iacgenie/logs/*.log` |
| **Config** | `docker-compose.logging-stack.yml` |

---

### 2.16 Backup System

| Property | Value |
|----------|-------|
| **Schedule** | `0 2 * * *` (daily at 2 AM) |
| **Retention** | 30 days |
| **Dest** | `/mnt/backups` |
| **Script** | `/usr/local/bin/backup.sh` |
| **pgBackRest** | S3-compatible (MinIO), config at `/etc/pgbackrest/pgbackrest.conf` |

**Backup Scope**: PostgreSQL (`pg_dumpall`), Redis (AOF copy), MinIO (tar.gz), Keycloak (tar.gz), Gitea (tar.gz)

---

### 2.17 Admin Gateway (RBAC Gateway)

| Property | Value |
|----------|-------|
| **Image** | `lightserp/admin-gateway:latest` |
| **Container** | `iacgenie-admin-gateway` |
| **Port** | `9090` / `9091` (backend) |
| **Config** | `/home/mkanavi/docker/iacgenie/admin-gateway/config.json` |

**Protected Backends** (role-gated):
| Path Prefix | Target | Required Role |
|-------------|--------|--------------|
| `/iacgenie/` | `https://iacgenie.local` | `platform-admin` |
| `/gitea-admin/` | `https://git.iacgenie.com` | `platform-admin` |
| `/keycloak-admin/` | `https://auth.iacgenie.com` | `platform-admin` |
| `/grafana/` | `https://infra.local/grafana/` | `project-admin` |
| `/minio/` | `https://infra.local/minio/` | `project-admin` |
| `/openbao/` | `https://vault.iacgenie.com` | `platform-admin` |

**RBAC Roles & Permissions**:
- `platform-admin`: read, write, admin, delete, manage_users, manage_projects
- `project-admin`: read, write, manage_own_project_members, manage_own_projects
- `project-member`: read

---

## 3. Service Dependency Graph

```
                    ┌──────────────┐
                    │  Nginx +     │
                    │  Cloudflare  │
                    └──┬──┬──┬──┬──┘
                       │  │  │  │
              ┌────────┘  │  │  └─────────┐
              ▼           ▼   ▼            ▼
       ┌──────────┐  ┌─────────┐  ┌──────┐  ┌──────────┐
       │ Keycloak │  │ SearXNG │  │Gitea │  │ Admin GW │
       └──┬───────┘  └─────────┘  └───┬──┘  └────┬─────┘
          │                           │          │
          ▼                           ▼          ▼
       ┌──────────┐  ┌──────────────────────────────────────────┐
       │ PostgreSQL│─│          Shared Backend                  │
       └──────────┘  │  Redis │ MinIO │ OpenBao                │
                     └───────┴────────┴────────────────────────┘
                                     │
               ┌─────────────────────┼──────────────────────┐
               ▼                     ▼                      ▼
        ┌──────────────┐     ┌──────────────┐      ┌──────────────┐
        │LightSerp API │     │    PageZen   │      │  LightSerp   │
        │  + WebUI     │     └──────────────┘      │   WebUI      │
        └──────┬───────┘                           └──────────────┘
               │
               ▼
        ┌──────────────┐
        │     NSQD     │
        └──────────────┘
```

---

## 4. Secrets & Authentication Matrix

| Service | Secret Source | Secrets Used |
|---------|--------------|--------------|
| PostgreSQL | OpenBao KV | `PG_ROOT_PASSWORD` |
| Redis | OpenBao KV | `REDIS_PASSWORD` |
| MinIO | defaults + OpenBao | `minio_root_user` (default), `minio_root_password` (OpenBao) |
| OpenBao | init_keys.json | `OPENBAO_ROOT_TOKEN` |
| Keycloak | OpenBao KV | `keycloak_admin_password`, `keycloak_db_password` |
| Gitea | OpenBao KV | `gitea_admin_password`, `gitea_db_password`, SMTP creds |
| LightSerp API | OpenBao KV | `lightserp_api_secret`, `minio_root_password`, `LIGHTSERP_DATABASE_URL`, `LIGHTSERP_KEYCLOAK_CLIENT_SECRET` |
| PageZen | OpenBao KV | `lightserp_api_secret` |
| SearXNG | OpenBao KV | `searxng_secret` |
| All others | defaults | No secrets |

**Authentication Flow**:
1. **Users** → Nginx (TLS) → Service
2. **Admin Gateway** → JWT Middleware → validates Keycloak JWT → enforces RBAC → proxied to backend
3. **Keycloak** → OIDC provider for: IacGenie Platform, LightSerp API, Gitea, SearXNG
4. **OpenBao** → Central secrets store for all passwords/tokens
5. **Gitea** → OpenID Connect via Keycloak (SSO)

---

## 5. Ansible Role Structure

```
infra/ansible/
├── ansible.cfg              # Vault: ./.vault_key, Inventory: ./inventory/hosts.ini
├── .vault_key               # Vault password file
├── inventory/
│   ├── hosts.ini            # Single VM: 192.168.0.118 (user: mkanavi)
│   └── group_vars/
│       └── all.yml          # ENCRYPTED — vault key failed to decrypt
├── roles/
│   ├── common/              # System hardening, SSH, UFW, fail2ban, users
│   ├── docker/              # Docker CE + Compose plugin install
│   ├── docker-setup/        # Compose validation, image pull, network check
│   ├── docker-compose-generator/   # Compose file generation, network creation
│   ├── docker-compose-service/     # systemd service for docker compose
│   ├── nginx/               # Nginx install, config deployment
│   ├── nginx-config/        # Nginx unified config (idempotent)
│   ├── certbot-setup/       # TLS certificate management
│   ├── cloudflare_tunnel/   # cloudflared binary + tunnel config
│   ├── postgresql/          # PostgreSQL .env template
│   ├── redis/               # Redis .env template
│   ├── minio/               # MinIO .env template, buckets
│   ├── openbao/             # OpenBao .env template
│   ├── openbao-secrets/     # KV mount, token management
│   ├── keycloak/            # Keycloak .env template
│   ├── keycloak_realm/      # Realm/clients/roles provisioning (API)
│   ├── gitea/               # Gitea .env template, admin setup
│   ├── gitea_orgs/          # Gitea orgs/teams/repos via API
│   ├── lightserp/           # LightSerp .env template
│   ├── searxng/             # SearXNG .env template
│   ├── nsqd/                # NSQD .env template
│   ├── pagezen/             # PageZen .env template
│   ├── monitoring/          # Prometheus + Grafana + cAdvisor
│   ├── logging_stack/       # Loki + Promtail
│   ├── admin_gateway/       # RBAC admin gateway
│   ├── jwt_middleware/      # JWT token validation middleware
│   ├── backup/              # pgBackRest + cron backup script
│   ├── ntp_config/          # Chrony NTP
│   ├── user_management/     # Deploy user setup
│   └── deploy-env/          # OpenBao → .env unified file fetcher
└── scripts/
    └── fetch-openbao-env.py # Python script to fetch KV secrets → .env
```

---

## 6. Infrastructure as Code — Cross-References Between Roles

The compose file was already generated and saved to the report. Key cross-references:
- `roles/docker-compose-generator/templates/docker-compose.yml.j2` is the primary orchestration template
- Each service role's `.env.j2` provides secrets (but note: `deploy-env` role fetches all from OpenBao instead)
- Role order: `common` → `docker` → `docker-compose-generator` → `deploy-env` → `nginx` → `cloudflare_tunnel` → service roles → `backup`/`monitoring`/`logging_stack`

---

## 7. Issues & Observations

1. **Vault decryption failed**: `all.yml` could not be decrypted with `.vault_key` (contents: `a1b2c3d4...`). The vault may have been re-keyed or the key is a placeholder.

2. **Placeholder secrets**: Many secrets still show `CHANGE_ME_IN_VAULT` defaults — these need to be populated in OpenBao KV before first deploy.

3. **Duplicate .env.j2 in docker-compose-generator**: The file `roles/docker-compose-generator/templates/.env.j2` appears to contain Keycloak environment variables — likely a copy-paste artifact.

4. **Port conflict**: Grafana is configured on `127.0.0.1:3001` (monitoring), same as LightSerp WebUI (`127.0.0.1:3001`). Only one can bind.

5. **Docker image pinning inconsistency**: MinIO and SearXNG use `:latest` despite comments saying "pinned for reproducibility." MinIO should use a pinned version.

6. **LightSerp API uses `LIGHTSERP_ALLOW_INSECURE: true`** — this may indicate development settings that should be reviewed.

7. **OpenBao health check uses wget** but the container image may not include wget. Consider using `bao health` or the HTTP endpoint directly.

8. **Two nginx config systems**: Both `roles/nginx/` and `roles/nginx-config/` deploy nginx config files. The latter is marked for Phase 10.23 idempotency hardening but may conflict.

9. **Netdata is enabled by default** (`netdata_enabled: true`) in monitoring role but no Docker container config exists — likely runs as a host-level service.

10. **Gitea data directory ownership**: Uses UID 100/GID 1000 for rootless mode — needs to match the container's user.
