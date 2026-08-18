# LightSerp — Project Context

## Project Overview
Self-hosted SERP (Search Engine Results Page) and content extraction MCP service. Alternative to commercial SERP APIs built with pluggable open-source components.

## Tech Stack
- **MCP Server:** Node.js / TypeScript
- **Gateway:** Go (Kono)
- **Search:** SearXNG
- **Scraper:** LightPanda (native stdio JSON-RPC)
- **Cache:** Redis (with memory fallback)
- **Queue:** NSQ (async job queuing)
- **Auth:** a12n-server (OAuth2/OIDC) with JWT fallback

## Architecture (6-Service Docker Stack)
1. **SearXNG** — Privacy-focused web search
2. **MCP Server** — Node.js, exposes SERP + extraction via MCP
3. **Redis** — Caching layer
4. **NSQ** — Async job queue
5. **a12n-server** — OAuth2/OIDC authentication
6. **LightPanda** — Headless browser for web scraping (native stdio JSON-RPC)

## Key Features
- Privacy-focused web search via SearXNG
- Content extraction with LightPanda MCP primary extractor
- OAuth2/OIDC auth with JWT fallback
- Redis cache with memory fallback
- NSQ async job queuing for scalability
- Pluggable scraper adapters

## Current State
**Phase 2** — All 11 unified infrastructure services running on `newvm`. Core LightSerp services (API + WebUI) migrated to unified stack with shared Postgres, Redis, Keycloak, SearXNG, NSQD, and PageZen.

### LightSerp Infrastructure Details
- **API:** `lightserp.iacgenie.com` → port 3071 (proxy via Nginx to `localhost:3071`)
- **WebUI:** `lightserp.iacgenie.com` → port 3070 (proxy via Nginx to `localhost:3070`)
- **Config:** `infra/docker-compose-unified.yml`, `infra/next.config.ts`, `infra/searxng-settings.yml`
- **Keycloak:** Keycloak clients configured via `setup-keycloak-clients.sh` + `setup-keycloak-prod.sh`
- **Shared DB:** PostgreSQL shared with iacgenie (database: `lightserp`)
- **Shared Cache:** Redis shared with iacgenie (host: `lightserp-redis`, port: 6379)
- **Shared Queue:** NSQD shared with iacgenie (host: `lightserp-nsqd`, port: 4150/4151)
- **Shared Search:** SearXNG shared with iacgenie (host: `lightserp-searxng`, port: 8888)
- **Shared Auth:** Keycloak shared with iacgenie (host: `lightserp-keycloak`, port: 8080)
- **Content Extraction:** PageZen shared with iacgenie (host: `lightserp-pagezen`, port: 8080)

### Unified Infrastructure Management
All 11 services managed via single `docker-compose-unified.yml` on `newvm`:
- `lightserp.service` systemd unit manages all 11 containers
- Cloudflare Tunnel exposes services externally
- Daily config sync at 21:00 via cron job
- All configs committed to `iacgenie/infra/` with `[REDACTED]` credentials

### Migration Notes
- LightSerp migration completed: API routes migrated, container images updated with new hostnames
- Configuration files imported from VM to local Git repos
- Keycloak realm exported and version-controlled

## Rules for Agents
- Go gateway must stay lightweight — no business logic
- MCP server follows MCP specification exactly
- Redis cache keys must have TTLs (never persistent for scraped content)
- NSQ channels must have proper retry/dead-letter queues
- a12n-server OAuth2 flows must handle token refresh
- No hardcoded API keys in code
- Phase 2 goal: Proxy rotation for search queries

## Agent Permissions
- **developer:** Full write access to src/, nginx/
- **architect:** Review all Docker and gateway changes
- **tester:** Run tests, verify Docker stack health
- **devops:** Docker Compose, container image builds, deployment scripts
