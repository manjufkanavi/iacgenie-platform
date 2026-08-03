# IacGenie New VM — Infrastructure Setup & Operations Guide

## System Information

| Field | Value |
|-------|-------|
| **Hostname** | elementary-os |
| **IP Address** | 192.168.0.118 |
| **OS** | elementary OS 8 (Ubuntu 24.04 LTS) |
| **CPU** | Intel x86_64 (AMD64) |
| **Docker** | 29.1.3 |
| **Docker Compose** | v5.1.4 |
| **Disk** | 465GB (430GB free) |
| **SSH User** | mkanavi |
| **SSH Key** | `~/.ssh/newvm_key` (on local Mac) |

## Service Architecture

### Overview

```
                                    Cloudflare Tunnel (iacgenie-pi)
                                    /     |     |     |     |     \
                                   /      |     |     |     |      \
                      jenkins.iacgenie.com  |     |     |     |       \
                      postgres.iacgenie.com |     |     |     |        \
                      redis.iacgenie.com    |     |     |     |         \
                      minio.iacgenie.com    |     |     |     |          \
                      console.minio.iacgenie.com |     |     |           \
                      vault.iacgenie.com        |     |     |             \
                      auth.iacgenie.com          |     |                   \
                      metrics.iacgenie.com        |                          \
                      dashboards.iacgenie.com     |                           \
                      panel.iacgenie.com          |                            \
                                                  v                             v
                                          ┌─────────────────────────────────────┐
                                          │     192.168.0.118 (VM)              │
                                          │                                     │
                                          │  ┌──────────┐ ┌────────────────┐  │
                                          │  │ postgres │ │ redis          │  │
                                          │  │ :5432    │ │ :6379          │  │
                                          │  └──┬───┬───┘ └───┬────────────┘  │
                                          │     │   │         │                │
                                          │  ┌──┴───┴───┬────┴────┬────────┐  │
                                          │  │  MinIO   │  OpenBao │ Jenkins│  │
                                          │  │ :9000/91 │  :8200   │ :8085  │  │
                                          │  └────┬─────┘   │       │        │  │
                                          │       │         │      ┌─┴───┐   │
                                          │  ┌────┴────┐    │      │ Key │   │
                                          │  │ Keycloak│    │     └─┤ clo │   │
                                          │  │  :8080  │    │       └─┤ ak  │   │
                                          │  └─────────┘    │        └─────┘   │
                                          │                  │                  │
                                          │  ┌────────────┐  │  ┌────────────┐ │
                                          │  │ Prometheus │  │  │ Grafana    │ │
                                          │  │  :9090     │  │  │ :3001      │ │
                                          │  └────────────┘  │  └────────────┘ │
                                          │  ┌────────────┐  │  ┌────────────┐ │
                                          │  │  Coolify   │  │  │ Cloudflared│ │
                                          │  │  :8089     │  │  │ (tunnel)   │ │
                                          │  └────────────┘  │  └────────────┘ │
                                          │                                     │
                                          └─────────────────────────────────────┘
```

### Service Inventory

| # | Service | Image | Memory | Port(s) | Subdomain | Purpose |
|---|---------|-------|--------|---------|-----------|---------|
| 1 | **PostgreSQL** | postgres:15-alpine | 1G | 5432 | postgres.iacgenie.com (TCP) | Primary database |
| 2 | **Redis** | redis:7-alpine | 256M | 6379 | redis.iacgenie.com (TCP) | Caching & sessions |
| 3 | **MinIO** | minio/minio:latest | 512M | 9000/9001 | minio.iacgenie.com, console.minio.iacgenie.com | S3-compatible storage |
| 4 | **OpenBao** | quay.io/openbao/openbao:2.6.0 | 512M | 8200 | vault.iacgenie.com | Secrets management (prod mode, TLS, Raft) |
| 5 | **Keycloak** | quay.io/keycloak/keycloak:26.0 | 1G | 8080 | auth.iacgenie.com | OAuth/OIDC provider |
| 6 | **Jenkins** | jenkins/jenkins:lts-jdk17 | 1G | 8085 | jenkins.iacgenie.com | CI/CD platform |
| 7 | **Prometheus** | prom/prometheus:latest | 512M | 9090 | metrics.iacgenie.com | Metrics collection |
| 8 | **Grafana** | grafana/grafana:latest | 512M | 3001 | dashboards.iacgenie.com | Dashboards |
| 9 | **Coolify** | ghcr.io/coollabsio/coolify:latest | 1G | 8089 | panel.iacgenie.com | PaaS deployment |
| 10 | **Cloudflared** | cloudflare/cloudflared:latest | 128M | (tunnel) | All *.iacgenie.com | Tunnel agent |

**Total memory**: ~5.3 GB

## Directory Structure

```
/home/mkanavi/docker/iacgenie/
├── docker-compose-newvm.yml      # Main compose file
├── .env.pi                       # Environment variables (secrets)
├── prometheus.yml                # Prometheus scrape config
├── postgres_data/                # PostgreSQL data volume (Docker managed)
├── redis_data/                   # Redis data volume (Docker managed)
├── minio_data/                   # MinIO data volume (Docker managed)
├── openbao_data/                 # OpenBao data volume (Docker managed)
├── jenkins_data/                 # Jenkins data volume (Docker managed)
├── prometheus_data/              # Prometheus data volume (Docker managed)
├── grafana_data/                 # Grafana data volume (Docker managed)
├── cloudflared/
│   ├── config.yml                # Cloudflare tunnel config
│   └── auth.json                 # Tunnel credentials
└── docker/
    ├── postgres/
    │   └── init.sh               # DB init script
    ├── minio/
    │   └── init.sh               # Bucket creation script
    ├── openbao/
    │   └── bootstrap.sh          # KV engine setup
    ├── keycloak/
    │   ├── import-realm.sh       # Realm import script
    │   └── realm-export.json     # Keycloak realm definition
    ├── jenkins/
    │   ├── startup.sh            # JCasC plugin installer
    │   └── jenkins.config.yml    # Jenkins config
    └── grafana/
        └── provisioning/
            └── datasources/
                └── datasources.yml # Prometheus + Postgres datasources
```

## Cloudflare Tunnel Configuration

**Tunnel Name**: `iacgenie-pi`
**Credentials**: `~/.ssh/newvm_key` (auth.json in cloudflared/ directory)

### DNS Records (Cloudflare Zero Trust)

All `*.iacgenie.com` subdomains use CNAME records pointing to `<tunnel-id>.cfargotunnel.com`.

### Ingress Rules

| Hostname | Service | Protocol |
|----------|---------|----------|
| jenkins.iacgenie.com | http://jenkins:8080 | HTTP |
| postgres.iacgenie.com | tcp://postgres:5432 | TCP passthrough |
| redis.iacgenie.com | tcp://redis:6379 | TCP passthrough |
| minio.iacgenie.com | http://minio:9000 | HTTP |
| console.minio.iacgenie.com | http://minio:9001 | HTTP |
| vault.iacgenie.com | https://openbao:8200 | HTTPS (TLS) |
| auth.iacgenie.com | http://keycloak:8080 | HTTP |
| metrics.iacgenie.com | http://prometheus:9090 | HTTP |
| dashboards.iacgenie.com | http://grafana:3000 | HTTP |
| panel.iacgenie.com | http://coolify:8000 | HTTP |

## Secrets Inventory

All secrets are defined in `iacgenie/docker/.env.pi` and deployed to `~/docker/iacgenie/.env` on the VM.

### Core Secrets

| Secret | Service | Generation Method |
|--------|---------|-------------------|
| `POSTGRES_SUPER_PASSWORD` | PostgreSQL superuser | 32-byte URL-safe random |
| `POSTGRES_APP_PASSWORD` | IacGenie app user | 32-byte URL-safe random |
| `POSTGRES_KC_PASSWORD` | Keycloak DB user | 32-byte URL-safe random |
| `REDIS_PASSWORD` | Redis auth | 32-byte URL-safe random |
| `MINIO_ROOT_PASSWORD` | MinIO auth | 32-byte URL-safe random |
| `OPENBAO_ROOT_TOKEN` | OpenBao root (Shamir) | Auto-generated at init |
| `OPENBAO_TOKEN` | OpenBao app (Shamir) | Auto-generated at init |
| `OPENBAO_ADMIN_PASSWORD` | OpenBao admin user | `3bWLGXFwEQVtFXFOKDbTg` |
| `KEYCLOAK_ADMIN_PASSWORD` | Keycloak admin | 32-byte URL-safe random |
| `GRAFANA_ADMIN_PASSWORD` | Grafana admin | 32-byte URL-safe random |
| `JWT_SECRET` | Backend JWT signing | 64-byte URL-safe random |
| `JENKINS_ADMIN_USER` | Jenkins admin username | `admin` |
| `JENKINS_ADMIN_PASSWORD` | Jenkins admin password | 32-byte URL-safe random |

### External Secrets

| Secret | Source |
|--------|--------|
| `CLOUDFLARE_TUNNEL_TOKEN` | Cloudflare Zero Trust Dashboard |
| `SMTP2GO_API_KEY` | SMTP2GO Dashboard |
| `SENTRY_DSN` | Sentry Dashboard |
| `GITHUB_TOKEN` | GitHub Settings → Developer settings → Personal access tokens (classic) |

### Default Credentials

| Service | Username | Password |
|---------|----------|----------|
| PostgreSQL superuser | `postgres` | `POSTGRES_SUPER_PASSWORD` |
| PostgreSQL app | `iacgenie_user` | `POSTGRES_APP_PASSWORD` |
| PostgreSQL Keycloak | `keycloak` | `POSTGRES_KC_PASSWORD` |
| MinIO | `minioadmin` | `MINIO_ROOT_PASSWORD` |
| Keycloak admin | `admin` | `KEYCLOAK_ADMIN_PASSWORD` |
| Grafana admin | `admin` | `GRAFANA_ADMIN_PASSWORD` |
| Jenkins admin | `admin` | `JENKINS_ADMIN_PASSWORD` |

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
docker compose -f docker-compose-newvm.yml logs -f postgres
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

## Troubleshooting

### Services Won't Start

1. Check if images are pulled: `docker images`
2. Check .env file: `cat ~/docker/iacgenie/.env.pi`
3. Validate compose: `docker compose -f docker-compose-newvm.yml config --quiet`
4. Check logs: `docker compose -f docker-compose-newvm.yml logs`

### PostgreSQL Issues

- **Init script not running**: The init.sh is mounted as `/docker-entrypoint-initdb.d/99-init-users.sql`. PostgreSQL only runs init scripts on first startup when data directory is empty. If data already exists, init scripts are skipped.
- **Reinitialize DB**: Stop services, remove postgres_data volume, restart.
  ```bash
  docker compose -f docker-compose-newvm.yml down
  docker volume rm iacgenie_postgres_data
  docker compose -f docker-compose-newvm.yml up -d postgres
  ```

### Keycloak Won't Connect to PostgreSQL

Keycloak uses the `keycloak` PostgreSQL user. If connection fails:
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

Check tunnel credentials exist:
```bash
cat ~/docker/iacgenie/cloudflared/auth.json
```
Check tunnel status on Cloudflare Zero Trust Dashboard.

### Coolify Panel Issues

- Coolify connects to external PostgreSQL and Redis
- First startup requires database migrations (may take 2-5 minutes)
- Check logs: `docker logs iacgenie-coolify`

### Disk Space

```bash
df -h ~/docker/iacgenie/
docker system df
```

### Docker Compose v1 vs v2

This VM uses Docker Compose v5.1.4 (installed at `~/.docker/cli-plugins/docker-compose`). Both `docker compose` (v2 syntax) and `docker-compose` (v1 syntax) work. The compose file is v3.8 compatible.

## Maintenance Schedule

| Task | Frequency |
|------|-----------|
| Check Docker image updates | Weekly |
| Check disk space | Daily |
| Backup PostgreSQL data | Weekly |
| Review OpenBao secrets rotation | Monthly |
| Review Cloudflare tunnel logs | Monthly |

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

## Comparison: Old Pi vs New VM

| Aspect | Pi (Decommissioned) | New VM (Active) |
|--------|-------------------|-----------------|
| IP | 192.168.0.101 | 192.168.0.118 |
| CPU | Raspberry Pi 5 ARM | Intel x86_64 |
| OS | Ubuntu 25.10 aarch64 | elementary OS 8 (Ubuntu 24.04) |
| Storage | USB `/mnt/storage/` | Local `~/docker/iacgenie/` |
| Coolify | Removed | Included |
| Panel tunnel | Removed | `panel.iacgenie.com` |

## SSH Access from Local Mac

Add to `~/.ssh/config` on your Mac:

```
Host newvm
    HostName 192.168.0.118
    User mkanavi
    IdentityFile ~/.ssh/newvm_key
    UserKnownHostsFile /dev/null
    StrictHostKeyChecking no
```

Usage:
```bash
ssh newvm
scp -r ./file mkanavi@192.168.0.118:~/docker/iacgenie/
```

## Jenkins CI/CD Setup

### Prerequisites

Ensure SSH access is configured (above) and the terragenius repo is at `/workspace/terragenius` on the VM.

### Deploy Jenkins

Run these commands from the local Mac (in the terragenius repo root):

```bash
# Stop existing Jenkins
ssh newvm "cd ~/docker/iacgenie && docker compose -f docker-compose-newvm.yml stop jenkins"

# Copy Jenkins home data (job configs, plugins, etc.)
rsync -avz jenkins_home_data/ newvm:~/docker/iacgenie/jenkins_data/

# Copy Jenkins build files (Dockerfile, config, startup script, plugins)
rsync -avz iacgenie/docker/jenkins/ newvm:~/docker/iacgenie/docker/jenkins/

# Ensure workspace symlink exists
ssh newvm "mkdir -p /workspace && ln -sfn ~/docker/iacgenie /workspace/terragenius"

# Build custom Jenkins image (includes Node 22, Python 3.11, Docker CLI, JCasC)
ssh newvm "cd ~/docker/iacgenie && docker compose -f docker-compose-newvm.yml build jenkins"

# Start Jenkins
ssh newvm "cd ~/docker/iacgenie && docker compose -f docker-compose-newvm.yml up -d jenkins"

# Wait for JCasC to apply authentication config (2-3 minutes)
sleep 120
```

### Configure GitHub Access in Jenkins

1. Open `https://jenkins.iacgenie.com` and log in with username `admin` and the password from `.env.pi` (`JENKINS_ADMIN_PASSWORD`)
2. **Add GitHub SSH credential** (for git operations in pipelines):
   - Go to **Manage Jenkins** → **Credentials** → **System** → **Global Credentials**
   - **Kind**: SSH Username with private key
   - **ID**: `github-ssh`
   - **Username**: `git`
   - **Private Key**: Paste your SSH private key content (e.g., `~/.ssh/id_ed25519`)
   - **Description**: `GitHub SSH Key — terragenius repo access`
3. **Add GitHub API token** (for GitHub webhook / API access):
   - Go to **Manage Jenkins** → **Credentials** → **System** → **Global Credentials**
   - **Kind**: Secret text
   - **ID**: `github-token` (this ID is used by JCasC; you can also set it via env var)
   - **Secret**: Your GitHub personal access token (classic, with `repo` scope)
4. Go to **Manage Jenkins** → **System** and verify the Jenkins URL is set to `https://jenkins.iacgenie.com`

### Configure GitHub Webhooks (for PR triggers)

1. Go to GitHub repo → **Settings** → **Webhooks** → **Add webhook**
2. **Payload URL**: `https://jenkins.iacgenie.com/github-webhook/`
3. **Content type**: `application/json`
4. **Events**: Select `push` and `Pull Request`
5. Click **Add webhook**

### Verify Setup

```bash
# Check login page loads
curl -s https://jenkins.iacgenie.com/login | grep -i "password"

# List all jobs
curl -s -u admin:<password> https://jenkins.iacgenie.com/jenkins/api/json \
  | python3 -c "import sys,json; print([j['name'] for j in json.load(sys.stdin)['jobs']])"
# Expected: ['terragenius-backend-lint-build', 'terragenius-frontend-lint-build',
#            'terragenius-full-cicd', 'terragenius-full-sanity', 'terragenius-full-unit-tests']

# Trigger a manual build of the full pipeline
curl -X POST -u admin:<password> https://jenkins.iacgenie.com/jenkins/job/terragenius-full-cicd/build

# Check build status
curl -s -u admin:<password> https://jenkins.iacgenie.com/jenkins/job/terragenius-full-cicd/lastBuild/api/json \
  | python3 -c "import sys,json; print('Status:', json.load(sys.stdin).get('result','RUNNING'))"
```

### Test with a Dummy Commit

```bash
# Push a small commit to trigger the CI pipeline
ssh newvm "cd /workspace/terragenius && echo '' >> README.md && git add README.md && git commit -m 'ci: dummy commit for Jenkins verification' && git push"
```

The `terragenius-full-cicd` job should start building automatically (after the next GitHub webhook is received or within 5 minutes of SCM polling).

### Generating a New Password

The admin password hash is compiled into the Jenkins Docker image via JCasC. To change it:

1. Generate a new password and hash:
   ```bash
   python3 iacgenie/docker/jenkins/generate_hash.py "your-new-password"
   ```

2. Update the `passwordHash` in `iacgenie/docker/jenkins/jenkins.config.yml`:
   ```yaml
   passwordHash: "#jbcrypt:<output-from-generate_hash.py>"
   ```

3. Update `JENKINS_ADMIN_PASSWORD` in `iacgenie/docker/.env.pi` to match the new password.

4. Rebuild and restart:
   ```bash
   cd ~/docker/iacgenie
   docker compose -f docker-compose-newvm.yml build jenkins
   docker compose -f docker-compose-newvm.yml up -d jenkins
   sleep 120
   ```

**Important**: The password in `.env` (on the VM) must match the one used to generate the hash in `jenkins.config.yml`.

### Job Descriptions

| Job | Description |
|-----|-------------|
| `terragenius-backend-lint-build` | Ruff check, Mypy type check, pip-audit, backend unit + router tests |
| `terragenius-frontend-lint-build` | TypeScript check, Vitest unit tests, Vite build |
| `terragenius-full-sanity` | All lint/build steps + start DB/Redis + smoke tests against live backend |
| `terragenius-full-unit-tests` | All lint/build steps + backend unit+routers + frontend vitest |
| `terragenius-full-cicd` | Full pipeline: lint + build + smoke + unit tests + Playwright E2E tests |

### Persistence

All Jenkins configuration persists in `/home/mkanavi/docker/iacgenie/jenkins_data/` which is a Docker volume mounted from the host filesystem. Jobs, plugins, and authentication settings survive container restarts and server reboots.

**Credential encryption keys to back up separately** (do NOT include in regular backups — store off-site):
```
/home/mkanavi/docker/iacgenie/jenkins_data/secrets/master.key
/home/mkanavi/docker/iacgenie/jenkins_data/secrets/secret.key
```

These keys are required to decrypt stored credentials (SSH keys, API tokens). If lost or regenerated, all previously stored credentials become unrecoverable.

### Authentication Model

- Jenkins uses its built-in `local` security realm with JCasC configuration
- `ProjectMatrix` authorization strategy: `admin` user has full Administer permissions
- GitHub token is provisioned via JCasC as a system-level secret text credential (`github-token` ID)
- GitHub SSH credential (`github-ssh` ID) must be added manually via Jenkins UI
- For MFA and external identity providers, see Cloudflare Access documentation in `infra/services-secrets.md`
