# IacGenie Platform — C4 Architecture Diagrams

> **Last Updated**: 2026-08-16  
> **VM**: 192.168.0.118 (elementary OS 8)

---

## Context Diagram (C4 Level 1)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                    Internet                                  │
│                                                                             │
│   ┌──────────┐      ┌──────────────────────┐      ┌──────────────────┐     │
│   │  Users   │─────▶│  Cloudflare Tunnel   │─────▶│  Nginx Reverse   │     │
│   │ (Browsers│      │  (cloudflared)       │      │  Proxy (host)    │     │
│   │  Apps)   │      └──────────────────────┘      └────────┬─────────┘     │
│   └──────────┘                                             │                 │
│                                                            ▼                 │
│                                                  ┌──────────────────┐      │
│                                                  │  Docker Compose  │      │
│                                                  │  Stack (20+ svcs)│      │
│                                                  └──────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Container Diagram (C4 Level 2)

```
                    ┌─────────────────────────────────────────────────┐
                    │              iacgenie-frontend network          │
                    │                                                 │
                    │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
                    │  │ LightSerp│  │ PageGen  │  │ Grafana      │  │
                    │  │  WebUI   │  │          │  │              │  │
                    │  │ :3070    │  │ :3031    │  │ :3001        │  │
                    │  └──────────┘  └──────────┘  └──────────────┘  │
                    │                                                 │
                    │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
                    │  │ CrowdSec │  │ ClamAV   │  │ IacGenie     │  │
                    │  │          │  │ Web      │  │  Frontend    │  │
                    │  │ :8080    │  │ :9092    │  │ :3002        │  │
                    │  └──────────┘  └──────────┘  └──────────────┘  │
                    └─────────────────────────────────────────────────┘

                    ┌─────────────────────────────────────────────────┐
                    │              iacgenie-backend network           │
                    │                                                 │
                    │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
                    │  │PostgreSQL│  │  Redis   │  │    MinIO     │  │
                    │  │  :5432   │  │  :6379   │  │ :9000/:9001  │  │
                    │  └──────────┘  └──────────┘  └──────────────┘  │
                    │                                                 │
                    │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
                    │  │ OpenBao  │  │ Keycloak │  │    Gitea     │  │
                    │  │  :8200   │  │  :9003   │  │   :3000      │  │
                    │  └──────────┘  └──────────┘  └──────────────┘  │
                    │                                                 │
                    │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
                    │  │ NSQD     │  │  SearXNG │  │  LightSerp   │  │
                    │  │ :4150/51 │  │  :8080   │  │   API        │  │
                    │  └──────────┘  └──────────┘  │   :3071      │  │
                    │                              └──────────────┘  │
                    │                                                 │
                    │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
                    │  │Prometheus│  │   Loki   │  │   Promtail   │  │
                    │  │  :9090   │  │  :3100   │  │   (no port)  │  │
                    │  └──────────┘  └──────────┘  └──────────────┘  │
                    └─────────────────────────────────────────────────┘

                    ┌─────────────────────────────────────────────────┐
                    │           iacgenie-messaging network            │
                    │                                                 │
                    │  ┌──────────┐                                  │
                    │  │  NSQD    │  (shared with backend)           │
                    │  │ :4150/51 │                                  │
                    │  └──────────┘                                  │
                    └─────────────────────────────────────────────────┘
```

---

## Component Diagram (C4 Level 3) — IacGenie Platform

```
┌─────────────────────────────────────────────────────────────────────┐
│                      IacGenie Platform                              │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │  React SPA   │    │   FastAPI    │    │   PostgreSQL         │  │
│  │  (Frontend)  │───▶│   (Backend)  │───▶│  (iacgenie database) │  │
│  │  :3002       │    │   :3003      │    │                      │  │
│  └──────────────┘    └──────┬───────┘    └──────────────────────┘  │
│                             │                                       │
│                    ┌────────┴────────┐                              │
│                    │                 │                              │
│              ┌─────▼─────┐    ┌──────▼──────┐                     │
│              │   Redis   │    │    MinIO    │                     │
│              │  (cache)  │    │  (objects)  │                     │
│              └───────────┘    └─────────────┘                     │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Authentication Layer                      │  │
│  │                                                              │  │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │  │
│  │  │   Keycloak   │───▶│    OpenBao   │───▶│   Auth       │  │  │
│  │  │   (OIDC)     │    │  (secrets)   │    │   Wrapper    │  │  │
│  │  └──────────────┘    └──────────────┘    │  :9096       │  │  │
│  └─────────────────────────────────────────└──────────────┘  │  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Monitoring Stack                          │  │
│  │                                                              │  │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │  │
│  │  │  Prometheus  │───▶│    Grafana   │    │     Loki     │  │  │
│  │  │  (metrics)   │    │  (dashboards)│    │   (logs)     │  │  │
│  │  └──────────────┘    └──────────────┘    └──────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
User Request
    │
    ▼
Cloudflare Tunnel (TLS termination)
    │
    ▼
Nginx (hostname-based routing)
    │
    ├── iacgenie.com ──▶ IacGenie Frontend (React SPA)
    │                        │
    │                        ▼
    │                   IacGenie Backend (FastAPI)
    │                        │
    │                    ┌───┴───┐
    │                    ▼       ▼
    │                 PostgreSQL  Redis (cache)
    │
    ├── api.iacgenie.com ──▶ IacGenie Backend (API)
    │
    ├── lightserp.iacgenie.com ──▶ LightSerp WebUI (Next.js)
    │                                    │
    │                                    ▼
    │                               LightSerp API (MCP)
    │                                    │
    │                            ┌───────┴───────┐
    │                            ▼               ▼
    │                         SearXNG          NSQD (queue)
    │
    ├── auth.iacgenie.com ──▶ Keycloak (OIDC)
    │                            │
    │                            ▼
    │                       OpenBao (secrets)
    │
    └── gitea.iacgenie.com ──▶ Gitea (Git)
```

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Security Layers                             │
│                                                                      │
│  Layer 1: Cloudflare Edge                                            │
│  ├── TLS termination (HTTPS)                                         │
│  ├── DDoS protection                                                 │
│  └── WAF (optional)                                                 │
│                                                                      │
│  Layer 2: Nginx                                                      │
│  ├── Rate limiting (10r/s general, 3r/m auth, 30r/s API)            │
│  ├── Content-Security-Policy headers                                │
│  ├── X-Frame-Options, HSTS                                          │
│  └── Hostname-based routing                                         │
│                                                                      │
│  Layer 3: Docker Network Isolation                                   │
│  ├── iacgenie-frontend (user-facing)                                 │
│  ├── iacgenie-backend (data services)                                │
│  └── iacgenie-messaging (NSQD)                                       │
│                                                                      │
│  Layer 4: OpenBao Secrets Management                                 │
│  ├── All credentials encrypted at rest                               │
│  ├── Shamir 3/3 unseal                                             │
│  └── 30-day token TTL                                              │
│                                                                      │
│  Layer 5: Service-Level Auth                                         │
│  ├── Keycloak OIDC for web services                                 │
│  ├── JWT tokens for API access                                      │
│  └── Service tokens for backend-to-backend                          │
└─────────────────────────────────────────────────────────────────────┘
```
