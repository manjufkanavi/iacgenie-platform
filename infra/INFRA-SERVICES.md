# IacGenie Platform — Infrastructure Services Reference

> **Last Updated**: 2026-08-16  
> **VM**: 192.168.0.118 (elementary OS 8)  
> **Total Services**: 20+

---

## Service Inventory

| # | Service | Container | Image | Port(s) | Network | Restart | Healthcheck | Purpose |
|---|---------|-----------|-------|---------|---------|---------|-------------|---------|
| 1 | PostgreSQL | `iacgenie_postgres` | `postgres:15-alpine` | 5432 | iacgenie-backend | always | ✅ | Primary database |
| 2 | Redis | `iacgenie_redis` | `redis:7-alpine` | 6379 | iacgenie-backend | always | ✅ | Caching & sessions |
| 3 | MinIO | `iacgenie_minio` | `minio:RELEASE.2025-06-13T05-20-52Z` | 9000, 9001 | iacgenie-backend | always | ✅ | S3 object storage |
| 4 | OpenBao | `iacgenie_openbao` | `openbao:2.6.0` | 8200 (host) | host | always | ✅ | Secrets management |
| 5 | Keycloak | `iacgenie_keycloak` | `keycloak:26.0-pg` | 9003 | iacgenie-backend | always | ✅ | OIDC provider |
| 6 | Gitea | `iacgenie_gitea` | `gitea:1.23.4-rootless` | 3000 | iacgenie-backend | always | ✅ | Git service |
| 7 | Cloudflare Tunnel | `iacgenie_cloudflared` | `cloudflared:2025.6.0` | — | iacgenie-frontend | always | ✅ | Edge tunnel |
| 8 | Nginx | `iacgenie-nginx` | `nginx:1.27-alpine` | 80, 443 (host) | host | always | ✅ | Reverse proxy |
| 9 | Auth Wrapper | `iacgenie_auth_wrapper` | custom (build) | 9096 | frontend+backend | unless-stopped | ✅ | OIDC auth proxy |
| 10 | LightSerp API | `iacgenie_lightserp_api` | `lightserp-api:v1.0.0` | 3071 | iacgenie-backend | unless-stopped | ✅ | MCP backend |
| 11 | LightSerp WebUI | `iacgenie_lightserp_webui` | `lightserp-webui:v1.0.0` | 3070 | iacgenie-frontend | unless-stopped | ✅ | Next.js frontend |
| 12 | SearXNG | `iacgenie_searxng` | `searxng:1.0.0` | 8080 | iacgenie-backend | unless-stopped | ✅ | Search engine |
| 13 | NSQD | `iacgenie_nsqd` | `nsq:v1.3.0` | 4150, 4151 | iacgenie-messaging | unless-stopped | ✅ | Message queue |
| 14 | PageZen | `iacgenie_pagezen` | `pagezen:v1.0.0` | 8082 | iacgenie-backend | unless-stopped | ✅ | Content extraction |
| 15 | ClamAV | `iacgenie_clamav` | `clamav:1.1.2` | 3310 | iacgenie-backend | unless-stopped | ✅ | Virus scanning |
| 16 | ClamAV Web Client | `iacgenie_clamav_web` | `clamav-web-client:1.0.0` | 9092 | iacgenie-frontend | unless-stopped | ✅ | Virus scan UI |
| 17 | CrowdSec | `iacgenie_crowdsec` | `crowdsec:2.2.0` | 8080 | iacgenie-frontend | unless-stopped | ✅ | WAF/IPS |
| 18 | PageGen | `iacgenie_pagegen` | `pagegen:v1.0.0` | 3031 | iacgenie-frontend | unless-stopped | ✅ | AI page generator |
| 19 | IacGenie Frontend | `iacgenie_frontend` | custom (build) | 3002 | iacgenie-frontend | unless-stopped | ✅ | React SPA |
| 20 | IacGenie Backend | `iacgenie_backend` | custom (build) | 3003 | iacgenie-backend | unless-stopped | ✅ | FastAPI backend |
| 21 | Prometheus | `iacgenie_prometheus` | `prom/prometheus:v3.2.0` | 9090 | iacgenie-backend | unless-stopped | ✅ | Metrics collection |
| 22 | Grafana | `iacgenie_grafana` | `grafana/grafana:11.5.0` | 3001 | iacgenie-frontend | unless-stopped | ✅ | Dashboards |
| 23 | Loki | `iacgenie_loki` | `grafana/loki:3.2.0` | 3100 | iacgenie-backend | unless-stopped | ✅ | Log aggregation |
| 24 | Promtail | `iacgenie_promtail` | `grafana/promtail:3.2.0` | — | iacgenie-backend | unless-stopped | ✅ | Log shipper |

---

## Network Topology

```
Internet
  │
  ▼
Cloudflare Tunnel (cloudflared)
  │
  ▼
Nginx (host: 80/443)
  │
  ├── iacgenie-frontend network
  │   ├── LightSerp WebUI (3070)
  │   ├── PageZen (8082)
  │   ├── CrowdSec (8080)
  │   ├── PageGen (3031)
  │   ├── IacGenie Frontend (3002)
  │   ├── ClamAV Web Client (9092)
  │   └── Grafana (3001)
  │
  ├── iacgenie-backend network
  │   ├── PostgreSQL (5432)
  │   ├── Redis (6379)
  │   ├── MinIO (9000)
  │   ├── OpenBao (8200)
  │   ├── Keycloak (9003)
  │   ├── Gitea (3000)
  │   ├── LightSerp API (3071)
  │   ├── NSQD (4150/4151)
  │   ├── SearXNG (8080)
  │   ├── ClamAV (3310)
  │   ├── IacGenie Backend (3003)
  │   ├── Prometheus (9090)
  │   ├── Loki (3100)
  │   └── Promtail (9080)
  │
  └── iacgenie-messaging network
      └── NSQD (4150/4151)
```

---

## DNS Mapping (via Cloudflare Tunnel)

| Hostname | Route | Service |
|----------|-------|---------|
| `iacgenie.com` | → `http://127.0.0.1:3002` | IacGenie Frontend |
| `api.iacgenie.com` | → `http://127.0.0.1:3003` | IacGenie Backend |
| `lightserp.iacgenie.com` | → `http://127.0.0.1:3070` | LightSerp WebUI |
| `search.iacgenie.com` | → `http://127.0.0.1:8080` | SearXNG |
| `auth.iacgenie.com` | → `http://127.0.0.1:9003` | Keycloak |
| `gitea.iacgenie.com` | → `http://127.0.0.1:3000` | Gitea |
| `minio.iacgenie.com` | → `http://127.0.0.1:9001` | MinIO Console |
| `vault.iacgenie.com` | → `http://127.0.0.1:8200` | OpenBao |
| `grafana.iacgenie.com` | → `http://127.0.0.1:3001` | Grafana |
| `prometheus.iacgenie.com` | → `http://127.0.0.1:9090` | Prometheus |
| `loki.iacgenie.com` | → `http://127.0.0.1:3100` | Loki |

---

## Service Dependencies

```
PostgreSQL ← all services (database)
Redis ← LightSerp API, IacGenie Backend (cache/sessions)
MinIO ← IacGenie Backend, LightSerp API (object storage)
OpenBao ← all services (secrets)
Keycloak ← all web services (OIDC auth)
NSQD ← LightSerp API, PageZen (messaging)
SearXNG ← LightSerp API (search)
```

---

## Resource Allocation

| Service | Memory Limit | CPU Limit |
|---------|-------------|-----------|
| PostgreSQL | 1 GB | — |
| Redis | 512 MB | — |
| MinIO | 512 MB | — |
| OpenBao | 512 MB | — |
| Keycloak | 1 GB | — |
| Gitea | 512 MB | — |
| Prometheus | 2 GB | — |
| Grafana | 512 MB | — |
| Loki | 512 MB | — |
| LightSerp API | 512 MB | — |
| LightSerp WebUI | 256 MB | — |
| IacGenie Frontend | 256 MB | — |
| IacGenie Backend | 512 MB | — |

---

## Quick Reference Commands

```bash
# Check all services
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

# View logs (last 100 lines)
docker logs --tail 100 iacgenie_<service>

# Restart a service
docker restart iacgenie_<service>

# Run health checks
cd ~/iacgenie-platform/infra && ./health-check.sh

# Run drift detection
cd ~/iacgenie-platform/infra && ./drift-detect.sh

# Full backup
cd ~/iacgenie-platform/infra && ./backup-restore.sh backup all

# Ansible deployment
cd ~/iacgenie-platform/infra/ansible && ansible-playbook site.yml
```
