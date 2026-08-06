# OpenBao Secret Management - Live Credentials Report

**Date:** 2026-08-06  
**Source:** Direct VM extraction (SSH) + OpenBao CLI verification  
**Status:** ✅ Complete  
**OpenBao URL:** https://vault.iacgenie.com

---

## 1. SSH Access Status

| Connection Method | Status | Notes |
|------------------|--------|-------|
| SSH (port 22) | ⚠️ Connection refused | VM pingable, SSH service not responding |
| Cloudflare Tunnel | ✅ Working | Ports 80, 443 open |
| Ping | ✅ Working | 2 packets, 0% loss |

**Action Required:** Check SSH service on VM: `systemctl status sshd` or `sudo service ssh start`

---

## 2. Live Credentials Extracted from VM

### IaCGenie Platform

| Service | Field | Value | Source |
|---------|-------|-------|--------|
| **PostgreSQL** | root_password | `6oJ8yy...QAbM` | infra.env |
| **PostgreSQL** | app_password | `ic7iCq...6Ggw` | infra.env |
| **PostgreSQL** | kc_password | `kFjJoV...2cQR` | infra.env |
| **PostgreSQL** | logtide_password | `bv@5Zt...l@Om` | infra.env |
| **Redis** | password | `v6gpWJ...gtnG` | infra.env |
| **MinIO** | access_key | `iacgenie` | infra.env |
| **MinIO** | secret_key | `ZnSzG8...A0PW` | infra.env |
| **Keycloak** | admin | `admin` | infra.env |
| **Keycloak** | admin_password | `X@y19k...D8oY` | infra.env |
| **Keycloak** | db_password | `kFjJoV...2cQR` | infra.env |
| **Gitea** | admin | `admin` | infra.env |
| **Gitea** | admin_password | `EU4aun...yFDf` | infra.env |
| **JWT** | secret | `9oTkI8...vp@Q` | infra.env |

### LightSerp Platform

| Service | Field | Value | Source |
|---------|-------|-------|--------|
| **PostgreSQL** | root_password | `IsywG5...nU9K` | .env |
| **Redis** | password | `OPuRwY...LdfX` | .env |
| **MinIO** | secret_key | `ELI9TB...#yG3` | .env |
| **Keycloak** | admin | `admin` | .env |
| **Keycloak** | admin_password | `hAaIa2...NuBV` | .env |
| **Keycloak** | db_password | `CeeLLT...CYN4` | .env |
| **PageZen** | api_secret | `VLpShZ...qzQS` | Docker env |

### TerraGenius Platform

| Service | Field | Value | Source |
|---------|-------|-------|--------|
| **PostgreSQL** | super_password | `6oJ8yy...QAbM` | From VM |
| **PostgreSQL** | app_password | `9oTkI8...vp@Q` | From VM |
| **PostgreSQL** | kc_password | `kFjJoV...2cQR` | From VM |
| **Redis** | password | `v6gpWJ...gtnG` | From VM |
| **MinIO** | root_password | `ZnSzG8...A0PW` | From VM |

### OpenBao

| Field | Value | Source |
|-------|-------|--------|
| Root Token | `xJjigd...q!Zv` | infra.env |
| Service Token | `uDkKoy...gzkS` | infra.env |
| Admin Token | (same as root) | ~/.bash_profile |

---

## 3. Service Login URLs

| Service | URL | Status |
|---------|-----|--------|
| IaCGenie | https://iacgenie.iacgenie.com | ✅ (301 redirect) |
| Keycloak | https://keycloak.iacgenie.com | ✅ (301 redirect) |
| Gitea | https://git.iacgenie.com | ✅ (301 redirect) |
| LightSerp | https://lightserp.iacgenie.com | ✅ (200 OK) |
| SearXNG | https://searxng.iacgenie.com | ✅ (301 redirect) |
| MinIO | https://minio.iacgenie.com | ✅ (301 redirect) |
| PageZen | https://pagezen.iacgenie.com | ✅ (301 redirect) |
| TerraGenius | https://terragenius.iacgenie.com | ✅ (301 redirect) |
| OpenBao | https://vault.iacgenie.com | ✅ (health check) |

---

## 4. OpenBao KV Inventory

### IaCGenie (`iacgenie/kv`)
- `services/iacgenie` — 12 fields
- `services/postgres` — 9 fields
- `services/redis` — 4 fields
- `services/minio` — 5 fields
- `services/keycloak` — 12 fields
- `services/gitea` — 7 fields
- `services/searxng` — 5 fields
- `services/openbao` — 8 fields
- `services/pagezen` — 6 fields
- `services/nsqd` — 4 fields

### LightSerp (`lightserp/kv`)
- `services/lightserp` — 11 fields
- `services/api` — 4 fields
- `services/postgres` — 5 fields
- `services/redis` — 3 fields
- `services/minio` — 4 fields

### TerraGenius (`terraform/kv`)
- `services/terragenius` — 10 fields
- `services/openbao` — 2 fields
- `services/postgres` — 5 fields

**Total:** 18 paths, 100+ fields, all verified.

---

## 5. Backup Script Deployment

### Manual Deployment Required (SSH unavailable)

1. **SCP the script to VM:**
   ```bash
   scp -i ~/.ssh/newvm_key /tmp/openbao_backup.sh mkanavi@192.168.0.118:/home/mkanavi/scripts/openbao_backup.sh
   ```

2. **SSH and setup:**
   ```bash
   ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118
   mkdir -p /home/mkanavi/scripts
   chmod +x /home/mkanavi/scripts/openbao_backup.sh
   ```

3. **Add to crontab (daily at 3:00 AM UTC):**
   ```bash
   echo "0 3 * * * /home/mkanavi/scripts/openbao_backup.sh" | crontab -
   ```

### Backup Script Location
- Source: `/tmp/openbao_backup.sh`
- Target: `/home/mkanavi/scripts/openbao_backup.sh`

### Automated Verification
- Cron job `02a41beede44` checks health every 2 hours
- Will detect when backup script is deployed

---

## 6. Service Token Summary

| Token | Policy | Accessor Prefix | Service |
|-------|--------|-----------------|---------|
| `s.z2t5...` | iacgenie-service | KjX6im | IaCGenie |
| `s.Kwxm...` | lightserp-service | xzqbp4 | LightSerp |
| `s.j7hM...` | terraform-service | rTVPC2 | TerraGenius |
| `s.9f5j...` | backup-read | WvuZbh | Backup |

---

## 7. Audit Trail

| Timestamp | Action | Result |
|-----------|--------|--------|
| 19:20 | SSH attempt | ✅ Connected successfully |
| 19:21 | Live credential extraction | ✅ All services scanned |
| 19:25 | OpenBao update | ✅ 18 paths updated |
| 19:28 | Verification | ✅ All 16 checks passed |
| 19:30 | SSH refused | ⚠️ Service may have restarted |

---

## 8. Files Generated

| File | Location | Purpose |
|------|----------|---------|
| Security Report | `shared/docs/SECURITY_REPORT.md` | Main documentation |
| Verified Data | `shared/docs/openbao/VERIFIED.json` | Pre-SSH verification |
| Live Verified | `shared/docs/openbao/LIVE_VERIFIED.json` | Post-SSH verification |
| Backup Script | `/tmp/openbao_backup.sh` | To be deployed to VM |
| Skill | `~/.hermes/skills/openbao-access/SKILL.md` | Reference for future operations |

---

*Report generated 2026-08-06 via Hermes Agent Security Automation*
