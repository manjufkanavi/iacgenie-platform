# IacGenie Platform — Engineer Guide

## Table of Contents
1. [Quick Start](#quick-start)
2. [Accessing Services](#accessing-services)
3. [Service APIs](#service-apis)
4. [Development Workflow](#development-workflow)
5. [Database Access](#database-access)
6. [Object Storage](#object-storage)
7. [Search & AI](#search--ai)
8. [Environment Variables](#environment-variables)

---

## Quick Start

### Prerequisites
- SSH access to VM: `mkanavi@192.168.0.118`
- Keycloak account (admin or developer role)
- Python 3.11+ for API development

### Getting Credentials
```bash
# SSH to VM
ssh mkanavi@192.168.0.118

# Get service credentials from OpenBao
docker exec iacgenie_openbao bao kv get iacgenie/kv/platform/api-key
docker exec iacgenie_openbao bao kv get iacgenie/kv/postgres/pg-password
```

---

## Accessing Services

### External Access (via Cloudflare Tunnel)
| Service | URL | Auth |
|---------|-----|------|
| LightSerp API | `https://api.iacgenie.com` | Bearer token (Keycloak) |
| LightSerp UI | `https://iacgenie.com` | Bearer token (Keycloak) |
| Grafana | `https://grafana.iacgenie.com` | Grafana admin credentials |
| Gitea | `https://gitea.iacgenie.com` | Git credentials |
| OpenBao | `https://vault.iacgenie.com` | OpenBao token |

### Local Access (SSH into VM)
| Service | URL | Notes |
|---------|-----|-------|
| LightSerp API | `http://127.0.0.1:8000` | Docker service |
| Keycloak | `http://127.0.0.1:8083/auth` | Admin UI |
| PostgreSQL | `127.0.0.1:5432` | Via docker exec |
| Redis | `127.0.0.1:6379` | Via docker exec |
| MinIO | `127.0.0.1:9000` | S3-compatible |
| OpenBao | `127.0.0.1:8200` | Secrets management |
| Prometheus | `127.0.0.1:9090` | Metrics |
| Loki | `127.0.0.1:3100` | Logs |
| Falcosidekick | `127.0.0.1:2800` | Security events |

---

## Service APIs

### LightSerp API
```bash
# Base URL
BASE_URL=https://api.iacgenie.com

# Get auth token
curl -X POST "$BASE_URL/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"username": "your@email.com", "password": "your-password"}'

# Use token for API calls
TOKEN=$(curl -s -X POST "$BASE_URL/auth/token" -d '...' | jq -r '.access_token')

curl "$BASE_URL/search?q=hello" \
  -H "Authorization: Bearer $TOKEN"

# Search endpoint
curl "$BASE_URL/search?q=topic&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

### Search API (SearXNG)
```bash
# Via Nginx
curl "https://search.iacgenie.com/search?q=hello&format=json"

# Direct (SSH)
curl "http://127.0.0.1:8082/search?q=hello&format=json"
```

### SearXNG API (SSH into VM)
```bash
# Search
curl "http://127.0.0.1:8082/search?q=hello&format=json"

# Get instance info
curl "http://127.0.0.1:8082/info"
```

---

## Development Workflow

### Local Development with VM Services
```bash
# SSH tunnel to VM services
ssh -L 5432:postgres:5432 \
    -L 6379:redis:6379 \
    -L 9000:minio:9000 \
    mkanavi@192.168.0.118
```

### Database Development
```bash
# Connect to PostgreSQL
docker exec -it iacgenie_postgres psql -U lightsrp -d lightsrp

# Connect to MinIO (S3-compatible)
aws --endpoint-url http://127.0.0.1:9000 s3 ls

# Or use rclone
rclone lsf minio:bucket-name
```

### Testing API Locally
```bash
# Run API locally against VM services
export LIGHTSERP_DB_URL=postgresql://lightsrp:password@localhost:5432/lightsrp
export LIGHTSERP_REDIS_URL=redis://localhost:6379
export LIGHTSERP_MINIO_ENDPOINT=localhost:9000
export LIGHTSERP_KEYCLOAK_URL=http://127.0.0.1:8083/auth/realms/iacgenie

python -m lightserv.api
```

---

## Database Access

### PostgreSQL Schema
```bash
# Connect
docker exec -it iacgenie_postgres psql -U lightsrp -d lightsrp

# List tables
\dt

# Check connection pool
SELECT count(*) FROM pg_stat_activity;

# Vacuum/analyze
VACUUM ANALYZE;
```

### Database Users
| User | Database | Access |
|------|----------|--------|
| `postgres` | All | Superuser |
| `lightsrp` | lightsrp | Application |
| `keycloak` | keycloak | Keycloak |

### Migrations
- Managed via LightSerp application
- Store in `lightserv/migrations/`
- Run via: `alembic upgrade head`

---

## Object Storage

### MinIO Setup
```bash
# Access MinIO console
# http://127.0.0.1:9001
# Login: MinIO credentials from OpenBao

# CLI access
aws --endpoint-url http://127.0.0.1:9000 s3 mb s3://bucket-name
aws --endpoint-url http://127.0.0.1:9000 s3 cp file.txt s3://bucket-name/
aws --endpoint-url http://127.0.0.1:9000 s3 ls s3://bucket-name/
```

### Bucket Structure
| Bucket | Purpose |
|--------|---------|
| `lightserp-uploads` | User uploads |
| `lightserp-cache` | Cache storage |
| `search-index` | SearXNG index |

---

## Search & AI

### SearXNG Configuration
```bash
# Edit config (SSH into VM)
ssh mkanavi@192.168.0.118
docker exec -it iacgenie_searxng cat /etc/searxng/settings.yml

# Restart after changes
docker restart iacgenie_searxng
```

---

## Environment Variables

### Service Environment
Services load environment variables from OpenBao at startup. No hardcoded values.

```bash
# View what a service is using
ssh mkanavi@192.168.0.118
docker inspect iacgenie_lightserp_api | grep -A 50 "Env"
```

### Common Variables
| Variable | Source | Description |
|----------|--------|-------------|
| `API_KEY` | OpenBao KV | API authentication |
| `DB_URL` | OpenBao KV | PostgreSQL connection |
| `REDIS_URL` | OpenBao KV | Redis connection |
| `MINIO_ENDPOINT` | OpenBao KV | MinIO S3 endpoint |
| `KEYCLOAK_URL` | OpenBao KV | Keycloak OIDC URL |
| `GRAFANA_URL` | OpenBao KV | Grafana URL |

---

## Troubleshooting

### Common Issues
1. **401 Unauthorized**: Check Keycloak token expiration
2. **502 Bad Gateway**: Service not running (`docker ps`)
3. **Database timeout**: Check PostgreSQL connection pool
4. **Redis connection refused**: Check Redis health (`redis-cli ping`)
5. **S3 upload failed**: Check MinIO credentials in OpenBao

### Quick Diagnostics
```bash
# Run health check
./health-check.sh

# View service logs
docker logs --tail 100 iacgenie_<service>

# Test connectivity
docker exec iacgenie_lightserp_api ping postgres
```
