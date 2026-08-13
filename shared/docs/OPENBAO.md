# OpenBao — Secret Management & Identity Backend

**Version:** 1.0.0  
**Last Updated:** 2026-08-07  
**Role:** Centralized secrets management + authentication backend for all services  
**Authentication:** Keycloak OIDC + Token-based (root/service tokens)

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    OpenBao (iacgenie_openbao)                │
│                    Port: 8200 (HTTP)                         │
│                    Container: iacgenie_openbao               │
│                    Storage: Raft (local)                     │
└──────────────────────────────────────────────────────────────┘
         ▲                                      ▲
         │                                      │
   OIDC (Keycloak)                      Token (Admin/Service)
         │                                      │
   /realms/lightserp                 root token / service tokens
         │                                      │
    ┌────┼──────────┐                           │
    │    │          │                    ┌──────┼──────┐
platform-admin  openbao-      iacgenie-   lightserp-  terraform-
  (admin)     admin (admin)   service     service     service
    │    │          │           │            │           │
    │    │          │           │            │           │
 admin       admin     iacgenie/    lightserp/   terraform/
 platform     admin    kv r/w      kv r/w     kv r/w
```

## Deployment

| Component | Value |
|-----------|-------|
| Version | OpenBao 2.6.0 |
| Container | `iacgenie_openbao` |
| Published Port | `8200` (HTTP) |
| External URL | `https://vault.iacgenie.com` (Cloudflare Tunnel) |
| Storage | Raft (local disk) |
| Raft Data Dir | `/home/mkanavi/docker/iacgenie/data/openbao_raft` |
| Ansible Role | `openbao` |

## Authentication Methods

### 1. Root Token (Admin Only)

```bash
# From init_keys.json on VM
ssh mkanavi@192.168.0.118 "cat /home/mkanavi/docker/iacgenie/data/openbao_raft/init_keys.json | python3 -c \"import sys,json;print(json.load(sys.stdin)['root_token'])")

# Or from ~/.bash_profile
export OPENBAO_ADDR=https://vault.iacgenie.com
export OPENBAO_TOKEN=<root-token>
```

### 2. Keycloak OIDC (Service & Admin)

```bash
# Get OIDC token from Keycloak
curl -s -X POST http://127.0.0.1:8083/realms/lightserp/protocol/openid-connect/token \
  -d "grant_type=client_credentials" \
  -d "client_id=openbao-oidc" \
  -d "client_secret=2AMmiNh62NQGzwmBiECfNWyIed1hbf04"

# Response: {"access_token":"***", "token_type":"Bearer", ...}

# Login to OpenBao with OIDC token
curl -s -X POST http://127.0.0.1:8200/v1/auth/oidc/login \
  -H "Content-Type: application/json" \
  -d '{"token": "***"}'

# Response includes auth.client_token for vault operations
```

### 3. Service Tokens (Application Services)

| Token | Policy | TTL | Usage |
|-------|--------|-----|-------|
| `openbao_ig_token_ttl` | `iacgenie-service` | 720h (30 days) | IaCGenie backend |
| `openbao_ls_token_ttl` | `lightserp-service` | 720h (30 days) | LightSerp backend |
| `openbao_tf_token_ttl` | `terraform-service` | 720h (30 days) | TerraGenius |
| `openbao_backup_token_ttl` | `backup-read` | 168h (7 days) | Backup verification |

## Key-Value Stores

### Mounted Engines

| Path | Description | Access Policy |
|------|-------------|---------------|
| `iacgenie/kv` | IaCGenie application secrets | iacgenie-service (r/w) |
| `lightserp/kv` | LightSerp application secrets | lightserp-service (r/w) |
| `terraform/kv` | TerraGenius state & provider secrets | terraform-service (r/w) |

### Secret Inventory

| Mount | Paths | Total Fields |
|-------|-------|-------------|
| `iacgenie/kv` | services/iacgenie, services/postgres, services/redis, services/minio, services/keycloak, services/gitea, services/searxng, services/openbao, services/pagezen, services/nsqd | ~40 |
| `lightserp/kv` | services/lightserp, services/postgres, services/redis, services/searxng, services/minio, services/api | ~15 |
| `terraform/kv` | services/terragenius, services/openbao, services/postgres | ~12 |

## Policies

### Policy Map

| Policy | Path Pattern | Capabilities |
|--------|-------------|--------------|
| `admin` | `*` | create,read,update,delete,list,sudo |
| `platform-admin` | `*` | create,read,update,delete,list |
| `iacgenie-service` | `iacgenie/kv/*` | create,read,update,delete,list |
| `lightserp-service` | `lightserp/kv/*` | create,read,update,delete,list |
| `terraform-service` | `terraform/kv/*` | create,read,update,delete,list |
| `openbao-service-read` | ALL KV engines | read,list |

### Policy Files (Ansible Templates)

| File | Purpose |
|------|---------|
| `policies/admin.hcl.j2` | Full admin access (sudo) |
| `policies/platform-admin.hcl.j2` | Full admin access (no sudo) |
| `policies/iacgenie-service.hcl.j2` | iacgenie KV r/w only |
| `policies/lightserp-service.hcl.j2` | lightserp KV r/w only |
| `policies/terraform-service.hcl.j2` | terraform KV r/w only |
| `policies/openbao-service-read.hcl.j2` | Read-only all KV engines |

## OIDC Integration with Keycloak

### Configuration

| Setting | Value |
|---------|-------|
| Discovery URL | `http://127.0.0.1:8083/realms/lightserp/.well-known/openid-configuration` |
| Client ID | `openbao-oidc` |
| Client Secret | `2AMmiNh62NQGzwmBiECfNWyIed1hbf04` |
| Scopes | `openid profile email roles` |
| User Claim | `email` |
| TTL | 8h |
| Max TTL | 24h |

### Role Bindings

| Keycloak Role | Bound Claim | OpenBao Policies | Vault Access |
|--------------|-------------|-----------------|--------------|
| `platform-admin` | `roles: "platform-admin"` | `admin,platform-admin` | Full admin |
| `openbao-admin` | `roles: "openbao-admin"` | `admin,platform-admin,openbao-admin` | Full admin |
| `iacgenie-service` | `roles: "iacgenie-service"` | `iacgenie-service` | iacgenie/kv r/w |
| `lightserp-service` | `roles: "lightserp-service"` | `lightserp-service` | lightserp/kv r/w |
| `openbao-service-read` | `roles: "openbao-service-read"` | `openbao-service-read` | All KV read-only |
| *(default)* | *(any)* | `openbao-service-read` | All KV read-only |

### OIDC Endpoint URLs

| Purpose | URL |
|---------|-----|
| Discovery | `http://127.0.0.1:8083/realms/lightserp/.well-known/openid-configuration` |
| Token | `http://127.0.0.1:8083/realms/lightserp/protocol/openid-connect/token` |
| Vault Login | `http://127.0.0.1:8200/v1/auth/oidc/login` |
| Vault Callback | `https://vault.iacgenie.com/oidc/callback` |

## RBAC Model: Admin-Only Write Access

### Principle: Only Admin Users Can Read/Write/Create

| Role Type | Who Has It | Capabilities |
|-----------|-----------|--------------|
| `platform-admin` | Only admin users | Full read/write for all realms, clients, users, policies, tokens |
| `openbao-admin` | Only admin users | Full admin access to OpenBao (all KV, all policies) |
| `project-admin` | Project owners (admin-controlled) | Read/write within their project's KV path |
| `project-member` | Regular users | Read-only within their project's KV path |
| `openbao-service-read` | Service accounts | Read-only access to all KV engines |

### Enforcement

1. **Keycloak FGAA**: Only `platform-admin` users can create/update realms and clients
2. **OpenBao OIDC**: Role bindings enforce `admin` policy only for admin role holders
3. **KV Policies**: Scoped to specific mount paths — no cross-contamination
4. **Token TTLs**: Service tokens auto-expire (720h for apps, 168h for backup)

## OpenBao CLI Cheat Sheet

```bash
export BAO_ADDR=http://127.0.0.1:8200
export BAO_TOKEN=<your-token>

# Health check
bao status

# List all mounts
bao secrets list

# List secrets in a path
bao kv list -mount=iacgenie

# Read a secret
bao kv get -mount=iacgenie services/iacgenie

# Read specific field
bao kv get -field=secret_key -mount=iacgenie services/iacgenie

# Write a secret
bao kv put -mount=iacgenie services/iacgenie secret_key=myvalue

# Delete a secret
bao kv delete -mount=iacgenie services/iacgenie

# List policies
bao policy list

# Read a policy
bao policy read admin

# Create a new token
bao auth token create -policy=iacgenie-service -ttl=720h

# Lookup current token
bao token lookup

# Rotate token
bao token rotate

# List auth methods
bao auth list
```

## Ansible Deployment

```bash
# Full deployment (all services)
cd /Users/manjunathkanavi/iacgenie-platform/infra/ansible
ansible-playbook -i hosts playbooks/services.yml

# OpenBao only
ansible-playbook -i hosts playbooks/services.yml --limit=gitea -t openbao

# Bootstrap policies + KV + tokens
ansible-playbook -i hosts playbooks/services.yml --tags bootstrap

# Unseal (if sealed)
ansible-playbook -i hosts playbooks/services.yml --tags unseal
```

## Health Checks

```bash
# Container health
ssh mkanavi@192.168.0.118 "docker inspect --format='{{.State.Health.Status}}' iacgenie_openbao"

# HTTP health
curl -s http://127.0.0.1:8200/v1/sys/health | python3 -m json.tool

# Raft status
ssh mkanavi@192.168.0.118 "docker exec iacgenie_openbao bao operator raft list-peers"

# OIDC auth method status
curl -s -H "X-Vault-Token: $BAO_TOKEN" http://127.0.0.1:8200/v1/sys/auth/oidc | python3 -m json.tool
```

## Backup & Disaster Recovery

### Raft Snapshots
- Location: `/home/mkanavi/docker/iacgenie/data/openbao_raft/`
- Snapshot command: `docker exec iacgenie_openbao bao operator raft snapshot save`
- Cron: Automated every 2h (job `02a41beede44`)

### Required VM Setup
```bash
# Backup script: /home/mkanavi/scripts/openbao_backup.sh
# Add to crontab: 0 3 * * * /home/mkanavi/scripts/openbao_backup.sh
```

## Security Hardening

- ✅ All KV engines are path-scoped (no wildcard r/w)
- ✅ OIDC role bindings enforce minimal privileges
- ✅ Service tokens have limited TTL (720h)
- ✅ Admin tokens have admin-only policies
- ✅ Read-only service accounts for backup/cron
- ✅ Audit logging enabled (`audit/file`)

## Troubleshooting

| Problem | Solution |
|---------|----------|
| OpenBao sealed | Run `bao operator unseal` with share key |
| OIDC login fails | Verify Keycloak `openbao-oidc` client is enabled |
| 403 Forbidden | Check if token's policies match the requested path |
| Token expired | Generate new token: `bao token create` |
| Raft data corrupted | Restore from backup snapshot |
| Nginx 502 | Verify OpenBao container is running on port 8200 |

## References

- Skill: `openbao-admin` (Hermes skill for programmatic access)
- Ansible Role: `openbao`
- Docs: `shared/docs/KEYCLOAK.md` (authentication), `shared/docs/SECURITY_REPORT.md` (audit trail)
- OpenBao CLI: `bao --help`
- OpenBao Status: `bao status`
- Health Check: `curl https://vault.iacgenie.com/v1/sys/health`
