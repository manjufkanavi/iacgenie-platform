# OpenBao Runbook

## Overview

OpenBao 2.6.0 is the centralized secrets management system for all IaCGenie platform services.

| Property | Value |
|----------|-------|
| Version | 2.6.0 |
| Container | `iacgenie_openbao` |
| API Address | `http://127.0.0.1:8200` |
| UI Address | `http://127.0.0.1:8200/ui` |
| Data Dir | `/home/mkanavi/docker/iacgenie/data/openbao_raft/` |
| Raft Dir | `/home/mkanavi/docker/iacgenie/data/openbao_raft/raft/` |
| Config | `/home/mkanavi/docker/iacgenie/data/openbao_raft/openbao-prod.hcl` |
| Init Keys | `/home/mkanavi/docker/iacgenie/data/openbao_raft/init_keys.json` |
| Tokens | `/home/mkanavi/docker/iacgenie/data/openbao_raft/service_tokens/` |

---

## Quick Health Check

```bash
# SSH to VM
ssh mkanavi@192.168.0.118

# Check container status
docker ps | grep openbao

# Check health via API
curl -s http://127.0.0.1:8200/v1/sys/health | python3 -m json.tool

# Expected: {"initialized": true, "sealed": false, "standby": false, ...}

# Check seal status
docker exec iacgenie_openbao wget -q -O - http://127.0.0.1:8200/v1/sys/health | python3 -c "import sys,json; d=json.load(sys.stdin); print('sealed:', d.get('sealed'))"
```

---

## Common Operations

### 1. OpenBao is Sealed — Manual Unseal

```bash
ssh mkanavi@192.168.0.118

# Read unseal keys
cat /home/mkanavi/docker/iacgenie/data/openbao_raft/init_keys.json | python3 -c "import sys,json; print('\n'.join(json.load(sys.stdin)['unseal_keys_b64']))"

# Unseal (run each key, threshold is 3 of 5)
docker exec iacgenie_openbao wget -q -O - --post-data='' --header="X-Vault-Token: $(cat /home/mkanavi/docker/iacgenie/.env.openbao | grep OPENBAO_ROOT_TOKEN | cut -d= -f2)" http://127.0.0.1:8200/v1/sys/unseal

# Or use the API directly:
KEY="nBMwFnI5HDKug2jlvtWTu5dP6XN7lz+/scoinmasAA02"
curl -s -X PUT http://127.0.0.1:8200/v1/sys/unseal \
  -H "X-Vault-Token: s.oDgguSgbx5rqpccCkkSI93BO" \
  -H "Content-Type: application/json" \
  -d "{\"key\": \"$KEY\"}"
```

### 2. Rotate Service Tokens

```bash
ssh mkanavi@192.168.0.118

# View current tokens
ls -la /home/mkanavi/docker/iacgenie/data/openbao_raft/service_tokens/

# Run token lifecycle playbook (from ansible dir)
ansible-playbook -i inventory/hosts.ini -b playbooks/openbao-token-lifecycle.yml

# Or renew a specific token:
TOKEN=$(cat /home/mkanavi/docker/iacgenie/data/openbao_raft/service_tokens/iacgenie_token.txt)
curl -s -X POST http://127.0.0.1:8200/v1/auth/token/renew \
  -H "X-Vault-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"increment": "720h"}'
```

### 3. Revoke a Service Token

```bash
# Revoke with orphan children
TOKEN=$(cat /home/mkanavi/docker/iacgenie/data/openbao_raft/service_tokens/lightserp_token.txt)
ROOT=$(cat /home/mkanavi/docker/iacgenie/.env.openbao | grep OPENBAO_ROOT_TOKEN | cut -d= -f2)

curl -s -X POST http://127.0.0.1:8200/v1/auth/token/revoke-orphan \
  -H "X-Vault-Token: $ROOT" \
  -H "Content-Type: application/json" \
  -d "{\"token\": \"$TOKEN\"}"
```

### 4. Read a Secret

```bash
# From ansible dir, read via API
ROOT=$(cat /home/mkanavi/docker/iacgenie/.env.openbao | grep OPENBAO_ROOT_TOKEN | cut -d= -f2)

# Read IaCGenie PostgreSQL credentials
curl -s http://127.0.0.1:8200/v1/iacgenie/kv/data/postgres \
  -H "X-Vault-Token: $ROOT" | python3 -m json.tool

# Read LightSerp API secret
curl -s http://127.0.0.1:8200/v1/lightserp/kv/data/api \
  -H "X-Vault-Token: $ROOT" | python3 -m json.tool
```

### 5. Add a New Secret

```bash
ROOT=$(cat /home/mkanavi/docker/iacgenie/.env.openbao | grep OPENBAO_ROOT_TOKEN | cut -d= -f2)

# Write to iacgenie/kv
curl -s -X POST http://127.0.0.1:8200/v1/iacgenie/kv/data/new_service \
  -H "X-Vault-Token: $ROOT" \
  -H "Content-Type: application/json" \
  -d '{"data": {"api_key": "new-secret-value", "url": "http://new-service:8080"}}'

# Write to lightserp/kv
curl -s -X POST http://127.0.0.1:8200/v1/lightserp/kv/data/new_service \
  -H "X-Vault-Token: $ROOT" \
  -H "Content-Type: application/json" \
  -d '{"data": {"api_key": "new-secret-value"}}'
```

### 6. List All KV Secrets

```bash
ROOT=$(cat /home/mkanavi/docker/iacgenie/.env.openbao | grep OPENBAO_ROOT_TOKEN | cut -d= -f2)

# List iacgenie/kv
curl -s http://127.0.0.1:8200/v1/iacgenie/kv/metadata/ \
  -H "X-Vault-Token: $ROOT" | python3 -m json.tool

# List lightserp/kv
curl -s http://127.0.0.1:8200/v1/lightserp/kv/metadata/ \
  -H "X-Vault-Token: $ROOT" | python3 -m json.tool
```

### 7. Backup OpenBao Data

```bash
ssh mkanavi@192.168.0.118

# Raft snapshot (consistent, online)
docker exec iacgenie_openbao bao operator raft snapshot save /tmp/openbao-snapshot.latest

# Copy to host backup location
docker cp iacgenie_openbao:/tmp/openbao-snapshot.latest /home/mkanavi/docker/iacgenie/backups/openbao-snapshot.latest

# Or use the existing backup directory
ls -la /home/mkanavi/docker/iacgenie/data/openbao_raft/backups/
```

### 8. Restore from Snapshot

```bash
ssh mkanavi@192.168.0.118

# Copy snapshot into container
docker cp /home/mkanavi/docker/iacgenie/backups/openbao-snapshot.latest iacgenie_openbao:/tmp/openbao-snapshot.latest

# Restore
docker exec iacgenie_openbao bao operator raft restore /tmp/openbao-snapshot.latest
```

### 9. Check Active Tokens

```bash
ROOT=$(cat /home/mkanavi/docker/iacgenie/.env.openbao | grep OPENBAO_ROOT_TOKEN | cut -d= -f2)

# List all active token accessors
curl -s http://127.0.0.1:8200/v1/auth/token/accessors \
  -H "X-Vault-Token: $ROOT" | python3 -m json.tool

# Lookup specific token
TOKEN="hvs.CAES..."
curl -s http://127.0.0.1:8200/v1/auth/token/lookup \
  -H "X-Vault-Token: $ROOT" \
  -d "token=$TOKEN" | python3 -m json.tool
```

---

## Policies

| Policy | Scope | Used By |
|--------|-------|---------|
| `admin` | Full read+write `*` | Legacy admin, bootstrap scripts |
| `platform-admin` | Full sys+all KV, sudo | Platform admins, automation |
| `iacgenie-service` | Read `iacgenie/*` | IaCGenie app, backup token |
| `lightserp-service` | Read `lightserp/*` | LightSerp API, WebUI |
| `terraform-service` | Read `terraform/*` | Terraform provider, CI/CD |

### Applying a New Policy

```bash
# Write policy file
cat > /home/mkanavi/docker/iacgenie/data/openbao_raft/policies/my-policy.hcl << 'EOF'
path "myorg/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
EOF

# Apply via API
ROOT=$(cat /home/mkanavi/docker/iacgenie/.env.openbao | grep OPENBAO_ROOT_TOKEN | cut -d= -f2)
curl -s -X PUT http://127.0.0.1:8200/v1/sys/policies/acl/my-policy \
  -H "X-Vault-Token: $ROOT" \
  -H "Content-Type: application/json" \
  -d "{\"policy\": \"$(cat /home/mkanavi/docker/iacgenie/data/openbao_raft/policies/my-policy.hcl)\"}"
```

---

## Ansible Operations

### Bootstrap / Re-initialize

```bash
cd /home/mkanavi/iacgenie-platform/infra/ansible
ansible-playbook -i inventory/hosts.ini -b playbooks/services.yml
```

### Token Lifecycle (rotate/audit)

```bash
ansible-playbook -i inventory/hosts.ini -b playbooks/openbao-token-lifecycle.yml
```

### Post-Deploy Verification

```bash
ansible-playbook -i inventory/hosts.ini -b playbooks/post-deploy.yml
```

---

## Troubleshooting

### Health check shows `unhealthy`

The Docker health check uses Python to parse the JSON health response. If it fails:

```bash
# Manual health check
curl -s http://127.0.0.1:8200/v1/sys/health | python3 -m json.tool

# Check if sealed
docker logs iacgenie_openbao 2>&1 | grep -i seal

# Restart OpenBao container
cd /home/mkanavi/docker/iacgenie
docker compose stop openbao
docker compose rm -f openbao
docker compose up -d openbao
```

### Container won't start

```bash
# Check logs
docker logs iacgenie_openbao 2>&1 | tail -50

# Verify config file
docker exec iacgenie_openbao cat /openbao/storage/openbao-prod.hcl

# Check data dir permissions
ls -la /home/mkanavi/docker/iacgenie/data/openbao_raft/
ls -la /home/mkanavi/docker/iacgenie/data/openbao_raft/raft/
```

### Token is revoked / expired

```bash
# Re-read from file
cat /home/mkanavi/docker/iacgenie/data/openbao_raft/service_tokens/iacgenie_token.txt

# Re-generate via Ansible (run full bootstrap)
ansible-playbook -i inventory/hosts.ini -b roles/openbao/
```

### KV engine not found

```bash
# List all engines
ROOT=$(cat /home/mkanavi/docker/iacgenie/.env.openbao | grep OPENBAO_ROOT_TOKEN | cut -d= -f2)
curl -s http://127.0.0.1:8200/v1/sys/mounts \
  -H "X-Vault-Token: $ROOT" | python3 -m json.tool

# Enable missing engine (example: terraform/kv)
curl -s -X POST http://127.0.0.1:8200/v1/sys/mounts/terraform/kv \
  -H "X-Vault-Token: $ROOT" \
  -H "Content-Type: application/json" \
  -d '{"type": "kv", "options": {"version": "2"}}'
```

### Can't unseal — corrupted init_keys.json

If the unseal keys in `init_keys.json` are corrupted (33-35 bytes instead of 32):

1. Re-initialize OpenBao:
   ```bash
   docker exec iacgenie_openbao bao operator reinit
   ```
2. Save the new keys from the output
3. Update `init_keys.json` on the host
4. Unseal with the new keys

### Raft directory has wrong permissions

```bash
ssh mkanavi@192.168.0.118

# Fix directory permissions
chmod 750 /home/mkanavi/docker/iacgenie/data/openbao_raft/
chmod 750 /home/mkanavi/docker/iacgenie/data/openbao_raft/raft/
chmod 750 /home/mkanavi/docker/iacgenie/data/openbao_raft/backups/
chmod 750 /home/mkanavi/docker/iacgenie/data/openbao_raft/service_tokens/
chown -R mkanavi:mkanavi /home/mkanavi/docker/iacgenie/data/openbao_raft/
```

### vault.iacgenie.com "Too Many Redirects"

**Symptom:** Browser shows "too many redirects" when accessing `vault.iacgenie.com`.

**Root Cause:** Cloudflare tunnel routes `vault.iacgenie.com` → `http://127.0.0.1:8200` (direct to OpenBao).
Without a matching nginx server block, traffic hits the default server → `return 301 https://$host$request_uri` → Cloudflare → loop.

**Fix:** Add `vault.iacgenie.com` blocks to both HTTP (cloudflared passthrough) and HTTPS (TLS termination) sections in the nginx template, and route the tunnel through nginx:80 instead of directly to OpenBao.

```bash
# Ansible: Ensure roles are updated
cd /Users/manjunathkanavi/iacgenie-platform/infra/ansible

# Check current config has vault block
grep -c "vault.iacgenie.com" roles/nginx/templates/reverse-proxy.conf.j2
# Should return: 2 (one HTTP, one HTTPS block)

# Check tunnel vars route through nginx
grep "vault.iacgenie.com" -A1 roles/cloudflare_tunnel/vars/main.yml
# service should be http://127.0.0.1:80 (NOT 127.0.0.1:8200)

# Deploy
ansible-playbook -i inventory/hosts.ini -b playbooks/services.yml

# Verify
ssh mkanavi@192.168.0.118
curl -sI http://127.0.0.1/v1/sys/health | grep -E "HTTP|location:"
# Should return 200 OK (not 301 redirect)
```

**Architecture:**
```
Browser → Cloudflare Proxy → nginx:443 (TLS terminate) → nginx:8080 → OpenBao:8200
Browser → Cloudflare Tunnel → nginx:80 (passthrough) → OpenBao:8200
```

**Key changes:**
1. HTTP block: `proxy_pass http://127.0.0.1:8200` with `X-Forwarded-Proto: $scheme` — no redirect
2. HTTPS block: TLS terminated at nginx, proxies to OpenBao over HTTP with `X-Forwarded-Proto: https`
3. Cloudflare Tunnel: `service: http://127.0.0.1:80` (through nginx, NOT direct OpenBao)
4. TLS certs: `/etc/letsencrypt/live/vault.iacgenie.com/`

---

## Multi-Tenant KV Structure

```
iacgenie/
  kv/
    data/
      postgres/     # username, host, port, password
      redis/        # host, port, password
      minio/        # access_key, secret_key, endpoint
      keycloak/     # admin_user, admin_password, db_password, db_host, db_port, db_name
      gitea/        # db_password, smtp_addr, smtp_port, smtp_user, smtp_pass, smtp_from
      openbao/      # root_token, addr, data_dir, storage_type
      searxng/      # secret, port
      lightserp/    # api_secret, api_url
      pagezen/      # api_url, api_secret, port
      nsqd/         # data_path, tcp_port, http_port

lightserp/
  kv/
    data/
      postgres/     # username, host, port
      redis/        # host, port
      minio/        # access_key, secret_key, endpoint
      searxng/      # secret, port
      api/          # api_secret, api_url

terraform/
  kv/
    data/
      postgres/     # username, host, port, password
      openbao/      # addr
```

---

## Audit Log

OpenBao audit logging is enabled and writes to `/openbao/audit/audit.log` inside the container.

To view recent audit events:
```bash
docker exec iacgenie_openbao tail -20 /openbao/audit/audit.log
```

To disable audit (for debugging):
```bash
ROOT=$(cat /home/mkanavi/docker/iacgenie/.env.openbao | grep OPENBAO_ROOT_TOKEN | cut -d= -f2)
curl -s -X DELETE http://127.0.0.1:8200/v1/sys/audit/file \
  -H "X-Vault-Token: $ROOT"
```

---

## Reference

- OpenBao Docs: https://openbao.org/docs/
- Raft Storage: https://openbao.org/docs/configuration/storage/raft
- KV v2 Secrets: https://openbao.org/docs/secrets/kv/kv-v2
- Token Auth: https://openbao.org/docs/auth/token
