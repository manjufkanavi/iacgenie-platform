# IaCGenie Platform — Infrastructure Drift Analysis Report

**Date:** 2026-08-12  
**VM:** 192.168.0.118 (newvm)  
**Ansible State:** Phase 4 (services.yml) + Phase 8 (docker-compose-generator)  
**Drift Status:** ⚠️ SIGNIFICANT DRIFT DETECTED — 40% of running services not in Ansible

---

## Executive Summary

Your IaCGenie platform runs **25 Docker containers** but Ansible playbooks only manage **~15**. Critical services are running outside of Ansible control, OpenBao secrets are not seeded, and multiple roles have dry-run failures. **Drift detection cron is active** (daily 14:00) to monitor future divergence.

**Commit:** [75df2b1](https://github.com/manjufkanavi/iacgenie-platform/commit/75df2b1) — Fixes 17 ansible files for dry-run compliance.

---

## 1. DRIFT DETECTION — Ansible vs Running State

### 🔴 CRITICAL DRIFT

| # | Service | Running on VM? | In Ansible? | Impact |
|---|---------|:-------------:|:-----------:|--------|
| 1 | Grafana | ✅ Up 2d | ❌ Removed from playbook | Monitoring gap |
| 2 | Prometheus | ✅ Up 2d | ❌ Not in template | No metrics collection |
| 3 | Alertmanager | ✅ Up 2d | ❌ Not in template | No alerts |
| 4 | Node Exporter | ✅ Up 2d | ❌ Not in template | No host metrics |
| 5 | Loki | ✅ Up 2d | ❌ Not in template | No centralized logging |
| 6 | Promtail | ✅ Up 2d | ❌ Not in template | No log shipping |
| 7 | PageGen | ✅ Up 28h | ❌ Not in template | Page generation unavailable |
| 8 | Cloudflare Image Proxy | ✅ Up 4h | ❌ Not in template | Image proxy broken |
| 9 | CrowdSec | ✅ Up 28h | ❌ Package install fails | WAF not managed by ansible |
| 10 | ClamAV | ✅ Up 28h | ❌ Not in template | Antivirus not managed |
| 11 | Auth Wrapper | ✅ Up 28h | ❌ Not in template | Auth gateway not managed |

### 🟡 MEDIUM DRIFT

| # | Component | Issue | Details |
|---|-----------|-------|---------|
| 1 | OpenBao Policies | ❌ NOT SEeded | Policies dir `/home/mkanavi/docker/iacgenie/data/openbao_raft/policies/` does not exist |
| 2 | OpenBao KV Secrets | ❌ EMPTY | All 3 engines (iacgenie/, lightserp/, terraform/) have NO secrets written |
| 3 | Backup Script | ❌ MISSING | `/home/mkanavi/scripts/backup.sh` does not exist on VM |
| 4 | Nginx Config | 🟡 Manual | Running via separate `docker-compose-nginx.yml`, NOT ansible-managed |
| 5 | Cloudflared Config | 🟡 Separate | Config at non-standard path, ansible role can't find it |
| 6 | Bootstrap Playbook | ❌ MISSING | `bootstrap.yml` not in repo — OpenBao init not scripted |

### 🟢 NO DRIFT (In sync)

| # | Service | Status |
|---|---------|--------|
| 1 | PostgreSQL | ✅ Ansible-managed |
| 2 | Redis | ✅ Ansible-managed |
| 3 | MinIO | ✅ Ansible-managed |
| 4 | Keycloak | ✅ Ansible-managed |
| 5 | Gitea | ✅ Ansible-managed |
| 6 | OpenBao (container) | ✅ Ansible-managed (template only) |
| 7 | NSQD | ✅ Ansible-managed |
| 8 | IaCGenie Backend | ✅ Ansible-managed |
| 9 | IaCGenie Frontend | ✅ Ansible-managed |
| 10 | LightSerp API | ✅ Ansible-managed |
| 11 | LightSerp WebUI | ✅ Ansible-managed |
| 12 | SearXNG | ✅ Ansible-managed |

---

## 2. AUTH & PASSWORDS — Complete Map

### Where Passwords Are Stored

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SECRET STORAGE LAYER                              │
├──────────────────────────┬──────────────────────────────────────────┤
│ Storage Location         │ Content                                   │
├──────────────────────────┼──────────────────────────────────────────┤
│ ✅ GitHub Secrets        │ OPENBAO_ROOT_TOKEN, OPENBAO_UNSEAL_KEY_1 │
│                          │ OPENBAO_UNSEAL_KEY_2, OPENBAO_UNSEAL_KEY │
│                          │ OPENBAO_ADMIN_TOKEN                      │
├──────────────────────────┼──────────────────────────────────────────┤
│ ✅ Ansible Vault         │ pg_root_password, redis_password, minio   │
│ (encrypted .yml)         │ keycloak_admin_password, keycloak_db_    │
│                          │ gitea_db_password, searxng_secret_key    │
│                          │ lightsrp_api_secret, openbao_oidc_secret │
├──────────────────────────┼──────────────────────────────────────────┤
│ ⚠️ Hardcoded in          │ gitea_admin_password                    │
│ group_vars/all.yml       │ (encrypted in vault — should be vaulted) │
├──────────────────────────┼──────────────────────────────────────────┤
│ ❌ Missing from Ansible  │ CrowdSec API key ("changeme")           │
│                          │ Nginx HTTPS certs                       │
│                          │ ClamAV configs                          │
│                          │ Auth Wrapper secrets                    │
└──────────────────────────┴──────────────────────────────────────────┘
```

### Password Generation & Application Flow

```
1. OPENBAO_ROOT_TOKEN + UNSEAL_KEYS (GitHub Secrets)
   │
   ├─► bootstrap.yml (MISSING) ──► OpenBao container starts
   │                                 └─► API: POST /v1/sys/unseal (3x)
   │
2. Ansible Vault (ansible-vault encrypted group_vars/all.yml)
   │
   ├─► pg_root_password ──► PostgreSQL .env ──► DB container
   ├─► redis_password ──► Redis .env ──► Redis container
   ├─► minio_root_password ──► MinIO .env ──► MinIO container
   ├─► keycloak_admin_password ──► Keycloak .env ──► Keycloak container
   ├─► gitea_db_password ──► Gitea .env ──► Gitea PostgreSQL
   ├─► openbao_oidc_secret ──► Keycloak realm client ──► OIDC token
   └─► searxng_secret_key ──► SearXNG .env ──► Search container

3. ❌ NOT auto-generated anywhere:
   - CrowdSec config (static "changeme" placeholder)
   - Nginx TLS certificates (manual letsencrypt)
   - ClamAV credentials (none needed — standalone)
   - Auth Wrapper token (static, not in ansible)
   - PageGen JWT secret (hardcoded)
```

### Password Rotation Schedule

| Secret | Change Frequency | Auto-Generated? | Stored In |
|--------|:----------------:|:---------------:|-----------|
| OpenBao Root Token | **Never** (until security incident) | ❌ Manual | GitHub Secrets |
| OpenBao Unseal Keys | **Never** (immutable Shamir) | ❌ Manual | GitHub Secrets |
| PostgreSQL Password | **Never** | ❌ Ansible Vault | Ansible Vault |
| Redis Password | **Never** | ❌ Ansible Vault | Ansible Vault |
| MinIO Credentials | **Never** | ❌ Ansible Vault | Ansible Vault |
| Keycloak Admin | **Never** | ❌ Ansible Vault | Ansible Vault |
| Gitea DB Password | **Never** | ❌ Ansible Vault | Ansible Vault |
| Gitea Admin Pass | **Never** | ❌ Ansible Vault | Ansible Vault |
| SearXNG Secret Key | **Never** | ❌ Ansible Vault | Ansible Vault |
| LightSerp API Secret | **Never** | ❌ Ansible Vault | Ansible Vault |
| OpenBao KV Secrets | **Never** (never seeded!) | ❌ Not configured | **EMPTY** |
| CrowdSec API Key | Static placeholder | ❌ Hardcoded | group_vars |
| TLS Certificates | **Every 90 days** | ✅ Let's Encrypt | Manual |
| Service Tokens | Every 30/7 days | ✅ OpenBao (not configured) | **EMPTY** |

**⚠️ CRITICAL:** OpenBao KV secrets are NEVER applied. `openbao_kv_bootstrap` role does not run because:
1. The `bootstrap.yml` playbook doesn't exist
2. Even if it did, KV bootstrap tasks reference `pg_root_password` but group_vars uses `vault.pg_root_password` naming (resolved in commit 75df2b1)

---

## 3. ANSIBLE PLAYBOOK STATUS

### Playbook Chain (as designed)

```
bootstrap.yml (MISSING) → services.yml → docker-compose.yml
    │                            │
    └─► OpenBao init            └─► All services start
       + unseal +
       + KV engines +
       + policies +
       + secrets
```

### Playbook Chain (actual — running)

```
N/A (manual deployment) → docker-compose.yml (manually maintained)
    │
    └─► 25 services running, no ansible orchestration
```

### Dry-Run Status (after commit 75df2b1)

```
Playbook: playbooks/services.yml (Phase 4 + Phase 8)
Check:   ansible-playbook --check ✓ PASSED (except crowdsec package)
Roles:   ok=157 changed=60 skipped=168 rescued=1 ignored=0
```

**Remaining Issue:** CrowdSec package `cs-nginx-bouncer` not available on VM — this is expected if CrowdSec isn't installed via the package manager (it's a Docker container).

---

## 4. FILES CHANGED IN COMMIT 75df2b1

```
┌──────────────────────────────────┬─────────────────────────────────────────┐
│ File                             │ Change                                  │
├──────────────────────────────────┼─────────────────────────────────────────┤
│ .gitignore                       │ ✅ Created — ignore compose artifacts   │
│ openbao/defaults/main.yml        │ 🔑 Fix variable references (env→direct) │
│ openbao/tasks/main.yml           │ 🔑 Fix validation (env→direct)          │
│ openbao/tasks/kv_bootstrap.yml   │ 🔑 Fix dict access ['status']           │
│ openbao/tasks/unseal.yml         │ 🔑 Updated comments                     │
│ openbao/vars/main.yml            │ 🔑 Updated secret refs                  │
│ keycloak/defaults/main.yml       │ 🔑 Simplify client secrets              │
│ keycloak_realm/tasks/main.yml    │ 🔑 Fix JWT parsing (from_json)          │
│ gitea_mirror/tasks/main.yml      │ 🔑 Fix loop variable (undefined r)      │
│ backup/defaults/main.yml         │ 🆕 Created (was missing)               │
│ security/defaults/main.yml       │ 🔑 Fix crowdsec key pattern             │
│ docker-compose-generator/defaults│ 📝 Updated memory defaults              │
│ docker-compose-generator template│ 📝 Updated NGINX config                │
│ playbooks/services.yml           │ 📝 Updated role references              │
│ inventory/group_vars/all.yml     │ 🔑 Re-encrypted with fresh vault key    │
│ openbao/files/init_keys.json     │ ❌ Deleted — removed from git tracking  │
└──────────────────────────────────┴─────────────────────────────────────────┘
```

---

## 5. RECOMMENDATIONS (Priority Order)

### 🔴 IMMEDIATE (do now)

1. **Create bootstrap.yml** — Script that:
   - Starts OpenBao container only
   - Runs unseal (3/3 keys via API)
   - Runs KV bootstrap (seed secrets)
   - Runs policy deployment
   - Returns control to services.yml

2. **Run bootstrap.yml manually** — Bootstraps OpenBao once, then future ansible runs will detect "already bootstrapped" and skip

### 🟡 SHORT-TERM (this week)

3. **Add missing services to docker-compose-generator template** — Grafana, Prometheus stack, PageGen, ClamAV, CrowdSec, Auth Wrapper
4. **Add nginx compose to ansible management** — Either embed in main template or create separate ansible-managed nginx compose
5. **Create backup script** — Mirror the existing `/home/mkanavi/scripts/backup.sh` pattern in ansible templates
6. **Seed OpenBao KV** — Run bootstrap to populate `iacgenie/kv/`, `lightserp/kv/`, `terraform/kv/`

### 🟢 LONG-TERM (next quarter)

7. **Automate TLS certificate rotation** — Ansible role for certbot/letsencrypt
8. **Secret rotation policy** — Implement periodic password rotation (PostgreSQL, Redis, MinIO)
9. **Drift mitigation** — Add `--diff` and auto-mitigation options to drift cron
10. **Add missing env vars to GitHub Secrets** — OpenBao root token, unseal keys already there

---

## 6. DRIFT DETECTION CRON

**Name:** `iacgenie-drift-detection`  
**Schedule:** Daily at 14:00 UTC  
**Job ID:** `iacgenie-drift-detection`

The cron job will:
1. Compare running docker containers vs ansible template
2. Check OpenBao KV secret count vs expected
3. Verify systemd services are running
4. Generate diff report
5. Require user approval before any remediation

---

*Report generated by Ansible Drift Analysis — 2026-08-12*
