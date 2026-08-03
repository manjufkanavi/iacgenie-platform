# Shared Infrastructure

## Overview

LightSerp and IacGenie share a **unified infrastructure stack** managed from a single location:

```
~/workspace/iacgenie/docker-compose-unified/
```

This document explains how LightSerp integrates with this shared stack and how to configure your development environment.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Unified Infrastructure Stack                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │
│  │ PostgreSQL  │    │    Redis    │    │    MinIO    │              │
│  │ :5432       │    │   :6379     │    │  :9000/9001  │              │
│  │ Schema:     │    │ DB1 =       │    │ Bucket:     │              │
│  │ lightsrp.*  │    │ lightsrp    │    │ lightsrp/*  │              │
│  └──────┬──────┘    └──────┬──────┘    └──────┬───────┘              │
│         │                   │                   │                     │
│  ┌──────┴───────────────────┴───────────────────┴───────┐              │
│  │                  iacgenie_network                     │              │
│  │                  (internal only)                      │              │
│  └──────┬───────────────────┬───────────────────┬───────┘              │
│         │                   │                   │                     │
│  ┌──────┴───────┐   ┌──────┴───────┐   ┌──────┴───────┐               │
│  │   Keycloak   │   │   OpenBao    │   │   SearXNG    │               │
│  │  :8443       │   │   :8200      │   │   :8070      │               │
│  │   OIDC Auth  │   │   Secrets Mgr│   │   Search     │               │
│  └──────────────┘   └──────────────┘   └──────────────┘               │
│                                                                       │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐               │
│  │   Prometheus │   │   Grafana    │   │     NSQ      │               │
│  │   :9090      │   │   :3001      │   │   :4150/4161 │               │
│  │   Metrics    │   │   Dashboards │   │   Message Q  │               │
│  └──────────────┘   └──────────────┘   └──────────────┘               │
├─────────────────────────────────────────────────────────────────────┤
│  Cloudflare Tunnel → Nginx → lightserp.yourdomain.com → LightSerp    │
└─────────────────────────────────────────────────────────────────────┘
```

## LightSerp's Role in the Shared Stack

LightSerp connects to these shared services:

| Shared Service | LightSerp Usage | Connection |
|---------------|-----------------|------------|
| **PostgreSQL** | Stores LightSerp app data in the `lightsrp` schema | Internal: `postgres:5432` |
| **Redis** | Caching + job queue persistence (DB1) | Internal: `redis:6379` |
| **SearXNG** | Web search engine | Internal: `searxng:8080` |
| **NSQ** | Async scraping job queue | Internal: `nsqd:4150` |
| **Keycloak** | OAuth2/OIDC authentication | Internal: `keycloak:8443` |
| **OpenBao** | API keys & secrets | Internal: `openbao:8200` |
| **MinIO** | Cache/file storage | Internal: `minio:9000` |

## Getting Started

### 1. Deploy the Shared Infrastructure

```bash
cd ~/workspace/iacgenie/docker-compose-unified

# Copy the shared environment
cp .env .env.local

# Start everything
./deploy-unified.sh
```

### 2. Link Shared Services to LightSerp

```bash
# Link the shared infrastructure compose files
ln -sf ~/workspace/iacgenie/docker-compose-unified/docker-compose-unified.yml ~/workspace/LightSerp/docker-compose-shared.yml
ln -sf ~/workspace/iacgenie/docker-compose-unified/docker-compose-lightsrp.yml ~/workspace/LightSerp/docker-compose.yml
ln -sf ~/workspace/iacgenie/docker-compose-unified/.env.local ~/workspace/LightSerp/.env
```

### 3. Start LightSerp

```bash
cd ~/workspace/LightSerp

# Start LightSerp services (they'll attach to the shared iacgenie_network)
docker compose up -d

# Or include the shared services in one command:
cd ~/workspace/LightSerp &&   docker compose -f docker-compose-shared.yml -f docker-compose.yml up -d
```

### 4. Verify Everything Is Running

```bash
# Check LightSerp services
docker compose ps

# Check shared services (run from the unified dir)
cd ~/workspace/iacgenie/docker-compose-unified
docker compose -f docker-compose-unified.yml ps
```

## Multi-Tenant PostgreSQL

LightSerp uses the `lightsrp` schema in the shared PostgreSQL instance:

- **Database:** `lightsrp`
- **Schema:** `lightsrp`
- **Role:** `lightsrp_app` (scoped to `lightsrp.*` only)

This ensures LightSerp cannot access IacGenie data or Keycloak tables.

## Redis Configuration

LightSerp uses **Redis DB1** in the shared Redis instance:

- **DB0:** IacGenie (caching, sessions)
- **DB1:** LightSerp (caching, search results, job queue)

Connection string in your `.env`:
```
REDIS_URL=redis://:<REDIS_PASSWORD>@redis:6379/1
```

## Keycloak Authentication

Keycloak is the shared OAuth2/OIDC provider for both platforms. LightSerp has a pre-configured client registration:

- **Client ID:** `lightsrp`
- **Redirect URIs:** configured for LightSerp's frontend URL
- **Grant Type:** Authorization Code with PKCE

User database is shared — one account works for both LightSerp and IacGenie.

## Secrets (OpenBao)

OpenBao provides centralized secrets storage. LightSerp reads from the `secret/lightsrp/*` path:

```bash
# Put a secret for LightSerp
docker exec openbao openbao kv put secret/lightsrp/api-key key=your-value

# Read a secret
docker exec openbao openbao kv get secret/lightsrp/api-key
```

## Service Ports

All services are bound to `127.0.0.1` for security. External access goes through the Cloudflare Tunnel.

| Service | Internal Port | External (via Tunnel) |
|---------|--------------|----------------------|
| LightSerp | 3001 | `lightserp.yourdomain.com` |
| Keycloak | 8443 | `keycloak.yourdomain.com` |
| Grafana | 3001 | `grafana.yourdomain.com` |
| MinIO | 9000/9001 | `minio.yourdomain.com` |
| OpenBao | 8200 | `openbao.yourdomain.com` |

## Configuration

Copy `.env` from the unified directory:

```bash
cp ~/workspace/iacgenie/docker-compose-unified/.env .env
```

Key environment variables for LightSerp:

| Variable | Description |
|----------|-------------|
| `LIGHTSERP_PORT` | HTTP server port (default: 3001) |
| `SEARXNG_URL` | SearXNG search endpoint (internal hostname) |
| `REDIS_URL` | Redis connection string (DB1 for LightSerp) |
| `NSQD_URL` | NSQ message queue endpoint |
| `KEYCLOAK_URL` | Keycloak OIDC endpoint |
| `KEYCLOAK_REALM` | Keycloak realm name |
| `KEYCLOAK_CLIENT_ID` | LightSerp client ID |
| `KEYCLOAK_CLIENT_SECRET` | LightSerp client secret (from `.env.lightserp`) |

## Development Workflow

### Local Development (without Docker)

When developing LightSerp locally, you can run it against the shared Docker infrastructure:

```bash
# From the shared stack directory
cd ~/workspace/iacgenie/docker-compose-unified
docker compose -f docker-compose-unified.yml up -d postgres redis minio keycloak openbao searxng nsqd

# In a separate terminal, run LightSerp locally
cd ~/workspace/LightSerp
# Point your local .env at the Docker-host IP (not localhost)
# LIGHTSFTP_PORT=3001
# REDIS_URL=redis://<DOCKER_HOST_IP>:6379/1
# etc.

npm install
npm run dev
```

### Full Stack Development

For full-stack development with Docker:

```bash
# Start shared services once
cd ~/workspace/iacgenie/docker-compose-unified
docker compose -f docker-compose-unified.yml up -d

# Start LightSerp services
cd ~/workspace/LightSerp
docker compose up -d

# Hot-reload LightSerp (dev mode)
docker compose up -d --no-deps --build lightserp
```

## Troubleshooting

### Connection refused from LightSerp to shared services

Verify LightSerp is on the correct network:
```bash
docker network ls | grep iacgenie
```

### Can't access shared services from local dev

Use your host's Docker IP instead of localhost:
```bash
# Find your Docker host IP
ipconfig getifaddr en0   # macOS Wi-Fi
ipconfig getifaddr en1   # macOS Ethernet
```

### Grafana not loading dashboards

The Grafana datasource is pre-provisioned. If dashboards don't load:
```bash
docker compose -f docker-compose-unified.yml restart grafana
```

### Need to reset all data

```bash
cd ~/workspace/iacgenie/docker-compose-unified
docker compose -f docker-compose-unified.yml down -v
docker compose -f docker-compose-unified.yml up -d
```

## File Reference

Shared infrastructure files:
- `~/workspace/iacgenie/docker-compose-unified/docker-compose-unified.yml` — Shared services
- `~/workspace/iacgenie/docker-compose-unified/docker-compose-lightsrp.yml` — LightSerp app services
- `~/workspace/iacgenie/docker-compose-unified/.env` — Shared credentials
- `~/workspace/iacgenie/docker-compose-unified/.env.lightserp` — LightSerp overrides

LightSerp project files:
- `~/workspace/LightSerp/docker-compose.yml` — Symlink to shared compose
- `~/workspace/LightSerp/docker-compose-shared.yml` — Symlink to shared compose
- `~/workspace/LightSerp/.env` — Symlink to shared .env
- `~/workspace/LightSerp/src/server.ts` — LightSerp MCP server
- `~/workspace/LightSerp/docker-compose.yml` — LightSerp service overlay

## Quick Reference

```bash
# Deploy everything
cd ~/workspace/iacgenie/docker-compose-unified && ./deploy-unified.sh

# Start LightSerp services
cd ~/workspace/LightSerp && docker compose up -d

# Check status
docker compose -f docker-compose-unified.yml ps
docker compose ps

# View logs
docker compose -f docker-compose-unified.yml logs -f lightserp

# Restart LightSerp
cd ~/workspace/LightSerp && docker compose restart

# Stop everything
docker compose -f docker-compose-unified.yml down
cd ~/workspace/LightSerp && docker compose down
```

See [docs/shared-infrastructure.md](./shared-infrastructure.md) for the complete shared infrastructure documentation.