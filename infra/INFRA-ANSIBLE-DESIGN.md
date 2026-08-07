# Ansible Infrastructure Design — Drift-Free Deployment

> **Status**: Production  
> **Last Updated**: 2026-08-08  
> **VM**: 192.168.0.118 (elementary OS 8 / Ubuntu 24.04)  
> **Scope**: All infrastructure services managed via Ansible with zero manual drift

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     VM 192.168.0.118                            │
│                                                                 │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │ Systemd     │───▶│ Docker Engine │───▶│ Docker Network   │   │
│  │ Order:      │    │              │    │ iacgenie-backend │   │
│  │ docker →    │    │              │    │ iacgenie-frontend│   │
│  │ postgres →  │    │              │    │ iacgenie-messaging│   │
│  │ keycloak →  │    │              │    │                  │   │
│  │ services →  │    │              │    │                  │   │
│  │ nginx →     │    │              │    │                  │   │
│  │ cloudflared │    │              │    │                  │   │
│  └─────────────┘    └──────────────┘    └──────────────────┘   │
│                             │         ▲         │               │
│                   ┌─────────┘         │         └─────────┐     │
│                   ▼                   │                   ▼     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Docker Compose Services (iacgenie)          │  │
│  │                                                          │  │
│  │  ┌─────────┐ ┌────────┐ ┌──────┐ ┌─────────┐ ┌────────┐│  │
│  │  │Postgres │ │ Redis  │ │ MinIO│ │ OpenBao │ │Keycloak││  │
│  │  │:5432    │ │:6379   │ │:9000 │ │ :8200   │ │:8080   ││  │
│  │  └─────────┘ └────────┘ └──────┘ └─────────┘ └────────┘│  │
│  │  ┌─────────┐ ┌────────┐ ┌────────┐ ┌─────────┐ ┌────────┐│  │
│  │  │ Gitea   │ │L.S.API │ │L.S.UI │ │PageZen  │ │SearXNG ││  │
│  │  │:3000   │ │:8000   │ │:3001  │ │:8081    │ │:8082  ││  │
│  │  └─────────┘ └────────┘ └────────┘ └─────────┘ └────────┘│  │
│  │  ┌─────────┐ ┌────────┐                                   │  │
│  │  │ NSQD    │ │MinIO-  │                                   │  │
│  │  │:4150   │ │Proxy   │                                   │  │
│  │  └─────────┘ └────────┘                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                   │                                               │
│         ┌─────────┴─────────┐                                     │
│         ▼                   ▼                                     │
│  ┌─────────────┐    ┌──────────────┐                              │
│  │ Nginx       │    │ Cloudflared  │                              │
│  │ (systemd)   │    │ (systemd x2) │                              │
│  │ Host-level  │    │  Redundant   │                              │
│  └─────────────┘    └──────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Ansible Role Structure

```
infra/ansible/
├── site.yml                          # Master playbook entry
├── playbook.yml                      # Single unified playbook (NEW)
├── inventory/
│   ├── hosts.yml                     # Inventory definition
│   └── group_vars/
│       └── all.yml                   # ALL variables (ANSIBLE_VAULT encrypted)
├── playbooks/
│   ├── bootstrap.yml                 # Server bootstrapping (redundant now)
│   └── validate.yml                  # Post-deploy validation (redundant now)
└── roles/
    ├── common/                       # Prerequisites: apt, hardening, SSH, NTP
    ├── docker/                       # Docker Engine + systemd
    ├── user_management/              # System users, sudo, SSH keys
    ├── ntp_config/                   # NTP synchronization
    ├── postgresql/                   # PostgreSQL 15 container + .env
    ├── redis/                        # Redis 7 container
    ├── minio/                        # MinIO container + init script
    ├── openbao/                      # OpenBao 2.6.0 Raft + policies + tokens
    ├── keycloak/                     # Keycloak 26.0 container + realm provisioner
    ├── keycloak_realm/               # Keycloak realm provisioning (API)
    ├── gitea/                        # Gitea 1.23.4 container
    ├── lightserp/                    # LightSerp API + WebUI containers
    ├── searxng/                      # SearXNG container
    ├── nsqd/                         # NSQD container
    ├── pagezen/                      # PageZen container
    ├── admin_gateway/                # Admin Gateway container
    ├── docker-compose-generator/     # Generates docker-compose.yml from Jinja2
    ├── nginx-config/                 # Nginx reverse proxy (host-level systemd)
    ├── cloudflare_tunnel/            # Cloudflared tunnels (systemd x2)
    ├── backup/                       # Backup scripts + cron
    └── drift-detect/                 # Drift detection script
```

---

## Deployment Flow

```
ansible-playbook playbook.yml
    │
    ├── 1. common              → apt update, SSH hardening, NTP, prerequisites
    ├── 2. docker              → Docker Engine installation + config
    ├── 3. user_management     → System users, sudo, SSH key deployment
    ├── 4. ntp_config          → NTP synchronization
    ├── 5. postgresql          → PostgreSQL container + .env + pg_hba + config
    ├── 6. redis               → Redis container + .env + config
    ├── 7. minio               → MinIO container + .env + init script
    ├── 8. openbao             → OpenBao container + config + unseal + policies + KV
    ├── 9. keycloak            → Keycloak container + .env + keycloak.conf + realm-export
    ├── 10. keycloak_realm     → Provision realms, clients, users via API
    ├── 11. gitea              → Gitea container + .env + config
    ├── 12. lightserp          → LightSerp API + WebUI containers + .env
    ├── 13. searxng            → SearXNG container + .env
    ├── 14. nsqd               → NSQD container + .env
    ├── 15. pagezen            → PageZen container + .env
    ├── 16. admin_gateway      → Admin Gateway container + .env + config
    ├── 17. docker-compose-generator → Generate all docker-compose.yml files
    ├── 18. nginx-config       → Nginx reverse proxy configuration
    ├── 19. cloudflare_tunnel  → Cloudflared tunnels + systemd service
    ├── 20. backup             → Backup scripts + cron jobs
    │
    └── POST-DEPLOY:
        ├── docker compose up -d    → Start all services
        ├── wait_for_services       → Health check all services
        ├── drift-detect.sh --check → Verify zero drift
        └── health-check.sh         → Full health check report
```

---

## Drift Prevention Strategy

### Rule 1: No Manual Edits
Every file on the VM must be generated by Ansible. Manual edits create drift.

### Rule 2: All Configs from Templates
No static config files. Every config is a Jinja2 template derived from `group_vars/all.yml`.

### Rule 3: Environment Variables from OpenBao
All secrets come from OpenBao KV at deploy time. No plaintext passwords in any file.

### Rule 4: Drift Detection
`drift-detect.sh` runs after every deployment and reports any deviation from Ansible state.

---

## Data Directory Mapping

| Service    | Container Name          | Host Data Directory                                         |
|------------|------------------------|------------------------------------------------------------|
| PostgreSQL | iacgenie_postgres      | /home/mkanavi/docker/iacgenie/data/postgres                 |
| Redis      | iacgenie_redis          | /home/mkanavi/docker/iacgenie/data/redis                    |
| MinIO      | iacgenie_minio          | /home/mkanavi/docker/iacgenie/data/minio                    |
| OpenBao    | iacgenie_openbao        | /home/mkanavi/docker/iacgenie/data/openbao (config)         |
|            |                        | /home/mkanavi/docker/iacgenie/data/openbao_raft (raft DB)   |
| Keycloak   | iacgenie_keycloak       | /home/mkanavi/docker/iacgenie/data/keycloak                 |
| Gitea      | iacgenie_gitea          | /home/mkanavi/docker/iacgenie/data/gitea                    |
| NSQD       | iacgenie_nsqd           | /home/mkanavi/docker/iacgenie/data/nsqd                     |
| Prometheus | - (host-level)          | /home/mkanavi/docker/iacgenie/prometheus/data               |
| Grafana    | - (host-level)          | /home/mkanavi/docker/iacgenie/grafana                       |
| Loki       | - (host-level)          | /home/mkanavi/docker/iacgenie/loki                          |
| Promtail   | - (systemd)             | /home/mkanavi/docker/iacgenie/promtail                      |
| Backups    | - (systemd)             | /home/mkanavi/backups/encrypted/                            |

---

## Network Segmentation

```
iacgenie-backend (bridge): PostgreSQL, Redis, MinIO, OpenBao, Keycloak, Gitea
iacgenie-frontend (bridge): LightSerp, SearXNG, PageZen, Nginx, Admin Gateway
iacgenie-messaging (bridge): NSQD, LightSerp API
```

---

## Port Mapping (Host → Container)

| Service       | Host Port | Container Port | Bind   |
|---------------|-----------|----------------|--------|
| PostgreSQL    | 5432      | 5432           | 127.0.0.1 |
| Redis         | 6379      | 6379           | 127.0.0.1 |
| MinIO API     | 9000      | 9000           | 127.0.0.1 |
| MinIO Console | 9001      | 9001           | 127.0.0.1 |
| OpenBao       | 8200      | 8200           | 127.0.0.1 |
| OpenBao API   | 8201      | 8201           | 127.0.0.1 |
| Keycloak      | 8083      | 8080           | 127.0.0.1 |
| Gitea Web     | 3000      | 3000           | 127.0.0.1 |
| Gitea SSH     | 2222      | 2222           | 127.0.0.1 |
| LightSerp API | 8000      | 3000           | 127.0.0.1 |
| LightSerp UI  | 3001      | 3070           | 127.0.0.1 |
| PageZen       | 8081      | 8082           | 127.0.0.1 |
| SearXNG       | 8082      | 8080           | 127.0.0.1 |
| NSQD HTTP     | 4151      | 4151           | 127.0.0.1 |
| NSQD TCP      | 4150      | 4150           | 127.0.0.1 |

---

## OpenBao Secret Paths (iacgenie/kv)

| Secret                    | OpenBao Path                              |
|---------------------------|------------------------------------------|
| PostgreSQL password       | `iacgenie/kv/postgres/password`          |
| Redis password            | `iacgenie/kv/redis/password`             |
| MinIO root user           | `iacgenie/kv/minio/root_user`            |
| MinIO root password       | `iacgenie/kv/minio/root_password`        |
| Keycloak admin user       | `iacgenie/kv/keycloak/admin_user`        |
| Keycloak admin password   | `iacgenie/kv/keycloak/admin_password`    |
| Keycloak DB password      | `iacgenie/kv/keycloak/db_password`       |
| Gitea DB password         | `iacgenie/kv/gitea/db_password`          |
| Gitea admin password      | `iacgenie/kv/gitea/admin_password`       |
| OpenBao root token        | `iacgenie/kv/openbao/root_token`         |
| OpenBao unseal keys       | `iacgenie/kv/openbao/unseal_keys`        |
| SearXNG secret key        | `iacgenie/kv/searxng/secret`             |
| LightSerp API secret      | `iacgenie/kv/lightserp/api_secret`       |
| JWT middleware secret     | `iacgenie/kv/jwt_middleware/secret`      |
| Admin gateway secret      | `iacgenie/kv/admin_gateway/secret`       |
| Ansible vault password    | `iacgenie/kv/ansible/vault_password`     |
| Cloudflare tunnel token   | `iacgenie/kv/cloudflare/tunnel_token`    |
| Cloudflare API token      | `iacgenie/kv/cloudflare/api_token`       |
| OpenBao OIDC client secret| `iacgenie/kv/openbao/oidc_client_secret` |
| LightSerp KC client secret| `iacgenie/kv/lightserp/kc_client_secret` |

---

## OpenBao Policies

| Policy                  | Description                                    |
|-------------------------|------------------------------------------------|
| `admin`                 | Full admin access to OpenBao                   |
| `platform-admin`        | Admin access to iacgenie/ KV only              |
| `iacgenie-service`      | Read access to iacgenie/ KV                   |
| `lightserp-service`     | Read access to lightserp/ KV                   |
| `terraform-service`     | Read access to terraform/ KV                   |
| `openbao-service-read`  | Read access to all KV + service-token creation |

---

## Service Startup Order

```
1. Docker Engine (systemd)
2. PostgreSQL (docker compose)
3. OpenBao (docker compose)
4. Keycloak (depends on PostgreSQL)
5. All other services (docker compose)
6. Nginx (systemd, host-level)
7. Cloudflared (systemd, host-level x2)
```

---

## Key Services & URLs

| Service       | Internal URL              | External URL (via Cloudflare)      |
|---------------|--------------------------|------------------------------------|
| Keycloak UI   | http://127.0.0.1:8083    | https://auth.iacgenie.com          |
| OpenBao UI    | http://127.0.0.1:8200    | https://vault.iacgenie.com         |
| Gitea         | http://127.0.0.1:3000    | https://gitea.iacgenie.com         |
| Nginx         | http://127.0.0.1:80      | https://iacgenie.com               |
| Prometheus    | http://127.0.0.1:9090    | (internal only)                    |
| Grafana       | http://127.0.0.1:3001    | https://grafana.iacgenie.com       |
| MinIO         | http://127.0.0.1:9000    | https://minio.iacgenie.com         |

---

## Configuration Locations

| Item                  | Location                                              |
|-----------------------|-------------------------------------------------------|
| Docker Compose files  | /home/mkanavi/docker/iacgenie/docker-compose.yml       |
| Keycloak realm export | /home/mkanavi/docker/iacgenie/data/keycloak/           |
| Keycloak config       | /home/mkanavi/docker/iacgenie/keycloak.conf            |
| Nginx config          | /etc/nginx/conf.d/iacgenie-unified.conf                |
| Cloudflared config    | /home/mkanavi/.cloudflared/config.yml                   |
| Cloudflared cert      | /home/mkanavi/.cloudflared/cert.pem                     |
| Backup encrypted      | /home/mkanavi/backups/encrypted/                        |
| Ansible playbooks     | /Users/manjunathkanavi/iacgenie-platform/infra/ansible/ |
| Ansible inventory     | /Users/manjunathkanavi/iacgenie-platform/infra/ansible/inventory/ |

---

## Deployment Commands

```bash
# Full deployment (from local machine)
cd ~/iacgenie-platform/infra/ansible
ansible-playbook playbook.yml -i inventory/hosts.yml

# Dry run (check mode)
ansible-playbook playbook.yml -i inventory/hosts.yml --check --diff

# Deploy specific role only
ansible-playbook playbook.yml -i inventory/hosts.yml --tags "keycloak"

# Post-deploy validation
ssh mkanavi@192.168.0.118 "docker ps --format 'table {{.Names}}\t{{.Status}}' | head -20"

# Health check
ssh mkanavi@192.168.0.118 "~/iacgenie-platform/infra/health-check.sh"

# Drift detection
ssh mkanavi@192.168.0.118 "~/iacgenie-platform/infra/drift-detect.sh"
```

---

## Emergency Recovery

1. **Service down**: `ssh mkanavi@192.168.0.118 && docker restart iacgenie_<service>`
2. **Data loss**: Restore from encrypted backup on Google Drive
3. **VM loss**: Redeploy from scratch using `ansible-playbook playbook.yml`
4. **Keycloak lockout**: Reset admin password from OpenBao → `openbao_ig_kc_admin_password`
5. **OpenBao sealed**: Retrieve unseal keys from `iacgenie/kv/openbao/unseal_keys`
6. **Docker corrupt**: `docker system prune -a --volumes` then redeploy Ansible

---

## Drift Prevention Checklist

After any manual change:
1. [ ] Was the change documented in Ansible role variables?
2. [ ] Is the change template-based (Jinja2) rather than static?
3. [ ] Can the change be reproduced by `ansible-playbook --check`?
4. [ ] Does `drift-detect.sh` report zero drift after the change?
5. [ ] Was the change pushed to git?
