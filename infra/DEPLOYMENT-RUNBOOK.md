# IacGenie Platform — Deployment Runbook

> **Last Updated**: 2026-08-16  
> **Target VM**: 192.168.0.118 (elementary OS 8)  
> **Repository**: https://github.com/manjufkanavi/iacgenie-platform

---

## Prerequisites

- SSH access to VM (`ssh mkanavi@192.168.0.118`)
- Cloudflare account with domain `iacgenie.com` configured
- OpenBao unseal keys (3 keys, Shamir 3/3)
- DNS records pointing `*.iacgenie.com` to Cloudflare Tunnel

---

## Full Deployment

### 1. Clone Repository

```bash
cd /home/mkanavi
git clone https://github.com/manjufkanavi/iacgenie-platform.git
cd iacgenie-platform
```

### 2. Verify Inventory

```bash
# Check inventory file
cat infra/ansible/inventory/hosts.yml

# Verify group vars
cat infra/ansible/inventory/group_vars/all.yml
cat infra/ansible/inventory/group_vars/docker_services.yml
```

### 3. Dry Run (Recommended)

```bash
cd infra/ansible
ansible-playbook site.yml --check --diff
```

This shows what would change without making any modifications.

### 4. Deploy

```bash
ansible-playbook site.yml
```

The playbook runs roles in this order:
1. `common` — apt packages, SSH, NTP
2. `docker` — Docker Engine installation
3. `openbao` — OpenBao + Raft storage
4. `keycloak` — Keycloak + realm provisioning
5. `gitea` — Gitea container
6. `docker-compose-generator` — Generate docker-compose.yml
7. `nginx-config` — Nginx reverse proxy
8. `cloudflare_tunnel` — Cloudflare Tunnel
9. `monitoring` — Prometheus + Grafana + Loki
10. `backup` — Backup cron job

### 5. Verify Deployment

```bash
# Check all containers are running
docker ps --format 'table {{.Names}}\t{{.Status}}'

# Run health checks
cd ~/iacgenie-platform/infra && ./health-check.sh

# Check Nginx config
sudo nginx -t && sudo systemctl reload nginx

# Verify Cloudflare Tunnel
sudo systemctl status cloudflared
```

---

## Partial Deployment

### Deploy Specific Role

```bash
cd infra/ansible
ansible-playbook site.yml --role nginx-config
ansible-playbook site.yml --role monitoring
ansible-playbook site.yml --role openbao
```

### Deploy Specific Tags

```bash
# Deploy only backup role
ansible-playbook site.yml --tags backup

# Deploy only monitoring role
ansible-playbook site.yml --tags monitoring
```

---

## Service-Specific Deployment

### PostgreSQL

```bash
# PostgreSQL is managed via docker-compose-generator role
ansible-playbook site.yml --role docker-compose-generator
```

### OpenBao

```bash
# Unseal OpenBao (if sealed)
docker exec iacgenie_openbao bao operator unseal <key1>
docker exec iacgenie_openbao bao operator unseal <key2>
docker exec iacgenie_openbao bao operator unseal <key3>

# Verify unsealed
docker exec iacgenie_openbao bao operator list-seal-status
```

### Keycloak

```bash
# Reset admin password
docker exec iacgenie_keycloak /opt/keycloak/bin/kc.sh \
  reset-password --username admin --realm master --password <new-password>

# Verify Keycloak is running
curl -s http://127.0.0.1:9003/health/ready
```

---

## Rollback

### 1. Identify Previous Commit

```bash
cd ~/iacgenie-platform
git log --oneline -10
```

### 2. Checkout Previous Version

```bash
git checkout <previous-commit-sha>
```

### 3. Redeploy

```bash
cd infra/ansible
ansible-playbook site.yml
```

### 4. Restore Data (if needed)

```bash
cd ~/iacgenie-platform/infra
./backup-restore.sh list
./backup-restore.sh restore <backup-file>
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs iacgenie_<service>

# Check container status
docker inspect iacgenie_<service>

# Check resource usage
docker stats --no-stream
```

### Nginx Config Error

```bash
# Test config
sudo nginx -t

# View error log
sudo tail -50 /var/log/nginx/error.log

# Reload
sudo systemctl reload nginx
```

### OpenBao Sealed

```bash
# Check status
docker exec iacgenie_openbao bao status

# Unseal with keys
docker exec -it iacgenie_openbao bao operator unseal
# Enter each key when prompted
```

### Cloudflare Tunnel Down

```bash
# Check status
sudo systemctl status cloudflared

# Check logs
sudo journalctl -u cloudflared --since "1 hour ago"

# Restart
sudo systemctl restart cloudflared
```

### High Memory Usage

```bash
# Check memory per container
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}"

# Restart high-memory service
docker restart iacgenie_<service>
```

---

## Maintenance Tasks

### Daily

- ✅ Backup runs automatically at 2:00 AM
- ✅ OpenBao Raft snapshots run automatically

### Weekly

```bash
# Check disk usage
df -h /home/mkanavi/docker/iacgenie

# Check container logs for errors
docker logs --since 7d iacgenie_openbao | grep -i error
docker logs --since 7d iacgenie_keycloak | grep -i error

# Verify backup integrity
cd ~/iacgenie-platform/infra && ./backup-restore.sh verify
```

### Monthly

```bash
# Update Docker images
cd ~/iacgenie-platform/infra/ansible
ansible-playbook site.yml --tags docker-compose-generator

# Rotate OpenBao tokens
# (tokens expire after 30 days)

# Review access logs
sudo tail -1000 /var/log/nginx/access.log | awk '{print $1}' | sort | uniq -c | sort -rn
```
