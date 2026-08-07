# Changes — 2026-08-07 Service Health Remediation

## Summary

Fixed all unhealthy services on VM `192.168.0.118`. Three services were reporting `unhealthy` due to broken Docker health check commands.

## Root Causes

### 1. Gitea — `unhealthy`
- **Cause**: Health check used `exec 6<>/dev/tcp/127.0.0.1/3000` which is a **bashism** — does not work in the minimal `/bin/sh` used by Docker health checks.
- **Secondary issue**: `app.ini` had corrupted `[database]` PASSWD line (`PASSWD=*** = <password>`) from a prior Ansible template rendering issue where `***` was a placeholder that persisted. Gitea was failing to authenticate to PostgreSQL.
- **Fix**:
  - Replaced health check with `wget -q --spider http://localhost:3000/ || exit 1`
  - Restored correct `PASSWD=<password>` in `app.ini`

### 2. NSQD — `unhealthy`
- **Cause**: Same `/dev/tcp` bashism in health check. Additionally, the health endpoint `/` on NSQD returns HTTP 404 (not found) — it has no root handler.
- **Fix**: Replaced health check with `wget -q -O /dev/null http://127.0.0.1:4151/stats 2>/dev/null || exit 1` (the `/stats` endpoint returns HTTP 200 with health info).

### 3. Keycloak — `unhealthy`
- **Cause**: Same `/dev/tcp` bashism. Keycloak's base image has **no wget or curl** — it's a minimal RHEL-based OpenJDK image.
- **Fix**: Used `bash -c 'exec 6<>/dev/tcp/127.0.0.1/8080 && exec 6>&-'` since Keycloak has bash installed.

## Files Changed

| File | Change |
|------|--------|
| `infra/ansible/roles/docker-compose-generator/templates/docker-compose.yml.j2` | Fixed health checks for Gitea, NSQD, Keycloak |
| `infra/ansible/roles/docker-compose-generator/templates/gitea/app.ini.j2` | `PASSWD` format corrected (was `PASSWD=*** = value`, now `PASSWD=value`) |

## Health Check Reference

| Service | Port | Old (broken) | New (fixed) |
|---------|------|--------------|-------------|
| Gitea | 3000 | `/dev/tcp/127.0.0.1/3000` (sh doesn't support) | `wget --spider http://localhost:3000/` |
| NSQD | 4151 | `/dev/tcp/127.0.0.1/4150` (sh doesn't support) | `wget http://127.0.0.1:4151/stats` |
| Keycloak | 8080 | `/dev/tcp/127.0.0.1/8080` (sh doesn't support) | `bash -c 'exec 6<>/dev/tcp/127.0.0.1/8080 && exec 6>&-'` |
| SearXNG | 8080 | `wget --spider http://127.0.0.1:8080/` ✅ | *(no change needed)* |
| OpenBao | 8200 | `wget ... /sys/health \| grep` ✅ | *(no change needed)* |

## Verification

All 12 containers verified healthy:

```
iacgenie_gitea              Up 49 minutes (healthy)
iacgenie_keycloak           Up 3 minutes (healthy)
iacgenie_nsqd               Up 3 minutes (healthy)
iacgenie_openbao            Up 2 hours (healthy)
iacgenie_searxng            Up 10 hours (healthy)
iacgenie_postgres           Up 4 hours (healthy)
iacgenie_minio              Up 10 hours (healthy)
iacgenie_redis              Up 10 hours (healthy)
iacgenie_lightserp_api      Up 10 hours
iacgenie_lightserp_webui    Up 10 hours
iacgenie_pagezen            Up 10 hours
iacgenie_minio_console_proxy Up 4 hours
```
