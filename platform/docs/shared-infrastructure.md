# Shared Infrastructure

## Overview

IacGenie and LightSerp both use a **unified shared infrastructure stack** managed as a single Docker Compose project at:

```
~/workspace/iacgenie/docker-compose-unified/
```

This eliminates running two separate infrastructure stacks, reduces resource usage, and provides a single source of truth for your shared services.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Unified Infrastructure Stack                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │
│  │ PostgreSQL  │    │    Redis    │    │    MinIO    │              │
│  │ :5432       │    │   :6379     │    │  :9000/9001  │              │
│  │ Multi-tenant│    │ Multi-DB    │    │ S3 Storage  │              │
│  └──────┬──────┘    └──────┬──────┘    └──────┬───────┘              │
│         │                   │                   │                     │
│  ┌──────┴───────────────────┴───────────────────┴───────┐              │
│  │                  iacgenie_network                     │              │
│  │                  (internal only)                      │              │
│  └──────┬───────────────────┬───────────────────┬───────┘              │
│         │                   │                   │                     │
│  ┌──────┴───────┐   ┌──────┴───────┐   ┌──────┴───────┐               │
│  │   Keycloak   │   │   OpenBao    │   │   SearXNG    │               │
│  │  :5432, 8443 │   │   :8200      │   │   :8070      │               │
│  │   OIDC Auth  │   │   Secrets Mgr│   │   Search     │               │
│  └──────────────┘   └──────────────┘   └──────────────┘               │
│                                                                       │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐               │
│  │   Prometheus │   │   Grafana    │   │     NSQ      │               │
│  │   :9090      │   │   :3001      │   │   :4150/4161 │               │
│  │   Metrics    │   │   Dashboards │   │   Message Q  │               │
│  └──────────────┘   └──────────────┘   └──────────────┘               │
├─────────────────────────────────────────────────────────────────────┤
│  Cloudflare Tunnel → Nginx → Per-hostname routing                   │
│  iacgenie.yourdomain.com → IacGenie App                              │
│  lightserp.yourdomain.com → LightSerp API                            │
└─────────────────────────────────────────────────────────────────────┘
```

## Shared Services

| Service | Port (host) | Port (container) | Purpose | Who Uses It |
|---------|-------------|------------------|---------|-------------|
| **PostgreSQL** | 127.0.0.1:5432 | 5432 | Multi-tenant database | IacGenie, LightSerp, Keycloak |
| **Redis** | 127.0.0.1:6379 | 6379 | Caching & sessions (db0=iagenie, db1=lightsrp) | IacGenie, LightSerp |
| **MinIO** | 127.0.0.1:9000/9001 | 9000/9001 | S3-compatible object storage | IacGenie, LightSerp |
| **Keycloak** | 127.0.0.1:8443 | 8443 | OAuth2/OIDC provider | IacGenie, LightSerp |
| **OpenBao** | 127.0.0.1:8200 | 8200 | Secrets management (KV-v2) | IacGenie, LightSerp |
| **SearXNG** | 127.0.0.1:8070 | 8080 | Web search engine | LightSerp |
| **NSQ** | 127.0.0.1:4150/4161 | 4150/4161 | Message queue | LightSerp |
| **Prometheus** | 127.0.0.1:9090 | 9090 | Metrics collection | All services |
| **Grafana** | 127.0.0.1:3001 | 3000 | Monitoring dashboards | DevOps/observability |

## Multi-Tenant PostgreSQL

The shared PostgreSQL instance uses **schema isolation** per platform:

- **`iacgenie`** database → `iacgenie` schema (IacGenie app data)
- **`lightsrp`** database → `lightsrp` schema (LightSerp app data)
- **`keycloak`** database → `public` schema (Keycloak internal tables)

Each tenant gets its own role with restricted access:
- `iacgenie_app` — full access to `iacgenie.*` schema only
- `lightsrp_app` — full access to `lightsrp.*` schema only
- `keycloak_app` — full access to `keycloak.public` schema only

## Getting Started

### 1. Deploy the Shared Infrastructure

```bash
cd ~/workspace/iacgenie/docker-compose-unified

# Copy and edit the shared environment file
cp .env .env.local
# Edit .env.local with your secrets

# Start the unified stack
./deploy-unified.sh
```

The deployment script will:
1. Validate the `.env` file
2. Start all 10 services in order
3. Wait for health checks to pass (up to 2 minutes)
4. Initialize OpenBao with tenant secrets
5. Verify all services are healthy

### 2. Configure Your Platform

#### For IacGenie

Copy the shared infrastructure and the IacGenie overlay to your workspace:

```bash
# Link to shared infrastructure
ln -sf ~/workspace/iacgenie/docker-compose-unified/docker-compose-unified.yml ~/workspace/iacgenie/docker-compose-shared.yml
ln -sf ~/workspace/iacgenie/docker-compose-unified/docker-compose-iacgenie.yml ~/workspace/iacgenie/docker-compose.yml
ln -sf ~/workspace/iacgenie/docker-compose-unified/.env.local ~/workspace/iacgenie/.env
```

Your IacGenie `docker-compose.yml` now references the shared services via the `iacgenie_network`.

#### For LightSerp

```bash
# Link to shared infrastructure
ln -sf ~/workspace/iacgenie/docker-compose-unified/docker-compose-unified.yml ~/workspace/LightSerp/docker-compose-shared.yml
ln -sf ~/workspace/iacgenie/docker-compose-unified/docker-compose-lightsrp.yml ~/workspace/LightSerp/docker-compose.yml
ln -sf ~/workspace/iacgenie/docker-compose-unified/.env.local ~/workspace/LightSerp/.env
```

### 3. Manage the Stack

```bash
cd ~/workspace/iacgenie/docker-compose-unified

# Start all shared services + your platform
docker compose -f docker-compose-unified.yml up -d
# Or use the deploy script:
./deploy-unified.sh

# Start just the shared infrastructure (no app services)
docker compose -f docker-compose-unified.yml up -d postgres redis minio keycloak openbao

# Start your platform services (assuming docker-compose.yml exists in project dir)
cd ~/workspace/iacgenie && docker compose up -d

# Stop everything
docker compose -f docker-compose-unified.yml down
cd ~/workspace/iacgenie && docker compose down

# View logs
docker compose -f docker-compose-unified.yml logs -f

# Restart a specific service
docker compose -f docker-compose-unified.yml restart keycloak

# Check health
docker compose -f docker-compose-unified.yml ps
```

## Network

All shared services run on the **`iacgenie_network`** Docker network (internal). Services are bound to `127.0.0.1` and only accessible:
- From containers on the same Docker network (internal communication)
- Through Cloudflare Tunnel for external access

## Keycloak Authentication

Keycloak serves as the shared OAuth2/OIDC provider for both platforms:

1. Log in at `https://keycloak.yourdomain.com/` (via Cloudflare Tunnel)
2. Default admin: `admin` / password from `.env`
3. Two client registrations are pre-configured:
   - **iacgenie** — with redirect URIs for IacGenie frontend
   - **lightsrp** — with redirect URIs for LightSerp frontend

Both platforms share the same user database. Users created in Keycloak can authenticate on either platform.

## Secrets Management (OpenBao)

OpenBao provides a centralized secrets backend with KV-v2 engine:

```bash
# Auto-bootstrap (run once during deployment)
docker exec openbao /openbao-bootstrap.sh

# Store a secret for IacGenie
docker exec openbao openbao kv put secret/iacgenie/api-key key=your-secret-value

# Store a secret for LightSerp
docker exec openbao openbao kv put secret/lightsrp/api-key key=your-secret-value

# Read a secret
docker exec openbao openbao kv get secret/iacgenie/api-key
```

Both platforms can read their respective secret paths at runtime.

## Service Mount Points

### PostgreSQL (data)
```
~/.local/share/docker/volumes/iacgenie-docker-compose-unified_postgres-data
```

### Redis (data)
```
~/.local/share/docker/volumes/iacgenie-docker-compose-unified_redis-data
```

### MinIO (data)
```
~/.local/share/docker/volumes/iacgenie-docker-compose-unified_minio-data
```

### Keycloak (data)
```
~/.local/share/docker/volumes/iacgenie-docker-compose-unified_keycloak-data
```

### OpenBao (data)
```
~/.local/share/docker/volumes/iacgenie-docker-compose-unified_openbao-data
```

### Grafana (dashboards/provisioning)
```
~/.local/share/docker/volumes/iacgenie-docker-compose-unified_grafana-data
```

## Configuration Override Pattern

Each platform can override shared service configurations using the compose override pattern:

```bash
# Example: Override Redis maxmemory for IacGenie
docker compose -f docker-compose-unified.yml -f docker-compose-iacgenie.yml up -d

# The overlay file can specify:
# - different environment variables per service
# - additional volumes
# - extra depends_on relationships
```

See `docker-compose-iacgenie.yml` for the IacGenie overlay pattern.
See `docker-compose-lightsrp.yml` for the LightSerp overlay pattern.

## Troubleshooting

### Service won't start
```bash
# Check logs
docker compose -f docker-compose-unified.yml logs <service>

# Force recreate (e.g. after env changes)
docker compose -f docker-compose-unified.yml up -d --force-recreate <service>
```

### Password corruption
If you changed `.env.local`, restart with force-recreate:
```bash
docker compose -f docker-compose-unified.yml up -d --force-recreate
```

### Database connection refused
Verify PostgreSQL is healthy:
```bash
docker compose -f docker-compose-unified.yml exec postgres pg_isready
```

### OpenBao sealed
Bootstrap OpenBao if it's in sealed state:
```bash
docker exec openbao /openbao-bootstrap.sh
```

## File Layout

```
docker-compose-unified/
├── docker-compose-unified.yml   # Shared infrastructure (9 services)
├── docker-compose-iacgenie.yml  # IacGenie app overlay
├── docker-compose-lightsrp.yml  # LightSerp app overlay
├── .env                         # Shared credentials
├── .env.iacgenie                # IacGenie overrides
├── .env.lightserp               # LightSerp overrides
├── deploy-unified.sh            # Deployment script with health checks
├── nginx-unified.conf           # Cloudflare Tunnel routing config
├── postgres/init-users.sql      # Multi-tenant DB initialization
├── openbao/bootstrap.sh         # OpenBao KV-v2 engine bootstrap
├── keycloak/realm-export.json   # Keycloak unified realm
├── prometheus.yml               # Prometheus scrape config
├── grafana-datasources.yml      # Grafana provisioning
└── README.md                    # This file
```

## Quick Reference

```bash
# Deploy everything
cd ~/workspace/iacgenie/docker-compose-unified && ./deploy-unified.sh

# Check all services healthy
docker compose -f docker-compose-unified.yml ps

# View service logs
docker compose -f docker-compose-unified.yml logs -f <service>

# Restart all
docker compose -f docker-compose-unified.yml restart

# Stop all
docker compose -f docker-compose-unified.yml down

# Remove all data (DANGER)
docker compose -f docker-compose-unified.yml down -v
```