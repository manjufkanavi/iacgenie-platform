# IacGenie Platform — AI Agent Guide

## Quick Reference Card

```
# Essential commands for AI agents to manage the platform:

# SSH to VM
ssh mkanavi@192.168.0.118

# Check service status
docker ps --format 'table {{.Names}}\t{{.Status}}'

# View logs (last 100 lines)
docker logs --tail 100 iacgenie_<service>

# Restart a service
docker restart iacgenie_<service>

# Run health check
/home/mkanavi/iacgenie-platform/health-check.sh

# Run drift detection
/home/mkanavi/iacgenie-platform/drift-detect.sh

# Run backup
/home/mkanavi/iacgenie-platform/backup-restore.sh backup all

# Get OpenBao secret
docker exec iacgenie_openbao bao kv get iacgenie/kv/<path>/<key>

# Ansible deployment
cd /Users/manjunathkanavi/iacgenie-platform/infra/ansible && ansible-playbook site.yml

# Check Nginx config
sudo nginx -t && sudo systemctl reload nginx
```

---

## Platform Overview

**Infrastructure**: Single Ubuntu VM (`192.168.0.118`), 16+ cores, 32GB RAM
**Orchestration**: Docker Compose (2 compose files)
**Auth**: Keycloak (OIDC provider)
**Secrets**: OpenBao KV v2
**Monitoring**: Prometheus + Grafana + Loki + Falco + Falcosidekick
**Tunnel**: Cloudflare Tunnel (no public ports)
**Reverse Proxy**: Nginx (systemd-managed)
**Git**: GitHub (iacgenie-platform repo)

### Service Map
| Service | Container Name | Port | Network |
|---------|---------------|------|---------|
| PostgreSQL | `iacgenie_postgres` | 5432 | backend |
| Redis | `iacgenie_redis` | 6379 | backend |
| MinIO | `iacgenie_minio` | 9000/9001 | backend |
| OpenBao | `iacgenie_openbao` | 8200 | backend |
| Keycloak | `iacgenie_keycloak` | 8083 | frontend+backend |
| NSQD | `iacgenie_nsqd` | 4150/4151 | backend |
| SearXNG | `iacgenie_searxng` | 8082 | backend |
| LightSerp API | `iacgenie_lightserp_api` | 8000 | backend |
| LightSerp WebUI | `iacgenie_lightserp_webui` | 3001 | backend |
| PageZen | `iacgenie_pagezen` | 8081 | backend |
| Gitea | `iacgenie_gitea` | 3000 | backend |
| Prometheus | `iacgenie_prometheus` | 9090 | frontend+backend |
| Alertmanager | `iacgenie_alertmanager` | 9093 | backend |
| Grafana | `iacgenie_grafana` | 3002 | frontend |
| Loki | `iacgenie_loki` | 3100 | backend |
| Promtail | `iacgenie_promtail` | — | backend |
| Node Exporter | `iacgenie_node_exporter` | 9100 | backend |
| Falco | `iacgenie_falco` | — | backend |
| Falcosidekick | `iacgenie_falcosidekick` | 2800 | frontend+backend |

---

## OpenBao Secrets Layout

All secrets in OpenBao KV v2:
```
iacgenie/kv/
├── platform/       # API keys, general platform secrets
├── lightserp/      # LightSerp-specific secrets
├── postgres/       # DB credentials
├── redis/          # Redis auth
├── minio/          # MinIO credentials
├── keycloak/       # Keycloak secrets
├── openbao/        # OpenBao tokens
├── git/            # Git credentials
├── monitoring/     # Monitoring stack secrets
├── cloudflare/     # Cloudflare credentials
├── gitea/          # Gitea credentials
├── searxng/        # SearXNG secrets
├── nsqd/           # NSQD secrets
└── nginx/          # Nginx SSL certs
```

### Key OpenBao Commands
```bash
# List secrets under a path
docker exec iacgenie_openbao bao kv list iacgenie/kv/platform/

# Get a specific secret
docker exec iacgenie_openbao bao kv get iacgenie/kv/platform/api-key

# Update a secret
docker exec -it iacgenie_openbao bash
bao kv put iacgenie/kv/platform/api-key newvalue

# Delete a secret
bao kv delete iacgenie/kv/platform/api-key
```

---

## Docker Compose Files

### 1. Unified Compose (`docker-compose-unified.yml`)
Location on VM: `/home/mkanavi/docker/iacgenie/docker-compose.yml`
Ansible template: `infra/docker-compose/docker-compose-unified.yml.j2`

**Services**: PostgreSQL, Redis, MinIO, OpenBao, Keycloak, NSQD, SearXNG, LightSerp, Gitea

### 2. Monitoring Compose (`docker-compose-monitoring.yml`)
Location on VM: `/home/mkanavi/docker/iacgenie/docker-compose-monitoring.yml`
Ansible template: `infra/docker-compose/docker-compose-monitoring.yml.j2`

**Services**: Prometheus, Alertmanager, Grafana, Loki, Promtail, Node Exporter, Falco, Falcosidekick

---

## Monitoring & Alerting

### Endpoints
| Service | URL (via tunnel) | Internal |
|---------|-----------------|----------|
| Grafana | `https://grafana.iacgenie.com` | `127.0.0.1:3002` |
| Prometheus | `https://prometheus.iacgenie.com` | `127.0.0.1:9090` |
| Alertmanager | `https://alertmanager.iacgenie.com` | `127.0.0.1:9093` |
| Loki | `https://loki.iacgenie.com` | `127.0.0.1:3100` |
| Falcosidekick | `https://falcosidekick.iacgenie.com` | `127.0.0.1:2800` |
| Prometheus Metrics | N/A | `http://127.0.0.1:9090/metrics` |
| Grafana API | N/A | `http://127.0.0.1:3002/api` |
| Loki API | N/A | `http://127.0.0.1:3100/loki/api/v1` |

### Alert Rules
Location: `infra/prometheus/alert_rules.yml.j2`
- Service availability (critical)
- Resource utilization (warning)
- Database alerts (warning/critical)
- Nginx error rate (warning)
- Security alerts (critical)
- Falco events (info/critical)

---

## Deployment Commands

### Ansible Playbook
```bash
# Full deployment
ansible-playbook site.yml

# Individual roles
ansible-playbook playbook.yml --role nginx
ansible-playbook playbook.yml --role keycloak
ansible-playbook playbook.yml --role monitoring
ansible-playbook playbook.yml --role falco

# Dry run
ansible-playbook site.yml --check --diff
```

### Docker Compose Management
```bash
# View running containers
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

# View logs
docker logs --tail 100 iacgenie_<service>

# Restart service
docker restart iacgenie_<service>

# Recreate service
docker compose -f /home/mkanavi/docker/iacgenie/docker-compose.yml up -d <service>

# Monitoring stack
docker compose -f /home/mkanavi/docker/iacgenie/docker-compose-monitoring.yml up -d
docker compose -f /home/mkanavi/docker/iacgenie/docker-compose-monitoring.yml down
```

### Systemd Services
```bash
# Monitoring stack (boot auto-start)
sudo systemctl start iacgenie-monitoring
sudo systemctl enable iacgenie-monitoring
sudo systemctl status iacgenie-monitoring

# Falco (runtime security)
sudo systemctl start falco
sudo systemctl enable falco
sudo systemctl status falco

# Cloudflare Tunnel (boot auto-start)
sudo systemctl start cloudflared
sudo systemctl enable cloudflared
sudo systemctl status cloudflared

# Nginx (reverse proxy)
sudo systemctl start nginx
sudo systemctl enable nginx
sudo systemctl reload nginx
```

---

## Backup & Restore

### Backup Commands
```bash
# Full backup
/home/mkanavi/iacgenie-platform/backup-restore.sh backup all

# Specific service
/home/mkanavi/iacgenie-platform/backup-restore.sh backup postgres
/home/mkanavi/iacgenie-platform/backup-restore.sh backup openbao
/home/mkanavi/iacgenie-platform/backup-restore.sh backup keycloak

# List backups
/home/mkanavi/iacgenie-platform/backup-restore.sh list

# Verify backups
/home/mkanavi/iacgenie-platform/backup-restore.sh verify
```

### Restore Commands
```bash
# Restore specific service
/home/mkanavi/iacgenie-platform/backup-restore.sh restore <backup-file>

# Restore all services
/home/mkanavi/iacgenie-platform/backup-restore.sh restore all
```

---

## Troubleshooting Commands

### Health Check
```bash
/home/mkanavi/iacgenie-platform/health-check.sh
```

### Drift Detection
```bash
/home/mkanavi/iacgenie-platform/drift-detect.sh
```

### Nginx
```bash
# Test config
sudo nginx -t

# Reload
sudo systemctl reload nginx

# Logs
tail -50 /var/log/nginx/error.log
tail -50 /var/log/nginx/access.log
```

### OpenBao
```bash
# Check status
docker exec iacgenie_openbao bao status

# Unseal if sealed
docker exec -it iacgenie_openbao bash
bao operator unseal

# List audit paths
bao audit list
```

### Keycloak
```bash
# Check health
curl -s http://127.0.0.1:8083/auth/health/ready

# Admin UI
# http://127.0.0.1:8083/auth/admin/

# Check realm
docker exec iacgenie_keycloak ls /opt/keycloak/data/h2/
```

### PostgreSQL
```bash
# Connect
docker exec -it iacgenie_postgres psql -U lightsrp -d lightsrp

# List databases
docker exec iacgenie_postgres psql -U postgres -c "\l"

# Check connections
docker exec iacgenie_postgres psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"
```

### Service Connectivity
```bash
# Test service-to-service connectivity
docker exec iacgenie_lightserp_api ping postgres

# Test DNS resolution
docker exec iacgenie_lightserp_api getent hosts redis
```

---

## Git Operations

### Repository
```bash
# Clone
git clone https://github.com/manjufkanavi/iacgenie-platform

# Pull latest
git pull

# Commit changes
git add -A
git commit -m "description"
git push origin main
```

### Infra Directory
All infrastructure code in `iacgenie-platform/infra/`:
- `ansible/` — Ansible playbooks and roles
- `docker-compose/` — Docker Compose templates
- `prometheus/` — Prometheus configs
- `loki/` — Loki/Promtail configs
- `grafana/` — Grafana provisioning
- `falco/` — Falco security rules
- `falcosidekick/` — Falcosidekick config
- `systemd/` — Systemd service units
- `docs/` — User documentation
- `health-check.sh` — Health check script
- `backup-restore.sh` — Backup/restore script
- `drift-detect.sh` — Drift detection script
