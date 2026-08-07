# Keycloak Deployment Guide

## Overview

Keycloak 26.0 provides IAM/SSO for the iacgenie platform with multi-tenant realm support.

### Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Nginx      │────▶│   Keycloak   │────▶│  PostgreSQL  │
│ :443 (TLS)   │     │  :8080       │     │  :5432       │
│ auth.iacgenie│     │              │     │  keycloak db │
└──────────────┘     └──────────────┘     └──────────────┘
```

### Realms & Clients

| Realm      | Clients                          | Purpose                  |
|------------|----------------------------------|--------------------------|
| `master`   | (system)                         | Keycloak admin console   |
| `iacgenie` | iacgenie-platform, gitea, searxng| Platform SSO             |
| `lightserp`| lightserp-webui, lightserp-api, openbao-oidc | AI Platform SSO |

### Services

| Service    | Port  | Protocol | Binding      |
|------------|-------|----------|--------------|
| Keycloak   | 8080  | HTTP     | 127.0.0.1:8083 (host) |
| PostgreSQL | 5432  | TCP      | 127.0.0.1:5432 |
| Nginx      | 443   | HTTPS    | 0.0.0.0:443 |

---

## Deployment

### Prerequisites

1. PostgreSQL running (service `iacgenie_postgres`)
2. Docker + Docker Compose installed
3. Cloudflare Tunnel configured (`auth.iacgenie.com`)
4. OpenBao running with secret at `iacgenie/kv/keycloak/admin_password`

### Deploy via Ansible

```bash
cd /Users/manjunathkanavi/iacgenie-platform/infra/ansible
ansible-playbook -i hosts.ini site.yml --limit=192.168.0.118
```

This will:
1. Generate `.env.*` files from Ansible variables
2. Render `docker-compose.yml` from template
3. Deploy keycloak.conf configuration
4. Build + start containers
5. Provision realms and clients
6. Configure OpenBao OIDC integration

### Deploy Manually

```bash
# 1. Clean old H2 data (if migrating from H2)
sudo rm -rf /home/mkanavi/docker/iacgenie/data/keycloak/h2/
sudo rm -rf /home/mkanavi/docker/iacgenie/data/keycloak/transaction-logs/

# 2. Generate env files (from Ansible variables)
cd /home/mkanavi/docker/iacgenie
# .env, .env.keycloak should already exist from Ansible

# 3. Deploy keycloak.conf
cp /path/to/keycloak.conf.j2 keycloak.conf  # rendered by Ansible

# 4. Start Keycloak
docker compose -f docker-compose.yml up -d keycloak

# 5. Wait for readiness (Keycloak needs ~60s for first boot migrations)
sleep 90
docker compose -f docker-compose.yml logs keycloak | grep "Started"

# 6. Verify
bash /path/to/infra/scripts/verify-keycloak.sh
```

---

## Security Configuration

### Password Management

Admin password is stored in OpenBao at `iacgenie/kv/keycloak/admin_password`.

**Rotate password:**
```bash
# Generate new password
NEW_PASS=$(python3 -c "import secrets; print(''.join(secrets.choice('abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789_#!') for _ in range(32)))")

# Update OpenBao
bao kv put iacgenie/kv/keycloak admin_password="$NEW_PASS"

# Restart Keycloak to pick up new password
docker compose -f docker-compose.yml up -d --force-recreate keycloak
```

### Hardening Applied

- ✅ `restart: unless-stopped` — automatic recovery
- ✅ Health check on port 8080 (30s interval, 3 retries)
- ✅ Resource limits: 2G memory, 1 CPU
- ✅ `security_opt: no-new-privileges` — container isolation
- ✅ `keycloak.conf` mounted read-only — auditability
- ✅ H2 data cleared, PostgreSQL-only mode
- ✅ Nginx rate limiting on auth endpoints (3 req/min burst=5)
- ✅ TLS termination at Nginx level
- ✅ All internal ports bound to 127.0.0.1

---

## Database Driver

Keycloak is configured with PostgreSQL driver:

- `--db=postgres` in container command
- Database: `keycloak` on PostgreSQL 15
- Volume: `/home/mkanavi/docker/iacgenie/data/keycloak:/opt/keycloak/data`
- H2 data removed — no embedded database fallback

### Driver Verification

```bash
# Inside the container:
docker exec -it iacgenie_keycloak kc.sh show-config | grep -i "db-"

# Expected output:
# db=postgres
# db-url=jdbc:postgresql://postgres:5432/keycloak
```

---

## Verification

### Automated Checks

```bash
bash /home/mkanavi/scripts/verify-keycloak.sh
```

Tests:
1. Admin CLI login
2. Admin console availability
3. Health endpoint (`/health/ready`)
4. Realm availability (iacgenie, lightserp)
5. Client configuration
6. Database driver verification

### Manual Checks

```bash
# Container status
docker ps | grep keycloak

# Logs
docker logs iacgenie_keycloak

# Health check
curl -s http://127.0.0.1:8083/health/ready | jq .

# Admin login
TOKEN=$(curl -s -X POST http://127.0.0.1:8083/realms/master/protocol/openid-connect/token \
  -d "grant_type=password" \
  -d "username=admin" \
  -d "password=$KC_PASS" \
  -d "client_id=admin-cli" | jq -r .access_token)

echo "Token: ${TOKEN:0:20}..."

# List realms
curl -s -H "Authorization: Bearer *** 2>/dev/null | jq .[].id

# List clients in iacgenie realm
curl -s -H "Authorization: Bearer *** 2>/dev/null | jq '.[].clientId'
```

---

## Troubleshooting

### "somethingWentWrongDescription" Error

**Cause:** Keycloak built with H2 driver + runtime `--db postgres` override conflict
**Fix:** Ensure `--db=postgres` is in the command line and H2 data is cleared

```bash
docker compose down keycloak
rm -rf /home/mkanavi/docker/iacgenie/data/keycloak/h2/
docker compose up -d keycloak
```

### Realm Data Missing After Rebuild

**Cause:** Realm was provisioned into H2 database, lost after rebuild
**Fix:** Re-run the keycloak_realm provisioning

```bash
# Via Ansible
ansible-playbook -i hosts.ini site.yml --limit=192.168.0.118 --tags=keycloak_realm

# Or manually
bash /home/mkanavi/scripts/keycloak-provision.sh
```

### Keycloak Not Starting

```bash
# Check config
docker exec iacgenie_keycloak cat /opt/keycloak/conf/keycloak.conf

# Check data dir permissions
ls -la /home/mkanavi/docker/iacgenie/data/keycloak/

# Common fix: ensure overlay2 permissions
chmod 777 /home/mkanavi/docker/iacgenie/data/keycloak/
docker compose restart keycloak
```

---

## Maintenance

### Backup

```bash
# Keycloak data backup
tar czf /backup/keycloak-data-$(date +%Y%m%d).tar.gz \
  /home/mkanavi/docker/iacgenie/data/keycloak/
```

### Upgrade

```bash
# 1. Pull new image
docker pull quay.io/keycloak/keycloak:TAG

# 2. Stop current
docker compose down keycloak

# 3. Remove data (if major version upgrade)
rm -rf /home/mkanavi/docker/iacgenie/data/keycloak/*

# 4. Start with new image
docker compose up -d keycloak
```

### Log Rotation

Keycloak logs are Docker-managed. Configure Docker log rotation:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
```
