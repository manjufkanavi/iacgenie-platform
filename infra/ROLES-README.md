# iacgenie-platform Infrastructure Ansible Roles

This directory contains the Ansible roles for the iacgenie-platform infrastructure.

## New Roles (Phase 10.5 - Service Authentication & Routing)

### `docker-services`
Deploys the shared auth-wrapper service dashboard containers:
- **iacgenie_auth_wrapper**: OIDC auth proxy for auth.iacgenie.com
- **iacgenie_clamav**: ClamAV dashboard with Keycloak login
- **iacgenie_crowdsec**: CrowdSec dashboard with Keycloak login
- **iacgenie_pagegen**: PageGen status dashboard with Keycloak login

All use a shared Node.js/Express auth-wrapper that handles OIDC login with Keycloak and JWT cookie management.

### `grafana`
Fixes Grafana configuration:
- Sets `domain = grafana.iacgenie.com` in grafana.ini
- Sets `root_url = https://grafana.iacgenie.com/`
- Restarts Grafana container

### `openbao`
Implements auto-unseal for OpenBao:
- Deploys `auto-unseal.sh` script
- Creates systemd service for automatic unseal on boot
- Uses unseal keys from `init_keys.json` (threshold=2)

## Existing Roles

- **nginx**: Unified nginx config with all vHosts
- **cloudflare_tunnel**: Cloudflare Tunnel configuration
- **keycloak**: Keycloak 26.0 deployment
- **openbao**: OpenBao 2.6.0 deployment (Core config)
- **monitoring**: Prometheus + Loki stack
- **security**: ClamAV + CrowdSec (core containers)
- And 30+ other roles for the full platform

## Usage

```bash
# Deploy all services
ansible-playbook ansible/playbooks/services.yml -i ansible/inventory/hosts.yml

# Deploy only specific roles
ansible-playbook ansible/playbooks/services.yml -i ansible/inventory/hosts.yml --tags "docker-services,grafana"
```

## Variables

Configure in `ansible/inventory/group_vars/all.yml` or via `--extra-vars`:
- `iacgenie_docker_path`: Docker compose root (default: `/home/mkanavi/docker/iacgenie`)
- `keycloak_auth_wrapper_secret`: Keycloak OIDC client secret for shared auth
- `grafana_domain`: Grafana domain (default: `grafana.iacgenie.com`)
- `grafana_root_url`: Grafana root URL (default: `https://grafana.iacgenie.com/`)
