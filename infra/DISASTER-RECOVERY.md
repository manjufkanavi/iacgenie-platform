# IacGenie Platform — Disaster Recovery Procedures

> **Last Updated**: 2026-08-16  
> **VM**: 192.168.0.118  
> **Backup Schedule**: Daily at 02:00 AM (automatic)

---

## Backup Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  Docker     │────▶│  backup-     │────▶│  Google      │
│  Volumes    │     │  restore.sh  │     │  Drive       │
│  & Configs  │     │  (cron 02:00)│     │  (encrypted) │
└─────────────┘     └──────────────┘     └──────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │  OpenBao     │
                  │  Raft Snap   │
                  │  (auto)      │
                  └──────────────┘
```

### Backup Locations

| Data | Location | Retention |
|------|----------|-----------|
| PostgreSQL | `~/iacgenie-platform/infra/backups/postgres_*.sql.gz.gpg` | 7 days |
| MinIO | `~/iacgenie-platform/infra/backups/minio_*.tar.gz.gpg` | 7 days |
| Gitea | `~/iacgenie-platform/infra/backups/gitea_*.tar.gz.gpg` | 7 days |
| OpenBao | `~/iacgenie-platform/infra/backups/openbao_*.tar.gz.gpg` | 7 days |
| Keycloak | `~/iacgenie-platform/infra/backups/keycloak_*.tar.gz.gpg` | 7 days |
| Configs | `~/iacgenie-platform/infra/backups/configs_*.tar.gz.gpg` | 7 days |

---

## Disaster Scenarios

### 1. Single Service Failure

**Impact**: One service unavailable  
**Recovery Time**: < 5 minutes

```bash
# Check service status
docker ps --format 'table {{.Names}}\t{{.Status}}'

# Restart the service
docker restart iacgenie_<service>

# If container won't start, recreate
docker rm -f iacgenie_<service>
docker compose -f /home/mkanavi/docker/iacgenie/docker-compose.yml up -d <service>
```

### 2. Data Corruption

**Impact**: Data loss in one service  
**Recovery Time**: 15-30 minutes

```bash
# List available backups
cd ~/iacgenie-platform/infra && ./backup-restore.sh list

# Verify backup integrity
./backup-restore.sh verify

# Restore specific service
./backup-restore.sh restore postgres <backup-file.gpg>
./backup-restore.sh restore minio <backup-file.gpg>
./backup-restore.sh restore gitea <backup-file.gpg>

# Restart affected service
docker restart iacgenie_<service>
```

### 3. OpenBao Sealed

**Impact**: All secrets inaccessible, services may fail  
**Recovery Time**: 2-5 minutes

```bash
# Check status
docker exec iacgenie_openbao bao status

# Unseal with keys (threshold: 3/3)
docker exec iacgenie_openbao bao operator unseal <key1>
docker exec iacgenie_openbao bao operator unseal <key2>
docker exec iacgenie_openbao bao operator unseal <key3>

# Verify unsealed
docker exec iacgenie_openbao bao operator list-seal-status
```

### 4. Keycloak Lockout

**Impact**: All OIDC authentication broken  
**Recovery Time**: 5 minutes

```bash
# Get admin password from OpenBao
bao kv get iacgenie/kv/keycloak/admin_password

# Reset admin password
docker exec iacgenie_keycloak /opt/keycloak/bin/kc.sh set-password \
  --username admin --realm master --password <new-password>

# Verify access
curl -s http://127.0.0.1:9003/health/ready
```

### 5. Nginx Config Error

**Impact**: All external access broken  
**Recovery Time**: 2 minutes

```bash
# Test config
sudo nginx -t

# View errors
sudo tail -50 /var/log/nginx/error.log

# Reload config
sudo systemctl reload nginx

# If config is broken, redeploy
cd ~/iacgenie-platform/infra/ansible && ansible-playbook site.yml --role nginx-config
```

### 6. Full VM Loss

**Impact**: Complete infrastructure loss  
**Recovery Time**: 1-2 hours

```bash
# Step 1: Provision new VM
sudo apt update && sudo apt install -y docker.io ansible git

# Step 2: Clone repository
git clone https://github.com/manjufkanavi/iacgenie-platform.git
cd iacgenie-platform

# Step 3: Deploy infrastructure
cd infra/ansible && ansible-playbook site.yml

# Step 4: Restore data from backup
cd ~/iacgenie-platform/infra
./backup-restore.sh list
./backup-restore.sh verify
./backup-restore.sh restore postgres <latest-backup.gpg>
./backup-restore.sh restore minio <latest-backup.gpg>
./backup-restore.sh restore gitea <latest-backup.gpg>

# Step 5: Unseal OpenBao
docker exec iacgenie_openbao bao operator unseal <key1>
docker exec iacgenie_openbao bao operator unseal <key2>
docker exec iacgenie_openbao bao operator unseal <key3>

# Step 6: Verify
./health-check.sh
```

---

## Backup Verification

### Weekly Verification

```bash
# List all backups
cd ~/iacgenie-platform/infra && ./backup-restore.sh list

# Verify backup integrity
./backup-restore.sh verify

# Test restore to isolated environment (monthly)
./backup-restore.sh restore --test postgres <backup-file>
```

### Backup Rotation

Backups are automatically rotated daily:
- Keeps 7 days of backups
- Oldest backups are deleted automatically
- Encrypted with GPG before upload to Google Drive

---

## Recovery Checklist

### After Any Disaster

- [ ] Verify all containers are running: `docker ps`
- [ ] Check health status: `./health-check.sh`
- [ ] Verify OpenBao is unsealed: `bao status`
- [ ] Verify Nginx config: `sudo nginx -t`
- [ ] Verify Cloudflare Tunnel: `sudo systemctl status cloudflared`
- [ ] Verify external access: curl all public endpoints
- [ ] Check monitoring: Grafana dashboards show green
- [ ] Review logs for errors: `docker logs --since 1h iacgenie_<service>`
- [ ] Verify backup job is running: `systemctl status backup-cron`

---

## Prevention Measures

### Disk Space Monitoring

```bash
# Check disk usage
df -h /home/mkanavi/docker/iacgenie

# Check container log sizes
docker system df

# Clean up old logs
docker system prune -f
```

### Memory Monitoring

```bash
# Check memory usage
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}"

# Check for memory leaks
docker stats --no-stream --format "{{.Name}}: {{.MemUsage}}" | sort -t: -k2 -hr
```

### Log Rotation

All containers use `json-file` logging driver with:
- `max-size: 100m`
- `max-file: 3`

This prevents disk exhaustion from container logs.
