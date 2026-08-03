# OpenBao (HashiCorp Vault Alternative) — Complete Reference

> **Last Updated:** 2025-07-22
> **Host:** vault.iacgenie.com (HTTP 443)
> **Internal:** https://127.0.0.1:8200 (inside Docker network `iacgenie-network`)

---

## 1. Architecture Overview

OpenBao is deployed as a **single-node production instance** on VM `192.168.0.118` using Docker Compose. It serves as the centralized secrets store for all IacGenie infrastructure services.

### Deployment Details
| Property | Value |
|----------|-------|
| Container | `iacgenie-openbao` |
| Image | `quay.io/openbao/openbao:2.6.0` |
| Mode | Production (not dev) |
| Storage Backend | Raft (single node) at `/openbao/raft` |
| Listener | `0.0.0.0:8200` (HTTPS with TLS) |
| UI | Enabled at `https://vault.iacgenie.com` |
| Config File | `/openbao/data/openbao-prod.hcl` |
| Certs | `/openbao/data/certs/` (self-signed CA) |
| Nginx Proxy | `vault.iacgenie.com` → `https://iacgenie_openbao:8200` |

### Docker Mounts
| Volume | Path (inside container) | Purpose |
|--------|------------------------|---------|
| `openbao_data` | `/openbao/data` | Config, certs, init scripts |
| `openbao_raft` | `/openbao/raft` | Raft storage backend (persistent) |
| `openbao_logs` | `/openbao/logs` | Audit and server logs |

### TLS Certificates
- **CA:** `ca.crt` / `ca.key`
- **Server:** `server.crt`, `server.key`, `server.csr`
- **Domain:** `vault.iacgenie.com` (internal CA, not public-trusted)
- **Nginx:** Uses `ssl_verify_client off` — TLS terminates at OpenBao, not at Nginx

---

## 2. Current State

### Service Health
- ✅ **Initialized** (Shamir key sharing, 3 keys, threshold 2)
- ✅ **Unsealed** (all 3 unseal keys shared successfully)
- ✅ **Running** (up 2+ hours, healthy)
- ✅ **Version** OpenBao 2.6.0

### Auth Backends
| Path | Type | Status |
|------|------|--------|
| `userpass/` | Username/password | Enabled |
| `token/` | Token-based | Enabled (default) |

### Secrets Engines
| Path | Type | Default Lease TTL |
|------|------|-------------------|
| `secret/` | KV v2 | 768h (32 days) |

### Policies
| Name | Description |
|------|-------------|
| `default` | Read-only access to `secret/` path |
| `root` | Full administrative access |

### Active Users (userpass)
| Username | Description |
|----------|-------------|
| `admin` | Superuser (configured during bootstrap) |

---

## 3. How to Use — For Regular Users

### Option A: OpenBao CLI (recommended)
```bash
# Install OpenBao CLI
brew tap openbao/brew
brew install openbao

# Set auth token (export once per session)
export VAULT_ADDR='https://vault.iacgenie.com'
export VAULT_TOKEN='s.rSbMYziTmxxIi7BRnJ4kxM7D'

# Read a secret
vault read secret/data/iacgenie/postgres

# Read a specific key
vault kv get secret/data/iacgenie/postgres password

# List secrets at a path
vault kv list secret/data/iacgenie/
```

### Option B: curl (quick access)
```bash
TOKEN='s.rSbMYziTmxxIi7BRnJ4kxM7D'
curl -sk https://vault.iacgenie.com/v1/secret/data/iacgenie/postgres \
  -H "X-Vault-Token: $TOKEN" | python3 -m json.tool
```

### Option C: Python (programmatic access)
```python
import hvac  # pip install hvac

client = hvac.Client(url='https://vault.iacgenie.com', token='s.rSbMYziTmxxIi7BRnJ4kxM7D')

# Read secret
secret = client.secrets.kv.v2.read_secret_version(path='iacgenie/postgres')
password = secret['data']['data']['password']

# Write secret
client.secrets.kv.v2.create_or_update_secret(
    path='iacgenie/myapp',
    secret={'api_key': 'my-secret-key'},
    mount_point='secret'
)

# List secrets
secrets = client.secrets.kv.v2.list_secrets(path='iacgenie/')
print(secrets['data']['keys'])
```

### Option D: Web UI (manual review)
1. Navigate to `https://vault.iacgenie.com`
2. Login with username `admin` and your password
3. Browse secrets under `secret/` path
4. Use the CLI in the browser for quick reads

### Common Operations
```bash
# Read PostgreSQL credentials
vault kv get secret/data/iacgenie/postgres

# Read Redis credentials
vault kv get secret/data/iacgenie/redis

# Read MinIO credentials
vault kv get secret/data/iacgenie/minio

# Read JWT secret
vault kv get secret/data/iacgenie/jwt

# List all available secret paths
vault kv list secret/data/iacgenie/
```

---

## 4. Maintenance — For DevOps Engineers

### Quick Health Check
```bash
# Check if OpenBao is healthy
curl -sk https://vault.iacgenie.com/v1/sys/health | python3 -m json.tool

# Expected: {"sealed":false,"standby":false,"operational":true,"version":"2.6.0"}

# Check seal status
curl -sk https://vault.iacgenie.com/v1/sys/seal-status | python3 -m json.tool

# Check if the server is initialized
curl -sk https://vault.iacgenie.com/v1/sys/init | python3 -m json.tool
```

### Container Management
```bash
# SSH to VM
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118

# View logs
docker logs iacgenie-openbao --tail 50

# Restart container
docker restart iacgenie-openbao

# Inspect container
docker inspect iacgenie-openbao --format '{{.Config.Cmd}}'

# Check disk usage
docker exec iacgenie-openbao du -sh /openbao/raft /openbao/data /openbao/logs
```

### Rotating Unseal Keys
If the Shamir keys need rotation:
```bash
# 1. Verify current keys exist
cat /home/mkanavi/docker/iacgenie/openbao_raft/init_keys.json

# 2. If keys are lost, you MUST reinitialize:
#    WARNING: This destroys all existing data!
docker stop iacgenie-openbao
docker rm iacgenie-openbao
# Then re-run bootstrap_openbao.sh
```

### Updating Configuration
```bash
# Edit the production config
nano /home/mkanavi/docker/iacgenie/openbao_data/openbao-prod.hcl

# Restart to apply (env vars are read at container start)
docker restart iacgenie-openbao
```

### Backup
```bash
# Backup raft data (critical — contains ALL secrets)
docker exec iacgenie-openbao tar czf /tmp/openbao_raft_backup.tar.gz /openbao/raft

# Download to local machine
scp mkanavi@192.168.0.118:/tmp/openbao_raft_backup.tar.gz .

# Cleanup remote temp file
ssh mkanavi@192.168.0.118 "rm /tmp/openbao_raft_backup.tar.gz"
```

### Disaster Recovery
If OpenBao data is corrupted:
1. Stop the container: `docker stop iacgenie-openbao`
2. Restore raft data from backup to `openbao_raft` mount
3. Start container: `docker start iacgenie-openbao`
4. Verify health: `curl -sk https://vault.iacgenie.com/v1/sys/health`

### Troubleshooting
| Symptom | Cause | Fix |
|---------|-------|-----|
| 400 Bad Request on API | Wrong token format or no TLS | Verify `X-Vault-Token` header + use `--cacert` or `-k` |
| Service unavailable | Docker container not running | `docker start iacgenie-openbao` |
| Connection timeout | Firewall/nginx misconfiguration | Check nginx config: `/etc/nginx/conf.d/iacgenie-unified.conf` |
| Raft data loss | No backup | Restore from backup or reinitialize (data loss) |
| User login fails | Password reset needed | Reset with root token: `curl -X PUT .../v1/auth/userpass/users/<user>` |

---

## 5. Administration — For Admin Users

### Admin Credentials
| Credential | Value | Location |
|------------|-------|----------|
| **Root Token** | `s.rSbMYziTmxxIi7BRnJ4kxM7D` | `.env`, OpenBao init |
| **Admin Username** | `admin` | `.env` |
| **Admin Password** | `3bWLGXFwEQVtFXFOKDbTg` | `.env` |
| **API URL** | `https://vault.iacgenie.com` | DNS |

### Managing Users
```bash
# Create a new user
curl -sk -X PUT https://vault.iacgenie.com/v1/auth/userpass/users/newuser \
  -H "X-Vault-Token: s.rSbMYziTmxxIi7BRnJ4kxM7D" \
  -H "Content-Type: application/json" \
  -d '{"password": "NewPass123!", "token_policies": ["default"]}'

# Update password
curl -sk -X PUT https://vault.iacgenie.com/v1/auth/userpass/users/newuser \
  -H "X-Vault-Token: s.rSbMYziTmxxIi7BRnJ4kxM7D" \
  -H "Content-Type: application/json" \
  -d '{"password": "NewerPass456!"}'

# Delete a user
curl -sk -X DELETE https://vault.iacgenie.com/v1/auth/userpass/users/newuser \
  -H "X-Vault-Token: s.rSbMYziTmxxIi7BRnJ4kxM7D"

# List all users
curl -sk https://vault.iacgenie.com/v1/auth/userpass/users?list=true \
  -H "X-Vault-Token: s.rSbMYziTmxxIi7BRnJ4kxM7D" | python3 -m json.tool
```

### Managing Secrets (KV-v2)
```bash
# Write a new secret
curl -sk -X POST https://vault.iacgenie.com/v1/secret/data/iacgenie/myapp \
  -H "X-Vault-Token: s.rSbMYziTmxxIi7BRnJ4kxM7D" \
  -H "Content-Type: application/json" \
  -d '{"data": {"username": "myuser", "password": "mypassword"}}'

# Read a secret
curl -sk https://vault.iacgenie.com/v1/secret/data/iacgenie/myapp \
  -H "X-Vault-Token: s.rSbMYziTmxxIi7BRnJ4kxM7D" | python3 -m json.tool

# List secrets at path
curl -sk "https://vault.iacgenie.com/v1/secret/metadata/iacgenie?list=true" \
  -H "X-Vault-Token: s.rSbMYziTmxxIi7BRnJ4kxM7D" | python3 -m json.tool

# Delete a secret (mark for deletion)
curl -sk -X DELETE https://vault.iacgenie.com/v1/secret/data/iacgenie/myapp \
  -H "X-Vault-Token: s.rSbMYziTmxxIi7BRnJ4kxM7D"

# Read all versions of a secret
curl -sk https://vault.iacgenie.com/v1/secret/metadata/iacgenie/myapp \
  -H "X-Vault-Token: s.rSbMYziTmxxIi7BRnJ4kxM7D" | python3 -m json.tool
```

### Managing Policies
```bash
# Create a new policy
vault policy write mypolicy - <<EOF
path "secret/data/myapp/*" {
  capabilities = ["read", "list"]
}
EOF

# List policies
curl -sk https://vault.iacgenie.com/v1/sys/policy?list=true \
  -H "X-Vault-Token: s.rSbMYziTmxxIi7BRnJ4kxM7D" | python3 -m json.tool
```

### Admin Password Reset
```bash
# Reset admin password (always keep a backup root token!)
curl -sk -X PUT https://vault.iacgenie.com/v1/auth/userpass/users/admin \
  -H "X-Vault-Token: s.rSbMYziTmxxIi7BRnJ4kxM7D" \
  -H "Content-Type: application/json" \
  -d '{"password": "NEW_ADMIN_PASSWORD"}'

# Then update .env file
sed -i '' 's/^OPENBAO_ADMIN_PASSWORD=.*/OPENBAO_ADMIN_PASSWORD=NEW_ADMIN_PASSWORD/' /path/to/.env
```

### Root Token Rotation
```bash
# Generate a new root token
# NOTE: This requires re-initialization in production mode
# The safest approach is to create a time-limited token instead

# Create a child token with specific policies (recommended over root rotation)
curl -sk -X POST https://vault.iacgenie.com/v1/auth/token/create \
  -H "X-Vault-Token: s.rSbMYziTmxxIi7BRnJ4kxM7D" \
  -H "Content-Type: application/json" \
  -d '{"policies": ["default"], "ttl": "1h"}' | python3 -m json.tool
```

---

## 6. Reference

### File Locations
| Resource | Path |
|----------|------|
| Production config | `/openbao/data/openbao-prod.hcl` |
| Config backup | `/openbao/data/openbao-prod.hcl.bak` |
| Raft data | `/openbao/raft/` |
| TLS certs | `/openbao/data/certs/` |
| Init keys (unseal) | `/home/mkanavi/docker/iacgenie/openbao_raft/init_keys.json` |
| Bootstrap script | `/home/mkanavi/docker/iacgenie/bootstrap_openbao.sh` |
| .env (VM) | `/home/mkanavi/docker/iacgenie/.env` |
| .env (local repos) | See `.env` files in each repo's `infra/` directory |

### Unseal Keys (Shamir — 3 of 3, threshold 1)
| Key | Hex |
|-----|-----|
| Key 1 | `579ef1fc6b1ca97168a6ed342f228c40f0f1f11fa97b874ce51826c286c1c0a7a7` |
| Key 2 | `325671403b13bfb7a80ed8df138fcdcf833e6d6cd11d7393b241d84518dfe65414` |
| Key 3 | `45131285a8b7768e77a93cb7b5bda9083d45f6d2861990c71f900a18288c5e8975` |

> ⚠️ **CRITICAL:** Store unseal keys in a secure offline location. Without them, OpenBao cannot be restarted after a crash.

### DNS Endpoints
| Service | URL |
|---------|-----|
| OpenBao API | `https://vault.iacgenie.com` |
| OpenBao UI | `https://vault.iacgenie.com` |

### Secret Paths (KV-v2)
| Path | Contents |
|------|----------|
| `secret/data/iacgenie/postgres` | PostgreSQL credentials |
| `secret/data/iacgenie/redis` | Redis credentials |
| `secret/data/iacgenie/minio` | MinIO credentials |
| `secret/data/iacgenie/jwt` | JWT signing secret |

---

## 7. Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────┐
│  OpenBao Quick Reference                                        │
├─────────────────────────────────────────────────────────────────┤
│  API URL:    https://vault.iacgenie.com                         │
│  Token:      s.rSbMYziTmxxIi7BRnJ4kxM7D                        │
│  User:       admin                                              │
│  Password:   3bWLGXFwEQVtFXFOKDbTg                             │
│  CLI:        vault read secret/data/iacgenie/postgres           │
│  Python:     hvac.Client(url, token)                           │
│  Health:     curl -sk https://vault.iacgenie.com/v1/sys/health  │
│  Containers: docker restart iacgenie-openbao                   │
│  Backup:     docker cp iacgenie-openbao:/openbao/raft ./backup  │
└─────────────────────────────────────────────────────────────────┘
```
