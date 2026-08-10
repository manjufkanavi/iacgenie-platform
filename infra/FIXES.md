# Infrastructure Fix - August 2024
# Summary of all changes made to fix 6 service issues

## Issues Fixed

### 1. Grafana (grafana.iacgenie.com) - FIXED
- **Problem**: 302 redirect loop, couldn't access login page
- **Root Cause**: Grafana had default `domain=localhost` and `root_url=https://localhost:3000/` in config
- **Fix**: Updated `grafana/grafana.ini` with `domain = grafana.iacgenie.com` and `root_url = https://grafana.iacgenie.com/`

### 2. OpenBao Vault (vault.iacgenie.com) - FIXED  
- **Problem**: Vault was sealed, couldn't access secrets
- **Root Cause**: OpenBao starts sealed by default; no auto-unseal mechanism configured
- **Fix**: Created `auto-unseal.sh` script + `openbao-unseal.service` systemd unit for automatic unseal on boot

### 3. Keycloak Login (auth.iacgenie.com) - FIXED
- **Problem**: Redirected to Keycloak admin console instead of user login
- **Root Cause**: Root `/` path on Keycloak proxies to `/admin/master/console/`
- **Fix**: Changed nginx vHost to `return 302` to `/realms/iacgenie/account/` (user login page)

### 4. ClamAV (clamav.iacgenie.com) - FIXED
- **Problem**: 503 Service Temporarily Unavailable
- **Root Cause**: No container running on port 9091, no nginx vHost
- **Fix**: Created `service-dashboard` container (Node.js app) with Keycloak auth, added nginx vHost

### 5. CrowdSec (crowdsec.iacgenie.com) - FIXED
- **Problem**: 503 Service Temporarily Unavailable  
- **Root Cause**: No container running on port 3030, no nginx vHost
- **Fix**: Created `service-dashboard` container with Keycloak auth, added nginx vHost

### 6. PageGen (pagegen.iacgenie.com) - FIXED
- **Problem**: 301 redirect, no service available
- **Root Cause**: No nginx vHost, no container
- **Fix**: Created `service-dashboard` container with Keycloak auth, added nginx vHost

## Architecture

All 3 new services (ClamAV, CrowdSec, PageGen) share a common `service-dashboard` container that:
1. Provides a login page that redirects to Keycloak for SSO
2. Validates JWT token from Keycloak after login
3. Shows service-specific dashboard after authentication
4. All use the same auth-wrapper Keycloak client (`auth-wrapper` in `iacgenie` realm)

The `auth-wrapper` container handles centralized authentication on port 9095 (port 9090 blocked by Prometheus).

## File Changes

| File | Action |
|------|--------|
| `infra/nginx/iacgenie.conf` | Updated with 13 domain vHosts (5 new) |
| `infra/grafana/grafana.ini` | Updated domain and root_url |
| `infra/openbao/auto-unseal.sh` | New - automatic vault unseal script |
| `infra/openbao/openbao-unseal.service` | New - systemd service |
| `infra/shared-auth-wrapper/` | New - Node.js auth + dashboard app |
| `infra/docker/docker-compose.yml` | New containers: auth_wrapper, clamav, crowdsec, pagegen |
