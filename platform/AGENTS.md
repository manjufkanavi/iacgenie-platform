# IaCGenie AI — Project Context

## Project Overview
SaaS platform that translates natural language prompts into deployable Terraform, Docker, and Kubernetes configurations using AI.

## Tech Stack
- **Backend:** Python (FastAPI) + Node.js (API layer)
- **Frontend:** React/Next.js dashboard
- **Database:** PostgreSQL (with authentication)
- **Auth:** JWT-based, GitHub integration
- **AI Models:** Google Gemini, Mistral, Claude, OpenAI (multi-model)
- **Infrastructure:** Docker, Terraform
- **Hosting:** AWS/GCP (multi-cloud)
- **Monitoring:** Netdata

## Key Features
- AI-powered infrastructure code generation
- Multi-cloud support (AWS, GCP, Azure)
- Modular monolith architecture
- Comprehensive workflow orchestration
- Enterprise-grade security
- Terraform, Docker, K8s output
- GitHub integration for direct deployment

## Current State
**Active** — Production-ready features implemented. All 11 infrastructure services unified on `newvm` (192.168.0.118) via single `docker-compose-unified.yml`.

## Infrastructure (newvm — 192.168.0.118)

### Unified Docker Stack (11 services)
| Service | Container Name | Bind Mount Path |
|---------|---------------|-----------------|
| PostgreSQL | `iacgenie-postgres` | `postgres_data` → `/var/lib/postgresql/data` |
| Redis | `iacgenie-redis` | `redis_data` → `/data/redis` |
| MinIO | `iacgenie-minio` | `minio_data` → `/data/minio` |
| Keycloak | `iacgenie-keycloak` | `keycloak_data` → `/opt/keycloak/data` |
| OpenBao | `iacgenie-openbao` | `openbao_data` → `/openbao/data` |
| NSQD | `iacgenie-nsqd` | In-memory (stateless) |
| SearXNG | `iacgenie-searxng` | `searxng-settings.yml` → `/etc/searxng/settings.yml` |
| Gitea | `iacgenie-gitea` | `gitea_data` → `/data/gitea` |
| LightSerp API | `iacgenie-lightserp-api` | Stateless (container image) |
| LightSerp WebUI | `iacgenie-lightserp-webui` | Stateless (container image) |
| PageZen | `iacgenie-pagezen` | Stateless (container image) |

### Nginx Reverse Proxy
- `gitea.iacgenie.com` → `localhost:3000`
- `iacgenie.iacgenie.com` → `localhost:8000`
- `keycloak.iacgenie.com` → `localhost:3070` (proxy) + `localhost:3070/auth` (auth)
- `lightserp.iacgenie.com` → `localhost:3071` (API) + `localhost:3070` (WebUI)

### Systemd Services
- `lightserp.service` → `docker-compose-unified.yml up -d` (restarts all 11 services)
- `cloudflared-tunnel.service` → Cloudflare Tunnel (exposes all services externally)

### Monitoring
- Prometheus: `iacgenie_prometheus` at `/home/mkanavi/docker/iacgenie/prometheus_data`
- Alertmanager: configured via `alertmanager.yml` + `iacgenie_rules.yml`

### Configuration Import
All infra configs are synced to local Git repos:
- `iacgenie/infra/` → docker-compose, nginx configs, systemd units, prometheus config
- `LightSerp/infra/` → docker-compose, keycloak setup scripts, nginx proxy config

### Credentials
- `.env` files are committed with `[REDACTED]` values for all secrets
- Real credentials remain only on VM (`/home/mkanavi/docker/iacgenie/.env`)

### Daily Sync
- Cron job `972ba9024229` runs at 21:00 daily to backup config changes to git

## Important Paths
- `src/` — Python backend (FastAPI)
- `server/` — Node.js API layer
- `frontend/` — React dashboard
- `docs/` — Full architectural documentation
- `docker/` — Container configs
- `infra/` — Terraform modules

## Rules for Agents
- AI model prompts must be safe — no injection attacks
- Generated infrastructure must pass `terraform validate` and `docker build`
- Multi-model output must be normalized to a common schema
- GitHub integration must use OAuth tokens (never user tokens in DB)
- All user data encrypted at rest (AES-256)
- JWT tokens must have short expiration + refresh tokens
- API endpoints must rate-limit per user
- Phase priorities: Model integration → Validation → UX improvements → Multi-cloud

## Agent Permissions
- **developer:** Full write access to src/, server/, frontend/
- **architect:** Review all AI prompt and infrastructure generation changes
- **tester:** Run pytest, validate generated Terraform/Docker configs
- **devops:** Docker builds, AWS/GCP deployment, Netdata monitoring
