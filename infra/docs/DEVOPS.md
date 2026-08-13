# IacGenie Platform — DevOps Engineer Guide

## Table of Contents
1. [Infrastructure as Code](#infrastructure-as-code)
2. [Ansible Automation](#ansible-automation)
3. [Docker Compose Management](#docker-compose-management)
4. [Deployment Pipeline](#deployment-pipeline)
5. [Secrets Management](#secrets-management)
6. [Monitoring Configuration](#monitoring-configuration)
7. [Backup Operations](#backup-operations)
8. [Troubleshooting Runbooks](#troubleshooting-runbooks)

---

## Infrastructure as Code

### Repository Structure
```
iacgenie-platform/
├── infra/
│   ├── ansible/          # Ansible playbooks & roles
│   │   ├── playbook.yml
│   │   ├── site.yml
│   │   ├── inventory/
│   │   │   ├── hosts.yml
│   │   │   └── group_vars/
│   │   │       └── all.yml
│   │   └── roles/
│   │       ├── bootstrap/
│   │       ├── nginx/
│   │       ├── cloudflare_tunnel/
│   │       ├── postgres/
│   │       ├── redis/
│   │       ├── minio/
│   │       ├── openbao/
│   │       ├── keycloak/
│   │       ├── keycloak_realm/
│   │       ├── monitoring/
│   │       ├── falco/
│   │       └── falcosidekick/
│   ├── docker-compose/
│   │   ├── docker-compose-unified.yml.j2    # Base services
│   │   ├── docker-compose-monitoring.yml.j2  # Monitoring stack
│   │   └── docker-compose-lightsrp.yml.j2    # LightSerp-specific
│   ├── prometheus/
│   │   ├── prometheus.yml.j2
│   │   ├── alert_rules.yml.j2
│   │   └── alertmanager.yml.j2
│   ├── loki/
│   │   └── promtail.yml.j2
│   ├── grafana/
│   │   └── provisioning/
│   ├── falco/
│   │   ├── falco.yaml.j2
│   │   └── falco_rules.yaml.j2
│   ├── falcosidekick/
│   │   └── config.yaml
│   ├── systemd/
│   │   ├── iacgenie-monitoring.service
│   │   ├── cloudflared.service
│   │   └── falco.service
│   ├── health-check.sh
│   ├── backup-restore.sh
│   └── drift-detect.sh
└── lightserv/
```

### Key Principles
- **Zero hardcoded secrets** — all secrets in OpenBao KV
- **Idempotent Ansible** — `ansible-playbook --check` always passes
- **Template-based** — all compose files use `.j2` templates
- **Git-tracked** — all changes committed to `main`
- **Drift detection** — automated comparison of running state vs code

---

## Ansible Automation

### Running Playbooks
```bash
# Full deployment
cd /Users/manjunathkanavi/iacgenie-platform/infra/ansible
ansible-playbook site.yml

# Individual roles
ansible-playbook playbook.yml --role postgres
ansible-playbook playbook.yml --role keycloak
ansible-playbook playbook.yml --role monitoring

# Dry run (check mode)
ansible-playbook site.yml --check --diff

# Limit to specific host
ansible-playbook site.yml --limit 192.168.0.118
```

### Role Structure
Each role follows this structure:
```
roles/<name>/
├── tasks/
│   └── main.yml        # Main task list
├── defaults/
│   └── main.yml        # Default variables
├── templates/
│   └── *.j2            # Configuration templates
├── handlers/
│   └── main.yml        # Service restart handlers
└── vars/
    └── main.yml        # Role-specific variables
```

### Ansible Inventory
```yaml
# infra/ansible/inventory/hosts.yml
all:
  children:
    iacgenie-vm:
      hosts:
        192.168.0.118:
          ansible_user: mkanavi
          ansible_ssh_private_key_file: ~/.ssh/id_ed25519
          ansible_python_interpreter: /usr/bin/python3
```

---

## Docker Compose Management

### Base Services Compose
```bash
# Location on VM: /home/mkanavi/docker/iacgenie/docker-compose.yml
# Managed by: ansible/roles/nginx-config/templates/

# View status
docker ps

# View logs
docker compose logs --tail 100 <service>

# Restart all services
docker compose -f /home/mkanavi/docker/iacgenie/docker-compose.yml down
docker compose -f /home/mkanavi/docker/iacgenie/docker-compose.yml up -d

# Restart single service
docker compose -f /home/mkanavi/docker/iacgenie/docker-compose.yml restart <service>
```

### Monitoring Stack Compose
```bash
# Location on VM: /home/mkanavi/docker/iacgenie/docker-compose-monitoring.yml
# Managed by: ansible/roles/monitoring/templates/

# View status
docker ps | grep -E 'prometheus|grafana|loki|falco|falcosidekick'

# Restart monitoring stack
docker compose -f /home/mkanavi/docker/iacgenie/docker-compose-monitoring.yml down
docker compose -f /home/mkanavi/docker/iacgenie/docker-compose-monitoring.yml up -d

# Check Grafana provisioning
docker exec -it iacgenie_grafana ls /etc/grafana/provisioning/
```

### Network Management
```bash
# List networks
docker network ls | grep iacgenie

# Inspect network
docker network inspect iacgenie_iacgenie-backend

# Create network (if missing)
docker network create iacgenie_iacgenie-backend
```

---

## Deployment Pipeline

### Pre-deployment Checklist
1. Update repo: `git pull`
2. Run health check: `./health-check.sh`
3. Run drift detection: `./drift-detect.sh`
4. Commit changes: `git commit -am "description"`
5. Push: `git push`

### Deployment Steps
```bash
# 1. Update code
git pull

# 2. Test locally
./health-check.sh

# 3. Run Ansible
ansible-playbook site.yml

# 4. Verify deployment
./health-check.sh
./drift-detect.sh

# 5. Check logs
docker compose logs --tail 50 --tail 50 <service>
```

### Rollback Procedure
```bash
# 1. Identify last good commit
git log --oneline -10

# 2. Check out specific commit
git checkout <commit-hash>

# 3. Run Ansible to restore
ansible-playbook site.yml

# 4. Verify services
./health-check.sh
```

---

## Secrets Management

### OpenBao KV Structure
All secrets stored in OpenBao KV v2 at `iacgenie/`.

```bash
# List all secret paths
ssh mkanavi@192.168.0.118
docker exec iacgenie_openbao bao kv list iacgenie/

# Read a secret
docker exec iacgenie_openbao bao kv get iacgenie/kv/platform/api-key

# Update a secret
docker exec -it iacgenie_openbao bash
bao kv put iacgenie/kv/platform/api-key new-value

# Delete a secret
bao kv delete iacgenie/kv/platform/api-key
```

### Service Secret Mapping
| Service | OpenBao Path |
|---------|-------------|
| LightSerp API | `iacgenie/kv/platform/api-key` |
| PostgreSQL | `iacgenie/kv/postgres/pg-password` |
| Redis | `iacgenie/kv/redis/redis-password` |
| MinIO | `iacgenie/kv/minio/minio-access-key` |
| Keycloak | `iacgenie/kv/keycloak/kc-admin-password` |
| Nginx SSL | `iacgenie/kv/nginx/ssl-cert` |
| Cloudflare | `iacgenie/kv/cloudflare/api-token` |
| Git credentials | `iacgenie/kv/git/github-token` |
| Monitoring | `iacgenie/kv/monitoring/grafana-admin-password` |

### Secret Rotation
```bash
# 1. Generate new secret
openssl rand -base64 32

# 2. Update in OpenBao
docker exec -it iacgenie_openbao bash
bao kv put iacgenie/kv/platform/api-key <new-value>

# 3. Restart affected services
docker restart iacgenie_lightserp_api

# 4. Verify service can read new secret
docker logs iacgenie_lightserp_api | grep "secret loaded"
```

---

## Monitoring Configuration

### Prometheus Scrape Targets
```yaml
# infra/prometheus/prometheus.yml
scrape_configs:
  - job_name: 'docker'
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
    relabel_configs:
      - source_labels: [__meta_docker_container_name]
        regex: iacgenie_.*
        action: keep

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['127.0.0.1:9100']

  - job_name: 'prometheus'
    static_configs:
      - targets: ['127.0.0.1:9090']
```

### Alert Rules
Located at `infra/prometheus/alert_rules.yml.j2`.
Alerts route to Alertmanager → Telegram/email.

### Grafana Dashboards
- **Infrastructure Overview**: `grafana/provisioning/dashboards/infrastructure-overview.json.j2`
- **Custom dashboards**: Add via Grafana UI → Save to `/home/mkanavi/docker/iacgenie/grafana/dashboards/`

---

## Backup Operations

### Backup Script Usage
```bash
# Full backup
./backup-restore.sh backup all

# Specific service
./backup-restore.sh backup postgres
./backup-restore.sh backup openbao
./backup-restore.sh backup keycloak

# List backups
./backup-restore.sh list

# Verify backups
./backup-restore.sh verify

# Restore service
./backup-restore.sh restore pg-20260808-030000.sql.gz.gpg
```

### Backup Retention
- **Daily backups**: 30 days
- **Automated via cron**: `0 3 * * *` (3 AM daily)
- **Google Drive sync**: Via rclone
- **Encrypted**: AES-256 GPG

---

## Troubleshooting Runbooks

### Service Won't Start
1. Check logs: `docker logs iacgenie_<service>`
2. Check OpenBao: `docker exec iacgenie_openbao bao audit list`
3. Check dependencies: `docker ps | grep <service>`
4. Restart: `docker restart iacgenie_<service>`

### Nginx Returns 502
1. Check upstream: `docker ps | grep <service>`
2. Check network: `docker network inspect iacgenie_iacgenie-backend`
3. Reload nginx: `sudo systemctl reload nginx`

### OpenBao Sealed
1. Check status: `docker exec iacgenie_openbao bao status`
2. Unseal: `docker exec iacgenie_openbao bao operator unseal`
3. Verify: `docker exec iacgenie_openbao bao status`

### High Disk Usage
```bash
# Check disk usage
du -sh /home/mkanavi/docker/*/data/* | sort -h

# Clean old logs
docker system prune -af --volumes
```

### Network Issues
```bash
# Check DNS resolution
docker exec iacgenie_lightserp_api getent hosts postgres

# Test connectivity
docker exec iacgenie_lightserp_api ping postgres
```
