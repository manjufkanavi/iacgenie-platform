# IacGenie Platform — Health Check Endpoints

> **Last Updated**: 2026-08-16  
> All health checks use `wget -q -O /dev/null http://127.0.0.1:<port>/<path>`  
> Interval: 30s | Timeout: 10s | Retries: 3

---

## Health Check Matrix

| Service | Container | Endpoint | Method | Port | Start Period |
|---------|-----------|----------|--------|------|-------------|
| PostgreSQL | `iacgenie_postgres` | `pg_isready` | CMD-SHELL | 5432 | 30s |
| Redis | `iacgenie_redis` | `redis-cli ping` | CMD-SHELL | 6379 | 10s |
| MinIO | `iacgenie_minio` | `mc ready local` | CMD | 9000 | 30s |
| OpenBao | `iacgenie_openbao` | `bao status` | CMD-SHELL | 8200 | 60s |
| Keycloak | `iacgenie_keycloak` | `curl /health/ready` | CMD-SHELL | 9003 | 30s |
| Gitea | `iacgenie_gitea` | `curl /version` | CMD-SHELL | 3000 | 30s |
| Nginx | `iacgenie-nginx` | `curl -f http://127.0.0.1/` | CMD-SHELL | 80 | 10s |
| Cloudflare | `iacgenie_cloudflared` | `curl http://127.0.0.1:2000/ready` | CMD-SHELL | 2000 | 30s |
| Auth Wrapper | `iacgenie_auth_wrapper` | `wget http://127.0.0.1:9096/health` | CMD-SHELL | 9096 | 30s |
| LightSerp API | `iacgenie_lightserp_api` | `wget http://127.0.0.1:3000/health` | CMD-SHELL | 3000 | 30s |
| LightSerp WebUI | `iacgenie_lightserp_webui` | `wget http://127.0.0.1:3070/` | CMD-SHELL | 3070 | 15s |
| SearXNG | `iacgenie_searxng` | `wget http://127.0.0.1:8000/health` | CMD-SHELL | 8000 | 30s |
| NSQD | `iacgenie_nsqd` | `wget http://127.0.0.1:4151/health` | CMD-SHELL | 4151 | 10s |
| PageZen | `iacgenie_pagezen` | `wget http://127.0.0.1:8082/health` | CMD-SHELL | 8082 | 30s |
| ClamAV | `iacgenie_clamav` | `clamdscan --ping` | CMD-SHELL | 3310 | 60s |
| ClamAV Web | `iacgenie_clamav_web` | `wget http://127.0.0.1:9092/` | CMD-SHELL | 9092 | 15s |
| CrowdSec | `iacgenie_crowdsec` | `wget http://127.0.0.1:3033/healthz` | CMD-SHELL | 3033 | 30s |
| PageGen | `iacgenie_pagegen` | `wget http://127.0.0.1:3032/health` | CMD-SHELL | 3032 | 30s |
| IacGenie Frontend | `iacgenie_frontend` | `wget http://127.0.0.1:3002/` | CMD-SHELL | 3002 | 15s |
| IacGenie Backend | `iacgenie_backend` | `wget http://127.0.0.1:3003/docs` | CMD-SHELL | 3003 | 30s |
| Prometheus | `iacgenie_prometheus` | `wget http://127.0.0.1:9090/-/healthy` | CMD-SHELL | 9090 | 30s |
| Grafana | `iacgenie_grafana` | `wget http://127.0.0.1:3001/api/health` | CMD-SHELL | 3001 | 30s |
| Loki | `iacgenie_loki` | `wget http://127.0.0.1:3100/ready` | CMD-SHELL | 3100 | 30s |

---

## Health Check Categories

### Critical (restart: always)
- PostgreSQL
- Redis
- MinIO
- OpenBao
- Keycloak
- Gitea
- Nginx
- Cloudflare Tunnel

### Application (restart: unless-stopped)
- Auth Wrapper
- LightSerp API
- LightSerp WebUI
- SearXNG
- NSQD
- PageZen
- ClamAV
- ClamAV Web Client
- CrowdSec
- PageGen
- IacGenie Frontend
- IacGenie Backend

### Monitoring (restart: unless-stopped)
- Prometheus
- Grafana
- Loki
- Promtail

---

## Manual Health Check Commands

### Quick Health Check

```bash
# Check all services
cd ~/iacgenie-platform/infra && ./health-check.sh

# Check single service
./health-check.sh postgres
./health-check.sh keycloak
./health-check.sh openbao
```

### Docker-Level Health Check

```bash
# Check container health status
docker inspect --format='{{.State.Health.Status}}' iacgenie_<service>

# Check container uptime
docker inspect --format='{{.State.StartedAt}}' iacgenie_<service>
```

### Service-Specific Health Checks

```bash
# PostgreSQL
docker exec iacgenie_postgres pg_isready -U lightsrp

# Redis
docker exec iacgenie_redis redis-cli ping

# MinIO
docker exec iacgenie_minio mc ready local

# OpenBao
docker exec iacgenie_openbao bao status

# Keycloak
curl -s http://127.0.0.1:9003/health/ready

# Gitea
curl -s http://127.0.0.1:3000/version

# Prometheus
curl -s http://127.0.0.1:9090/-/healthy

# Loki
curl -s http://127.0.0.1:3100/ready
```

---

## Health Check Configuration

All health checks use the same base configuration:

```yaml
healthcheck:
  test: ["CMD-SHELL", "<command>"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: <varies by service>
```

### Start Period Guidelines

| Start Period | Services |
|-------------|----------|
| 10s | Redis, NSQD, Prometheus |
| 15s | LightSerp WebUI, ClamAV Web, IacGenie Frontend |
| 30s | PostgreSQL, MinIO, Keycloak, Gitea, SearXNG, PageZen, CrowdSec, IacGenie Backend, Grafana, Loki, Auth Wrapper, LightSerp API |
| 60s | OpenBao, ClamAV |
