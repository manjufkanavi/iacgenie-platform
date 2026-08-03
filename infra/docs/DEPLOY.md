# DEPLOY.md — Infrastructure Deployment & Management Guide

|> **Last Updated**: 2026-08-03
> **Host**: 192.168.0.118 (VM)
> **Version**: 1.0
> **Status**: Active

---

## Table of Contents

- [1. Architecture Overview](#1-architecture-overview)
- [2. Prerequisites](#2-prerequisites)
- [3. Initial Setup](#3-initial-setup)
- [4. Service Deployment](#4-service-deployment)
- [5. CI/CD Automation](#5-cicd-automation)
- [6. Deployment Scripts](#6-deployment-scripts)
- [7. Health Checks](#7-health-checks)
- [8. Troubleshooting](#8-troubleshooting)
- [9. Security Hardening (Phase 10)](#9-security-hardening-phase-10)
- [10. Multi-Tenant & RBAC (Phase 10.3)](#10-multi-tenant--rbac-phase-103)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                       VM: 192.168.0.118                         │
│                                                                 │
│  ┌──────────────┐     ┌──────────────────────────────────────┐ │
│  │  Nginx       │◄────│  cloudflared tunnel                  │ │
│  │  (port 443)  │     │  *.iacgenie.com → 127.0.0.1          │ │
│  └──────┬───────┘     └──────────────────────────────────────┘ │
│         │                                                      │
│  ┌──────┼──────────────────────────────────────────────────────┤ │
│  │      ▼                                                      │ │
│  │  ┌─────────────────────────────────────────────────────────┐ │
│  │  │ Docker Network: iacgenie_network (shared)               │ │
│  │  │ Docker Network: shared_internal (service-to-service)    │ │
│  │  └─────────────────────────────────────────────────────────┘ │
│  │      │                                                      │
│  │  ┌───┴───┬───┴───┬───┴───┬───┴───┬───┴───┬───┴───┬───┴───┐ │
│  │  │  pg   │ redis │  ob   │  kc   │ minio │ gitea │ searx │ │
│  │  └───────┴───────┴───────┴───────┴───────┴───────┴───────┘ │
│  │      │                                                      │
│  │  ┌───┴──────────────────────────┬───────────────────────────┐ │
│  │  │  Platform Services           │  Monitoring               │ │
│  │  │  - IacGenie (:3000)          │  - OpenBao audit log      │ │
│  │  │  - LightSerp (:3071)         │  - OpenBao KV-v2 secrets │ │
│  │  │  - PageZen (:3080)           │  - Gitea CI runner        │ │
│  │  │  - NSQD (:3070)              │                           │ │
│  │  │  - NSQD Admin (:3072)        │                           │ │
│  │  └──────────────────────────────┴───────────────────────────┘ │
│  └──────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Service Summary

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| PostgreSQL | iacgenie-postgres | 5432 | Primary database |
| Redis | iacgenie-redis | 6379 | Cache + message broker |
| OpenBao | iacgenie-openbao | 8200 | Secrets management |
| Keycloak | iacgenie-keycloak | 8080 | Authentication |
| MinIO | iacgenie-minio | 9000, 9001 | Object storage (S3) |
| Gitea | iacgenie-gitea | 3000, 22 | Git + CI/CD |
| LightSerp | iacgenie-lightsrp | 3071 | Search + SearXNG |
| SearXNG | iacgenie-searxng | 8081 | Metasearch engine |
| PageZen | iacgenie-pagezen | 3080 | Local search |
| NSQD | iacgenie-nsqd | 3070 | Message queue |
| NSQD Admin | iacgenie-nsqadmin | 3072 | NSQ dashboard |

---

## 2. Prerequisites

### Hardware
- **CPU**: 4+ cores
- **RAM**: 8GB+ (16GB recommended)
- **Storage**: 100GB+ SSD
- **OS**: Ubuntu 22.04 LTS / Debian 12

### Software
- Docker Engine ≥ 24.0
- Docker Compose ≥ 2.20
- Nginx ≥ 1.24
- Cloudflare Tunnel
- Git ≥ 2.40

### Network
- Domain: `*.iacgenie.com` (pointing to VM IP)
- Ports 80, 443 open (Cloudflare proxy)
- Internal ports: 22, 3000, 3070-3080, 5432, 8080-8081, 8200, 9000-9001

### Domain Mapping (Nginx)

| Hostname | Proxy To | Service |
|----------|----------|---------|
| `gitea.iacgenie.com` | 127.0.0.1:3000 | Gitea |
| `keycloak.iacgenie.com` | 127.0.0.1:8080 | Keycloak |
| `lightsrp.iacgenie.com` | 127.0.0.1:3071 | LightSerp |
| `vault.iacgenie.com` | 127.0.0.1:8200 | OpenBao |
| `searxng.iacgenie.com` | 127.0.0.1:8081 | SearXNG |

---

## 3. Initial Setup

### 3.1 Clone Repository

```bash
# Clone the unified infrastructure repository
mkdir -p ~/gitea-sync
cd ~/gitea-sync
git clone https://gitea.iacgenie.com/iacgenie/iacgenie-unified-infra.git
cd iacgenie-unified-infra
```

### 3.2 Set Environment Variables

```bash
# Copy and edit environment template
cp .env.example .env
# Edit .env with your values
nano .env
```

**Required `.env` variables:**

| Variable | Description |
|----------|-------------|
| `OPENBAO_ROOT_TOKEN` | OpenBao root token |
| `POSTGRES_SUPER_PASSWORD` | PostgreSQL superuser password |
| `POSTGRES_APP_PASSWORD` | Application database user password |
| `POSTGRES_KC_PASSWORD` | Keycloak database user password |
| `REDIS_PASSWORD` | Redis authentication password |
| `MINIO_ROOT_USER` | MinIO admin username |
| `MINIO_ROOT_PASSWORD` | MinIO admin password |
| `JWT_SECRET` | JWT signing secret |
| `SEARXNG_SECRET` | SearXNG secret key |

### 3.3 Start Infrastructure

```bash
# Start all services
docker compose -f docker-compose-unified.yml up -d

# Verify all services are running
docker compose -f docker-compose-unified.yml ps

# Check service health
for container in $(docker compose -f docker-compose-unified.yml ps -q); do
    echo "$(docker inspect --format '{{.Name}} {{.State.Health.Status}}' $container)"
done
```

---

## 4. Service Deployment

### 4.1 PostgreSQL

```bash
# Ensure persistent data
ls -la /home/mkanavi/docker/iacgenie/data/postgresql/

# Restart with volume
docker compose -f docker-compose-unified.yml up -d postgres
```

### 4.2 Redis

```bash
# Ensure persistence
docker compose -f docker-compose-unified.yml up -d redis
```

### 4.3 OpenBao

```bash
# Wait for OpenBao to start
sleep 10

# Initialize OpenBao (first time only)
bash /home/mkanavi/gitea-sync/iacgenie-unified-infra/scripts/bootstrap_openbao.sh init

# Unseal OpenBao
bash /home/mkanavi/gitea-sync/iacgenie-unified-infra/scripts/bootstrap_openbao.sh unseal

# Seed secrets
bash /home/mkanavi/gitea-sync/iacgenie-unified-infra/scripts/bootstrap_openbao.sh seed
```

### 4.4 Gitea

```bash
# Gitea is initialized via web UI
# Access: http://127.0.0.1:3000/install
# Configuration:
#   - Database: PostgreSQL (host: postgres, port: 5432)
#   - Database name: gitea
#   - Database user: gitea
#   - Database password: (from .env)

# Verify Gitea API
curl -s http://127.0.0.1:3000/api/v1/version

# Register self-hosted runner
mkdir -p ~/.runner
cd ~/.runner
/home/mkanavi/bin/gitea-runner register \
    --instance https://gitea.iacgenie.com \
    --token <registration-token>

# Start runner as systemd service
sudo systemctl daemon-reload
sudo systemctl enable --now gitea-runner.service
sudo systemctl status gitea-runner.service
```

### 4.5 Nginx

```bash
# Copy configuration
sudo cp /home/mkanavi/gitea-sync/iacgenie-unified-infra/nginx-unified.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/nginx-unified.conf /etc/nginx/sites-enabled/

# Test and reload
sudo nginx -t
sudo systemctl reload nginx

# Check service
sudo systemctl status nginx
```

### 4.6 Cloudflare Tunnel

```bash
# Configure tunnel
sudo tee /etc/systemd/system/cloudflared-iacgenie.service > /dev/null << 'EOF'
[Unit]
Description=Cloudflare Tunnel for IacGenie
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
ExecStart=/home/mkanavi/bin/cloudflared tunnel --no-autoupdate run \
    --url http://127.0.0.1:80 \
    --protocol http2
Restart=always
RestartSec=10
User=mkanavi

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now cloudflared-iacgenie
sudo systemctl status cloudflared-iacgenie
```

---

## 5. CI/CD Automation

This project uses **GitHub Actions** for automated infrastructure deployment and destruction. Both workflows run on push to `main` branch and include:

- SSH-based deployment to the production VM (`192.168.0.118`)
- Service health verification with port-level checks
- Beautiful HTML status reports (dark/light theme)
- Email notifications with full report attached

### Available Workflows

| Workflow | Purpose | Trigger | Preserves |
|----------|---------|---------|-----------|
| [**Deploy & Verify**](.github/workflows/deploy-and-verify.yml) | Deploy all 11 services, verify health | Push to `main` | Data volumes, `.env`, configs |
| [**Destroy Services**](.github/workflows/destroy-without-proxy.yml) | Tear down Docker services | Push to `main` | Nginx, Cloudflare Tunnel, data |

### GitHub Secrets Required

| Secret | Required | Description |
|--------|----------|-------------|
| `SSH_PRIVATE_KEY` | ✅ | SSH private key for VM access |
| `SSH_HOST` | ✅ | VM IP address (`192.168.0.118`) |
| `SSH_USER` | ✅ | SSH username (`mkanavi`) |
| `EMAIL_TO` | ✅ | Notification email |
| `SMTP_HOST` | ✅ | SMTP server (e.g., `smtp.gmail.com`) |
| `SMTP_PORT` | ✅ | SMTP port (`587`) |
| `SMTP_USER` | ✅ | Sender email |
| `SMTP_PASSWORD` | ✅ | SMTP app password |

### Manual Trigger

Workflows can also be triggered manually:
1. Go to **GitHub → Actions** tab
2. Select the workflow
3. Click **"Run workflow"** → `main` → **Run workflow**

### HTML Reports

Both workflows generate a dark-themed HTML report showing:
- ✅ Service health status (all 11 Docker services)
- 🔌 Port connectivity verification
- 📊 Duration, timestamps, commit SHA
- 📜 Execution log timeline

Reports are available as GitHub Actions artifacts (30-day retention) and sent via email.

> **Full CI/CD documentation**: See [CICD-GUIDE.md](./CICD-GUIDE.md) for setup instructions, troubleshooting, and workflow diagrams.

---

## 6. Deployment Scripts

### 6.1 Quick Start

```bash
#!/bin/bash
# quick-start.sh — Full infrastructure bootstrap

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Starting IacGenie Infrastructure ==="

# 1. Start all services
echo "[1/6] Starting Docker services..."
docker compose -f "$SCRIPT_DIR/docker-compose-unified.yml" up -d

# 2. Wait for database
echo "[2/6] Waiting for PostgreSQL..."
for i in $(seq 1 30); do
    if docker exec iacgenie-postgres pg_isready -q 2>/dev/null; then
        echo "  PostgreSQL ready."
        break
    fi
    echo "  Waiting... ($i/30)"
    sleep 2
done

# 3. Wait for OpenBao
echo "[3/6] Waiting for OpenBao..."
for i in $(seq 1 30); do
    if curl -sf http://127.0.0.1:8200/v1/sys/health >/dev/null 2>&1; then
        echo "  OpenBao ready."
        break
    fi
    sleep 2
done

# 4. Initialize OpenBao
echo "[4/6] Initializing OpenBao..."
bash "$SCRIPT_DIR/openbao/bootstrap.sh"

# 5. Deploy platform services
echo "[5/6] Starting platform services..."
docker compose -f "$SCRIPT_DIR/docker-compose-iacgenie.yml" up -d
docker compose -f "$SCRIPT_DIR/docker-compose-lightsrp.yml" up -d

# 6. Configure Nginx and Tunnel
echo "[6/6] Configuring Nginx and Cloudflare Tunnel..."
sudo nginx -t && sudo systemctl reload nginx
sudo systemctl restart cloudflared-iacgenie

echo "=== Infrastructure ready! ==="
docker compose -f "$SCRIPT_DIR/docker-compose-unified.yml" ps
```

### 6.2 Rollback

```bash
#!/bin/bash
# rollback.sh — Rollback to previous state

set -euo pipefail

echo "=== Rolling back infrastructure ==="

# Stop platform services
docker compose -f docker-compose-iacgenie.yml down
docker compose -f docker-compose-lightsrp.yml down

# Stop infrastructure
docker compose -f docker-compose-unified.yml down

# Start from previous snapshot
docker compose -f docker-compose-unified.yml up -d
docker compose -f docker-compose-iacgenie.yml up -d
docker compose -f docker-compose-lightsrp.yml up -d

echo "=== Rollback complete ==="
```

---

## 7. Health Checks

### 7.1 Docker Health

```bash
#!/bin/bash
# docker-health.sh — Check all service health

echo "=== Service Health Status ==="
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -i healthy
echo ""
echo "=== Failed Services ==="
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -iv healthy | grep -iv "NAME"
echo ""
echo "=== OpenBao Status ==="
curl -sf http://127.0.0.1:8200/v1/sys/seal-status | python3 -m json.tool 2>/dev/null || echo "OpenBao unreachable"
echo ""
echo "=== Nginx Status ==="
sudo nginx -t 2>&1 | tail -1
sudo systemctl is-active nginx
```

### 7.2 Automated Monitoring

Service health is tracked via:
- **Docker healthchecks** (embedded in compose files)
- **OpenBao audit logging** (file + syslog)
- **Systemd service status** (for Nginx, cloudflared, gitea-runner)
- **Cron-based checks** (run via `systemd-timer` or `crontab`)

### 7.3 Gitea CI Pipeline

Each repo has a `.gitea/workflows/` CI pipeline:

| Repository | Workflow | Trigger |
|-----------|----------|---------|
| `iacgenie` | `iacgenie-ci.yml` | push/PR to main |
| `iacgenie-unified-infra` | `infra-ci.yml` | push/PR to main |
| `lightserp` | `phase1-ci.yml` | push/PR to main |

**CI Pipeline Steps:**
1. `actions/checkout@v4` — Clone repository
2. `actions/setup-python@v5` — Python 3.11
3. Install dependencies
4. Run linter (ruff → flake8)
5. Run tests (pytest / Django)
6. Validate Docker Compose files

---

## 8. Troubleshooting

### 8.1 Services Won't Start

```bash
# Check Docker logs
docker logs iacgenie-postgres --tail 50
docker logs iacgenie-openbao --tail 50
docker logs iacgenie-gitea --tail 50

# Verify network
docker network ls
docker network inspect iacgenie_network

# Check disk space
df -h
docker system df

# Clean up unused resources
docker system prune -af
docker volume prune -f
```

### 8.2 OpenBao Issues

```bash
# Check seal status
curl -sf http://127.0.0.1:8200/v1/sys/seal-status

# Unseal if needed
OPENBAO_TOKEN="your-token"
curl -s -X POST http://127.0.0.1:8200/v1/sys/unseal \
    -H "Content-Type: application/json" \
    -H "X-Vault-Token: $OPENBAO_TOKEN" \
    -d '{"key": "unseal-key-1"}'

# Verify KV engine
curl -sf http://127.0.0.1:8200/v1/sys/mounts | python3 -m json.tool
```

### 8.3 Nginx Issues

```bash
# Test configuration
sudo nginx -t

# Check access/error logs
sudo tail -50 /var/log/nginx/error.log
sudo tail -50 /var/log/nginx/access.log

# Reload after changes
sudo systemctl reload nginx
```

### 8.4 Gitea Issues

```bash
# Check Gitea logs
docker logs iacgenie-gitea --tail 50

# Check Gitea API
curl -s http://127.0.0.1:3000/api/v1/status

# Verify runner
curl -s http://127.0.0.1:3000/api/v1/actions/runners/launchers
```

### 8.5 Network Issues

```bash
# Test connectivity between containers
docker exec iacgenie-postgres ping -c 1 iacgenie-redis
docker exec iacgenie-lightsrp ping -c 1 iacgenie-openbao

# Test external access
curl -sfk https://gitea.iacgenie.com/api/v1/version
curl -sfk https://lightsrp.iacgenie.com/health
```

---

## 9. Security Hardening (Phase 10)

Phase 10 applies production-grade security hardening across all infrastructure components.

### 9.1 Secrets Management

All sensitive values are encrypted via **Ansible Vault**. Variables are managed through templates (`.env.j2`) — never committed in plaintext.

| File | Vault Target |
|------|-------------|
| `all.yml` | `roles/encrypt-secrets/` |
| `cloudflare_tunnel.yml` | `roles/encrypt-secrets/` |

### 9.2 Docker Network Segmentation

Three isolated Docker networks replace the legacy single `iacgenie_network`:

| Network | Purpose | Services |
|---------|---------|----------|
| `frontend` | Public-facing, nginx routing | iacgenie, lightserp, pagezen |
| `backend` | Service-to-service communication | postgres, redis, openbao, keycloak, minio, nsqd |
| `messaging` | Queue communication | nsqd, iacgenie, lightserp |

### 9.3 Nginx Security Headers

All deployed nginx configs include 8 security headers:

| Header | Value | Purpose |
|--------|-------|---------|
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` | Enforce HTTPS |
| `X-Frame-Options` | `SAMEORIGIN` | Prevent clickjacking |
| `X-Content-Type-Options` | `nosniff` | MIME-type sniffing |
| `X-XSS-Protection` | `1; mode=block` | XSS filtering |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limit referrer leakage |
| `Content-Security-Policy` | Restrictive policy | Prevent code injection |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=(), payment=()` | Disable sensitive APIs |
| `X-Permitted-Cross-Domain-Policies` | `none` | Restrict cross-domain access |

**Nginx configs** are deployed to `/etc/nginx/sites-enabled/` on the VM. Template files are version-controlled in the `docker-configs` repository.

### 9.4 Gitea Hardening

Gitea security defaults (`roles/gitea/defaults/main.yml`):

- ✅ 2FA enforced (`settings.security.REQUIRE_2FA_AUTH = true`)
- ✅ User registration disabled (`settings.services.ENABLE_REGISTRATION = false`)
- ✅ CAPTCHA enabled on signup (`settings.security.REQUIRE_CAPTCHA = true`)
- ✅ Login rate limiting: `settings.security.LOGIN_CAPTCHA_RATE_LIMIT = 60`
- ✅ SSH cloning enforced (`settings.git.disable_shell = true`)
- ✅ Auto-redirect to HTTPS (`settings.server.ENABLE_FALLBACK_SSL = true`)

### 9.5 MinIO Console Lockdown

- MinIO console API (port 9001) is **not exposed** directly
- Only the MinIO API (port 9002) and console proxy (nginx proxy via `minio-nginx.conf`) are accessible
- Console access restricted to `127.0.0.1` via `allow 127.0.0.1; deny all;`

### 9.6 Credential Isolation

- All admin passwords sourced from `.env` / Ansible Vault — never hardcoded in compose files
- Gitea admin credentials: `GITEA_ADMIN_USER` + `GITEA_ADMIN_PASSWORD` (from vault)
- Database passwords: rotated via `bootstrap_openbao.sh` and stored in OpenBao

### 9.7 Nginx Deployment

To deploy nginx config changes to the VM:

```bash
# From the repo root
scp iacgenie-nginx.conf mkanavi@192.168.0.118:/etc/nginx/sites-enabled/iacgenie-nginx.conf
ssh mkanavi@192.168.0.118 "sudo nginx -t && sudo systemctl reload nginx"
```

Nginx templates are also version-controlled in:
- `docker-configs/iacgenie-nginx.conf` (standalone deployment)
- `roles/nginx/templates/` (Ansible-managed)

---

## 10. Multi-Tenant & RBAC (Phase 10.3)

Phase 10.3 introduces multi-tenant identity management and project-based access control across all platform services.

### 10.1 Keycloak Multi-Tenant Realm (10.11)

The Keycloak realm has been migrated from a single `unified` realm to a `iacgenie` realm with project-based scoping.

#### Realm Structure

**Realm**: `iacgenie`

**Realm Roles** (hierarchical):

| Role | Scope | Description |
|------|-------|-------------|
| `platform-admin` | Global | Full platform access — all projects, services, and configuration |
| `project-admin` | Per-project | Admin access within assigned projects (repo management, team assignment) |
| `member` | Per-project | Standard access to project repositories |
| `service-account` | Global | Machine-to-machine access for automated workflows |

**Legacy Role Mapping**:

| Legacy Role | New Role | Notes |
|-------------|----------|-------|
| `admin` | `platform-admin` | Composite role — includes `platform-admin` |
| `iacgenie_admin` | `platform-admin` | Composite role — includes `platform-admin` |
| `user` | `member` | Default role for all new users |
| `app_user` | `member` | Default role with `member` sub-role |

**Realm Groups**:

| Group | Default Role | Purpose |
|-------|-------------|---------|
| `/platform-admins` | `platform-admin` | Platform administrators (super-admins) |
| `/project-admins` | `project-admin` | Project-level administrators |
| `/project-members` | `member` | Standard project contributors |
| `/iacgenie-users` | (none) | IacGenie platform users group |
| `/lightsrp-users` | (none) | LightSerp platform users group |

**Client Scopes** (injected into JWT tokens):

| Scope | Protocol Mapper | Claim | Purpose |
|-------|----------------|-------|---------|
| `iacgenie-project-scope` | `oidc-usermodel-attribute-mapper` | `project_id` | Maps user to their project identifier |
| `iacgenie-project-scope` | `oidc-usermodel-attribute-mapper` | `project_path` | Maps user to their Gitea project path |
| `iacgenie-role-scope` | `oidc-usermodel-realm-role-mapper` | `roles` | Maps user realm roles to JWT claim |
| `iacgenie-role-scope` | `oidc-usermodel-realm-role-mapper` | `groups` | Maps user group memberships |
| `project-dynamic-scope` | `oidc-script-mapper` | `projects` | Dynamic project list from user attributes |
| `project-dynamic-scope` | `oidc-script-mapper` | `project_permissions` | Per-project permission mapping |

**Clients**:

| Client | Default Scopes | Redirect URIs |
|--------|---------------|---------------|
| `iacgenie` | project-scope, role-scope, dynamic-scope | `https://iacgenie.local/*`, `http://localhost:5173/*` |
| `lightsrp` | project-scope, role-scope, dynamic-scope | `https://lightsrp.local/*`, `http://localhost:3001/*` |

**Users**:

| User | Roles | Groups | Projects |
|------|-------|--------|----------|
| `admin` | platform-admin, member | /platform-admins, /iacgenie-users | iacgenie-platform, lightsrp-platform |
| `iacgenie-service` | service-account, member | /project-members | iacgenie-platform |
| `lightsrp-service` | service-account, member | /project-members | lightsrp-platform |

#### Adding New Projects

To add a new project:

1. **Create Keycloak user attribute** on the user:
   ```bash
   # Via Keycloak Admin Console or REST API
   curl -X PUT \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     "http://localhost:8080/admin/realms/iacgenie/users/<user-id>/attributes/projects" \
     -d '{"value": "iacgenie-platform,lightsrp-platform,new-project"}'
   ```

2. **Create Gitea organization** (via setup script):
   ```bash
   ./scripts/setup-gitea-orgs.sh --dry-run  # Preview
   ./scripts/setup-gitea-orgs.sh            # Execute
   ```

3. **Verify JWT claim injection**:
   ```bash
   # Decode the JWT and check for project_id claim
   echo "$JWT_TOKEN" | cut -d. -f2 | base64 -d | python3 -m json.tool
   ```

### 10.2 Gitea Project-Based Organization (10.12)

Gitea is configured for multi-tenant project management with organization-level isolation.

#### Organization Structure

| Organization | Admin | Repositories | Purpose |
|-------------|-------|-------------|---------|
| `iacgenie-platform` | admin | iacgenie-unified-infra, iacgenie-web, lightsrp | Core IacGenie infrastructure and apps |
| `lightsrp-platform` | admin | lightsrp-web, lightsrp-api, lightserp-searxng | LightSerp platform services |

#### Configuration

**docker-compose-unified.yml** adds the Gitea service with:

```yaml
gitea:
  environment:
    - GITEA_ADMIN_ORG=iacgenie-platform      # Default org for admin user
    - GITEA__admin__org=iacgenie-platform     # Org creation on first login
    - GITEA__service__DISABLE_REGISTRATION=true
    - GITEA__server__HTTP_PORT=3000
    - GITEA__server__SSH_PORT=2222
    - GITEA__security__INSTALL_LOCK=true
```

#### Auto-Setup Script

`scripts/setup-gitea-orgs.sh` creates the default org/project structure on first boot:

```bash
# Preview what would be created
./scripts/setup-gitea-orgs.sh --dry-run

# Create organizations, repos, and teams
./scripts/setup-gitea-orgs.sh

# Environment variables used:
#   GITEA_URL      — Gitea instance URL (default: http://127.0.0.1:3000)
#   GITEA_ADMIN_USER — Admin username (default: from GITEA_ADMIN_USER env)
#   GITEA_ADMIN_TOKEN — Admin API token (default: GITEA_ADMIN_PASSWORD)
```

#### RBAC Flow

```
User logs in via Keycloak
  │
  ▼
Keycloak issues JWT with claims:
  ├── roles: [platform-admin, member]
  ├── groups: [platform-admins, iacgenie-users]
  ├── project_id: "iacgenie-platform"
  ├── projects: ["iacgenie-platform", "lightsrp-platform"]
  └── project_permissions: {"iacgenie-platform": "admin"}
  │
  ▼
IacGenie platform validates JWT
  ├── Checks issuer = Keycloak realm
  ├── Checks project_id matches user attribute
  ├── Checks role scope for action authorization
  └── Grants access based on RBAC policy
  │
  ▼
Gitea API called with user token
  ├── Gitea maps Keycloak roles to organization teams
  ├── Team determines repo access level
  └── Repository operations allowed/denied
```

### 10.3 Cross-Service Integration

| Service | Integration | Key Claim |
|---------|------------|-----------|
| IacGenie Platform | Validates JWT, checks `project_id` + `roles` | `project_id`, `roles` |
| LightSerp Platform | Validates JWT, checks `projects` | `projects` |
| Gitea | Maps Keycloak org to teams | Org name from `project_id` |
| OpenBao | Keys per-project in KV store | `project_id` as path prefix |
| MinIO | Bucket-per-project storage | `project_id` as bucket name |

---

## Appendix A: Docker Compose Reference

### docker-compose-unified.yml

Core infrastructure services. Managed via `docker compose -f docker-compose-unified.yml`.

### docker-compose-iacgenie.yml

IacGenie application service. Depends on unified infrastructure.

### docker-compose-lightsrp.yml

LightSerp application service. Depends on unified infrastructure.

## Appendix B: Backup & Recovery

See [BACKUP.md](./BACKUP.md) for backup procedures.

## Appendix C: Security Checklist (Updated 2026-08-03, Phase 10)

- ✅ All services bound to 127.0.0.1 (not 0.0.0.0)
- ✅ Cloudflare Tunnel for external access
- ✅ Nginx reverse proxy with HTTPS + 8 security headers
- ✅ OpenBao for secrets management (Ansible Vault encrypted)
- ✅ Keycloak for authentication
- ✅ Firewall rules restrict direct access to service ports
- ✅ Regular secret rotation via OpenBao
- ✅ Audit logging enabled (OpenBao file + syslog)
- ✅ Docker network segmentation (frontend/backend/messaging)
- ✅ Gitea hardening (2FA, no registration, CAPTCHA, rate limiting)
- ✅ MinIO console locked down (port 9001 not directly exposed)
- ✅ Credential isolation (no hardcoded passwords in compose files)
