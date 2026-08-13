---
name: openbao-secrets-pipeline
description: Centralized secrets management using OpenBao → GitHub Secrets → Docker Compose. Zero hardcoded passwords.
---

# OpenBao Secrets Pipeline

## Trigger
When deploying new infrastructure services or migrating existing services to use centralized secrets management.

## Prerequisites
- OpenBao 2.6.0+ running with KV v2 mounted at `iacgenie/kv/`
- SSH access to VM
- GitHub repository with Actions enabled
- All services use `${VAR_NAME}` references in docker-compose, never hardcoded values

## Workflow

### 1. Fetch secrets from OpenBao
```python
# On VM: list all secrets
curl -sk -H 'X-Vault-Token: $ROOT_TOKEN' \
  http://127.0.0.1:8200/v1/iacgenie/kv/metadata/?list=true

# Read a specific secret
curl -sk -H 'X-Vault-Token: $ROOT_TOKEN' \
  http://127.0.0.1:8200/v1/iacgenie/kv/data/<service_name>
```

### 2. Generate .env from OpenBao
Read all KV pairs, map to env var names, write `.env` to VM.

Key env var naming convention:
- `PG_ROOT_PASSWORD` → PostgreSQL root
- `REDIS_PASSWORD` → Redis
- `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` → MinIO
- `KEYCLOAK_ADMIN_USER` / `KEYCLOAK_ADMIN_PASSWORD` → Keycloak admin
- `JWT_SECRET` → JWT signing key
- `LIGHTSERP_API_SECRET` → LightSerp API auth
- `CLOUDFLARE_TUNNEL_TOKEN` → Cloudflare tunnel
- `SEARXNG_SECRET_KEY` → SearXNG
- `GRAFANA_ADMIN_PASSWORD` / `GRAFANA_ADMIN_USER` → Grafana
- `GITEA_ADMIN_PASSWORD` → Gitea
- `AUTH_WRAPPER_KC_SECRET` / `AUTH_WRAPPER_SESSION_SECRET` → Auth wrapper

### 3. Update docker-compose.yml
Every env var must use `${ENV_VAR_NAME}` syntax. Never hardcode.

Common patterns:
```yaml
# Database
POSTGRES_USER: "${POSTGRES_USER}"
POSTGRES_PASSWORD: "${POSTGRES_PASSWORD}"
POSTGRES_DB: "${POSTGRES_DB}"

# Redis in connection strings
REDIS_URL: "redis://:${REDIS_PASSWORD}@redis:6379/0"

# MinIO
MINIO_ROOT_USER: "${MINIO_ROOT_USER}"
MINIO_ROOT_PASSWORD: "${MINIO_ROOT_PASSWORD}"

# Services referencing other services
MINIO_ACCESS_KEY: "${MINIO_ROOT_USER}"
MINIO_SECRET_KEY: "${MINIO_ROOT_PASSWORD}"
```

### 4. Sync secrets to GitHub (optional)
For GitOps workflows, push secrets to GitHub repository secrets:
```python
# Read from OpenBao, push to GitHub REST API
# Endpoint: POST /repos/{owner}/{repo}/actions/secrets
# Token: GitHub personal access token with 'repo' scope
```

Name conventions for GitHub secrets:
- Do NOT use `GITHUB_` prefix (reserved by GitHub Actions)
- Use service-specific prefix: `MINIO_ROOT_PASSWORD`, `JWT_SECRET`, etc.
- If OAuth credentials are not yet available, set to empty string as placeholder

### 5. Deploy .env to VM
```bash
# Use Python to read OpenBao, generate .env, SCP to VM
python3 /Users/manjunathkanavi/iacgenie-platform/scripts/deploy-secrets.py
```

### 6. Cleanup hardcoded secrets
Remove ALL hardcoded passwords from:
- `.env` files in repos → replace with `***` or `${ENV_VAR}` references
- `.env.*.env` example files → replace real values with `CHANGE_ME_IN_VAULT`
- Any hardcoded strings in source code

Update `.gitignore` to catch all env variants:
```
.env
.env.*.local
*.env
*.env.prod
*.env.staging
.env.test
*.secret
```

## Verification Checklist
- [ ] `docker-compose config` passes without errors
- [ ] All services start successfully
- [ ] No `undefined variable` warnings in docker-compose output
- [ ] `.env` file on VM has all required vars
- [ ] No hardcoded secrets in git-tracked files
- [ ] `.gitignore` blocks `.env` files

## Files Created
- `scripts/deploy-secrets.py` — OpenBao → .env → VM deployment
- `ansible/fetch-github-secrets.yml` — Ansible playbook for GitHub secrets
- `ansible/templates/env.j2` — Jinja2 template for env generation
- `infra/docker-compose-iacgenie.yml` — Updated docker-compose with env var references

## Pitfalls
1. **OpenBao KV key names**: Service names in KV (e.g., `postgres`, `keycloak`) map to env vars with uppercase prefixes (e.g., `PG_ROOT_PASSWORD`, `KEYCLOAK_ADMIN_PASSWORD`)
2. **GitHub secret naming**: Never use `GITHUB_` prefix — use `GH_OAUTH_*` or service-specific names
3. **Password special chars**: Docker Compose handles `$` in passwords when wrapped in quotes. If passwords contain `{`, use double quotes: `"${VAR}"`
4. **Missing env vars**: All docker-compose `${VAR}` references must exist in `.env` or Docker Compose will substitute empty strings
5. **OpenBao userpass plugin**: May be missing in container image — use root token for admin operations
6. **Redis URL format**: Must include password with `@` separator: `redis://:${PASSWORD}@host:port/0`
