# Current State & Fix Plan for iacgenie-platform Infrastructure

## 1. CURRENT SERVICE MAP

### URL → Service → Port Mapping
| URL | Host Port | Container | Status | Issue |
|-----|-----------|-----------|--------|-------|
| auth.iacgenie.com | :8083 → :8080 | iacgenie_keycloak | Running (unhealthy) | Ghost user in DB |
| search.iacgenie.com | :8082 → :8080 | iacgenie_searxng | Healthy | OK |
| api.iacgenie.com | :8000 → :3000 | iacgenie_lightserp-api | Running | OK |
| app.iacgenie.com | :3001 → :3070 | iacgenie_lightserp-webui | Running | OK |
| git.iacgenie.com | :3000 → :3000 | iacgenie_gitea | Healthy | OK |
| page.iacgenie.com | :8081 → :8082 | iacgenie_pagezen | Running | OK |
| platform.iacgenie.com | :3001 → :3070 | iacgenie_lightserp-webui | Running | Duplicate of app |
| lightserp.iacgenie.com | :3001 → :3070 | iacgenie_lightserp-webui | Running | Duplicate of app |
| vault.iacgenie.com | :8200 → :8200 | iacgenie_openbao | **RESTARTING** | Volume mismatch |
| admin.iacgenie.com | :3004 → :3000 | iacgenie_grafana | Running | OK |
| monitor.iacgenie.com | :9090 → :9090 | iacgenie_prometheus | Running | OK |
| clamav.iacgenie.com | :9092 → :80 | iacgenie_clamav | Running | Recent deploy |
| crowdsec.iacgenie.com | :3033 → :8080 | iacgenie_crowdsec | Running | Recent deploy |
| loki.iacgenie.com | :3100 → :3100 | iacgenie_loki | Running | Recent deploy |

## 2. CRITICAL ISSUES

### Issue 1: DUPLICATION - cloudflared runs BOTH as systemd AND Docker
- **systemd cloudflared**: PID 1943692, running since Aug 12, port 12345
- **Docker iacgenie_cloudflared**: Also running
- **Fix**: Remove Docker container, keep only systemd. Remove from docker-compose.yml

### Issue 2: DUPLICATION - nginx runs BOTH as host systemd AND Docker
- **Host nginx**: Running on ports 80/443, config at /etc/nginx/conf.d/iacgenie.conf + vault-iacgenie.conf
- **Docker iacgenie_nginx**: Running without port bindings (blocking nothing)
- **systemd nginx**: DISABLED but host process IS running
- **Fix**: Remove Docker nginx container. Keep host systemd nginx. Fix systemd to be ENABLED.

### Issue 3: OPENBAO CRASHING - Volume path mismatch
- **Compose defines**: `/home/mkanavi/docker/iacgenie/data/openbao` → `/openbao/storage`
- **Compose defines**: `/home/mkanavi/docker/iacgenie/data/openbao_raft` → `/openbao/raft`
- **Actual data at**: `/home/mkanavi/docker/iacgenie/openbao_raft/` (vault.db + raft/ + certs)
- **Host dir exists**: `/home/mkanavi/docker/iacgenie/data/openbao_raft/` (empty/non-data)
- **Result**: Docker mounts empty dir → OpenBao starts fresh → health check fails → restart loop

### Issue 4: PORT CONFLICT - Docker binds to 127.0.0.1 but nginx proxies via 127.0.0.1
- All services use `127.0.0.1:PORT → CONTAINER_PORT` which is correct
- But nginx also proxies from 127.0.0.1 — no conflict, this is correct architecture

### Issue 5: UNNECESSARY SERVICES IN DOCKER COMPOSE
- `iacgenie_nginx` container exists but should not
- `iacgenie_cloudflared` container exists but should not (systemd handles it)

## 3. REQUIRED CHANGES

### A. Docker Compose Fixes
1. Remove `iacgenie_cloudflared` from compose (keep systemd)
2. Remove `iacgenie_nginx` from compose (keep host systemd)
3. Fix openbao volumes to use correct host paths:
   - Mount `/home/mkanavi/docker/iacgenie/openbao_raft` → `/openbao/raft`
   - Mount `/home/mkanavi/docker/iacgenie/data/openbao` → `/openbao/storage`
4. Fix openbao command: `bao server -config=/openbao/raft/openbao-prod.hcl`
5. Remove duplicate nginx vHost blocks from iacgenie.conf
6. Add openbao to ansible roles if not already

### B. Systemd Fixes
1. Enable nginx systemd service (`systemctl enable nginx`)
2. Verify cloudflared systemd is the only tunnel instance
3. Verify nginx config is valid and reloads correctly

### C. Nginx Config Fixes
1. Merge vault-iacgenie.conf into iacgenie.conf (remove separate file)
2. Remove duplicate server blocks for platform/lightserp/app URLs
3. Verify all vHost proxy_pass targets match Docker-exposed ports
4. Ensure gitea-frontend is listed in service backends

### D. OpenBao Production Config
1. Deploy new HCL config with audit enabled
2. Enable OpenBao TLS via Nginx proxy (not directly)
3. Set up health check for openbao
4. Fix backup cron job
5. Register Ansible openbao role tasks

### E. Ansible Role Updates
1. Update `infra/ansible/roles/docker-compose-generator/` to produce correct compose
2. Add openbao service to compose template
3. Update nginx role to manage host nginx config properly
4. Update cloudflare role to manage systemd cloudflared (not docker)
5. Add openbao backup cron to backup role

## 4. DEPLOYMENT ORDER

1. **Stop affected services**: `docker compose stop openbao cloudflared nginx`
2. **Clean openbao data**: Remove empty data dir, symlink correct data
3. **Fix compose file**: Remove duplicate services, fix openbao volumes
4. **Deploy fixed compose**: `docker compose up -d`
5. **Fix systemd nginx**: Enable and start
6. **Merge nginx configs**: Combine vault-iacgenie.conf into iacgenie.conf
7. **Fix openbao**: Mount correct data, start container
8. **Verify all services**: Check health, URLs, ports
9. **Deploy to Ansible**: Update all roles for persistent changes
10. **Commit & push**: All changes to git

## 5. FILES TO MODIFY

| File | Change |
|------|--------|
| `infra/docker-compose/docker-compose-unified.yml` | Remove cloudflared/nginx, fix openbao volumes |
| `infra/ansible/roles/nginx/` | Manage host nginx, merge vHosts |
| `infra/ansible/roles/docker-compose-generator/` | Updated compose template |
| `infra/ansible/roles/openbao/` | Add tasks for HCL, backup cron |
| `infra/ansible/roles/cloudflare/` | Manage systemd cloudflared |
| `infra/nginx/vault-iacgenie.conf` | Merge into iacgenie.conf, remove separate file |
| `/etc/nginx/conf.d/iacgenie.conf` (on VM) | Merge with vault config, dedup blocks |
| VM: systemd config | Enable nginx, verify cloudflared |
| VM: openbao data | Symlink correct paths |
