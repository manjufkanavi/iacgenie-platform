---
name: openbao-secrets
description: Comprehensive guide for managing secrets in the IaCGenie platform using OpenBao (HashiCorp Vault fork). Covers architecture, KV paths, RBAC policies, token lifecycle, TypeScript/Python clients, troubleshooting, and operational runbooks.
---

### Architecture
- OpenBao v2.6.0 with Raft storage on VM 192.168.0.118:8200
- External URL: https://vault.iacgenie.com
- Container: `iacgenie-openbao` in Docker Compose
- Shamir unseal (3 of 5 keys)

### KV-v2 Secret Engines
- `iacgenie/kv` — IaCGenie platform secrets
- `lightserp/kv` — LightSerp service secrets
- `terraform/kv` — Terraform/IaC secrets

### Complete Secret Paths Map

#### iacgenie/kv paths:
| Path | Keys | Used By |
|---|---|---|
| `iacgenie/kv/data/postgres` | username, host, port, password | Backend |
| `iacgenie/kv/data/redis` | host, port, password | Backend |
| `iacgenie/kv/data/minio` | access_key, secret_key, endpoint | Backend |
| `iacgenie/kv/data/keycloak` | admin_user, admin_password, db_password, db_host, db_port, db_name | Backend |
| `iacgenie/kv/data/gitea` | db_password, smtp_* | Backend |
| `iacgenie/kv/data/openbao` | root_token, addr, data_dir, storage_type | Admin |
| `iacgenie/kv/data/searxng` | secret, port | Backend |
| `iacgenie/kv/data/lightserp` | api_secret, api_url | Backend |
| `iacgenie/kv/data/pagezen` | api_url, api_secret, port | Backend |
| `iacgenie/kv/data/nsqd` | data_path, tcp_port, http_port | Backend |
| `iacgenie/kv/data/smtp` | api_key, server, port, from_address | Backend |
| `iacgenie/kv/data/llm` | gemini_api_key, anthropic_api_key, openai_api_key | Backend |
| `iacgenie/kv/data/jwt` | secret, issuer, audience | Backend |
| `iacgenie/kv/data/cloudflare` | tunnel_token, account_id | Infra |

#### lightserp/kv paths:
| Path | Keys | Used By |
|---|---|---|
| `lightserp/kv/data/postgres` | username, host, port, password | LightSerp API |
| `lightserp/kv/data/redis` | host, port, password | LightSerp API |
| `lightserp/kv/data/minio` | access_key, secret_key, endpoint | LightSerp API |
| `lightserp/kv/data/searxng` | secret, port | LightSerp API |
| `lightserp/kv/data/api` | api_secret, api_url | LightSerp API |
| `lightserp/kv/data/keycloak` | admin_password, db_password, url, realm, client_id, client_secret | LightSerp API |
| `lightserp/kv/data/smtp` | api_key, server, port, from_address | LightSerp API |
| `lightserp/kv/data/jwt` | secret | LightSerp API |

### RBAC Policies
| Policy | Access | Paths | For |
|---|---|---|---|
| `admin` | Full CRUD + sudo | `*` | Single admin user only |
| `platform-admin` | Read + list | `*` | Platform engineers (read-only) |
| `iacgenie-service` | Read + list | `iacgenie/kv/*` | IaCGenie backend containers |
| `lightserp-service` | Read + list | `lightserp/kv/*` | LightSerp containers |
| `terraform-service` | Read + list | `terraform/kv/*` | Terraform CI/CD |
| `openbao-service-read` | Read + list | All KV mounts | Default OIDC users, monitoring |

### Authentication Methods
1. **Token Auth** — Service tokens with 30-day TTL, stored in `/home/mkanavi/docker/iacgenie/data/openbao_raft/service_tokens/`
2. **OIDC Auth** — Keycloak integration (`openbao-oidc` client in `lightserp` realm)
3. **Kubernetes Auth** — For K8s deployments

### How Services Read Secrets

#### Python (IaCGenie Backend)
```python
from modules.secret_store.vault_client import VaultClient
from modules.secret_store.config import SecretStoreConfig

config = SecretStoreConfig.from_env()
client = VaultClient(config)
result = client.read_secret('iacgenie/kv/data/postgres')
password = result['data']['password']
```

#### TypeScript (LightServ)
```typescript
import { secrets } from './lib/secrets-provider.js';
const pgConfig = await secrets.getPostgresConfig();
// { host, port, username, password }
```

### Operational Commands
- Health check: `curl -s http://127.0.0.1:8200/v1/sys/health | jq .`
- List secrets: `bao kv list iacgenie/kv/`
- Read secret: `bao kv get iacgenie/kv/postgres`
- Unseal: `ansible-playbook -i inventory/hosts.ini playbooks/services.yml --tags openbao`
- Rotate tokens: `ansible-playbook -i inventory/hosts.ini playbooks/openbao-token-lifecycle.yml`

### Bootstrap Secrets Storage
- OpenBao root token and unseal keys → `git-secret` encrypted in repo
- Ansible Vault password → `git-secret` encrypted in repo  
- CI/CD secrets → Gitea/GitHub repository secrets

### File References
- Ansible OpenBao role: `infra/ansible/roles/openbao/`
- Python VaultClient: `platform/backend/modules/secret_store/vault_client.py`
- TypeScript OpenBao client: `lightserv/src/lib/openbao-client.ts`
- Secrets provider: `lightserv/src/lib/secrets-provider.ts`
- Bootstrap script: `infra/openbao/bootstrap.sh`
- KV bootstrap: `infra/ansible/roles/openbao/tasks/kv_bootstrap.yml`
- Docker Compose: `infra/docker-compose/docker-compose-unified.yml`
