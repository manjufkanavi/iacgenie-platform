# LightSerp Secrets Management

## Overview

LightSerp uses **OpenBao** (self-hosted secrets management) for credential storage and access. Sensitive configuration data — API keys, database credentials, service tokens — are stored in OpenBao and consumed by LightSerp via its service token.

## Architecture

```
┌──────────────────────────────────────────────┐
│                   LightSerp                   │
│            iacgenie_network                   │
│ ┌────────────┐  ┌──────────────────┐         │
│ │ LightSerp   │  │ OpenBao          │         │
│ │ Container   │──│ vault.iacgenie   │         │
│ │ (port 3000) │  │ .com             │         │
│ └────────────┘  └──────────────────┘         │
│                           ↑                   │
│                    Cloudflare Tunnel           │
└──────────────────────────────────────────────┘
```

**Note**: LightSerp runs on its own Docker network (`lightserp_net`). It accesses OpenBao via the external URL `https://vault.iacgenie.com/v1` rather than the internal network.

## OpenBao Configuration

### Service Details

| Property | Value |
|----------|-------|
| OpenBao Host | vault.iacgenie.com |
| OpenBao Internal URL | https://127.0.0.1:8200 |
| OpenBao Container | iacgenie-openbao |
| OpenBao Image | quay.io/openbao/openbao:2.6.0 |
| Server IP | 192.168.0.118 |

### Accessing OpenBao

```bash
# From inside the VM (OpenBao container)
curl -sfk https://127.0.0.1:8200/v1/sys/health

# From outside the VM (via Cloudflare tunnel)
curl -sk https://vault.iacgenie.com/v1/sys/health
```

## Authentication

LightSerp uses **token-based authentication** with the service token:

```python
import os
import requests

def get_lightsper_secrets():
    """Read secrets from OpenBao."""
    token = os.environ.get("LIGHTSERP_OPENBAO_TOKEN")
    if not token:
        raise ValueError("LIGHTSERP_OPENBAO_TOKEN not set")
    
    response = requests.get(
        "https://vault.iacgenie.com/v1/lightserp/kv/data/lightserp",
        headers={"X-Vault-Token": token}
    )
    response.raise_for_status()
    return response.json()["data"]["data"]

# Usage
secrets = get_lightsper_secrets()
print(secrets)
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LIGHTSERP_OPENBAO_ADDR` | OpenBao address | `https://vault.iacgenie.com/v1` |
| `LIGHTSERP_OPENBAO_TOKEN` | Service token | (stored in `.env`) |

### `.env` Configuration

```bash
# LightSerp .env
LIGHTSERP_OPENBAO_ADDR=https://vault.iacgenie.com/v1
LIGHTSERP_OPENBAO_TOKEN=${LIGHTSERP...n
```

## Secret Paths

LightSerp reads secrets from the `lightserp/kv` KV mount:

| Secret Type | KV Path |
|-------------|---------|
| Service config | `lightserp/kv/data/lightserp` |
| Database credentials | `lightserp/kv/data/lightserp/db_creds` |
| API keys | `lightserp/kv/data/lightserp/api_keys` |
| SMTP credentials | `lightserp/kv/data/lightserp/smtp` |

## Terraform Configuration

```hcl
# OpenBao Provider
provider "openbao" {
  address = "https://vault.iacgenie.com/v1"
  token   = var.openbao_token
}

# Read a secret
data "openbao_secret" "lightsper_config" {
  path = "lightserp/kv/data/lightserp"
}

# Use secret in application config
resource "lightserp_config" "main" {
  api_key = data.openbao_secret.lightsper_config.data["api_key"]
  db_host = data.openbao_secret.lightsper_config.data["db_host"]
}
```

## Service Token Management

### Token Lifecycle

1. **Generation**: Service tokens are created by the admin via the OpenBao API
2. **Storage**: Tokens are stored in `/home/mkanavi/docker/iacgenie/openbao_data/service_tokens/lightserp_token.txt`
3. **Distribution**: Tokens are copied to LightSerp's `.env` file
4. **Rotation**: Admin creates new token, copies to `.env`, restarts LightSerp

### Rotating Tokens

```bash
# SSH to the VM
ssh mkanavi@192.168.0.118

# Generate new token
docker exec iacgenie-openbao bao token create \
  -policy=lightserp \
  -ttl=720h

# Copy new token to LightSerp .env file
vim /home/mkanavi/docker/lightserp/.env

# Restart LightSerp
docker compose -f /home/mkanavi/docker/lightserp/docker-compose.yml restart lightserp
```

### Docker Compose Configuration

```yaml
services:
  lightserp:
    image: lightsper:latest
    networks:
      - lightserp_net
    environment:
      - LIGHTSERP_OPENBAO_ADDR=https://vault.iacgenie.com/v1
      - LIGHTSERP_OPENBAO_TOKEN=${LIGHTSERP_TOKEN}
    volumes:
      - ./data:/app/data
```

## Security Best Practices

1. **Token Rotation**: Rotate service tokens every 90 days
2. **Access Control**: Use scoped policies (lightserp) — never use admin tokens
3. **Secret Injection**: Never log secrets; use environment variables
4. **Audit**: Monitor OpenBao audit logs at `/home/mkanavi/docker/iacgenie/openbao_data/audit/`
5. **Backup**: Ensure OpenBao RAFT snapshots are backed up regularly
6. **Network Isolation**: LightSerp uses a separate Docker network from the main IacGenie stack

## Related Documents

- [OpenBao Complete Reference](../docs/openbao-reference.md)
- [Shared Infrastructure](./shared-infrastructure.md)
