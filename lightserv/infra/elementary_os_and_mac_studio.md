# Elementary OS VM and Mac Studio — Infrastructure Guide

## System Information

| Field | VM (Infrastructure) | Mac Studio (Dev) |
|-------|-------------------|-----------------|
| **Hostname** | vm.iacgenie.com | mac.iacgenie.com |
| **IP Address** | 192.168.0.118 | 192.168.0.120 |
| **OS** | elementary OS 8 (Ubuntu 24.04) | macOS |
| **CPU** | Intel x86_64 | Apple Silicon / Intel |
| **Docker** | 29.1.3 | (dev only) |
| **SSH User** | mkanavi | mkanavi |
| **SSH Key** | `~/.ssh/newvm_key` (on Mac) | `~/.ssh/macvm_key.pub` (on VM) |
| **Role** | Docker host + Cloudflare tunnel agent | Dev machine + App backend/frontend |

## Service Architecture

```
                                    Cloudflare Tunnel (iacgenie-pi)
                                    /     |     |     |     |     \
                                   /      |     |     |     |      \
                      vm.iacgenie.com   |     |     |     |        \
                      jenkins.iacgenie.com|    |     |     |         \
                      mac.iacgenie.com    |    |     |     |          \
                      postgres.iacgenie.com|   |     |     |           \
                      redis.iacgenie.com    |   |     |     |            \
                      minio.iacgenie.com    |   |     |     |             \
                      console.minio.iacgenie.com| |     |                 \
                      vault.iacgenie.com      |   |     |                  \
                      auth.iacgenie.com       |   |     |                   \
                      metrics.iacgenie.com    |   |     |                    \
                      dashboards.iacgenie.com |   |     |                     \
                      panel.iacgenie.com      |   |     |                      \
                      app.iacgenie.com        |   |     |                       \
                      api.iacgenie.com        |   |     |                        \
                                              v   v     v                         v
                                          ┌──────────┐ ┌──────────┐ ┌──────────┐
                                          │ vm       │ │ Mac      │ │ VM       │
                                          │ :80      │ │ :5173/   │ │ Docker   │
                                          │          │ │ :8000    │ │ Network│
                                          │          │ │          │ │          │
                                          └──────────┘ └──────────┘ └──────────┘
                                                                      |
                                                              ┌───────┴───────┐
                                                              │               │
                                                        ┌───────┐   ┌───────┐
                                                        │postgres│   │ redis │
                                                        │ :5432  │   │ :6379 │
                                                        └───┬────┘   └───┬───┘
                                                            │              │
                                                        ┌───┴───┬───┬───┴───┐
                                                        │  MinIO│  │ OpenBao│ Jenkins│
                                                        │ :9000 │  │ :8200  │ :8085 │
                                                        └───┬───┘  └───┬───┘ └───┬──┘
                                                            │          │         │
                                                        ┌───┴────┐    │      ┌──┴─────┐
                                                        │Keycloak│    │      │Prom    │
                                                        │ :8080  │    │      │:9090  │
                                                        └────────┘    │      └──┬─────┘
                                                                      │         │
                                                                    ┌─┴────┐ ┌─┴─────┐
                                                                    │Grafana│ │Coolify│
                                                                    │:3001 │ │:8089  │
                                                                    └──────┘ └───────┘
```

## Service Inventory

| # | Service | Image | Memory | Port | Subdomain | Purpose |
|---|---------|-------|--------|------|-----------|---------|
| 1 | **PostgreSQL** | postgres:15-alpine | 1G | 127.0.0.1:5432 | N/A | Primary database (local-only) |
| 2 | **Redis** | redis:7-alpine | 256M | 127.0.0.1:6379 | N/A | Caching & sessions (local-only) |
| 3 | **MinIO** | minio/minio:latest | 512M | 127.0.0.1:9000/9001 | minio.iacgenie.com, console.minio.iacgenie.com | S3-compatible storage |
| 4 | **OpenBao** | quay.io/openbao/openbao:latest | 512M | 127.0.0.1:8200 | N/A | Secrets management (local-only) |
| 5 | **Keycloak** | quay.io/keycloak/keycloak:26.0 | 1G | 127.0.0.1:8080 | auth.iacgenie.com | OAuth/OIDC provider |
| 6 | **Jenkins** | jenkins/jenkins:lts-jdk17 | 1G | 127.0.0.1:8085 | jenkins.iacgenie.com | CI/CD platform |
| 7 | **Prometheus** | prom/prometheus:latest | 512M | 127.0.0.1:9090 | metrics.iacgenie.com | Metrics collection |
| 8 | **Grafana** | grafana/grafana:latest | 512M | 127.0.0.1:3001 | dashboards.iacgenie.com | Dashboards |
| 9 | **Coolify** | ghcr.io/coollabsio/coolify:latest | 1G | 127.0.0.1:8089/8090 | panel.iacgenie.com | PaaS deployment |
| 10 | **Mac Frontend** | — | — | 192.168.0.120:5173 | app.iacgenie.com | Frontend dev server |
| 11 | **Mac Backend** | — | — | 192.168.0.120:8000 | api.iacgenie.com | Backend API |

**Total VM memory**: ~5.3 GB

## Cloudflare Tunnel Configuration

**Tunnel name**: `iacgenie-pi`
**Tunnel ID**: `1291108a-4e8d-4439-9fa6-316be7da5f97`
**Cloudflared**: Systemd service (`cloudflared-tunnel.service`) on the VM

### How It Works

cloudflared runs as a **systemd service** on the VM (NOT in Docker). This is critical because:
- Ingress rules must use `127.0.0.1:<host-port>` instead of Docker service names
- cloudflared cannot resolve Docker DNS names like `http://jenkins:8080`
- The tunnel directly connects to host-bound ports

### Ingress Rules

| Hostname | Backend | Protocol | Notes |
|----------|---------|----------|-------|
| vm.iacgenie.com | http://127.0.0.1:80 | HTTP | Mac nginx proxy on VM |
| mac.iacgenie.com | http://192.168.0.120:80 | HTTP | Mac nginx proxy |
| jenkins.iacgenie.com | http://127.0.0.1:8085 | HTTP | Via tunnel only |
| postgres.iacgenie.com | ~~removed~~ | — | Removed: databases must not be exposed |
| redis.iacgenie.com | ~~removed~~ | — | Removed: databases must not be exposed |
| minio.iacgenie.com | http://127.0.0.1:9000 | HTTP | Via tunnel only |
| console.minio.iacgenie.com | http://127.0.0.1:9001 | HTTP | Via tunnel only |
| vault.iacgenie.com | ~~removed~~ | — | Removed: access via SSH tunnel or API only |
| auth.iacgenie.com | http://127.0.0.1:8080 | HTTP | Keycloak OAuth/OIDC |
| metrics.iacgenie.com | http://127.0.0.1:9090 | HTTP | Prometheus (localhost-bound) |
| dashboards.iacgenie.com | http://127.0.0.1:3001 | HTTP | Grafana (localhost-bound) |
| panel.iacgenie.com | http://127.0.0.1:8089 | HTTP | Coolify PaaS |
| app.iacgenie.com | http://192.168.0.120:5173 | HTTP | Mac frontend dev server |
| api.iacgenie.com | http://192.168.0.120:8000 | HTTP | Mac backend API |

### Cloudflare DNS

All `*.iacgenie.com` subdomains use a **wildcard CNAME** record:

| Type | Name | Content | Proxy |
|------|------|---------|-------|
| CNAME | `*` | `<tunnel-id>.cfargotunnel.com` | Proxied (orange) |

## Configuration Files

### Directory Structure

```
/home/mkanavi/docker/iacgenie/
├── docker-compose-newvm.yml      # Main compose file
├── .env                          # Environment variables (secrets)
├── .env.pi                       # Secrets template
├── prometheus.yml                # Prometheus scrape config
├── cloudflared/
│   ├── config.yml                # Cloudflare tunnel config
│   └── auth.json                 # Tunnel credentials
├── postgres_data/                # PostgreSQL data volume
├── redis_data/                   # Redis data volume
├── minio_data/                   # MinIO data volume
├── openbao_data/                 # OpenBao data volume
├── jenkins_data/                 # Jenkins data volume
├── prometheus_data/              # Prometheus data volume
├── grafana_data/                 # Grafana data volume
└── docker/
    ├── postgres/init.sh          # DB init script
    ├── minio/init.sh             # Bucket creation script
    ├── openbao/bootstrap.sh      # KV engine setup
    ├── keycloak/
    │   ├── import-realm.sh       # Realm import script
    │   └── realm-export.json     # Keycloak realm definition
    ├── jenkins/
    │   ├── startup.sh            # JCasC plugin installer
    │   └── jenkins.config.yml    # Jenkins config
    └── grafana/provisioning/datasources/
        └── datasources.yml       # Prometheus + Postgres datasources
```

## SSH Configuration

### From Mac to VM

Add to `~/.ssh/config` on Mac:

```
Host newvm
    HostName 192.168.0.118
    User mkanavi
    IdentityFile ~/.ssh/newvm_key
```

Usage:
```bash
ssh newvm
scp -r ./file newvm:~/docker/iacgenie/
```

### From VM to Mac

Add to `~/.ssh/config` on VM:
```
Host mac
    HostName 192.168.0.120
    User mkanavi
    IdentityFile ~/.ssh/macvm_key
```

## Deployment Commands

### Start All Services

```bash
cd ~/docker/iacgenie
docker compose -f docker-compose-newvm.yml up -d
```

### Stop All Services

```bash
cd ~/docker/iacgenie
docker compose -f docker-compose-newvm.yml down
```

### View Status

```bash
cd ~/docker/iacgenie
docker compose -f docker-compose-newvm.yml ps
```

### View Logs

```bash
cd ~/docker/iacgenie
docker compose -f docker-compose-newvm.yml logs -f
# Or specific service:
docker compose -f docker-compose-newvm.yml logs -f jenkins
```

### Pull Latest Images & Update

```bash
cd ~/docker/iacgenie
docker compose -f docker-compose-newvm.yml pull
docker compose -f docker-compose-newvm.yml up -d
```

### Cleanup Unused Images

```bash
docker image prune -a --filter "until=24h"
docker volume prune -f
docker system prune -f
```

### Cloudflared Tunnel Management

```bash
# Restart tunnel
sudo systemctl restart cloudflared-tunnel

# Check status
sudo systemctl status cloudflared-tunnel

# View logs
journalctl -u cloudflared-tunnel -f
```

## Secrets Inventory

All secrets are defined in `.env` (copied from `.env.pi` template).

| Secret | Service | Type |
|--------|---------|------|
| `POSTGRES_SUPER_PASSWORD` | PostgreSQL superuser | Generated |
| `POSTGRES_APP_PASSWORD` | IacGenie app user | Generated |
| `POSTGRES_KC_PASSWORD` | Keycloak DB user | Generated |
| `REDIS_PASSWORD` | Redis auth | Generated |
| `MINIO_ROOT_PASSWORD` | MinIO auth | Generated |
| `OPENBAO_ROOT_TOKEN` | OpenBao root | Generated |
| `OPENBAO_TOKEN` | OpenBao app | Generated |
| `KEYCLOAK_ADMIN_PASSWORD` | Keycloak admin | Generated |
| `GRAFANA_ADMIN_PASSWORD` | Grafana admin | Generated |
| `JWT_SECRET` | Backend JWT signing | Generated |
| `CLOUDFLARE_TUNNEL_TOKEN` | Cloudflare tunnel | External |
| `SMTP2GO_API_KEY` | SMTP2GO | External |
| `SENTRY_DSN` | Sentry | External |
| `JENKINS_ADMIN_USER` | Jenkins admin username | Config |
| `JENKINS_ADMIN_PASSWORD` | Jenkins admin password | Generated |
| `GITHUB_TOKEN` | Jenkins SCM (GitHub API) | External |

## Default Credentials

| Service | Username | Password |
|---------|----------|----------|
| PostgreSQL superuser | `postgres` | `POSTGRES_SUPER_PASSWORD` |
| PostgreSQL app | `iacgenie_user` | `POSTGRES_APP_PASSWORD` |
| PostgreSQL Keycloak | `keycloak` | `POSTGRES_KC_PASSWORD` |
| MinIO | `minioadmin` | `MINIO_ROOT_PASSWORD` |
| Keycloak admin | `admin` | `KEYCLOAK_ADMIN_PASSWORD` |
| Grafana admin | `admin` | `GRAFANA_ADMIN_PASSWORD` |
| Jenkins admin | `admin` | `JENKINS_ADMIN_PASSWORD` |

## Accessing Services

| Service | URL | Notes |
|---------|-----|-------|
| VM Web Interface | https://vm.iacgenie.com | Port 80 on VM |
| Mac Web Interface | https://mac.iacgenie.com | Port 80 on Mac |
| Jenkins | https://jenkins.iacgenie.com | JCasC-configured; admin login via Jenkins built-in realm |
| PostgreSQL | N/A (local tunnel only) | SSH tunnel or backend API at api.iacgenie.com |
| Redis | N/A (local tunnel only) | SSH tunnel or backend API at api.iacgenie.com |
| MinIO API | https://minio.iacgenie.com | S3-compatible storage |
| MinIO Console | https://console.minio.iacgenie.com | Storage management UI |
| OpenBao | N/A (local tunnel only) | SSH tunnel or backend API at api.iacgenie.com |
| Keycloak | https://auth.iacgenie.com | OAuth/OIDC provider |
| Prometheus | https://metrics.iacgenie.com | Metrics collection |
| Grafana | https://dashboards.iacgenie.com | Dashboards |
| Coolify | https://panel.iacgenie.com | PaaS deployment |
| Mac Frontend | https://app.iacgenie.com | Frontend dev server |
| Mac Backend API | https://api.iacgenie.com | Backend API |

## Troubleshooting

### Services Won't Start

1. Check if images are pulled: `docker images`
2. Check .env file: `cat ~/docker/iacgenie/.env`
3. Validate compose: `docker compose -f docker-compose-newvm.yml config --quiet`
4. Check logs: `docker compose -f docker-compose-newvm.yml logs`

### PostgreSQL Issues

- **Init script not running**: The init.sh runs on first startup only when data directory is empty.
- **Reinitialize DB**: Stop services, remove postgres_data volume, restart.
  ```bash
  docker compose -f docker-compose-newvm.yml down
  docker volume rm iacgenie_postgres_data
  docker compose -f docker-compose-newvm.yml up -d postgres
  ```

### Keycloak Won't Connect to PostgreSQL

```bash
docker exec iacgenie-postgres-1 psql -U postgres -c "ALTER USER keycloak WITH PASSWORD '${POSTGRES_KC_PASSWORD}';"
docker restart iacgenie-keycloak-1
```

### OpenBao Not Ready

OpenBao dev mode has a startup delay. The openbao-init service waits for health check.
```bash
docker logs iacgenie-openbao
docker logs iacgenie-openbao-init
```

### Cloudflared Tunnel Down

Check service status:
```bash
sudo systemctl status cloudflared-tunnel
journalctl -u cloudflared-tunnel --no-pager -n 50
```

### Jenkins Issues

- Jenkins takes 1-2 minutes to fully initialize
- Check logs: `docker logs iacgenie-jenkins`
- Default admin credentials in `.env` (`JENKINS_ADMIN_USER` / `JENKINS_ADMIN_PASSWORD`)
- Jenkins config is JCasC-driven from `iacgenie/docker/jenkins/jenkins.config.yml`
- Jenkins data persists in `/home/mkanavi/docker/iacgenie/jenkins_data/` (bind mount)
- **Never delete** `jenkins_data/secrets/` — these keys encrypt all stored credentials. If lost, all credentials become unrecoverable.
- Add GitHub SSH credential (`github-ssh`) via Jenkins UI: Manage Jenkins → Credentials → System domain → Add Credentials → SSH Username with private key
- For full credential management details, see `infra/services-secrets.md`

### Disk Space

```bash
df -h ~/docker/iacgenie/
docker system df
```

### Docker Compose v1 vs v2

This VM uses Docker Compose v5.1.4 (installed at `~/.docker/cli-plugins/docker-compose`). Both `docker compose` (v2 syntax) and `docker-compose` (v1 syntax) work.

## Backup Procedures

### Full Backup

```bash
cd ~/docker
tar czf /tmp/iacgenie-backup-$(date +%Y%m%d).tar.gz \
  --exclude='*_data' \
  iacgenie/
# Data volumes are Docker named volumes — backup with:
docker run --rm -v iacgenie_postgres_data:/data -v /tmp:/backup alpine \
  tar czf /backup/postgres-$(date +%Y%m%d).tar.gz /data
```

### Restore

```bash
# Stop services
cd ~/docker/iacgenie
docker compose -f docker-compose-newvm.yml down

# Restore data volumes
docker run --rm -v iacgenie_postgres_data:/data -v /tmp:/backup alpine \
  tar xzf /backup/postgres-20260612.tar.gz -C /data

# Restart
docker compose -f docker-compose-newvm.yml up -d
```

## Maintenance Schedule

| Task | Frequency |
|------|-----------|
| Check Docker image updates | Weekly |
| Check disk space | Daily |
| Backup PostgreSQL data | Weekly |
| Review OpenBao secrets rotation | Monthly |
| Review Cloudflare tunnel logs | Monthly |
