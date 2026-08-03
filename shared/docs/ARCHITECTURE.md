# IacGenie Platform Architecture

## Overview

The IacGenie Platform is a unified monorepo containing:
- **IaCGenie**: AI-powered infrastructure-as-code generation (Terraform, Docker, Kubernetes)
- **LightSerp**: Privacy-focused SERP extraction with MCP interface

Both services share a unified infrastructure stack deployed on a single VM.

## Architecture

```
                              ┌─────────────────────────────────┐
                              │     Cloudflare Tunnel (HTTPS)    │
                              └────────────┬────────────────────┘
                                           │
                              ┌────────────▼────────────────────┐
                              │         Nginx (vHost routing)     │
                              │  127.0.0.1:443 → internal:443   │
                              └────────────┬────────────────────┘
                                           │
         ┌──────────────┐         ┌────────▼────────────────┐
         │ Terra WebUI   │         │ Auth Gateway (Keycloak)  │
         │ (port 3000)   │         │ (port 8083)              │
         └──────┬───────┘         └────────┬────────────────┘
                │                          │
         ┌──────▼──────────────────────────▼────────────────┐
         │                  Shared Infrastructure            │
         │                                                  │
         │  ┌──────────┐ ┌──────┐ ┌──────┐ ┌──────────┐    │
         │  │PostgreSQL│ │Redis │ │MinIO │ │ OpenBao   │    │
         │  │ (5432)   │ │(6379)│ │(9000)│ │ (8200)    │    │
         │  └──────────┘ └──────┘ └──────┘ └──────────┘    │
         │                                                  │
         │  ┌──────────┐ ┌──────────┐ ┌──────────┐         │
         │  │ Gitea    │ │ SearXNG  │ │  NSQD    │         │
         │  │ (3000)   │ │ (8082)   │ │ (4150)   │         │
         │  └──────────┘ └──────────┘ └──────────┘         │
         └─────────────────────────────────────────────────┘
                              ▲
                    ┌─────────┴─────────┐
                    │    Docker Compose  │
                    │   (monorepo infra) │
                    └───────────────────┘
```

## Service Topology

| Service | Port | Domain | Purpose |
|---------|------|--------|---------|
| Terra (IaCGenie WebUI) | 3000 | terra.iacgenie.com | Infrastructure code generator |
| IaCGenie API | 8080 | api.iacgenie.com | Backend API |
| Auth Gateway | 8081 | auth.iacgenie.com | API authentication |
| Keycloak | 8083 | - | Identity provider |
| LightSerp API | 8000 | lightserp.iacgenie.com | SERP extraction |
| LightSerp WebUI | 3001 | - | Web interface |
| PageZen | 8081 | - | Browser scraping |
| Gitea | 3002 | gitea.iacgenie.com | Git hosting |
| SearXNG | 8082 | - | Privacy search |
| OpenBao | 8200 | vault.iacgenie.com | Secrets management |
| MinIO | 9000 | - | Object storage |

## Deployment

All services are deployed via Docker Compose from `infra/docker-compose/`:

```bash
# Deploy everything
cd infra/
docker compose -f docker-compose-unified.yml up -d

# Deploy a single group
docker compose -f docker-compose-services.yml up -d iacgenie-api iacgenie-webui

# View status
docker compose -f docker-compose-unified.yml ps
```

## Monitoring Stack

- **Prometheus**: Metrics collection (port 9090)
- **Loki**: Log aggregation (port 3100)
- **Grafana**: Visualization (port 3001)
- **Cloudflared**: Secure tunnel (systemd service)
