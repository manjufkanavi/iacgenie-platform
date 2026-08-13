# IacGenie Platform — Admin Operations Guide

## Table of Contents
1. [Overview](#overview)
2. [Service Architecture](#service-architecture)
3. [Access Control](#access-control)
4. [Monitoring & Health](#monitoring--health)
5. [Backup & Disaster Recovery](#backup--disaster-recovery)
6. [Security Hardening](#security-hardening)
7. [Troubleshooting](#troubleshooting)
8. [Security Incidents](#security-incidents)

---

## Overview

IacGenie Platform runs on **Ubuntu VM 192.168.0.118** (single server, 16+ cores, 32GB RAM).
All services run in Docker containers on a shared network `iacgenie_iacgenie-backend`.

### Service Groups
| Group | Services | Network |
|-------|----------|---------|
| **Database** | PostgreSQL, Redis | iacgenie-backend |
| **Storage** | MinIO, OpenBao | iacgenie-backend |
| **Auth** | Keycloak | iacgenie-frontend + backend |
| **Platform** | LightSerp, NSQD, SearXNG, Gitea | iacgenie-backend |
| **Edge** | Nginx, Cloudflare Tunnel | external |
| **Monitoring** | Prometheus, Alertmanager, Grafana, Loki, Falco, Falcosidekick | iacgenie-frontend |

### Nginx Routes (via Cloudflare)
| Hostname | Service |
|----------|---------|
| `iacgenie.com` | LightSerp API |
| `api.iacgenie.com` | LightSerp API |
| `grafana.iacgenie.com` | Grafana (port 3002) |
| `vault.iacgenie.com` | OpenBao |
| `gitea.iacgenie.com` | Gitea |
| `*.iacgenie.com` | Wildcard tunnel |

---

## Access Control

### Primary Auth: Keycloak (OIDC)
- **Admin UI**: `http://127.0.0.1:8083/auth/admin/`
- **Realm**: `iacgenie`
- **OIDC Provider** for: LightSerp, IacGenie, OpenBao (when OIDC integration needed)
- **Client IDs**: `lightsrp`, `iacgenie`, `falcosidekick`

### OpenBao Secrets Management
All service secrets stored in **OpenBao KV v2** at:
```
iacgenie/kv/platform/     # Platform service secrets
iacgenie/kv/lightserp/    # LightSerp-specific secrets
iacgenie/kv/postgres/     # Database credentials
iacgenie/kv/redis/        # Redis auth
iacgenie/kv/minio/        # MinIO credentials
iacgenie/kv/keycloak/     # Keycloak secrets
iacgenie/kv/openbao/      # OpenBao tokens
iacgenie/kv/git/          # Git credentials
iacgenie/kv/monitoring/   # Monitoring stack secrets
iacgenie/kv/cloudflare/   # Cloudflare credentials
iacgenie/kv/gitea/        # Gitea credentials
iacgenie/kv/searxng/      # SearXNG secrets
iacgenie/kv/nsqd/         # NSQD secrets
iacgenie/kv/nginx/        # Nginx SSL certs
```

### Emergency Admin Access
```bash
# Keycloak admin (local)
ssh mkanavi@192.168.0.118
docker exec -it iacgenie_keycloak kubectl get pods  # No, use:
ssh mkanavi@192.168.0.118
curl -s http://127.0.0.1:8083/auth/realms/iacgenie/.well-known/openid-configuration

# OpenBao unseal (emergency)
docker exec -it iacgenie_openbao bao operator init
docker exec -it iacgenie_openbao bao operator unseal

# Emergency container shell
ssh mkanavi@192.168.0.118
docker exec -it iacgenie_postgres bash
```

### Service Credentials (auto-loaded from OpenBao)
Services load credentials at startup via environment variables sourced from OpenBao. No plaintext secrets in docker-compose files.

```bash
# View OpenBao secrets for a service
ssh mkanavi@192.168.0.118
docker exec -it iacgenie_openbao bao kv get iacgenie/kv/platform/api-key
docker exec -it iacgenie_openbao bao kv get iacgenie/kv/platform/db-password
```

---

## Monitoring & Health

### Health Check Endpoint
```bash
# Run from local machine
cd /Users/manjunathkanavi/iacgenie-platform/infra
ssh mkanavi@192.168.0.118 'bash /home/mkanavi/iacgenie-platform/health-check.sh'
```

### Service Status Dashboard
- **Grafana**: `https://grafana.iacgenie.com` (port 3002)
- **Prometheus**: `https://prometheus.iacgenie.com` (port 9090)
- **Falcosidekick**: `https://falcosidekick.iacgenie.com` (port 2800) — Falco events & alerts
- **Alertmanager**: `https://alertmanager.iacgenie.com` (port 9093) — alert routing

### Monitoring Retention
- **Prometheus metrics**: 30 days
- **Loki logs**: 30 days (compaction enabled)
- **Falco events**: forwarded to Loki + Alertmanager

### Docker Commands
```bash
# Quick status
ssh mkanavi@192.168.0.118
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep iacgenie

# View logs
docker logs --tail 100 iacgenie_<service>

# Restart service
docker restart iacgenie_<service>

# Remove and recreate
docker compose -f /home/mkanavi/docker/iacgenie/docker-compose.yml up -d <service>
```

---

## Backup & Disaster Recovery

### Backup Schedule (Cron)
```cron
# Daily full backup at 3am
0 3 * * * /home/mkanavi/iacgenie-platform/backup-restore.sh backup all >> /var/log/backup.log 2>&1

# Health check every 5 minutes
*/5 * * * * /home/mkanavi/iacgenie-platform/health-check.sh >> /var/log/health.log 2>&1

# Drift detection daily at 6am
0 6 * * * /home/mkanavi/iacgenie-platform/drift-detect.sh --json >> /var/log/drift.log 2>&1
```

### Backup Locations
| Location | Contents |
|----------|----------|
| `/home/mkanavi/backups/encrypted/` | Local encrypted backups |
| `gdrive:iacgenie-backups/` | Google Drive backup via rclone |

### Restore Procedure
```bash
# List available backups
ssh mkanavi@192.168.0.118
/home/mkanavi/iacgenie-platform/backup-restore.sh list

# Restore specific service
/home/mkanavi/iacgenie-platform/backup-restore.sh restore postgres

# Restore full platform
/home/mkanavi/iacgenie-platform/backup-restore.sh restore all

# Verify backup integrity
/home/mkanavi/iacgenie-platform/backup-restore.sh verify
```

### Disaster Recovery Checklist
1. Provision new VM with same specs
2. Clone repo: `git clone https://github.com/manjufkanavi/iacgenie-platform`
3. Install dependencies: Docker, OpenBao, Cloudflare Tunnel
4. Run restore: `./backup-restore.sh restore all`
5. Verify all services: `./health-check.sh`
6. Update DNS if needed
7. Update Cloudflare tunnel config

---

## Security Hardening

### Key Security Controls
1. **All services bound to 127.0.0.1** — no external exposure without tunnel
2. **Cloudflare Tunnel** — all external traffic encrypted
3. **Nginx reverse proxy** — TLS termination, rate limiting, IP allowlisting
4. **Keycloak OIDC** — centralized authentication for all services
5. **OpenBao KV v2** — all secrets encrypted at rest
6. **Falco runtime security** — detects runtime anomalies
7. **Encrypted backups** — AES-256 GPG encryption
8. **Docker security** — no privileged containers, read-only where possible

### SSL/TLS Configuration
```bash
# Nginx SSL certs
ssh mkanavi@192.168.0.118
ls -la /etc/letsencrypt/live/iacgenie.com/

# Cloudflare SSL (Managed certificates)
# Managed by Cloudflare — no local cert management needed
```

### Firewall Rules (iptables)
```bash
ssh mkanavi@192.168.0.118
sudo iptables -L -n | head -20
# All ports bound to 127.0.0.1, no public ports open
```

---

## Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check logs
docker logs iacgenie_<service> --tail 200

# Check container health
docker inspect iacgenie_<service> | grep -A 5 Health

# Restart
docker restart iacgenie_<service>
```

#### Nginx 502 Errors
```bash
# Check if upstream service is running
docker ps | grep <service>

# Check nginx error logs
ssh mkanavi@192.168.0.118
tail -50 /var/log/nginx/error.log

# Reload nginx
sudo systemctl reload nginx
```

#### PostgreSQL Connection Issues
```bash
# Check database
docker exec -it iacgenie_postgres psql -U postgres -c "\l"

# Check connections
docker exec -it iacgenie_postgres psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"
```

#### Keycloak Login Failures
```bash
# Check Keycloak health
curl -s http://127.0.0.1:8083/auth/health/ready

# Check realm configuration
docker exec -it iacgenie_keycloak ls /opt/keycloak/data/h2/

# Reset admin password (emergency)
docker exec -it iacgenie_keycloak /opt/keycloak/bin/kc.sh reset-password
```

#### Monitoring Stack Issues
```bash
# Check Prometheus scrape targets
curl -s http://127.0.0.1:9090/api/v1/targets | jq '.data.activeTargets[] | select(.health!="up") | .labels.job'

# Check Grafana provisioning
docker exec -it iacgenie_grafana ls /etc/grafana/provisioning/

# Check Loki log retention
curl -s http://127.0.0.1:3100/ready
```

---

## Security Incidents

### Response Playbook
1. **Detect**: Alert from Falco/Alertmanager
2. **Assess**: Check logs (`docker logs`, Loki queries)
3. **Contain**: Stop affected container (`docker stop`)
4. **Investigate**: Preserve evidence, check OpenBao audit log
5. **Remediate**: Fix root cause, rotate affected secrets
6. **Verify**: Run health check, monitor for recurrence
7. **Document**: Update incident report

### Emergency Contacts
| Role | Contact |
|------|---------|
| Platform Admin | mkanavi (via Telegram) |
| DevOps | mkanavi (via SSH) |
| Security | mkanavi (direct) |

### Audit Logs
- **OpenBao**: `docker exec iacgenie_openbao bao audit status`
- **Nginx**: `/var/log/nginx/access.log` + `/var/log/nginx/error.log`
- **Falco**: Via Falcosidekick UI at port 2800
- **Keycloak**: Admin audit log in Keycloak console
