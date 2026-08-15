# IacGenie Platform — OpenBao Secrets Structure

> **Last Updated**: 2026-08-16  
> **OpenBao Version**: 2.6.0  
> **Raft Storage**: `/home/mkanavi/docker/iacgenie/openbao_raft`  
> **Listener**: `127.0.0.1:8200` (HTTPS via Cloudflare Tunnel)  
> **URL**: https://vault.iacgenie.com

---

## KV Engines

| Engine | Path | Version | Purpose |
|--------|------|---------|---------|
| `iacgenie/kv` | `iacgenie/kv/` | v2 | Platform secrets |
| `lightserp/kv` | `lightserp/kv/` | v2 | LightSerp secrets |
| `terraform/kv` | `terraform/kv/` | v2 | Terraform state secrets |

---

## Secret Paths

### iacgenie/kv/

```
iacgenie/kv/
├── platform/
│   ├── jwt_secret          # JWT signing secret
│   ├── api_key             # Platform API key
│   └── encryption_key      # Data encryption key
├── postgres/
│   ├── username            # DB username: lightsrp
│   └── password            # DB password
├── redis/
│   └── password            # Redis AUTH password
├── minio/
│   ├── root_user           # MinIO access key
│   └── root_password       # MinIO secret key
├── keycloak/
│   ├── admin_password      # Keycloak admin password
│   └── client_secret       # OIDC client secret
├── openbao/
│   ├── root_token          # OpenBao root token (READ-ONLY)
│   ├── unseal_keys         # 3 unseal keys (base64)
│   ├── iacgenie_token      # Service token (30-day TTL)
│   ├── lightserp_token     # Service token (30-day TTL)
│   ├── terraform_token     # Service token (30-day TTL)
│   └── backup_token        # Backup token (30-day TTL)
├── gitea/
│   ├── admin_token         # Gitea admin token
│   └── ssh_key             # Gitea SSH deploy key
├── cloudflare/
│   ├── api_key             # Cloudflare API token
│   └── zone_id             # Cloudflare zone ID
├── nginx/
│   ├── ssl_key             # SSL private key
│   └── ssl_cert            # SSL certificate
├── monitoring/
│   ├── grafana_admin_password  # Grafana admin password
│   └── alertmanager_token    # Alertmanager auth token
└── git/
    ├── github_token        # GitHub PAT
    └── gitea_token         # Gitea PAT
```

### lightserp/kv/

```
lightserp/kv/
├── api_key                 # LightSerp API key
├── gemini_key              # Google Gemini API key
├── claude_key              # Anthropic Claude API key
├── mistral_key             # Mistral API key
├── openai_key              # OpenAI API key
├── redis_password          # Redis password (shared)
├── nsq_auth_token          # NSQ authentication token
└── searxng_api_key         # SearXNG API key (if required)
```

---

## Token Management

### Service Tokens (30-day TTL)

| Token | Path | TTL | Purpose |
|-------|------|-----|---------|
| `iacgenie_token` | `iacgenie/kv/openbao/iacgenie_token` | 30 days | IacGenie platform service |
| `lightserp_token` | `iacgenie/kv/openbao/lightserp_token` | 30 days | LightSerp service |
| `terraform_token` | `iacgenie/kv/openbao/terraform_token` | 30 days | Terraform state access |
| `backup_token` | `iacgenie/kv/openbao/backup_token` | 30 days | Backup operations |

### Token Rotation

```bash
# Generate new token
docker exec iacgenie_openbao bao auth token create -ttl=720h -period=720h \
  -policy="iacgenie-service" > /tmp/new_token

# Update secret
docker exec iacgenie_openbao bao kv put iacgenie/kv/openbao/iacgenie_token \
  token=@/tmp/new_token

# Restart service to pick up new token
docker restart iacgenie_backend
```

---

## OpenBao Operations

### Bootstrap

```bash
# Initialize (first time only)
docker exec iacgenie_openbao bao operator init \
  -key-shares=3 \
  -key-threshold=3 \
  -format=json > /tmp/init_keys.json

# Unseal
docker exec iacgenie_openbao bao operator unseal <key1>
docker exec iacgenie_openbao bao operator unseal <key2>
docker exec iacgenie_openbao bao operator unseal <key3>
```

### Status Check

```bash
docker exec iacgenie_openbao bao status
```

### List All Secrets

```bash
# List top-level paths
docker exec iacgenie_openbao bao kv list iacgenie/kv/

# List all secrets recursively
docker exec iacgenie_openbao ba
