# Keycloak — Centralized Identity & Access Management

**Version:** 1.0.0  
**Last Updated:** 2026-08-07  
**Role:** Single authentication backend for all IacGenie platform services  
**Authentication Method:** OpenID Connect (OIDC) + Keycloak Admin REST API

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                     Keycloak (iacgenie_keycloak)              │
│                     Port: 8083                               │
│                     Container: iacgenie_keycloak             │
└──────────────────────────────────────────────────────────────┘
         ▲                                      ▲
         │                                      │
   /realms/iacgenie                    /realms/lightserp
         │                                      │
    ┌────┼────┐                            ┌────┼──────────┐
    │    │    │                            │    │          │
  iacgenie  gitea          lightserp      lightserp  openbao-
platform  (Git)             (API)        webui   oidc (Vault)
    │    │    │                            │    │          │
    └────┼────┘                            └────┼──────────┘
         │                                      │
         ▼                                      ▼
  admin.iacgenie.com              vault.iacgenie.com
  gitea.iacgenie.com              app.iacgenie.com /
  search.iacgenie.com             lightserp.iacgenie.com
```

## Deployment

| Component | Value |
|-----------|-------|
| Version | Keycloak 26.0 |
| Container | `iacgenie_keycloak` |
| Published Port | `8083` |
| Admin URL | `http://127.0.0.1:8083` |
| Health Endpoint | `http://127.0.0.1:8083/health/ready` |
| Ansible Role | `keycloak` (container setup) + `keycloak_realm` (realm/clients) |

## Authentication

### Admin Login
```bash
# Access Keycloak Admin Console
curl -s -X POST http://127.0.0.1:8083/realms/master/protocol/openid-connect/token \
  -d "grant_type=password&username=admin&password=hAaIa219fq5VzAP81SDyNuBV&client_id=admin-cli"
```

### Service Authentication (Client Credentials)
```bash
curl -s -X POST http://127.0.0.1:8083/realms/{realm}/protocol/openid-connect/token \
  -d "grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}"
```

## Realms & Clients

### iacgenie Realm

| Client | Secret | Redirect URIs | Service Accounts |
|--------|--------|---------------|------------------|
| `iacgenie-platform` | `fHjGjbMqf1xiJThpv1JftTjA79dvp01y` | `https://admin.iacgenie.com/*`, `https://iacgenie.com/*` | ✅ Yes |
| `gitea` | `DmDOIo0Cbw76jbr67BpRhmpERPb4PyZv` | `https://gitea.iacgenie.com/user/oauth2/gitea` | ❌ No |
| `searxng` | `jvnJcywoiySjkDrgEhwjDSV9KBZb26Eu` | `https://search.iacgenie.com/*` | ❌ No |

### lightserp Realm

| Client | Secret | Redirect URIs | Service Accounts |
|--------|--------|---------------|------------------|
| `lightserp-webui` | `X3mPK9L3WNwU3F8iDBWxFp2VZLlwfbYZ` | `https://lightserp.iacgenie.com/*`, `https://app.iacgenie.com/*` | ❌ No |
| `lightserp-api` | `4gDElECb74VEKbmKE6317Qg6UEZTa1hC` | `https://api.iacgenie.com/*` | ✅ Yes |
| `openbao-oidc` | `2AMmiNh62NQGzwmBiECfNWyIed1hbf04` | `https://vault.iacgenie.com/*` | ✅ Yes |

## Roles

### iacgenie Realm Roles

| Role | Description |
|------|-------------|
| `platform-admin` | Full platform administrator — access all projects |
| `project-admin` | Project-level administrator — manage own project members |
| `project-member` | Project read-only member |

### lightserp Realm Roles

| Role | Description | OpenBao Access |
|------|-------------|----------------|
| `platform-admin` | Full platform administrator — access all projects | Admin policies |
| `openbao-admin` | OpenBao vault administrator | Admin policies |
| `project-admin` | Project-level administrator — manage own project members | Project KV access |
| `project-member` | Project read-only member | KV read-only |
| `openbao-service-read` | Read-only OpenBao service access | Read-only all KV |

## RBAC Model

### Admin-Only Write Access
- **Only `platform-admin` and `openbao-admin` roles** can create/update/delete users, clients, and realm configurations
- Service accounts (`iacgenie-platform`, `lightserp-api`, `openbao-oidc`) are configured via Ansible, not through Keycloak console

### Read-Only for Project Users
- `project-member` role: read-only access to project resources
- `openbao-service-read` role: read-only access to all KV engines in OpenBao

### RBAC Enforcement
- Keycloak: FGAA (Fine-Grained Authorization) with realm roles + client roles
- OpenBao: OIDC role bindings map Keycloak roles to OpenBao policies
- Policy: `platform-admin` → `admin` (full), `openbao-service-read` → `openbao-service-read` (read-only)

## Nginx Routing

| Domain | Backend Port | Purpose |
|--------|-------------|---------|
| `auth.iacgenie.com` | 8083 | Keycloak (HTTPS) |
| `gitea.iacgenie.com` | 3000 | Gitea (not Keycloak) |
| `search.iacgenie.com` | 8082 | SearXNG |
| `app.iacgenie.com` | 3001 | LightSerp WebUI |
| `api.iacgenie.com` | 8000 | LightSerp API |

## Keycloak Admin API Cheat Sheet

```bash
KC="http://127.0.0.1:8083"

# Get admin token
TOKEN=$(curl -s -X POST "$KC/realms/master/protocol/openid-connect/token" \
  -d "grant_type=password&username=admin&password=hAaIa219fq5VzAP81SDyNuBV&client_id=admin-cli" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# List all realms
curl -s -H "Authorization: Bearer $TOKEN" "$KC/admin/realms"

# List clients in a realm
curl -s -H "Authorization: Bearer $TOKEN" "$KC/admin/realms/iacgenie/clients?search=iacgenie-platform"

# Get client secret
curl -s -X GET -H "Authorization: Bearer $TOKEN" "$KC/admin/realms/iacgenie/clients/{clientId}/client-secret"

# Create realm
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"realm":"new-realm","enabled":true}' "$KC/admin/realms"

# Create client
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"clientId":"new-client","name":"New Client","enabled":true,"clientAuthenticatorType":"client-secret","standardFlowEnabled":true,"protocol":"openid-connect"}' \
  "$KC/admin/realms/iacgenie/clients"
```

## Ansible Deployment

```bash
# Bootstrap Keycloak container + realm provisioning
cd /Users/manjunathkanavi/iacgenie-platform/infra/ansible
ansible-playbook -i hosts playbooks/services.yml
```

## Health Checks

```bash
# Container health
ssh mkanavi@192.168.0.118 "docker inspect --format='{{.State.Health.Status}}' iacgenie_keycloak"

# HTTP health
curl -s -f http://127.0.0.1:8083/health/ready && echo "Keycloak is ready"

# Admin login test
curl -s -X POST http://127.0.0.1:8083/realms/master/protocol/openid-connect/token \
  -d "grant_type=password&username=admin&password=hAaIa219fq5VzAP81SDyNuBV&client_id=admin-cli"
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Admin login fails | Verify `hAaIa219fq5VzAP81SDyNuBV` in `.env.keycloak` |
| 401 on Admin API | Check Bearer token expiry; regenerate |
| Client not found | Verify realm is created first (`keycloak_realm` role) |
| Redirect URI mismatch | Update client `redirectUris` in Keycloak console or Ansible |
| Keycloak not healthy | Check `docker logs iacgenie_keycloak` for DB connection issues |

## References

- Skill: `keycloak-admin` (Hermes skill for programmatic access)
- Ansible Role: `keycloak` (container), `keycloak_realm` (realms/clients)
- Docs: `shared/docs/SECURITY_REPORT.md` (audit trail), `shared/docs/INFRASTRUCTURE.md` (architecture)
