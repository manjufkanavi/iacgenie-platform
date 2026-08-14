# Deployment Summary — 2026-08-14

## Overview
Deployed critical infrastructure changes across Nginx, Docker Compose, Keycloak, OpenBao, and Cloudflare roles to achieve full operational status for auth-protected services.

## Changes Deployed

### 1. Nginx Reverse Proxy (`roles/nginx/templates/reverse-proxy.conf.j2`)
| Change | Before | After |
|--------|--------|-------|
| Keycloak HTTP vHost | `proxy_pass https://` | `proxy_pass http://` |
| Keycloak HTTPS vHost | `proxy_pass https://` | `proxy_pass http://` |
| Platform frontend | `proxy_pass http://127.0.0.1:3001` | `proxy_pass http://127.0.0.1:3002` |
| OpenBao protocol | `proxy_pass https://127.0.0.1:8200` | `proxy_pass http://127.0.0.1:8200` |
| Git hostname | `git.iacgenie.com` | `gitea.iacgenie.com` |
| Auth wrapper ports | N/A | Added 9091/9092/9093 for ClamAV/CrowdSec/PageGen |
| X-Service headers | N/A | Added for auth-gated services |

### 2. Nginx Main Config (`roles/nginx/templates/nginx.conf.j2`)
- Added rate limiting zones: `general` (10r/s), `auth` (3r/m), `api` (30r/s)
- Moved `limit_req_zone` definitions from `reverse-proxy.conf` to `nginx.conf` to prevent duplicate definitions

### 3. Docker Compose (`roles/docker-compose-generator/templates/docker-compose.yml.j2`)
- Added `--http-admin-port=9000` to Keycloak for internal admin API
- Added `iacgenie_auth_wrapper` container with 3 host ports (9091/9092/9093)
- Updated Cloudflare tunnel hostname: `git` → `gitea`

### 4. Environment Template (`roles/docker-compose-generator/templates/.env.j2`)
- Added `AUTH_WRAPPER_CLIENT_SECRET`
- Added `AUTH_WRAPPER_INTERNAL_TOKEN`
- Added `CLAMAV_ADMIN_PASSWORD`
- Added `CROWDSEC_API_KEY`
- Added `PAGEGEN_API_KEY`

### 5. Keycloak (`roles/keycloak/`)
- Added `iacgenie-auth-wrapper` client config in defaults
- Created `files/keycloak_client_setup.py` for idempotent client provisioning
- Updated `tasks/main.yml` to run the setup script (graceful failure handling)

### 6. OpenBao (`roles/openbao/`)
- Added `service-admin` credential variables for ClamAV, CrowdSec, PageGen, Auth Wrapper
- Updated `kv_bootstrap.yml` to seed new KV secrets

### 7. Cloudflare Tunnel (`roles/cloudflare_tunnel/`)
- Renamed `git` service key to `gitea` in defaults and template

### 8. New: Auth Wrapper Role (`roles/auth-wrapper/`)
- Ansible role to deploy shared-auth-wrapper OIDC gateway
- Container uses FastAPI to route auth-gated requests through Keycloak

## Deployment Issues Resolved
1. **Ansible `command` module limitation**: Replaced `command: cmd:` pattern with `shell:` to support `register`/`failed_when` parameters
2. **Docker port conflict**: Resolved stale port allocations by killing orphaned docker-proxy processes
3. **Nginx duplicate `limit_req_zone`**: Moved rate limit zone definitions from `reverse-proxy.conf.j2` to `nginx.conf.j2`
4. **Nginx `iacgenie.conf` duplicate**: Removed old `iacgenie.conf` that had overlapping server blocks
5. **Auth wrapper `docker_compose_dir` undefined**: Added `docker_compose_dir` default in auth-wrapper role

## Service Health Status (Post-Deploy)
| Service | Status | Notes |
|---------|--------|-------|
| Nginx (host) | ✅ Running | Ports 80/443 listening |
| Postgres | ✅ Healthy | Restarted during deploy |
| Redis | ✅ Healthy | |
| MinIO | ✅ Healthy | |
| OpenBao | ⚠️ Running | Container unhealthy (known issue) |
| Keycloak | ✅ Healthy | Admin API on port 9000 |
| Gitea | ✅ Healthy | |
| Cloudflare Tunnel | ✅ Running | Wildcard `*.iacgenie.com` |
| Auth Wrapper | ✅ Running | New container, rebuilding ports |
| Frontend | ✅ Healthy | |
| LightSerp | ✅ Healthy | |
| ClamAV | ✅ Running | |
| CrowdSec | ✅ Running | |
| PageZen | ✅ Running | |
| Prometheus | ✅ Running | |
| Grafana | ✅ Running | |
| NSQD | ✅ Healthy | |
| Loki | ✅ Running | |
| Promtail | ✅ Running | |
| SearXNG | ✅ Healthy | |

## Known Issues
1. **OpenBao container unhealthy** — Raft storage bind mount issue (pre-existing, from namespace remapping)
2. **Auth wrapper ports** — Port 9092 had stale allocation; resolved manually
3. **Missing .env variables** — OpenBao KV not reachable, so new secrets (AUTH_WRAPPER_CLIENT_SECRET, etc.) not yet populated in .env
4. **Cloudflare tunnel** — Uses wildcard routing; gitea.hostname change doesn't affect tunnel config

## Files Modified
- `roles/nginx/templates/reverse-proxy.conf.j2`
- `roles/nginx/templates/nginx.conf.j2`
- `roles/docker-compose-generator/templates/docker-compose.yml.j2`
- `roles/docker-compose-generator/templates/.env.j2`
- `roles/keycloak/tasks/main.yml`
- `roles/keycloak/files/keycloak_client_setup.py`
- `roles/keycloak/defaults/main.yml`
- `roles/openbao/defaults/main.yml`
- `roles/openbao/tasks/kv_bootstrap.yml`
- `roles/cloudflare_tunnel/defaults/main.yml`
- `roles/cloudflare_tunnel/templates/cloudflared.yaml.j2`
- `roles/auth-wrapper/tasks/main.yml` (new)
- `roles/auth-wrapper/defaults/main.yml` (new)
- `roles/auth-wrapper/files/server.py` (new)
- `playbooks/services.yml`

## Post-Deployment Checklist
- [ ] Seed OpenBao KV with new service-admin credentials
- [ ] Update .env file with actual secrets from OpenBao
- [ ] Verify auth wrapper routing through all 3 ports
- [ ] Test Keycloak client provisioning for auth-wrapper
- [ ] Verify Cloudflare tunnel still routes gitea.iacgenie.com correctly
