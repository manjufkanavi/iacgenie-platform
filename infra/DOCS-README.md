# IacGenie Platform — End-to-End Documentation

> **Last Updated**: 2026-08-08  
> **VM**: 192.168.0.118 (elementary OS 8)  
> **Repository**: https://github.com/manjufkanavi/iacgenie-platform  

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Admin Guide](#admin-guide)
3. [DevOps Engineer Guide](#devops-engineer-guide)
4. [Engineer/AI Agent Guide](#engineerai-agent-guide)
5. [Security Reference](#security-reference)
6. [Emergency Procedures](#emergency-procedures)

---

## Architecture Overview

### Service Topology

```
User → Cloudflare Tunnel → Nginx (reverse proxy) → [Services]
                                                      │
                                        ┌───────────┼───────────┐
                                        │           │           │
                                   ┌────┴──┐    ┌──┴────┐  ┌──┴────┐
                                   │IacGenie│    │LightSerp│ │Other │
                                   │Services│    │Services │ │Svcs │
                                   └────┬───┘    └──┬────┘  └──┬────┘
                                        │           │           │
                                        └──────┬────┴──────┬────┘
                                               │           │
                                          ┌────┴──┐  ┌────┴────┐
                                          │  DBs   │  │Secrets  │
                                          └────────┘  └─────────┘
```

### Running Services (20+)

| Service | Container | Purpose | URL (via Cloudflare) |
|---------|-----------|---------|---------------------|
| PostgreSQL | `iacgenie_postgres` | Primary database | N/A (internal) |
| Redis | `iacgenie_redis` | Caching & sessions | N/A (internal) |
| MinIO | `iacgenie_minio` | S3 object storage | https://minio.iacgenie.com |
| OpenBao | `iacgenie_openbao` | Secrets management | https://vault.iacgenie.com |
| Keycloak | `iacgenie_keycloak` | OIDC provider | https://auth.iacgenie.com |
| Gitea | `iacgenie_gitea` | Git service | https://gitea.iacgenie.com |
| LightSerp API | `iacgenie_lightserp_api` | MCP backend | https://api.iacgenie.com |
| LightSerp WebUI | `iacgenie_lightserp_webui` | Next.js frontend | https://lightserp.iacgenie.com |
| NSQD | `iacgenie_nsqd` | Message queue | N/A (internal) |
| SearXNG | `iacgenie_searxng` | Search | https://search.iacgenie.com |
| Nginx | (systemd) | Reverse proxy | https://iacgenie.com |
| Cloudflared | (systemd x2) | Tunnel | N/A |

---

## Admin Guide

### What You Need to Know

As an admin, you have access to the platform administration panels. This section covers the operations you'll perform regularly.

### Key Service URLs

| Service | URL | Credentials |
|---------|-----|------------|
| Keycloak Admin | https://auth.iacgenie.com/admin | Platform admin role |
| OpenBao Vault | https://vault.iacgenie.com | Root token (vault) |
| Gitea | https://gitea.iacgenie.com | Keycloak SSO |
| Grafana | https://grafana.iacgenie.com | grafana-admin |

### Common Admin Tasks

#### 1. Create a New User

```
1. Go to https://auth.iacgenie.com
2. Login with your admin credentials
3. Navigate to Realm Settings → Users → Create
4. Set role: project-member, project-admin, or platform-admin
5. Set initial password or enable email registration
```

#### 2. Reset a User's Password

```
1. Go to https://auth.iacgenie.com/admin
2. Select the realm (iacgenie or lightserp)
3. Users → find user → Credentials → Reset Password
4. Send the reset link to the user
```

#### 3. Add a New Service Client

```
1. Keycloak Admin → Realm Settings → Clients → Create
2. Set client_id (e.g., "new-service")
3. Set redirect URIs (e.g., "https://new-service.iacgenie.com/*")
4. Set Web Origins (same as redirect URIs)
5. Note the Client Secret for the service configuration
6. Store the secret in OpenBao: iacgenie/kv/<service>/client_secret
```

#### 4. Check Service Health

```bash
# Run from any machine with SSH access
ssh mkanavi@192.168.0.118 "cd ~/iacgenie-platform/infra && ./health-check.sh"

# Or check individual services
ssh mkanavi@192.168.0.118 "docker ps --format 'table {{.Names}}\t{{.Status}}'"
```

#### 5. Restart a Service

```bash
# Restart a single service
ssh mkanavi@192.168.0.118 "docker restart iacgenie_<service_name>"

# Restart all services
ssh mkanavi@192.168.0.118 "cd ~/docker/iacgenie && docker compose up -d"
```

### OpenBao (Secrets Management)

OpenBao stores ALL secrets for the platform. As an admin, you may need to:

#### Add a New Secret

```bash
# Example: Add a new API key
ssh mkanavi@192.168.0.118 "bao kv put iacgenie/kv/new-service/api_secret value='your-secret-here'"
```

#### Read a Secret

```bash
ssh mkanavi@192.168.0.118 "bao kv get -field=password iacgenie/kv/postgres/password"
```

#### List All Secret Paths

```bash
ssh mkanavi@192.168.0.118 "bao kv list iacgenie/kv/"
```

### Backups

Backups run automatically at 2:00 AM daily and store encrypted copies on Google Drive.

#### Manual Backup

```bash
# Full backup
ssh mkanavi@192.168.0.118 "cd ~/iacgenie-platform/infra && ./backup-restore.sh backup all"

# Single service backup
ssh mkanavi@192.168.0.118 "cd ~/iacgenie-platform/infra && ./backup-restore.sh backup postgres"

# List available backups
ssh mkanavi@192.168.0.118 "cd ~/iacgenie-platform/infra && ./backup-restore.sh list"
```

#### Restore from Backup

```bash
# List backups first
ssh mkanavi@192.168.0.118 "cd ~/iacgenie-platform/infra && ./backup-restore.sh list"

# Restore specific backup
ssh mkanavi@192.168.0.118 "cd ~/iacgenie-platform/infra && ./backup-restore.sh restore <backup-file.gpg>"
```

---

## DevOps Engineer Guide

### Deployment

#### Full Deployment

```bash
cd ~/iacgenie-platform/infra
./deploy.sh
```

#### Dry Run (Check Mode)

```bash
./deploy.sh --check
./deploy.sh --diff   # Shows exactly what would change
```

#### Deploy Specific Role

```bash
./deploy.sh --role keycloak
./deploy.sh --role openbao
```

#### Start/Stop Services Only

```bash
./deploy.sh --services
```

### Drift Detection

```bash
# Full drift check
./drift-detect.sh

# Check specific area
./drift-detect.sh --check nginx
./drift-detect.sh --check data

# Auto-fix drift
./drift-detect.sh --fix
```

### Ansible Roles

All roles are under `infra/ansible/roles/`:

```
roles/
├── common/           → apt, SSH, NTP, prerequisites
├── docker/           → Docker Engine installation
├── postgresql/       → PostgreSQL container + config
├── redis/            → Redis container
├── minio/            → MinIO container
├── openbao/          → OpenBao + Raft + policies
├── keycloak/         → Keycloak container
├── keycloak_realm/   → Keycloak realm provisioning
├── gitea/            → Gitea container
├── lightserp/        → LightSerp API + WebUI
├── searxng/          → SearXNG container
├── nsqd/             → NSQD container
├── nginx-config/     → Nginx reverse proxy
├── cloudflare_tunnel/ → Cloudflared tunnels
├── backup/           → Backup scripts + cron
└── drift-detect/     → Drift detection script
```

### Systemd Services

Services are managed by systemd on the host:

```bash
# Master service
sudo systemctl status iacgenie-platform.service

# Nginx
sudo systemctl status nginx

# Cloudflare tunnels (2 instances)
sudo systemctl status cloudflared.service
```

### Monitoring

| Tool | Port | Purpose |
|------|------|---------|
| Prometheus | 9090 | Metrics |
| Grafana | 3001 | Dashboards |
| Loki | — | Logs (30-day retention) |

#### PromQL Examples

```sql
# Service uptime
up{job="iacgenie"}

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Memory usage
container_memory_usage_bytes{container="iacgenie_keycloak"}

# Disk usage
node_filesystem_avail_bytes{mountpoint="/"}
```

### Docker Management

```bash
# View all containers
docker ps -a

# View logs
docker logs -f iacgenie_keycloak
docker logs --tail 100 iacgenie_openbao

# Exec into container
docker exec -it iacgenie_keycloak /opt/keycloak/bin/kc.sh --help

# Resource usage
docker stats --no-stream
```

---

## Engineer/AI Agent Guide

### Connecting to Services

#### PostgreSQL

```bash
# Connection string
postgres://lightsrp:<password>@192.168.0.118:5432/lightsrp

# Get password from OpenBao
bao kv get -field=password iacgenie/kv/postgres/password
```

#### Redis

```bash
# Connection string
redis://:<password>@192.168.0.118:6379/0

# Get password from OpenBao
bao kv get -field=password iacgenie/kv/redis/password
```

#### MinIO

```bash
# S3 connection
export MINIO_ENDPOINT=minio.iacgenie.com
export MINIO_ACCESS_KEY=$(bao kv get -field=access_key iacgenie/kv/minio/root_user)
export MINIO_SECRET_KEY=$(bao kv get -field=password iacgenie/kv/minio/root_password)
export MINIO_SECURE=true

# Create bucket
mc alias set iacgenie https://minio.iacgenie.com
mc mb iacgenie/my-bucket
```

#### OpenBao API

```bash
# Login with service token
export VAULT_ADDR=https://vault.iacgenie.com
export VAULT_TOKEN=$(bao kv get -field=token iacgenie/kv/openbao/service_token)

# Read a secret
bao kv get iacgenie/kv/postgres/password

# List secrets
bao kv list iacgenie/kv/
```

#### Keycloak (OIDC)

```bash
# Get access token
curl -s -X POST https://auth.iacgenie.com/realms/iacgenie/protocol/openid-connect/token \
  -d "client_id=iacgenie-platform" \
  -d "client_secret=<from-openbao>" \
  -d "grant_type=client_credentials" \
  -d "scope=openid profile"

# Use token
curl -H "Authorization: Bearer <token>" https://iacgenie.com/api/resource
```

### Git Operations

```bash
# Clone
git clone https://gitea.iacgenie.com/iacgenie-platform.git

# Branch naming convention
feature/<description>    # New features
fix/<description>         # Bug fixes
infra/<description>       # Infrastructure changes
docs/<description>        # Documentation

# Commit message convention
type: short description

Types: feat, fix, docs, style, refactor, test, chore, infra
```

### Health Check API

```bash
# Full health check
cd ~/iacgenie-platform/infra && ./health-check.sh

# Check single service
./health-check.sh postgres
./health-check.sh keycloak
```

### Backup Commands (Quick Reference)

```bash
# Backup all services
./backup-restore.sh backup all

# Backup specific service
./backup-restore.sh backup postgres
./backup-restore.sh backup openbao
./backup-restore.sh backup gitea

# List backups
./backup-restore.sh list

# Verify backup integrity
./backup-restore.sh verify
```

---

## Security Reference

### Secrets Management

All secrets are stored in OpenBao KV under `iacgenie/kv/`:

| Secret | Path |
|--------|------|
| PostgreSQL password | `iacgenie/kv/postgres/password` |
| Redis password | `iacgenie/kv/redis/password` |
| MinIO root password | `iacgenie/kv/minio/root_password` |
| Keycloak admin password | `iacgenie/kv/keycloak/admin_password` |
| OpenBao root token | `iacgenie/kv/openbao/root_token` |
| Service API keys | `iacgenie/kv/<service>/api_secret` |

### Network Security

- All services bind to `127.0.0.1` (localhost only)
- External access only via Cloudflare Tunnel
- Nginx rate limiting: general 10r/s, auth 3r/m, API 30r/s
- Nginx security headers: X-Frame-Options, HSTS, CSP, etc.
- Docker security: no-new-privileges, minimal capabilities

### Authentication Flow

```
User → Cloudflare → Nginx → Keycloak Login → JWT Token
                                    │
                      ┌─────────────┼─────────────┐
                      │             │             │
                  IacGenie      LightSerp      Gitea
                  (OAuth)       (OAuth)       (SSO via KC)

Service → Keycloak OIDC → Service Token → OpenBao KV (secrets)
```

### User Roles

| Role | Description |
|------|-------------|
| platform-admin | Full admin across all platforms |
| project-admin | Admin for own project only |
| project-member | Read-only project access |
| api-user | API access (no web UI) |

---

## Emergency Procedures

### Service Down

```bash
# Check status
docker ps --format 'table {{.Names}}\t{{.Status}}'

# Restart
docker restart iacgenie_<service>

# View logs
docker logs --tail 200 iacgenie_<service>
```

### Data Loss Recovery

```bash
# 1. List backups
./backup-restore.sh list

# 2. Verify backup
./backup-restore.sh verify

# 3. Restore
./backup-restore.sh restore <backup-file.gpg>

# 4. Restart affected service
docker restart iacgenie_<service>
```

### VM Loss / Full Redeploy

```bash
# 1. Set up new VM
sudo apt update && sudo apt install -y docker.io ansible

# 2. Clone repo
git clone https://github.com/manjufkanavi/iacgenie-platform.git
cd iacgenie-platform/infra

# 3. Run deployment
./deploy.sh

# 4. Restore data from backup if needed
./backup-restore.sh restore <file>
```

### OpenBao Sealed

```bash
# 1. Get unseal keys
bao kv get iacgenie/kv/openbao/unseal_keys

# 2. Unseal
docker exec iacgenie_openbao bao operator unseal <key1>
docker exec iacgenie_openbao bao operator unseal <key2>
docker exec iacgenie_openbao bao operator unseal <key3>

# 3. Verify
docker exec iacgenie_openbao bao operator list-seal-status
```

### Keycloak Lockout

```bash
# 1. Get admin password from OpenBao
bao kv get iacgenie/kv/keycloak/admin_password

# 2. Reset via admin CLI
docker exec iacgenie_keycloak /opt/keycloak/bin/kc.sh set-password \
  --username admin --realm master --password <new-password>
```
