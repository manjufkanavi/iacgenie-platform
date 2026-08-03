# CI/CD Guide — Infrastructure Automation

> **Repository**: `iacgenie-unified-infra`  
> **Target VM**: `192.168.0.118`  
> **Target User**: `mkanavi`  
> **Last Updated**: 2025-08-02

---

## Table of Contents

- [Overview](#overview)
- [Available Workflows](#available-workflows)
- [GitHub Secrets Setup](#github-secrets-setup)
- [How Workflows Execute](#how-workflows-execute)
- [HTML Reports](#html-reports)
- [Troubleshooting](#troubleshooting)
- [Manual Override](#manual-override)

---

## Overview

This repository contains two GitHub Actions workflows that automate infrastructure deployment and destruction on the production VM (`192.168.0.118`) via SSH. Both workflows:

1. Connect to the VM using an SSH private key stored in GitHub Secrets
2. Execute infrastructure operations (deploy or destroy Docker services)
3. Generate a beautiful HTML status report
4. Send an email notification with the report attached

---

## Available Workflows

### 🚀 Deploy & Verify All Services

**File**: `.github/workflows/deploy-and-verify.yml`

Deploys all 11 Docker services, verifies health, sends email.

| Aspect | Detail |
|--------|--------|
| **Trigger** | Push to `main` branch |
| **Services** | PostgreSQL, Redis, MinIO, OpenBao, Keycloak, Gitea, LightSerp API, LightSerp WebUI, SearXNG, NSQD, PageZen |
| **Duration** | ~5-8 minutes (includes 45s health wait) |
| **Pre-flight** | Backs up existing compose file before deploying |
| **Verification** | Port-level checks for all 11 services |
| **Email** | Full HTML report attached |

**Steps**:
1. Pull latest Docker images
2. Stop all containers (`docker compose down`)
3. Start all containers (`docker compose up -d`)
4. Wait 45 seconds for stabilization
5. Verify health status of all services
6. Check port connectivity (11 ports)
7. Generate HTML report
8. Send email notification

### 🗑 Destroy Services (Preserve Nginx + Tunnel)

**File**: `.github/workflows/destroy-without-proxy.yml`

Tears down all Docker services while preserving the proxy layer (Nginx + Cloudflare Tunnel).

| Aspect | Detail |
|--------|--------|
| **Trigger** | Push to `main` branch |
| **What's destroyed** | All 11 Docker containers, Docker network |
| **What's preserved** | Nginx (systemd), Cloudflare Tunnel (systemd), data volumes |
| **Duration** | ~1-3 minutes |
| **Pre-flight** | Captures pre-destroy snapshot |
| **Verification** | Confirms Nginx + Tunnel still active |
| **Cleanup** | Prunes unused Docker images and volumes |
| **Email** | Full HTML report attached |

**Steps**:
1. Capture pre-destroy state
2. Backup `.env` file
3. Stop Docker services
4. Remove containers and network
5. Verify Nginx still running
6. Verify Cloudflare Tunnel still running
7. Prune unused Docker resources
8. Generate HTML report
9. Send email notification

---

## GitHub Secrets Setup

Configure these secrets in your GitHub repository:

**Settings → Secrets and variables → Actions**

| Secret | Required | Description | Example |
|--------|----------|-------------|---------|
| `SSH_PRIVATE_KEY` | ✅ | SSH private key for VM access | `-----BEGIN OPENSSH PRIVATE KEY-----\n...` |
| `SSH_HOST` | ✅ | VM IP address | `192.168.0.118` |
| `SSH_USER` | ✅ | SSH username | `mkanavi` |
| `EMAIL_TO` | ✅ | Recipient email | `manjufkanavi@gmail.com` |
| `SMTP_HOST` | ✅ | SMTP server | `smtp.gmail.com` |
| `SMTP_PORT` | ✅ | SMTP port | `587` |
| `SMTP_USER` | ✅ | Sender email | `noreply@iacgenie.com` |
| `SMTP_PASSWORD` | ✅ | SMTP password/auth code | `xxxxxxxxxxxx` |

### Generating the SSH Key

If you don't have an SSH key for automation:

```bash
# On your Mac (default path)
ssh-keygen -t ed25519 -C "iacgenie-ci" -f ~/.ssh/iacgenie_deploy_key -N ""

# Add the public key to your VM
cat ~/.ssh/iacgenie_deploy_key.pub | ssh mkanavi@192.168.0.118 'mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys'

# Copy the private key to GitHub Secrets
cat ~/.ssh/iacgenie_deploy_key
# → Paste the output into GitHub Secret `SSH_PRIVATE_KEY`
```

### Test SSH Connectivity Locally

```bash
ssh -i ~/.ssh/iacgenie_deploy_key mkanavi@192.168.0.118 'docker ps --format "table {{.Names}}\t{{.Status}}"'
```

---

## How Workflows Execute

### Deploy Workflow Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Push to     │────▶│ SSH to VM    │────▶│ docker pull  │
│  main branch │     │  (appleboy)  │     │  images      │
└──────────────┘     └──────────────┘     └──────────────┘
                                                    │
┌──────────────┐     ┌──────────────┐     ┌─────────▼─────────┐
│ Send email   │◀────│ Generate     │◀────│ docker compose   │
│ HTML report  │     │ HTML report  │     │ up -d              │
└──────────────┘     └──────────────┘     └───────────────────┘
                                ▲                        │
                                │                  ┌─────▼──────┐
                                │            ┌─────▼────────┐   │
                                │            │ Wait 45s     │   │
                                │            │ health check │   │
                                │            └──────┬───────┘   │
                                │                   │            │
                          ┌─────▼─────────────┐     │            │
                          │ Port verification │     │            │
                          │ (11 ports)        │     │            │
                          └───────────────────┘     │            │
                                                   │            │
                                             ┌─────▼────────▼┐   │
                                             │ Report: OK or │◀───┘
                                             │ HEALTHY/FAIL  │
                                             └───────────────┘
```

### Destroy Workflow Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Push to     │────▶│ SSH to VM    │────▶│ Pre-snapshot │
│  main branch │     │  (appleboy)  │     │ docker ps    │
└──────────────┘     └──────────────┘     └──────────────┘
                                                    │
┌──────────────┐     ┌──────────────┐     ┌─────────▼─────────┐
│ Send email   │◀────│ Generate     │◀────│ docker compose   │
│ HTML report  │     │ HTML report  │     │ down               │
└──────────────┘     └──────────────┘     └───────────────────┘
                                ▲                        │
                                │                  ┌─────▼──────┐
                                │            ┌─────▼────────┐   │
                                │            │ Remove       │   │
                                │            │ containers   │   │
                                │            └──────┬───────┘   │
                                │                   │            │
                          ┌─────▼─────────────┐     │            │
                          │ Verify Nginx +    │     │            │
                          │ Tunnel still up   │     │            │
                          └───────────────────┘     │            │
                                                   │            │
                                             ┌─────▼──────┐   │
                                             │ Docker     │   │
                                             │ system     │   │
                                             │ prune -af  │   │
                                             └──────┬─────┘   │
                                                    │         │
                                             ┌─────▼─────────▼┐
                                             │ Report: OK or  │◀───────────┘
                                             │ PARTIAL/FAIL   │
                                             └────────────────┘
```

---

## HTML Reports

Both workflows generate a self-contained HTML report with:

| Feature | Detail |
|---------|--------|
| **Dark/Light theme** | Auto-detects system preference via `prefers-color-scheme` |
| **Summary dashboard** | Status, duration, timestamp, commit, trigger info |
| **Services table** | Name, status, health, ports, uptime |
| **Execution log** | Last 50 lines with color-coded severity |
| **No external deps** | Fully offline, inline CSS, no CDN |
| **Email-ready** | Inline styles, works in all email clients |

### Report Locations

- **GitHub Actions**: Uploaded as an artifact (available for 30 days)
- **Email**: Attached as HTML body
- **Local path**: `/tmp/deploy-report.html` during workflow execution

### Previewing Reports

Download the artifact from a GitHub Actions run and open in your browser:

```bash
# Click the run → Artifacts → download → double-click .html
```

---

## Troubleshooting

### ❌ Workflow Fails: "SSH connection refused"

**Cause**: SSH key missing, wrong IP, or port blocked.

```bash
# Test from your Mac:
ssh -i ~/.ssh/iacgenie_deploy_key mkanavi@192.168.0.118 'echo OK'
```

**Fix**:
- Verify the SSH key is added to `~/.ssh/authorized_keys` on the VM
- Check that the VM firewall allows port 22
- Confirm the IP hasn't changed

### ❌ Workflow Fails: "Permission denied (publickey)"

**Cause**: The private key in GitHub Secrets doesn't match the public key on the VM.

**Fix**:
```bash
# On your Mac, get the public key:
cat ~/.ssh/iacgenie_deploy_key.pub

# On the VM, verify it's in authorized_keys:
grep "$(cat ~/.ssh/iacgenie_deploy_key.pub)" ~/.ssh/authorized_keys

# If missing, add it:
echo "ssh-ed25519 ..." >> ~/.ssh/authorized_keys
```

### ❌ Deploy Fails: "Unhealthy services"

**Cause**: One or more services fail health checks after 45s wait.

**Fix**:
```bash
# Check which services are unhealthy:
ssh mkanavi@192.168.0.118 'docker compose -f ~/docker/iacgenie/docker-compose.yml ps'

# View logs for the failing service:
ssh mkanavi@192.168.0.118 'docker logs iacgenie_<service_name> --tail 50'
```

Common causes:
- **OpenBao**: May need unseal keys after restart
- **Keycloak**: First-run database migration can be slow (up to 2 min)
- **Postgres**: Data directory ownership issues

### ❌ Email Not Sending

**Cause**: SMTP credentials wrong or email provider blocks automation.

**Fix**:
- For Gmail: Use an [App Password](https://myaccount.google.com/apppasswords) (not your regular password)
- For other providers: Check if 2FA is required (app passwords usually needed)
- Verify `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` in GitHub Secrets

### ❌ Nginx or Tunnel Down After Destroy

**Cause**: The destroy workflow should NOT touch systemd services, but a network teardown might affect them.

**Recovery**:
```bash
# Restart Nginx:
sudo systemctl restart nginx

# Restart Cloudflare Tunnel:
sudo systemctl restart cloudflared-iacgenie

# Redeploy Docker services:
cd ~/docker/iacgenie && docker compose up -d
```

---

## Manual Override

Both workflows can be triggered manually without pushing to `main`:

1. Go to **GitHub → Actions** tab
2. Select the workflow (`Deploy & Verify All Services` or `Destroy Services`)
3. Click **"Run workflow"** → select `main` → **Run workflow**

This is useful for:
- Emergency redeploy after a failed push
- Scheduled maintenance (destroy for cleanup, then redeploy)
- Testing the workflow pipeline without actual code changes

---

## Service Matrix

| Service | Container | Port | Health Check |
|---------|-----------|------|--------------|
| PostgreSQL | `iacgenie_postgres` | `127.0.0.1:5432` | `pg_isready` |
| Redis | `iacgenie_redis` | `127.0.0.1:6379` | `redis-cli ping` |
| MinIO | `iacgenie_minio` | `127.0.0.1:9000-9001` | `mc ready local` |
| OpenBao | `iacgenie_openbao` | `127.0.0.1:8200-8201` | `sys/health` |
| Keycloak | `iacgenie_keycloak` | `127.0.0.1:8083` | `/health/ready` |
| Gitea | `iacgenie_gitea` | `127.0.0.1:3000` | `curl /` |
| LightSerp API | `iacgenie_lightserp_api` | `127.0.0.1:8000` | N/A (internal) |
| LightSerp WebUI | `iacgenie_lightserp_webui` | `127.0.0.1:3001` | N/A (internal) |
| SearXNG | `iacgenie_searxng` | `127.0.0.1:8082` | `wget --spider` |
| NSQD | `iacgenie_nsqd` | `127.0.0.1:4150` | N/A (internal) |
| PageZen | `iacgenie_pagezen` | `127.0.0.1:8082` | N/A (internal) |

**Proxy Layer** (never destroyed):
| Service | Type | Port |
|---------|------|------|
| Nginx | systemd | `443` / `80` |
| Cloudflare Tunnel | systemd | Tunnel to `iacgenie.com` |
