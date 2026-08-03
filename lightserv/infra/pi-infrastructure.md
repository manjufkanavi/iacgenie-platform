# Raspberry Pi Infrastructure — IacGenie Platform Services

## Overview

The Raspberry Pi acts as a **headless infrastructure provider**. It does NOT run development workloads. Development (backend + frontend) runs on the local Mac. The Pi hosts only platform services that the Mac applications consume remotely.

### Architecture

```
Cloudflare DNS (*.iacgenie.com)
        │
        ▼
Cloudflare Tunnel (cloudflared container on RPi)
        │
        ├── jenkins.iacgenie.com      → Jenkins CI/CD
        ├── minio.iacgenie.com        → Object storage
        ├── console.minio.iacgenie.com→ MinIO Console
        ├── auth.iacgenie.com         → Keycloak (OIDC/OAuth)
        ├── vault.iacgenie.com        → OpenBao (secrets)
        ├── postgres.iacgenie.com     → PostgreSQL (TCP)
        └── redis.iacgenie.com        → Redis (TCP)

Prometheus & Grafana are NOT exposed via tunnel — accessible locally on Pi
only (Mac can reach via SSH to Pi).

Raspberry Pi (192.168.0.101)
├── Platform Services:
│   ├── postgres, redis, minio, openbao, openbao-init
│   ├── keycloak, minio-init
│   ├── jenkins, prometheus, grafana, cloudflared
└── NOT on Pi (run on Mac, managed externally):
    ├── iacgenie backend  (FastAPI)
    └── iacgenie frontend (Nginx SPA)
```

## Hardware & Storage

### Hardware

| Component | Specification |
|-----------|--------------|
| **Model** | Raspberry Pi 5 (8 GB) |
| **CPU** | aarch64 |
| **Kernel** | 6.17.0-1008-raspi |
| **OS** | Ubuntu 25.10 SMP PREEMPT_DYNAMIC |
| **Total RAM** | 7.7 GiB |

### Login

| Field | Value |
|-------|-------|
| **IP** | `192.168.0.101` |
| **User** | `mkanavi` |
| **SSH Key** | `~/.ssh/raspberry_key` (ed25519) |
| **SSH Alias** | `ssh rpi` |

### Storage

| Location | Device | Size | Purpose |
|----------|--------|------|---------|
| MicroSD | `/dev/mmcblk0` | 238 GB | OS + system containers (cloudflared) |
| USB Drive | `/dev/sda1` | 120 GB | Data volumes (`/mnt/storage/docker/`) |

Data volumes are stored on the USB drive to preserve microSD lifespan. Docker images and caches are managed via `docker image prune` during maintenance.

---

## Services

### Platform Services (on Pi)

| # | Service | Image | Volume | Port (external) | Port (internal) | Memory | Subdomain |
|---|---------|-------|--------|-----------------|-----------------|--------|-----------|
| 1 | **PostgreSQL** | postgres:15-alpine | postgres_data | 5432 | 5432 | 1G | postgres.iacgenie.com (TCP) |
| 2 | **Redis** | redis:7-alpine | redis_data | 6379 | 6379 | 256M | redis.iacgenie.com (TCP) |
| 3 | **MinIO** | minio/minio:latest | minio_data | 9000 / 9001 | 9000 / 9001 | 512M | minio.iacgenie.com |
| 4 | **OpenBao** | quay.io/openbao/openbao:latest | openbao_data | 8200 | 8200 | 512M | vault.iacgenie.com |
| 5 | **OpenBao Init** | curlimages/curl:8.6.0 | — | — | — | — | (one-shot) |
| 6 | **Keycloak** | quay.io/keycloak/keycloak:26.0 | (postgres) | 8080 | 8080 | 1G | auth.iacgenie.com |
| 7 | **MinIO Init** | minio/mc:latest | — | — | — | — | (one-shot) |
| 8 | **Jenkins** | jenkins/jenkins:lts-jdk17 | jenkins_data | 8085 | 8080 | 1G | jenkins.iacgenie.com |
| 9 | **Prometheus** | prom/prometheus:latest | prometheus_data | 127.0.0.1:9090 | 9090 | 512M | (local only) |
| 10 | **Grafana** | grafana/grafana:latest | grafana_data | 3001 | 3000 | 512M | (local only) |
| 11 | **Cloudflared** | cloudflare/cloudflared:latest | cloudflared_config (microSD) | — | — | 128M | tunnel agent |

**Total memory**: ~5.1 GB of 7.7 GB (~2.6 GB headroom)

### One-Shot Init Containers

| Service | Purpose |
|---------|---------|
| `openbao-init` | Configures KV-v2 engine + policies via `/bootstrap.sh` |
| `minio-init` | Creates buckets: `artifacts`, `logs`, `plans`, `outputs` |

Both run once on startup and auto-restart: "no".

---

## Cloudflare Tunnel

### DNS Records

All `*.iacgenie.com` subdomains use CNAME records pointing to `<tunnel-id>.cfargotunnel.com` via Cloudflare Zero Trust.

### Tunnel Configuration

File: `iacgenie/docker/cloudflared/config.yml`

```yaml
tunnel: iacgenie-pi
credentials-file: /etc/cloudflared/auth/token.json

ingress:
  - hostname: jenkins.iacgenie.com
    path: /*
    service: http://jenkins:8080

  - hostname: postgres.iacgenie.com
    path: /*
    service: tcp://postgres:5432

  - hostname: redis.iacgenie.com
    path: /*
    service: tcp://redis:6379

  - hostname: minio.iacgenie.com
    path: /*
    service: http://minio:9000

  - hostname: console.minio.iacgenie.com
    path: /*
    service: http://minio:9001

  - hostname: vault.iacgenie.com
    path: /*
    service: http://openbao:8200

  - hostname: auth.iacgenie.com
    path: /*
    service: http://keycloak:8080

  - service: http_status:404
```

### Token

Obtained from Cloudflare Zero Trust → Tunnels. Stored in `iacgenie/docker/cloudflared/auth.json` on the Pi at `/etc/cloudflared/auth/token.json`.

---

## Secrets Management

### Environment File

File: `iacgenie/docker/.env.pi`

Contains all secrets for Pi services. Transferred to Pi as `/mnt/storage/docker/iacgenie/.env`.

| Category | Variables |
|----------|-----------|
| PostgreSQL | `POSTGRES_SUPER_PASSWORD`, `POSTGRES_APP_PASSWORD`, `POSTGRES_KC_PASSWORD` |
| Redis | `REDIS_PASSWORD` |
| MinIO | `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` |
| OpenBao | `OPENBAO_ROOT_TOKEN`, `OPENBAO_TOKEN` |
| Keycloak | `KEYCLOAK_ADMIN`, `KEYCLOAK_ADMIN_PASSWORD` |
| Grafana | `GRAFANA_ADMIN_USER`, `GRAFANA_ADMIN_PASSWORD` |
| Jenkins | `JENKINS_ADMIN_USER`, `JENKINS_ADMIN_PASSWORD` |
| JWT | `JWT_SECRET` |
| External | `SMTP2GO_API_KEY`, `SENTRY_DSN`, `CLOUDFLARE_TUNNEL_TOKEN` |
| LLM Keys | `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` |
| OAuth | `GOOGLE_CLIENT_ID/SECRET`, `GITHUB_CLIENT_ID/SECRET` |

### External Secrets (manual setup)

| Secret | Source |
|--------|--------|
| `CLOUDFLARE_TUNNEL_TOKEN` | Cloudflare Zero Trust → Tunnels |
| `SMTP2GO_API_KEY` | SMTP2GO Dashboard |
| `SENTRY_DSN` | Sentry Dashboard |

---

## Jenkins CI/CD

### Access

- URL: `https://jenkins.iacgenie.com`
- Admin user: `admin`
- Admin password: `91Y53bvH8VcSlOtPAngfgE1LVdD95pjwguoLU9SWpfM` (from `JENKINS_ADMIN_PASSWORD` in `.env.pi`)
- Admin credentials also in: `iacgenie/admin_credentials.txt`
- **Full reference**: `iacgenie/infra/jenkins-credentials.md`

### Initial Setup

Jenkins uses JCasC (Configuration as Code) for automatic first-boot configuration:

1. On first boot, `startup.sh` installs the `configuration-as-code` plugin
2. Container restarts automatically (Docker restart policy)
3. JCasC reads `jenkins.config.yml` and creates the admin user with `ProjectMatrix` authorization
4. Jenkins starts with configured security realm and authorization

The setup wizard is pre-skipped (`jenkins.install.runSetupWizard=false`).

### Authorization

- Strategy: `ProjectMatrix` (admin user has explicit Administer/Create/Configure permissions)
- Security Realm: Jenkins' own user database (local)
- Signup: Disabled

### GitHub SCM Credentials

| ID | Type | Configured Via |
|----|------|----------------|
| `github-token` | Secret Text | JCasC (`${GITHUB_TOKEN:-}`) |
| `github-ssh` | SSH Key | Added via Jenkins UI (Manage Jenkins → Credentials → System) |

### Storage

Jenkins home is at `/var/jenkins_home`, backed by `/home/mkanavi/docker/iacgenie/jenkins_data/` on local disk (VM, not USB drive).

**Encryption keys to back up separately** (stored in `jenkins_data/secrets/`):
- `master.key` — decrypts credential store
- `secret.key` — secondary decryption key

See `iacgenie/infra/jenkins-credentials.md` for backup procedures and credential management.

---

## Keycloak

### Access

- URL: `https://auth.iacgenie.com`
- Admin console: `https://auth.iacgenie.com/admin/`
- Admin: `admin` / from `KEYCLOAK_ADMIN_PASSWORD`
- Database: PostgreSQL `keycloak` database

### Configuration

Realm is imported from `iacgenie/keycloak/realm-export.json` on startup.
Keycloak is configured with `KC_HOST_NAME: auth.iacgenie.com` to ensure correct redirect URLs (prevents redirect to `/admin/master/console/`).

### SMTP

Configured via SMTP2GO for email notifications. Set `SMTP2GO_USERNAME` and `SMTP2GO_API_KEY` in `.env.pi`.

---

## OpenBao (Vault)

### Access

- URL: `https://vault.iacgenie.com`
- Dev mode: running in development mode with root token from `OPENBAO_ROOT_TOKEN`

### Secret Engine

KV-v2 engine is configured by `openbao-init` container via `/bootstrap.sh`.

---

## MinIO

### Access

| Service | URL | Port |
|---------|-----|------|
| API | `https://minio.iacgenie.com` | 9000 |
| Console | `https://console.minio.iacgenie.com` | 9001 |

### Buckets

Created by `minio-init`: `artifacts`, `logs`, `plans`, `outputs`

### Credentials

- User: `minioadmin` (from `MINIO_ROOT_USER`)
- Password: from `MINIO_ROOT_PASSWORD`

---

## PostgreSQL

### Access

- Port: 5432 (bound to all interfaces on Pi)
- Cloudflare tunnel: `postgres.iacgenie.com` (TCP passthrough — no web UI)
- Database: `iacgenie`
- App user: `iacgenie_user`
- Superuser: `postgres`

### CLI Access from Mac

```bash
# Connect as app user
ssh rpi "psql -h 127.0.0.1 -U iacgenie_user -d iacgenie"

# Connect as superuser
ssh rpi "psql -h 127.0.0.1 -U postgres -d postgres"

# Quick test
ssh rpi "psql -h 127.0.0.1 -U iacgenie_user -d iacgenie -c 'SELECT 1'"

# List databases
ssh rpi "psql -h 127.0.0.1 -U postgres -c '\l'"
```

### Notes

- `postgres.iacgenie.com` via Cloudflare shows TCP ping but no web UI — PostgreSQL has no built-in web interface
- Use `pgAdmin`, DBeaver, or CLI for database management
- For local database GUI: `ssh -L 5432:localhost:5432 rpi` then connect via any PostgreSQL client to `localhost:5432`

---

## Redis

### Access

- Port: 6379 (bound to all interfaces on Pi)
- Cloudflare tunnel: `redis.iacgenie.com` (TCP passthrough — no web UI)
- Password: from `REDIS_PASSWORD` in `.env.pi`

### CLI Access from Mac

```bash
# Connect via CLI
ssh rpi "redis-cli -h 127.0.0.1 -a ${REDIS_PASSWORD} ping"

# Interactive session
ssh rpi "redis-cli -h 127.0.0.1 -a ${REDIS_PASSWORD}"

# Quick test
ssh rpi "redis-cli -h 127.0.0.1 -a ${REDIS_PASSWORD} ping"

# List keys
ssh rpi "redis-cli -h 127.0.0.1 -a ${REDIS_PASSWORD} KEYS '*'"
```

### Notes

- `redis.iacgenie.com` via Cloudflare shows TCP ping but no web UI — Redis has no built-in web interface
- For Redis GUI: `ssh -L 6379:localhost:6379 rpi` then connect via any Redis client to `localhost:6379`

---

## Monitoring

### Prometheus

- Port: 9090 (bound to `127.0.0.1` on Pi — not exposed to internet)
- Access from Mac: `ssh rpi "curl -s http://localhost:9090/-/healthy"`
- Access from Mac with browser: `ssh -L 9090:localhost:9090 rpi` then open `http://localhost:9090`
- Config: `iacgenie/prometheus.yml`
- Data: `/mnt/storage/docker/prometheus_data`
- Health check: `ssh rpi "curl -s http://localhost:9090/-/healthy"`

### Grafana

- Port: 3001 (bound to all interfaces on Pi, but not exposed via Cloudflare tunnel)
- Access from Mac: `ssh -L 3001:localhost:3001 rpi` then open `http://localhost:3001`
- Admin: `admin` / from `GRAFANA_ADMIN_PASSWORD` in `.env.pi`
- Data: `/mnt/storage/docker/grafana_data`
- Root URL: `https://dashboards.iacgenie.com` (configured for tunnel access)
- Datasources: Pre-configured via provisioning:
  - **Prometheus**: `http://prometheus:9090` (default)
  - **PostgreSQL**: `postgres:5432`, database `iacgenie`, user `iacgenie_user`

### Accessing Prometheus/Grafana from Mac

```bash
# SSH port forwarding for both services
ssh -L 9090:localhost:9090 -L 3001:localhost:3001 rpi

# Then open in browser:
# http://localhost:9090     → Prometheus
# http://localhost:3001     → Grafana (login required)
```

---

## Docker Compose Usage

### Start all services

```bash
ssh rpi "cd /mnt/storage/docker/iacgenie && docker compose -f docker-compose-pi.yml up -d"
```

### Check status

```bash
ssh rpi "cd /mnt/storage/docker/iacgenie && docker compose -f docker-compose-pi.yml ps"
```

### View logs

```bash
ssh rpi "cd /mnt/storage/docker/iacgenie && docker compose -f docker-compose-pi.yml logs -f"
```

### Restart a service

```bash
ssh rpi "cd /mnt/storage/docker/iacgenie && docker compose -f docker-compose-pi.yml restart jenkins"
```

### Stop all services

```bash
ssh rpi "cd /mnt/storage/docker/iacgenie && docker compose -f docker-compose-pi.yml down"
```

### Restart Pi (services auto-recover)

```bash
ssh rpi "sudo reboot"
```

All services have `restart: unless-stopped` — they auto-recover after reboot.

---

## File Transfer to Pi

### SCP files

```bash
scp -i ~/.ssh/raspberry_key iacgenie/docker-compose-pi.yml mkanavi@192.168.0.101:/mnt/storage/docker/iacgenie/
scp -i ~/.ssh/raspberry_key iacgenie/docker/.env.pi mkanavi@192.168.0.101:/mnt/storage/docker/iacgenie/.env
scp -i ~/.ssh/raspberry_key iacgenie/docker/cloudflared/config.yml mkanavi@192.168.0.101:/mnt/storage/docker/iacgenie/docker/cloudflared/config.yml
scp -i ~/.ssh/raspberry_key iacgenie/docker/jenkins/startup.sh mkanavi@192.168.0.101:/mnt/storage/docker/iacgenie/docker/jenkins/startup.sh
scp -i ~/.ssh/raspberry_key iacgenie/docker/jenkins/jenkins.config.yml mkanavi@192.168.0.101:/mnt/storage/docker/iacgenie/docker/jenkins/jenkins.config.yml
scp -i ~/.ssh/raspberry_key iacgenie/docker/grafana/provisioning/datasources/datasources.yml mkanavi@192.168.0.101:/mnt/storage/docker/iacgenie/docker/grafana/provisioning/datasources/datasources.yml
```

### Transfer directory

```bash
scp -r -i ~/.ssh/raspberry_key iacgenie/docker/openbao/ mkanavi@192.168.0.101:/mnt/storage/docker/iacgenie/docker/openbao/
```

### Redeploy after config changes

```bash
ssh rpi "cd /mnt/storage/docker/iacgenie && docker compose -f docker-compose-pi.yml down && docker compose -f docker-compose-pi.yml up -d"
```

### Redeploy after docker-compose-pi.yml changes (selective)

```bash
ssh rpi "cd /mnt/storage/docker/iacgenie && docker compose -f docker-compose-pi.yml stop cloudflared && docker compose -f docker-compose-pi.yml rm -f cloudflared && docker compose -f docker-compose-pi.yml up -d cloudflared"
```

### Deploying new infrastructure fixes

For infrastructure changes (Cloudflare config, docker-compose, new files):

```bash
# 1. SCP all changed/new files from Mac
scp -i ~/.ssh/raspberry_key iacgenie/docker-compose-pi.yml mkanavi@192.168.0.101:/tmp/
scp -i ~/.ssh/raspberry_key iacgenie/docker/cloudflared/config.yml mkanavi@192.168.0.101:/tmp/
scp -i ~/.ssh/raspberry_key iacgenie/docker/jenkins/startup.sh mkanavi@192.168.0.101:/tmp/
scp -i ~/.ssh/raspberry_key iacgenie/docker/jenkins/jenkins.config.yml mkanavi@192.168.0.101:/tmp/
scp -i ~/.ssh/raspberry_key iacgenie/docker/grafana/provisioning/datasources/datasources.yml mkanavi@192.168.0.101:/tmp/

# 2. On Pi terminal (run sudo locally on Pi):
sudo mv /tmp/docker-compose-pi.yml /mnt/storage/docker/iacgenie/
sudo mv /tmp/config.yml /mnt/storage/docker/iacgenie/docker/cloudflared/config.yml
sudo mkdir -p /mnt/storage/docker/iacgenie/docker/jenkins
sudo mv /tmp/startup.sh /mnt/storage/docker/iacgenie/docker/jenkins/startup.sh
sudo mv /tmp/jenkins.config.yml /mnt/storage/docker/iacgenie/docker/jenkins/jenkins.config.yml
sudo chmod +x /mnt/storage/docker/iacgenie/docker/jenkins/startup.sh
sudo mkdir -p /mnt/storage/docker/iacgenie/docker/grafana/provisioning/datasources
sudo mv /tmp/datasources.yml /mnt/storage/docker/iacgenie/docker/grafana/provisioning/datasources/datasources.yml

# 3. Redeploy services (in dependency order)
cd /mnt/storage/docker/iacgenie
docker compose -f docker-compose-pi.yml down cloudflared
docker compose -f docker-compose-pi.yml up -d cloudflared
docker compose -f docker-compose-pi.yml up -d jenkins
# Wait for JCasC init (~1-2 min for plugin install + restart)
sleep 90
docker compose -f docker-compose-pi.yml restart keycloak
docker compose -f docker-compose-pi.yml restart grafana
```

---

## Digger Phase 2b — Planned Architecture

### Overview

Digger (Terraform CI/CD) will be added as the next CI/CD service on the Pi after Jenkins.

### Planned Setup

- Image: `diggerhq/digger:latest`
- Runs as a separate container or within Jenkins pipeline
- Integrates with Keycloak for authentication
- Uses MinIO as Terraform remote state backend
- Uses OpenBao for Terraform secrets (AWS/GCP credentials)

### Planned docker-compose addition

```yaml
digger:
  image: diggerhq/digger:latest
  environment:
    DIGGER_OIDC_CLIENT_ID: ${DIGGER_CLIENT_ID}
    DIGGER_OIDC_CLIENT_SECRET: ${DIGGER_CLIENT_SECRET}
    TF_HTTP_ADDRESS: http://minio:9000/iacgenie/terraform
    TF_HTTP_SECRET_address: http://minio:9000/iacgenie/terraform
  volumes:
    - /mnt/storage/docker/digger_data:/home/digger/.digger
  depends_on:
    - minio
    - openbao
  deploy:
    resources:
      limits:
        memory: 512M
        cpus: "0.5"
```

### Required additional secrets

| Variable | Source |
|----------|--------|
| `DIGGER_CLIENT_ID` | Digger Cloud |
| `DIGGER_CLIENT_SECRET` | Digger Cloud |
| `DIGGER_PROJECT` | Digger Cloud |

### DNS records needed

- `digger.iacgenie.com` → CNAME to tunnel

---

## Troubleshooting

### Service won't start

```bash
# Check service logs
ssh rpi "cd /mnt/storage/docker/iacgenie && docker compose -f docker-compose-pi.yml logs <service>"

# Check resource usage
ssh rpi "docker stats --no-stream"
```

### OOM kills

If a service is killed due to memory, check:
```bash
ssh rpi "docker inspect --format='{{.Name}}: {{.State.OOMKilled}}' $(docker ps -aq)"
```

Adjust memory limits in `docker-compose-pi.yml` if needed.

### Cloudflared 503 errors

```bash
# Check tunnel status
ssh rpi "docker logs iacgenie-cloudflared"

# Verify ingress config
ssh rpi "cat /etc/cloudflared/config/config.yml"
```

### Storage full

```bash
# Check USB drive usage
ssh rpi "df -h /mnt/storage"

# Find large directories
ssh rpi "du -sh /mnt/storage/docker/*/ 2>/dev/null | sort -rh | head -10"
```

### Jenkins slow startup

Jenkins has a 60s `start_period` in its healthcheck. It typically takes 1-2 minutes to fully initialize. Check:
```bash
ssh rpi "docker logs -f iacgenie-jenkins"
```

### JCasC first-boot issue

Jenkins uses JCasC for admin user creation on first boot. If Jenkins doesn't start properly:

```bash
# Check startup progress — look for "JCasC plugin installed" or "starting Jenkins..."
ssh rpi "docker logs iacgenie-jenkins"

# Verify JCasC plugin is installed
ssh rpi "docker exec iacgenie-jenkins ls /usr/share/jenkins/plugins/configuration-as-code"

# Verify config file is mounted
ssh rpi "docker exec iacgenie-jenkins cat /usr/share/jenkins/ref/jenkins.config.yml"

# Force restart (JCasC runs on every boot)
ssh rpi "cd /mnt/storage/docker/iacgenie && docker compose -f docker-compose-pi.yml restart jenkins"
```

If Jenkins still doesn't create admin user after restart:
```bash
# Check if JAVA_OPTS is causing issues
ssh rpi "docker inspect iacgenie-jenkins | grep -A5 JAVA_OPTS"

# Check Jenkins logs for JCasC errors
ssh rpi "docker logs iacgenie-jenkins 2>&1 | grep -i 'jasc\\|config\\|admin'"
```

### PostgreSQL init script issues

PostgreSQL runs `privileged: true` to handle the init script's DO block. If the init script fails:
```bash
ssh rpi "docker logs iacgenie-postgres | tail -50"
ssh rpi "cat /mnt/storage/docker/iacgenie/docker/postgres/init.sh"
```

---

## Maintenance

### Backup data volumes

```bash
# Backup USB drive data
ssh rpi "tar czf /tmp/iacgenie-backup-$(date +%Y%m%d).tar.gz -C /mnt/storage/docker ."
# Then SCP from Pi to local machine
scp -i ~/.ssh/raspberry_key mkanavi@192.168.0.101:/tmp/iacgenie-backup-*.tar.gz /tmp/
```

### Update services

```bash
# Pull latest images
ssh rpi "cd /mnt/storage/docker/iacgenie && docker compose -f docker-compose-pi.yml pull"

# Restart with new images
ssh rpi "cd /mnt/storage/docker/iacgenie && docker compose -f docker-compose-pi.yml up -d"
```

### Docker cleanup

```bash
# Remove unused images
ssh rpi "docker image prune -a -f --filter 'label!=maintained'"

# Remove unused volumes (careful!)
ssh rpi "docker volume prune -f"
```
