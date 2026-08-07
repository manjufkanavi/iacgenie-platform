# IacGenie Platform — Infrastructure

> **Status**: Production  
> **VM**: 192.168.0.118 (elementary OS 8 / Ubuntu 24.04)  
> **Last Updated**: 2026-08-08  

## Quick Start

```bash
# Full deployment
cd ~/iacgenie-platform/infra
./deploy.sh

# Health check
./health-check.sh

# Drift detection
./drift-detect.sh

# Backup
./backup-restore.sh backup all

# List backups
./backup-restore.sh list
```

## Directory Structure

```
infra/
├── INFRA-ANSIBLE-DESIGN.md    # Architecture & design document
├── README.md                  # This file
├── deploy.sh                  # Master deployment script
├── health-check.sh            # Health check for all services
├── drift-detect.sh            # Drift detection between Ansible & running state
├── backup-restore.sh          # Backup & restore for all data
├── ansible/                   # Ansible playbooks & roles
│   ├── playbook.yml           # Master playbook (unified)
│   ├── site.yml               # Legacy entry point
│   ├── inventory/             # Inventory & variables
│   ├── roles/                 # Per-service Ansible roles
│   └── playbooks/             # Ancillary playbooks
├── docker-compose/            # Docker Compose templates
│   └── docker-compose.yml.j2  # Main compose template (Jinja2)
├── nginx/                     # Nginx configuration
│   ├── nginx-unified.conf.j2  # Unified reverse proxy template
│   └── all-vhosts.conf.j2     # All virtual host configs
├── systemd/                   # Systemd service templates
│   └── iacgenie-platform.service
└── scripts/                   # Helper scripts
```

## Running Services (20+)

| Service | Container | Port (Host) | Port (Container) | Purpose |
|---------|-----------|-------------|------------------|---------|
| PostgreSQL | `iacgenie_postgres` | 5432 | 5432 | Central database |
| Redis | `iacgenie_redis` | 6379 | 6379 | Caching & sessions |
| MinIO | `iacgenie_minio` | 9000 | 9000 | S3 object storage |
| MinIO Console | `iacgenie_minio_console_proxy` | 9001 | 9001 | MinIO admin UI |
| OpenBao | `iacgenie_openbao` | 8200 | 8200 | Secrets management |
| Keycloak | `iacgenie_keycloak` | 8083 | 8080 | OIDC/SAML auth |
| Gitea | `iacgenie_gitea` | 3000 / 2222 | 3000 / 2222 | Git service |
| LightSerp API | `iacgenie_lightserp_api` | 8000 | 3000 | MCP tools backend |
| LightSerp WebUI | `iacgenie_lightserp_webui` | 3001 | 3070 | Next.js frontend |
| PageZen | `iacgenie_pagezen` | 8081 | 8082 | Content generation |
| SearXNG | `iacgenie_searxng` | 8082 | 8080 | Search engine |
| NSQD | `iacgenie_nsqd` | 4150 / 4151 | 4150 / 4151 | Message queue |
| Nginx | (systemd) | 80/443 | — | Reverse proxy |
| Cloudflared | (systemd) | — | — | Tunnel (x2 redundant) |

## Key Services & URLs

| Service | URL | Auth |
|---------|-----|------|
| Keycloak UI | https://auth.iacgenie.com | platform-admin |
| OpenBao UI | https://vault.iacgenie.com | openbao-root-token |
| Gitea | https://gitea.iacgenie.com | Keycloak SSO |
| Prometheus | http://127.0.0.1:9090 | none |
| Grafana | https://grafana.iacgenie.com | grafana-admin |

## Secrets Management

All secrets are stored in **OpenBao KV** under `iacgenie/kv/`:

| Secret | OpenBao Path |
|--------|-------------|
| PostgreSQL password | `iacgenie/kv/postgres/password` |
| Keycloak admin | `iacgenie/kv/keycloak/admin_password` |
| Gitea DB password | `iacgenie/kv/gitea/db_password` |
| MinIO credentials | `iacgenie/kv/minio/root_password` |
| OpenBao root token | `iacgenie/kv/openbao/root_token` |
| SearXNG secret | `iacgenie/kv/searxng/secret` |
| LightSerp API key | `iacgenie/kv/lightserp/api_secret` |

## OpenBao OIDC Integration

Keycloak `openbao-oidc` client provides OIDC to OpenBao for service account authentication:

```bash
# Get OIDC access token
curl -s -X POST https://auth.iacgenie.com/realms/lightserp/protocol/openid-connect/token \
  -d "client_id=openbao-oidc" \
  -d "client_secret=<from-openbao>" \
  -d "grant_type=client_credentials"

# Use token with OpenBao
curl -H "X-Vault-Token: <oidc-token>" http://127.0.0.1:8200/v1/iacgenie/kv/data/postgres
```

## Backup Strategy

| Data | Frequency | Retention | Destination |
|------|-----------|-----------|-------------|
| PostgreSQL | Daily 2 AM | 30 days | GDrive (encrypted) |
| OpenBao raft | Daily 2 AM | 30 days | GDrive (encrypted) |
| Gitea | Daily 2 AM | 30 days | GDrive (encrypted) |
| Keycloak realm | Daily 2 AM | 30 days | GDrive (encrypted) |
| MinIO | Daily 2 AM | 30 days | GDrive (encrypted) |
| Config files | Daily 2 AM | 30 days | GDrive (encrypted) |

## Authentication Flow

```
User → Nginx → [Keycloak Login] → JWT Token
                                    │
                              ┌──────┼──────┐
                              │      │      │
                    IacGenie  LightSerp  Gitea
                    (OAuth)   (OAuth)    (SSO)
                                    
Service-to-Service:
Keycloak (OIDC) → OpenBao (reads KV secrets)
                 → All services (JWT validation)
```

## Emergency Procedures

1. **Service down**: `docker restart iacgenie_<service>`
2. **Data loss**: `./backup-restore.sh restore <file>`
3. **VM loss**: Full redeploy with `./deploy.sh`
4. **Keycloak lockout**: Reset from OpenBao → `iacgenie/kv/keycloak/admin_password`
5. **OpenBao sealed**: Unseal with keys from `iacgenie/kv/openbao/unseal_keys`

## Monitoring

| Tool | Port | Purpose |
|------|------|---------|
| Prometheus | 9090 | Metrics collection |
| Grafana | 3001 | Dashboards & alerts |
| Loki | — | Log aggregation (30-day retention) |
| Promtail | — | Log shipper |
