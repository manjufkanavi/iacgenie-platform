# OpenBao Credential Management Guide

> **Version:** 1.0 — 2026-08-08
> **OpenBao Version:** 2.6.0 (Raft storage)
> **Storage:** `/home/mkanavi/docker/iacgenie/data/openbao_raft/`

---

## 1. Architecture

```
┌─────────────────────────────────────────────────────┐
│  OpenBao 2.6.0 (Raft)                               │
│  http://127.0.0.1:8200                              │
│                                                     │
│  KV-v2 Mounts:                                      │
│    ┌── iacgenie/kv/          ← 12 service secrets   │
│    ├── lightserp/kv/        ← LightSerp secrets     │
│    └── terraform/kv/        ← Terraform secrets     │
│                                                     │
│  RBAC:                                              │
│    ├── admin       → full CRUD + sudo               │
│    ├── read-only   → read-only per-mount             │
│    └── AppRole     → service-to-service auth         │
│                                                     │
│  Unseal: Shamir (3 shares, threshold 2)              │
│  Storage: Raft (local filesystem, file: vault.db)    │
└─────────────────────────────────────────────────────┘
         │
         │ curl / HTTP API
         ▼
┌─────────────────────────────────────────────────────┐
│  Services (docker-compose-unified.yml)              │
│                                                     │
│  PostgreSQL (lightsrp)  ← iacgenie/kv/postgres      │
│  Redis                  ← iacgenie/kv/redis         │
│  MinIO                  ← iacgenie/kv/minio         │
│  Gitea                  ← iacgenie/kv/gitea         │
│  Keycloak               ← iacgenie/kv/keycloak      │
│  LightSerp API          ← iacgenie/kv/lightserp     │
│  SearXNG                ← iacgenie/kv/searxng       │
│  NSQD                   ← iacgenie/kv/nsqd          │
│  PageZen                ← iacgenie/kv/pagezen       │
│  Nginx (JWT)            ← iacgenie/kv/nginx         │
│  Terraform              ← iacgenie/kv/terraform     │
└─────────────────────────────────────────────────────┘
```

---

## 2. Secret Path Map

| Service      | OpenBao Path               | Keys                                     |
|-------------|---------------------------|------------------------------------------|
| PostgreSQL  | `iacgenie/kv/postgres`     | `username`, `password`, `database`        |
| Redis       | `iacgenie/kv/redis`        | `password`                               |
| MinIO       | `iacgenie/kv/minio`        | `access_key`, `secret_key`                |
| Gitea       | `iacgenie/kv/gitea`        | `admin_password`                         |
| Keycloak    | `iacgenie/kv/keycloak`     | `admin_user`, `admin_password`            |
| KC DB       | `iacgenie/kv/keycloak_db`  | `username`, `password`, `database`        |
| LightSerp   | `iacgenie/kv/lightserp`    | `api_secret`, `keycloak_client_secret`, `keycloak_db_password` |
| SearXNG     | `iacgenie/kv/searxng`      | `secret_key`                             |
| Nginx       | `iacgenie/kv/nginx`        | `jwt_secret`                             |
| NSQD        | `iacgenie/kv/nsqd`         | `auth_token`                             |
| PageZen     | `iacgenie/kv/pagezen`      | `api_secret`                             |
| Terraform   | `iacgenie/kv/terraform`    | `api_key`                                |

---

## 3. RBAC (Access Control)

### 3.1 Policies

| Policy Name          | Path Pattern                          | Capabilities                              |
|---------------------|---------------------------------------|-------------------------------------------|
| `admin`             | `/*`                                  | create, read, update, delete, list, sudo  |
| `openbao-iacgenie-ro`  | `iacgenie/kv/data/*`               | read                                      |
|                     | `iacgenie/kv/metadata/*`             | read, list                                |
|                     | `iacgenie/kv/*`                       | list                                      |
| `openbao-lightserp-ro` | `lightserp/kv/data/*`             | read                                      |
|                     | `lightserp/kv/metadata/*`            | read, list                                |
| `openbao-terraform-ro` | `terraform/kv/data/*`             | read                                      |
|                     | `terraform/kv/metadata/*`            | read, list                                |

### 3.2 Access Rules

```
┌──────────────────────────────────────────────────┐
│  Admin (root token)                               │
│  ├─ Read all secrets                              │
│  ├─ Write/update any secret                       │
│  ├─ Delete any secret                             │
│  └─ Manage policies & auth methods                │
│                                                   │
│  Service Tokens (read-only policies)              │
│  ├─ Read: own service secrets only                │
│  ├─ Write: DENIED                               │
│  ├─ Delete: DENIED                              │
│  └─ List: own mount only                         │
└──────────────────────────────────────────────────┘
```

### 3.3 AppRole Auth (Machine-to-Machine)

```
Service → AppRole → SecretID → Accessor → Token (auto-generated)
```

AppRoles are configured for each service with:
- `secret_id_ttl`: 24 hours
- `token_ttl`: 1 hour
- `token_max_ttl`: 4 hours
- Bound to specific read-only policies

---

## 4. Password Consistency Strategy

### 4.1 Principle: Single Source of Truth

```
Infrastructure Code (Git)  ←→  OpenBao KV  ←→  .env (VM)
       (authoritative)          (source of           (runtime copy)
                             truth for secrets)
```

**Key Rule:** All secret values MUST be identical across:
1. OpenBao KV (authoritative)
2. `.env` file on VM (runtime)
3. Git-tracked configuration (declarative)

### 4.2 Tools

| Script                         | Purpose                                  |
|-------------------------------|------------------------------------------|
| `openbao-seed.py`            | Generate NEW random secrets for all services |
| `openbao-consistency-check.py` | Compare .env values against OpenBao KV   |
| `bootstrap.sh`               | Full initialization: unseal + seed + RBAC |

### 4.3 Workflow

**Adding/Changing a Secret:**

```bash
# 1. Update .env file
# 2. Run consistency check
python3 openbao-consistency-check.py

# 3. If mismatch, fix it
python3 openbao-consistency-check.py --fix

# 4. Commit changes to Git
git add . && git commit -m "Update <service> secret"
```

**Generating Fresh Secrets:**

```bash
python3 openbao-seed.py
# → Generates new passwords, updates .env, seeds OpenBao
```

### 4.4 Validation Pipeline

```
Every deployment:
  1. bootstrap.sh runs → seeds OpenBao from .env
  2. Consistency check → validates all values match
  3. If mismatch detected → FAIL deployment
  4. If all match → deployment proceeds
```

---

## 5. Emergency Operations

### 5.1 OpenBao Unseal

```bash
# Check status
bao status

# Unseal (need 2 of 3 keys)
bao operator unseal <key1>
bao operator unseal <key2>
```

Unseal keys are stored in GitHub secrets:
- `OPENBAO_UNSEAL_KEY_1`
- `OPENBAO_UNSEAL_KEY_2`
- `OPENBAO_UNSEAL_KEY_3`

### 5.2 Admin Token Recovery

Root token is stored in GitHub secrets:
- `OPENBAO_ROOT_TOKEN`

### 5.3 Full Re-initialization

```bash
# WARNING: This will DELETE all existing secrets!
cd /home/mkanavi/docker/iacgenie
docker compose stop openbao
rm -rf data/openbao_raft/
mkdir -p data/openbao_raft/ && chmod 777 data/openbao_raft/
docker compose up -d openbao

# Wait for OpenBao to be ready, then:
cd /Users/manjunathkanavi/iacgenie-platform/infra/openbao
bash bootstrap.sh
```

### 5.4 Permission Fix (Raft DB)

If OpenBao fails to start with permission errors:

```bash
sudo chmod 600 /home/mkanavi/docker/iacgenie/data/openbao_raft/vault.db
sudo chown mkanavi:mkanavi /home/mkanavi/docker/iacgenie/data/openbao_raft/
docker compose restart openbao
```

---

## 6. Service Access Patterns

### 6.1 Read-Only (Services)

Services authenticate to OpenBao using their AppRole or pre-generated token:

```bash
# Read a secret (read-only)
bao kv get iacgenie/kv/postgres
# Returns: username=lightsrp, password=*****, database=lightsrp
```

### 6.2 Admin (Ops/DevOps)

Admins use the root token for full management:

```bash
# List all secrets
bao kv list iacgenie/kv

# Read a specific secret
bao kv get iacgenie/kv/postgres

# Update a secret
bao kv put iacgenie/kv/postgres password=NewPassword

# Delete a secret
bao kv delete iacgenie/kv/postgres password
```

### 6.3 GitOps Integration

GitHub Actions can access OpenBao via stored tokens:

```yaml
env:
  OPENBAO_ADDR: http://127.0.0.1:8200
  OPENBAO_TOKEN: ${{ secrets.OPENBAO_ROOT_TOKEN }}
```

---

## 7. File Locations

| Item                              | Location                                        |
|-----------------------------------|-------------------------------------------------|
| OpenBao config                    | `data/openbao/openbao-prod.hcl`                 |
| OpenBao Raft storage              | `data/openbao_raft/`                            |
| Service tokens                    | `data/openbao_raft/service_tokens/*.token`       |
| Unseal keys (backup)              | `data/openbao_raft/init_keys.json`              |
| Bootstrap script                  | `infra/openbao/bootstrap.sh`                    |
| RBAC setup                        | `infra/openbao/openbao-rbac-setup.sh`            |
| Consistency checker               | `infra/openbao/openbao-consistency-check.py`     |
| Secret generator                  | `infra/openbao/openbao-seed.py`                  |
| Service .env                      | `/home/mkanavi/docker/iacgenie/.env`             |
| Docker compose                    | `/home/mkanavi/docker/iacgenie/docker-compose.yml` |
| GitHub secrets                    | `iacgenie-platform` repo secrets                 |

---

## 8. Security Notes

- **Never commit** actual secret values to Git
- **Root token** and **unseal keys** are stored in GitHub repository secrets
- **Service tokens** are stored in `service_tokens/` directory with 600 permissions
- **Admin-only** operations: delete, update, policy management
- **Service tokens** can only read their assigned mount
- **AppRole** tokens auto-expire (1h TTL, 4h max)
- **Vault.db** permissions must be `600` or OpenBao refuses to start
- **Backup** the `data/openbao_raft/` directory regularly

---

*Last updated: 2026-08-08*
