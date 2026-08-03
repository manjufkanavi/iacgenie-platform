# IacGenie Platform

Unified monorepo for the entire IacGenie platform — IaCGenie (AI infrastructure code generation) and LightSerp (SERP/search MCP service) with shared infrastructure.

## Repository Structure

```
iacgenie-platform/
├── platform/          # IaCGenie application (backend + frontend)
├── lightserv/         # LightSerp service (API + WebUI + gateway + MCP server)
├── infra/             # Shared infrastructure (Docker, Ansible, Nginx, scripts)
├── shared/            # Cross-cutting docs and conventions
└── .github/workflows/ # CI/CD pipelines
```

## Quick Start

```bash
# Deploy full stack
./scripts/deploy.sh

# Deploy a single service group
./scripts/deploy.sh --group lightsrp
./scripts/deploy.sh --group iacgenie

# Run backups
./scripts/deploy.sh --backup
```

## Architecture

- **Shared Infrastructure**: PostgreSQL, Redis, MinIO, OpenBao, Keycloak, Gitea, SearXNG, NSQ, Loki/Prometheus/Grafana, Cloudflare Tunnel
- **IaCGenie**: NLP → Terraform/Docker/K8s generation with multi-model support
- **LightSerp**: Privacy-focused SERP extraction with MCP interface
- **All services bound to 127.0.0.1** — external access via Cloudflare Tunnel + Nginx

See `shared/docs/ARCHITECTURE.md` for full details.
