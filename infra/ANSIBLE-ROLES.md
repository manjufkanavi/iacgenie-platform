# IacGenie Platform — Ansible Role Documentation

> **Last Updated**: 2026-08-16  
> **Ansible Version**: 2.17+  
> **Playbook**: `site.yml`

---

## Role Inventory

| Role | Purpose | Depends On | Tags |
|------|---------|------------|------|
| `common` | System prerequisites (apt, SSH, NTP) | — | common |
| `docker` | Docker Engine installation | common | docker |
| `openbao` | OpenBao + Raft storage + policies | docker | openbao |
| `keycloak` | Keycloak container + realm provisioning | docker, openbao | keycloak |
| `gitea` | Gitea container | docker | gitea |
| `docker-compose-generator` | Generate docker-compose.yml | all above | docker-compose |
| `nginx-config` | Nginx reverse proxy config | docker | nginx |
| `cloudflare_tunnel` | Cloudflare Tunnel | docker | cloudflare |
| `monitoring` | Prometheus + Grafana + Loki | docker | monitoring |
| `backup` | Backup cron job | docker | backup |

---

## Role Details

### `common`

**Purpose**: System-level configuration  
**Files**: `tasks/main.yml`, `handlers/main.yml`  
**Variables**:
```yaml
ntp_server: "pool.ntp.org"
ssh_port: 22
```

### `docker`

**Purpose**: Docker Engine installation  
**Files**: `tasks/main.yml`, `defaults/main.yml`  
**Variables**:
```yaml
docker_version: "27.0"
docker_compose_version: "2.29"
```

### `openbao`

**Purpose**: OpenBao 2.6.0 deployment with Raft storage  
**Files**: `tasks/main.yml`, `templates/openbao-prod.hcl.j2`, `files/unseal.sh`  
**Variables**:
```yaml
openbao_version: "2.6.0"
openbao_raft_path: "/home/mkanavi/docker/iacgenie/openbao_raft"
openbao_cluster_addr: "https://vault.iacgenie.com:8201"
```

### `keycloak`

**Purpose**: Keycloak 26.0 deployment with realm provisioning  
**Files**: `tasks/main.yml`, `templates/keycloak.conf.j2`  
**Variables**:
```yaml
keycloak_version: "26.0-pg"
keycloak_http_port: 9003
keycloak_admin_user: "admin"
keycloak_admin_password: "{{ lookup('env', 'KEYCLOAK_ADMIN_PASSWORD') }}"
```

### `gitea`

**Purpose**: Gitea 1.23.4 deployment  
**Files**: `tasks/main.yml`, `templates/gitea.conf.j2`  
**Variables**:
```yaml
gitea_version: "1.23.4-rootless"
gitea_http_port: 3000
gitea_ssh_port: 2222
```

### `docker-compose-generator`

**Purpose**: Generate docker-compose.yml from Jinja2 template  
**Files**: `templates/docker-compose.yml.j2`  
**Variables**:
```yaml
docker_compose_version: "3.9"
network_name_frontend: "iacgenie-frontend"
network_name_backend: "iacgenie-backend"
network_name_messaging: "iacgenie-messaging"
```

### `nginx-config`

**Purpose**: Nginx reverse proxy configuration  
**Files**: `templates/nginx-unified.conf.j2`  
**Variables**:
```yaml
nginx_worker_processes: "auto"
nginx_worker_connections: 1024
nginx_keepalive_timeout: 65
nginx_client_max_body_size: "64m"
```

### `cloudflare_tunnel`

**Purpose**: Cloudflare Tunnel deployment  
**Files**: `tasks/main.yml`, `templates/cloudflared-config.yml.j2`  
**Variables**:
```yaml
cloudflared_version: "2025.6.0"
cloudflare_account_id: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_ID') }}"
cloudflare_tunnel_token: "{{ lookup('env', 'CLOUDFLARE_TUNNEL_TOKEN') }}"
```

### `monitoring`

**Purpose**: Prometheus + Grafana + Loki monitoring stack  
**Files**: `templates/prometheus.yml.j2`, `templates/grafana-dashboards.yml.j2`  
**Variables**:
```yaml
prometheus_version: "v3.2.0"
grafana_version: "11.5.0"
loki_version: "3.2.0"
```

### `backup`

**Purpose**: Automated backup cron job  
**Files**: `tasks/main.yml`, `templates/backup-cron.j2`  
**Variables**:
```yaml
backup_schedule: "0 2 * * *"  # Daily at 2 AM
backup_retention_days: 7
backup_gpg_key: "{{ lookup('env', 'BACKUP_GPG_KEY') }}"
```

---

## Usage

### Full Deployment

```bash
ansible-playbook site.yml
```

### Dry Run

```bash
ansible-playbook site.yml --check --diff
```

### Deploy Specific Role

```bash
ansible-playbook site.yml --role docker-compose-generator
ansible-playbook site.yml --role monitoring
```

### Deploy with Tags

```bash
ansible-playbook site.yml --tags backup
ansible-playbook site.yml --tags monitoring
```

### Deploy with Extra Vars

```bash
ansible-playbook site.yml --extra-vars="keycloak_admin_password=mysecretpassword"
```
