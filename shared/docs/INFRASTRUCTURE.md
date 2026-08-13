# IacGenie Platform Infrastructure Documentation

> Last updated: 2026-08-05
> VM: `192.168.0.118` (vm.iacgenie.com)
> User: `mkanavi`
> Local repo: `/Users/manjunathkanavi/iacgenie-platform`

## Architecture Overview

```
                    Cloudflare Tunnel
      ┌──────────────────────────────────────┐
      │       *.iacgenie.com                 │
      └──────────────┬───────────────────────┘
                     │ HTTPS
                     ▼
              ┌─────────────┐
              │   cloudflared│  (systemd service)
              │  :127.0.0.1:80│
              └──────┬──────┘
                     │
                     ▼
              ┌─────────────┐
              │     nginx    │  (host-level systemd)
              │  conf.d/*.conf│
              └──┬───┬───┬──┘
                 │   │   │
    ┌────────────┤   │   ├──────────────────┐
    │            │   │   │                  │
    ▼            ▼   ▼   ▼                  ▼
 keycloak     searxng  lightserp  gitea   other services
 :8083        :8082   :8002     :3000
```

## Running Services (as of 2026-08-05)

| Service | Container | Status | Port (host) | Notes |
|---------|-----------|--------|-------------|-------|
| Gitea | `iacgenie-gitea` | ✅ Running | 127.0.0.1:3000, :2222 (SSH) | gitea/gitea:1.23.4-rootless |
| Postgres | `iacgenie_postgres` | ✅ Healthy | 127.0.0.1:5432 | postgres:15-alpine |
| Redis | `iacgenie_redis` | ✅ Healthy | 127.0.0.1:6379 | redis:7-alpine |
| MinIO | `iacgenie_minio` | ✅ Healthy | 127.0.0.1:9000-9001 | minio/minio:latest |
| OpenBao | `iacgenie_openbao` | ✅ Healthy | 127.0.0.1:8200-8201 | 2.6.0 (unsealed) |
| Keycloak | `iacgenie_keycloak` | ✅ Healthy | 127.0.0.1:8083 | keycloak:26.0 |
| LightSerp API | `iacgenie-lightserp-api` | ✅ Running | 127.0.0.1:3071 | custom image |
| LightSerp WebUI | `iacgenie-lightserp-webui` | ✅ Running | 127.0.0.1:3070 | custom image |
| SearXNG | `iacgenie_searxng` | ✅ Healthy | 127.0.0.1:8081 | searxng:latest |
| NSQD | `iacgenie_nsqd` | ✅ Running | 127.0.0.1:4150-4151 | nsqio/nsq:latest |
| PageZen | `iacgenie-pagezen` | ✅ Running | 127.0.0.1:8082 | custom image |
| Frontend | `iacgenie-frontend` | ✅ Healthy | 0.0.0.0:3001 | Vite + React |
| Backend | `iacgenie-backend` | ✅ Healthy | 0.0.0.0:8002 | FastAPI |
| Gitea Runner | systemd | ✅ Running | — | gitea-runner v0.6.1 |
| Cloudflared | systemd | ✅ Running | — | Tunnel: iacgenie-tunnel |
| Nginx | systemd | ✅ Running | :80 (HTTP) | Host-level service |

## Gitea Configuration

### Admin User
- **Username**: `manjufkanavi`
- **Email**: manjufkanavi@iacgenie.com
- **Admin**: Yes
- **API Token**: `669ad7...4b15` (scope: write:repository, read:repository)

### Repositories
| Repo | Visibility | Branch |
|------|-----------|--------|
| iacgenie | Private | main |
| iacgenie-unified-infra | Private | main |
| LightSerp | Private | main |

### Gitea Actions
- **Status**: Enabled (`[actions] ENABLED = true` in app.ini)
- **Runner**: `iacgenie-vm-runner-2` (v0.6.1)
- **Runner Labels**: ubuntu-latest, ubuntu-24.04, ubuntu-22.04
- **Runner Config**: `/home/mkanavi/.runner` (JSON)
- **Runner Service**: `gitea-runner.service` (systemd)

### Gitea Data Paths
- Config: `/home/mkanavi/docker/iacgenie/data/gitea/app.ini` → `/etc/gitea` inside container
- Data: `/home/mkanavi/docker/iacgenie/data/gitea` → `/var/lib/gitea` inside container
- Container image: `gitea/gitea:1.23.4-rootless`

### Gitea PostgreSQL
- Database: `gitea`
- Schema: `user` table with `id=1` (manjufkanavi)
- Mirror table: `mirror` table with 3 entries (cron-triggered)

## GitHub → Gitea Sync

### Strategy: Push Mirror (GitHub → Gitea)
Since Gitea's native pull mirror API is not available in v1.23.4, we use a git-based sync script.

### Sync Script
- **Location**: `/home/mkanavi/bin/sync-gitea.py`
- **Approach**: git clone/fetch → push to Gitea remote
- **Work Dir**: `/tmp/gitea-sync-work`
- **Log**: `/home/mkanavi/bin/sync-gitea.log`

### Prerequisites
1. **GitHub PAT** (Personal Access Token) with `repo` scope — stored in `GITHUB_TOKEN` env var
2. **Gitea API Token** with `write:repository` scope — stored in `GITEA_PASS` env var
3. **Sync script** deployed at `/home/mkanavi/bin/sync-gitea.py`

### SSH Key for GitHub
- **Generated**: `~/.ssh/github_sync` (ed25519)
- **Public key**: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBvIKRhnd5hHdc6b7rUgNUkIeTiyDrU3WkmlSO+1iOhw mkanavi@vm.iacgenie.com`
- **Status**: Needs to be added to GitHub account settings

### Sync Schedule
- **Target**: Every 6 hours (`0 */6 * * *`)
- **Pending**: Cron job needs GitHub PAT to be active

### Mirror Table (Gitea DB)
Three pull mirror entries exist in the `mirror` table:
| ID | Repo | Remote URL | Interval |
|----|------|-----------|----------|
| 1 | iacgenie | https://github.com/manjufkanavi/iacgenie.git | 3600s |
| 2 | iacgenie-unified-infra | https://github.com/manjufkanavi/iacgenie-unified-infra.git | 3600s |
| 3 | LightSerp | https://github.com/manjufkanavi/LightSerp.git | 3600s |

Note: The Gitea background mirror scheduler needs a valid remote address (with PAT embedded) to sync. The `/api/v1/repos/{owner}/{repo}/mirror` API endpoint is not available in Gitea v1.23.4.

## Cloudflare Tunnel

### Service
- **Type**: systemd service (host-level)
- **Config**: `/etc/cloudflared/config.yml`
- **Credentials**: `/etc/cloudflared/iacgenie-tunnel.json`
- **Legacy**: `/home/mkanavi/.cloudflared/argotunnel.json` (preserved)
- **Cert**: `/home/mkanavi/.cloudflared/cert.pem` (NOT present — tunnel uses credentials file)

### Tunnel Config
```yaml
tunnel: iacgenie-tunnel
credentials-file: /etc/cloudflared/iacgenie-tunnel.json
grace-period: 30s
ingress:
  - hostname: '*.iacgenie.com'
    service: http://127.0.0.1:80
  - service: http://status.tcp:8080
```

### Tunnel routing
All `*.iacgenie.com` traffic → Cloudflare Edge → cloudflared → nginx:80 → hostname-based routing

## Nginx Configuration

### Service
- **Type**: Host-level systemd service
- **Main config**: `/etc/nginx/nginx.conf`
- **VHosts**: `/etc/nginx/conf.d/iacgenie.conf`
- **Backups**: `/etc/nginx/conf.d/iacgenie.conf.bak`

### Reverse Proxy (conf.d/iacgenie.conf)
| Subdomain | Proxy Target | Port | Service |
|-----------|-------------|------|---------|
| auth.iacgenie.com | 127.0.0.1:8083 | — | Keycloak |
| search.iacgenie.com | 127.0.0.1:8082 | — | SearXNG |
| api.iacgenie.com | 127.0.0.1:8002 | — | LightSerp API |
| gitea.iacgenie.com | 127.0.0.1:3000 | — | Gitea |
| *.iacgenie.com (catch-all) | 404 | — | Unknown |

### HTTP handling
- Default (port 80): Redirect to HTTPS for external users
- Cloudflare tunnel passthrough: No redirect (original Host preserved)

## Ansible Roles

### Roles Directory
`/Users/manjunathkanavi/iacgenie-platform/infra/ansible/roles/`

| Role | Purpose |
|------|---------|
| `gitea` | Gitea container config, Actions, runner status |
| `cloudflare_tunnel` | Cloudflared binary, tunnel credentials, service |
| `sync-gitea` | GitHub→Gitea sync script, cron job |
| `nginx-config` | Nginx reverse proxy config |
| `docker-compose-generator` | Docker Compose file generation |
| `postgres` | PostgreSQL deployment |
| `redis` | Redis deployment |
| `minio` | MinIO deployment |
| `openbao` | OpenBao deployment & unseal |
| `keycloak` | Keycloak deployment |
| `common` | System hardening, prerequisites |
| `docker` | Docker & Docker Compose installation |
| `backup` | Backup scripts & configuration |
| `certbot-setup` | Let's Encrypt SSL certificates |
| `monitoring` | Prometheus, Grafana, Loki |
| `lightserp` | LightSerp deployment |
| `nsqd` | NSQ message queue |
| `searxng` | SearXNG search engine |
| `keycloak_realm` | Keycloak realm configuration |

### Playbook Flow
```
site.yml
  ├── bootstrap.yml (system prep, common role)
  └── services.yml
       ├── docker-compose-generator (creates docker-compose.yml)
       ├── nginx-config
       ├── cloudflare_tunnel
       ├── gitea
       ├── postgres
       ├── redis
       ├── minio
       ├── openbao
       ├── keycloak
       └── sync-gitea
```

## OpenBao

### Status
- **State**: Unsealed (as of 2026-08-05)
- **Unseal Key 3**: `tSpeZmXPfBcfXAT6TEfcqOnr6lXdtDIEu36o14vcEb0h`
- **Unseal Key 1 & 2**: Must be stored securely in OpenBao init_keys.json
- **Health Check**: `docker inspect --format='{{.State.Health.Status}}' iacgenie_openbao`

### Mounts
- `iacgenie/kv` — Key for Gitea, LightSerp, Keycloak
- Vault address: `https://vault.iacgenie.com`

## SSH Keys

### On VM (`~/.ssh/`)
| Key | Purpose |
|-----|---------|
| `github_sync` | GitHub access (newly generated) |
| `github_lightserp` | LightSerp GitHub (older) |
| `gitea_iacgenie_deploy_key` | Gitea iacgenie repo deploy key |
| `gitea_iacgenie-unified-infra_deploy_key` | Gitea infra repo deploy key |
| `gitea_lightserp_deploy_key` | Gitea LightSerp repo deploy key |
| `gitea_lightserv_deploy_key` | Gitea lightserp repo deploy key |
| `gitea_iacgenie_key` | Legacy Gitea key |

## Docker Compose

### Main File
- **Location**: `/Users/manjunathkanavi/iacgenie-platform/infra/docker-compose/docker-compose-unified.yml`
- **Environment file**: `.env` (in the same directory as compose file)
- **Network**: `iacgenie_network` (bridge)

### Key Containers (as named in compose)
- `iacgenie-postgres` → Postgres
- `iacgenie-redis` → Redis
- `iacgenie-minio` → MinIO
- `iacgenie-openbao` → OpenBao
- `iacgenie-keycloak` → Keycloak
- `iacgenie-gitea` → Gitea
- `iacgenie-lightserp-api` → LightSerp API
- `iacgenie-lightserp-webui` → LightSerp WebUI
- `iacgenie-searxng` → SearXNG
- `iacgenie-nsqd` → NSQD
- `iacgenie-pagezen` → PageZen
- `iacgenie-frontend` → Frontend (Vite)
- `iacgenie-backend` → Backend (FastAPI)
- `iacgenie-loki` → Grafana Loki
- `iacgenie-promtail` → Promtail
- `iacgenie-prometheus` → Prometheus
- `iacgenie-grafana` → Grafana
- `iacgenie-cloudflared` → Cloudflare Tunnel (container — host service also runs)

## Security

### Network Binding
All database and sensitive services bound to `127.0.0.1`:
- Postgres: `127.0.0.1:5432`
- Redis: `127.0.0.1:6379`
- MinIO: `127.0.0.1:9000-9001`
- OpenBao: `127.0.0.1:8200-8201`
- Keycloak: `127.0.0.1:8083`
- Gitea: `127.0.0.1:3000, :2222`

### External Access
- Via Cloudflare Tunnel (encrypted, no direct port exposure)
- Nginx listens on port 80 (HTTP only, Cloudflare handles HTTPS)

### Secrets Management
- OpenBao as centralized secrets store
- Keycloak for authentication/identity
- Gitea API tokens stored in runner config

## Issues & TODOs

### Pending
1. **GitHub PAT** — Create a PAT with `repo` scope and set in `GITHUB_TOKEN` env var
2. **SSH Key** — Add `~/.ssh/github_sync.pub` to GitHub account
3. **Cron Job** — Set up `0 */6 * * *` cron for sync-gitea.py
4. **Ansible vars** — Add GitHub/Gitea credentials to ansible group_vars
5. **OpenBao unseal keys 1&2** — Need to verify keys 1 and 2 are recoverable
6. **Docker Compose** — Update gitea container definition with Actions config
7. **Mirror table** — Update remote_address to include GitHub PAT for native Gitea sync
8. **Nginx** — The current nginx config on VM does not match the local template (`nginx-unified.conf` is outdated)

### Known Limitations
- Gitea v1.23.4 does not expose the mirror pull API endpoint
- Cloudflare tunnel does not use cert.pem (works without it via credentials file)
- The `docker-compose-unified.yml` file has a Keycloak service definition that's incomplete (missing postgres keycloak DB, has wrong environment variables)
