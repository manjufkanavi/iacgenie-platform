# Infrastructure State & Architecture

> Last updated: 2026-08-05  
> VM: 192.168.0.118 (mkanavi)

## Architecture Overview

```
                  ┌─────────────────┐
                  │   Cloudflare    │
                  │     Tunnel      │
                  │  iacgenie-tunnel│
                  └───────┬─────────┘
                          │ HTTPS
                    ┌─────┴──────┐
                    │    Nginx   │
                    │ (vHost     │
                    │  routing)  │
                    └─────┬──────┘
                          │
              ┌───────────┼──────────────┐
              │           │              │
     ┌────────▼──┐  ┌────▼─────┐  ┌─────▼──────┐
     │   Gitea   │  │  Keycloak│  │  LightSerp │
     │  :3000    │  │  :8080   │  │  (frontend)│
     │  :2222 SSH│  └──────────┘  └────────────┘
     └─────┬─────┘
           │
     ┌─────▼──────┐  ┌─────────┐  ┌──────┐  ┌───────┐
     │  Postgres  │  │  Redis  │  │ MinIO│  │OpenBao│
     │  (gitea)   │  │         │  │      │  │(unsealed)│
     └────────────┘  └─────────┘  └──────┘  └───────┘
```

## Container Inventory

| Container | Image | Port | Status | Health |
|-----------|-------|------|--------|--------|
| `iacgenie-gitea` | `gitea/gitea:1.23.4-rootless` | 127.0.0.1:3000, :2222 | Running | healthy |
| `iacgenie_postgres` | `postgres:15-alpine` | internal | Running | healthy |
| `iacgenie_redis` | redis | internal | Running | healthy |
| `iacgenie_minio` | minio | internal | Running | healthy |
| `iacgenie_openbao` | openbao | internal | Running | **healthy** (unsealed) |
| `iacgenie_keycloak` | keycloak | :8080 | Running | healthy |
| `iacgenie_light_serp` | nginx (frontend) | 127.0.0.1:3002 | Running | healthy |
| `iacgenie-tunnel` | cloudflared | system | Running | healthy |

## Services

### Gitea (Internal Git Server + CI/CD)
- **Container**: `iacgenie-gitea` (rootless)
- **Image**: `gitea/gitea:1.23.4-rootless`
- **Data**: `/home/mkanavi/docker/iacgenie/data/gitea` → `/var/lib/gitea` (data) + `/etc/gitea` (config)
- **Admin User**: `manjufkanavi`
- **Actions**: ✅ Enabled (`[actions] ENABLED = true` in app.ini)
- **Runner**: `iacgenie-vm-runner-2` — registered, running, labels: `ubuntu-latest, 24.04, 22.04`
- **SSH Port**: 2222
- **Host Port**: 3000 (bound to 127.0.0.1)

### OpenBao (Secrets Manager)
- **Status**: Initialized, **unsealed** (key 3: `tSpeZmXPfBcfXAT6TEfcqOnr6lXdtDIEu36o14vcEb0h`)
- **Data**: `/home/mkanavi/docker/iacgenie/data/openbao`
- **Mount Path**: `/opt/openbao/data`
- **TLS**: Enabled with cert at `/opt/openbao/data/tls/cert.pem`

### Cloudflare Tunnel
- **Tunnel**: `iacgenie-tunnel`
- **Credentials**: `/etc/cloudflared/iacgenie-tunnel.json`
- **Config**: `/etc/cloudflared/config.yml` (via `cloudflared.yaml.j2`)
- **Legacy Migration**: `argotunnel.json` → `iacgenie-tunnel.json` handled automatically

### Nginx (Reverse Proxy)
- **Config**: `/home/mkanavi/docker/nginx/nginx-unified.conf`
- **VHosts**: all served via hostname-based routing
- **Domains**:
  - `gitea.iacgenie.com` → `iacgenie-gitea:3000`
  - `keycloak.iacgenie.com` → `iacgenie_keycloak:8080`
  - `lightserp.iacgenie.com` → `iacgenie_light_serp:80` (front door:8000)

### Postgres
- **Database**: `gitea` (for Gitea)
- **Data**: `/home/mkanavi/docker/iacgenie/data/postgres`
- **Connection**: internal Docker network only (127.0.0.1)

## Repository Mirrors (GitHub → Gitea Pull)

| Repo | GitHub URL | Gitea Status | Last Sync |
|------|-----------|--------------|-----------|
| `iacgenie` | `github.com/manjufkanavi/iacgenie` | ✅ Mirror | 2026-08-05 |
| `iacgenie-unified-infra` | `github.com/manjufkanavi/iacgenie-unified-infra` | ✅ Mirror | 2026-08-05 |
| `LightSerp` | `github.com/manjufkanavi/LightSerp` | ✅ Mirror | 2026-08-05 |

**Sync interval**: 1 hour (`gitea_mirror_interval: 3600`)  
**Prune**: enabled (removes unreferenced objects)  
**Implementation**: Direct `mirror` table entries in Gitea Postgres, synced via Gitea's built-in mirror job

### Mirror Architecture
```
GitHub ──(pull mirror, 1h)──→ Gitea (internal)
                              ↑
                         Gitea Actions (CI/CD)
                         triggered on push/PR to Gitea
```

**Important**: Push → GitHub only. Gitea pulls automatically via pull mirror.  
This avoids infinite sync loops and keeps GitHub as the single source of truth.

## Ansible Roles

| Role | Purpose |
|------|---------|
| `common` | Server hardening, SSH, logrotate, unattended-upgrades |
| `docker` | Docker + Docker Compose installation |
| `user_management` | Deploy user (`mkanavi`), sudo, SSH keys |
| `ntp_config` | Chrony NTP synchronization |
| `postgresql` | Postgres installation + DB provisioning |
| `redis` | Redis installation |
| `minio` | MinIO S3-compatible storage |
| `openbao` | OpenBao secrets manager (init + unseal) |
| `keycloak` | Keycloak auth server |
| `gitea` | Gitea container health, Actions config, admin user, API tokens |
| `lightserp` | LightSerp frontend deployment |
| `searxng` | SearXNG search engine |
| `nsqd` | Nashorn message queue |
| `pagezen` | PageZen frontend |
| `docker-compose-generator` | Unified docker-compose.yml generation |
| `docker-compose-service` | Service-specific compose deployment |
| `nginx` | Nginx reverse proxy configuration |
| `cloudflare_tunnel` | Cloudflare Tunnel (login, create, config, service) |
| `backup` | Automated backups (Postgres) |
| `monitoring` | Prometheus + Grafana |
| `logging_stack` | Loki + Promtail |
| `keycloak_realm` | Keycloak realm/provisioning |
| `gitea_orgs` | Gitea org/teams/RBAC provisioning |
| `gitea_mirror` | **NEW** — GitHub → Gitea pull mirror setup |
| `sync-gitea` | Custom sync script (legacy, superseded by mirror role) |

## Playbook Flow

```
site.yml
  ├── bootstrap.yml
  │     ├── common
  │     ├── docker
  │     └── ntp_config
  └── services.yml
        ├── common, docker, user_management, ntp_config
        ├── postgresql, redis, minio, openbao, keycloak
        ├── gitea, lightserp, searxng, nsqd, pagezen
        ├── docker-compose-generator, docker-compose-service, nginx, cloudflare_tunnel
        ├── backup
        ├── monitoring
        ├── logging_stack
        ├── keycloak_realm
        ├── gitea_orgs
        └── gitea_mirror (NEW)
        └── [post-deploy tasks: openbao unseal, realm, orgs, mirrors]
```

## Key Credentials (REDACTED)

| Credential | Location |
|-----------|----------|
| Gitea admin user | `manjufkanavi` |
| Gitea API token | Generated via `gitea admin user generate-access-token` |
| Gitea runner token | Generated via Gitea UI → Settings → Actions → Runner Registration |
| GitHub PAT | `~/.bash_profile` (`GITHUB_TOKEN` env var) |
| Cloudflare API Token | `cloudflared_api_token` ansible var |
| OpenBao master key | `/opt/openbao/data/init_keys.json` |

## Notes

- All infrastructure services bound to `127.0.0.1` — only Cloudflare Tunnel exposes externally
- Gitea uses rootless image (`gitea:1.23.4-rootless`)
- OpenBao sealed state handled via ansible post-deploy unseal tasks
- Pull mirrors updated via direct DB manipulation — no Gitea API mirror endpoint in 1.23.4
- Runner registered via Gitea API, runs as systemd service
