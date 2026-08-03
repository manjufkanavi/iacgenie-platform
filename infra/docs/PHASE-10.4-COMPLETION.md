# Phase 10.4 Completion Report

**Date:** 2026-08-04
**Status:** Complete
**Branch:** main
**Parent Commit:** aae79bb (Phase 10.17-10.22)

---

## Overview

Phase 10.4 covers production hardening across logging, monitoring, backup, TLS, tunnel redundancy, resource quotas, and idempotency. It also includes two critical bug fixes.

---

## Sub-Phase Breakdown

### Phase 10.17 — Logging Stack (Loki + Promtail)

**Purpose:** Centralized log collection and aggregation.

**Services Added:**
- **Loki** (`grafana/loki:2.9.0`) — Log aggregation on port 3100
- **Promtail** (`grafana/promtail:2.9.0`) — Log shipper on port 9080

**Files Created/Modified:**
- `docker-compose-unified.yml` — Added Loki and Promtail service definitions
- `configs/loki/` — Loki configuration directory
- `configs/promtail/` — Promtail configuration directory

**Deployment:**
```bash
cd ~/docker/iacgenie
./deploy.sh --group iacgenie
```

**Health Check:**
- Loki: `http://127.0.0.1:3100/ready` → 200
- Promtail: Tail log files, push to Loki endpoint

---

### Phase 10.18 — Monitoring Stack (Prometheus + Grafana)

**Purpose:** Metrics collection, alerting, and visualization.

**Services Added:**
- **Prometheus** (`prom/prometheus:v2.50.0`) — Metrics store on port 9090
- **Grafana** (`grafana/grafana:10.3.0`) — Dashboards on port 3000

**Files Created/Modified:**
- `docker-compose-unified.yml` — Added Prometheus and Grafana service definitions
- `configs/prometheus/` — Prometheus configuration (scrape targets, retention)
- `configs/` — Prometheus alerting rules (if any)

**Deployment:**
```bash
cd ~/docker/iacgenie
./deploy.sh --group monitoring
```

**Configuration:**
- Prometheus scrape targets: Docker, Loki, Gitea, Keycloak, OpenBao
- Grafana: Pre-configured datasources for Prometheus and Loki
- Retention: 10GB disk limit

---

### Phase 10.19 — Gitea Backup & Disaster Recovery

**Purpose:** Automated backup and restore for Gitea data.

**Files Created/Modified:**
- `scripts/backup_gitea.sh` — Automated Gitea backup with checksums
- `scripts/backup_verification.sh` — Backup verification script
- `scripts/dr_test.sh` — Disaster recovery test script
- `docker-compose-unified.yml` — Backup cron in Gitea container
- `docker/gitea/` — Updated Gitea configuration for backup integration

**Backup Details:**
- **Schedule:** Daily at 3:00 AM
- **Retention:** 7 days
- **Contents:** Git repositories, database, LFS objects
- **Verification:** SHA256 checksums per backup file
- **DR Test:** Full restore to temporary container

---

### Phase 10.20 — TLS Certificate Automation

**Purpose:** Automated TLS certificate management via Certbot + DNS-01 challenge.

**Files Created/Modified:**
- `scripts/certbot-auto.sh` — Automated certbot renewal
- `scripts/cert-monitor.sh` — Certificate expiry monitoring
- `configs/systemd/certbot-renew.service` — Systemd service
- `configs/systemd/certbot-renew.timer` — Systemd timer (daily at 4:00 AM)
- `docker-compose-unified.yml` — Certbot volume mounts

**Certificate Domains:**
- `iacgenie.local`
- `lightsrp.local`
- `infra.local`
- `grafana.iacgenie.com`

**DNS Challenge:** Cloudflare DNS API (DNS-01)

---

### Phase 10.21 — Nginx Reverse Proxy + Cloudflare Redundancy

**Purpose:** Production-grade reverse proxy and tunnel redundancy.

**Services Added:**
- **Nginx** (`nginx:1.25-alpine`) — Reverse proxy on port 443
- **Cloudflare 2** (`cloudflare/cloudflared:latest`) — Secondary tunnel on port 8090

**Files Created/Modified:**
- `nginx-unified.conf` — Complete Nginx configuration with security headers, rate limiting, TLS
- `docker-compose-unified.yml` — Added Nginx and cloudflared-2 services
- `configs/` — Nginx configuration templates

**Security Features:**
- TLS 1.2+ only
- CSP, HSTS, X-Frame-Options, X-Content-Type-Options headers
- Rate limiting (10r/s general, 3r/m auth, 30r/s API)
- Disabled dangerous HTTP methods
- Health check endpoint at `127.0.0.1:8888/health`

---

### Phase 10.22 — Resource Quotas Enforcement

**Purpose:** Ensure all services have resource limits to prevent runaway containers.

**Changes Applied:**
- All services in `docker-compose-unified.yml` have `deploy.resources.limits`
- Memory and CPU limits per service
- Cgroups v2 compatible format
- Documentation in README.md

**Resource Summary:**
- PostgreSQL: 1.5G mem, 0.5 CPU
- Redis: 256M mem, 0.25 CPU
- MinIO: 1G mem, 1.0 CPU
- Gitea: 512M mem, 0.5 CPU
- Total: ~7.5G memory, ~3.5 cores

---

### Phase 10.23 — Ansible Idempotency Hardening

**Purpose:** Automated validation and drift detection.

**Files Created:**
- `ansible/site.yml` — Main playbook orchestrating all roles
- `ansible/vars/main.yml` — Global variables + version-pinned Docker images
- `ansible/playbooks/validate_compose.yml` — Pre-deploy compose validation
- `ansible/playbooks/drift_detection.yml` — Post-deploy drift detection
- `ansible/roles/docker-setup/` — Container lifecycle management
  - `tasks/main.yml` — Image pulls, compose validation, network checks
  - `handlers/main.yml` — Prune unused images, health validation
  - `defaults/main.yml` — Default variables
  - `vars/main.yml` — Internal role variables
  - `templates/.gitkeep` — Template directory (no templates needed)
- `ansible/roles/service-validation/` — Health check validation
  - `tasks/main.yml` — Service health, disk usage, resource checks
  - `handlers/main.yml` — Container restart handler
  - `defaults/main.yml` — Health check services, volume paths
  - `vars/main.yml` — Internal variables
  - `templates/.gitkeep` — Template directory
- `ansible/roles/nginx-config/` — Nginx management
  - `tasks/main.yml` — Config validation, TLS cert checks
  - `handlers/main.yml` — Nginx reload handler
  - `defaults/main.yml` — TLS domains, rate limits
  - `vars/main.yml` — Internal variables
  - `templates/nginx-unified.conf.j2` — Jinja2 Nginx config template
- `ansible/roles/certbot-setup/` — TLS certificate management
  - `tasks/main.yml` — Certificate expiry checks, renewal status
  - `handlers/main.yml` — Renewal test and force renewal
  - `defaults/main.yml` — Certificate domains
  - `vars/main.yml` — Internal variables
  - `templates/.gitkeep` — Template directory

**Key Features:**
- All tasks use `always_run: true` on critical operations
- Check-mode compatible patterns (`stat`, `command` with `check_mode`)
- Version-pinned Docker images (exact tags)
- Drift detection compares running containers to compose config

---

## Bug Fixes

### Bug 1: Gitea Admin Registration Security Hardening

**Problem:** Gitea admin registration endpoints were not fully locked down.

**Fix Applied:**
- Added `NEW_USER_SIGNUP_CONFIRM = false` to `[auth]` section of `docker/gitea/app.ini`
- Confirmed existing settings:
  - `DISABLE_REGISTRATION = true` ✅
  - `ENABLE_REGISTRATION = false` ✅
  - `REGISTER_EMAIL_CONFIRM = false` ✅
  - `ENABLE_CAPTCHA = true` ✅

**File Modified:**
- `docker/gitea/app.ini` — Added `NEW_USER_SIGNUP_CONFIRM = false`

**Verification:**
```ini
[auth]
REQUIRE_SIGNIN_VIEW = true
DISABLE_REGISTRATION = true
ENABLE_REGISTRATION = false
NEW_USER_SIGNUP_CONFIRM = false
REGISTER_EMAIL_CONFIRM = false
ENABLE_CAPTCHA = true
```

---

### Bug 2: Unknown *.iacgenie.com Redirect Fix

**Problem:** Any unmatched `*.iacgenie.com` subdomain (e.g., `foo.iacgenie.com`, `random.iacgenie.com`) was being proxied to unknown backends, potentially exposing services unintentionally.

**Fix Applied:**
- Added catch-all HTTP server block (port 80) with `default_server` — returns JSON 404
- Added catch-all HTTPS server block (port 443) with `default_server` — returns JSON 404
- Both blocks placed BEFORE other server blocks (nginx processes first match)
- Known services (gitea, auth, grafana, etc.) continue to work via explicit `server_name` matching

**File Modified:**
- `nginx-unified.conf` — Added catch-all vHost blocks

**Catch-all Response:**
```json
{
  "error": "Not Found",
  "message": "No service registered for this subdomain",
  "redirect": "https://iacgenie.com"
}
```

**Verification:**
- Known domains (`git.iacgenie.com`, `gitea.iacgenie.com`, `grafana.iacgenie.com`, etc.) → routed to backend
- Unknown domains (`xyz.iacgenie.com`, `*.iacgenie.com`) → HTTP 404 JSON response
- Cloudflare Tunnel continues to route known subdomains correctly

---

## Documentation Updates

### README.md
- Version updated: 10.22 → 10.23
- Added "Ansible Automation" section with:
  - Project structure diagram
  - Key features list
  - Usage examples (full playbook, pre-deploy validation, drift detection, dry run)

### INFRA-DESIGN.md
- Version updated: 2.1 → 2.2
- Last updated: 2026-07-29 → 2026-08-04
- Updated "Key Directives" — Loki, Promtail, Prometheus, Grafana, Nginx, Cloudflare 2 marked ACTIVE
- Updated "Permanently Disabled" — Removed Prometheus/Grafana from disabled list
- Updated "Nginx Routing Table" — Added grafana.iacgenie.com, catch-all note
- Updated "Phase Completion Summary" — Added Phase 10.17 through 10.23

---

## Deployment Steps

### For New Services (Loki, Promtail, Prometheus, Grafana)
```bash
cd ~/docker/iacgenie
# Validate compose
docker compose -f docker-compose-unified.yml config

# Deploy the monitoring/logging group
./deploy.sh --group monitoring
./deploy.sh --group iacgenie

# Verify services
docker compose -f docker-compose-unified.yml ps
```

### For TLS Certificate Setup
```bash
# Install certbot DNS plugin
sudo certbot plugins

# Enable automatic renewal
sudo cp configs/systemd/certbot-renew.service /etc/systemd/system/
sudo cp configs/systemd/certbot-renew.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now certbot-renew.timer
```

### For Nginx Configuration
```bash
# Validate nginx config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx

# Test catch-all
curl -I http://random-nonexistent.iacgenie.com
# Expected: HTTP/1.1 404
```

### For Ansible Playbooks
```bash
# Pre-deploy validation
ansible-playbook ansible/playbooks/validate_compose.yml

# Full deployment
ansible-playbook ansible/site.yml

# Drift detection
ansible-playbook ansible/playbooks/drift_detection.yml

# Dry run
ansible-playbook ansible/site.yml --check --diff
```

---

## Configuration References

| Resource | Location |
|----------|----------|
| Docker Compose | `docker-compose-unified.yml` |
| Nginx Config | `nginx-unified.conf` |
| Gitea Config | `docker/gitea/app.ini` |
| Loki Config | `configs/loki/` |
| Promtail Config | `configs/promtail/` |
| Prometheus Config | `configs/prometheus/` |
| Certbot Config | `configs/systemd/certbot-renew.*` |
| Ansible Site | `ansible/site.yml` |
| Ansible Variables | `ansible/vars/main.yml` |
| Ansible Roles | `ansible/roles/` |
| Ansible Playbooks | `ansible/playbooks/` |

---

## Summary

Phase 10.4 represents a comprehensive production readiness upgrade covering:
- **Logging:** Loki + Promtail centralization
- **Monitoring:** Prometheus + Grafana metrics and dashboards
- **Backup:** Automated Gitea backup with DR verification
- **TLS:** Certbot-automated certificates with DNS-01 challenge
- **Redundancy:** Dual Cloudflare tunnels + Nginx reverse proxy
- **Security:** Bug fixes for Gitea registration and unknown subdomain access
- **Idempotency:** Ansible automation for validation and drift detection
- **Resources:** Hard quotas on all services

All changes are committed and ready for deployment.
