# Phase 0: Infrastructure Stabilization — Change Log

**Date:** 2026-07-26  
**VM:** 192.168.0.118 (vm.iacgenie.com)  
**Operator:** Manjunath Kanavi

## Summary

Stabilized all critical infrastructure services on the shared VM. Five of six services are now running and healthy. One service (OpenBao) requires manual unsealing.

---

## Changes by Service

### PostgreSQL ✅ FIXED

| Item | Before | After |
|------|--------|-------|
| Status | Exited (0) | Up, healthy |
| Root Cause | Data dir `/home/mkanavi/docker/iacgenie/postgres_data` owned by uid 7 (root) but container runs as uid 70 (postgres) | Changed ownership to uid 70:70 |
| LightSerp DB | User `lightsrp` had hardcoded password `'ic7iCqW9...'` that didn't match `.env.api` (`i1K2cQ...3Y06`) | Updated `lightsrp` password via `ALTER USER` to match `.env.api` |
| Databases | All 4 app databases present (iacgenie, keycloak, lightsrp, logtide) | Verified all 4 + gitea + postgres are accessible |
| Health Check | N/A | `pg_isready` passes, health check enabled |
| Restart Policy | `unless-stopped` (via compose) | Confirmed active |

**Config Changes:**
- Host dir: `chmod/chown 70:70 /home/mkanavi/docker/iacgenie/postgres_data/`
- DB: `ALTER USER lightsrp WITH PASSWORD 'i1K2cQ1HFUNxu2&iwtY90Q0eKMRv3Y06';`
- **Action Required:** Update `docker/postgres/init.sh` in git to match current passwords before any reinitialization

---

### Redis ✅ FIXED

| Item | Before | After |
|------|--------|-------|
| Status | Exited (0) | Up, healthy |
| Root Cause | Container was stopped/exited | Restarted via `docker compose up -d` |
| Health Check | N/A | Health check active, passing |
| Restart Policy | `unless-stopped` (via compose) | Confirmed active |

**Config Changes:** None (container was simply stopped)

---

### OpenBao ⚠️ RUNNING BUT SEALED

| Item | Status |
|------|--------|
| Status | Up, but **sealed** (returns `{"errors":["Vault is sealed"]}`) |
| Root Cause | OpenBao unseal (Shamir) keys are **LOST** — `init_keys.json` only contains root token and project tokens, not the 2-of-3 unseal key shares |
| Impact | All secrets stored in OpenBao (service tokens, OAuth secrets, etc.) are inaccessible |
| Data | Raft store is intact — vault data exists at `/home/mkanavi/docker/iacgenie/openbao_raft/` |
| Fixes Applied | Data dir ownership changed to uid 100:1000 (openbao container user), permissions set |
| Recovery | Requires admin to re-initialize vault (will lose all stored secrets) OR find backup of unseal keys |

**Config Changes:**
- Host dir: `chown -R 100:1000 /home/mkanavi/docker/iacgenie/openbao_data/` and `openbao_raft/`
- **Action Required (CRITICAL):** Re-initialize OpenBao vault with `bootstrap_openbao.sh init`, then properly save unseal keys to a secure backup location

---

### SearXNG ✅ FIXED

| Item | Before | After |
|------|--------|-------|
| Status | Exited (0) | Up, search API returning results (24 results/test query) |
| Root Cause | Container was stopped | Restarted via `docker compose up -d lightserp-searxng` |
| Health | Non-critical: Wikidata engine fails init (403 error, suspended) | Other search engines working |
| API | N/A | `GET /search?q=test&format=json` returns results |

**Config Changes:** None (container was simply stopped)

---

### Other Services (No Changes Needed)

| Service | Status | Notes |
|---------|--------|-------|
| Gitea | ✅ Healthy | Running ~1 hour, no intervention |
| MinIO | ✅ Healthy | Running ~1 hour, no intervention |
| Keycloak | ✅ Healthy | Running ~10 minutes, no intervention |
| NSQD | ✅ Running | Running ~1 hour, no intervention |
| LightSerp API | ✅ Running | Redis connected ✅, PostgreSQL connected ✅, NSQ connected ✅ |
| LightSerp WebUI | ✅ Running | No issues |
| PageZen | ✅ Running | Mock server on :8082 |

---

## Non-Critical Issues

1. **DNS: `logtide` hostname** — LightSerp API logs `getaddrinfo EAI_AGAIN logtide` on startup. This is a DNS resolution for the `logtide` database/user that doesn't exist in this context. LightSerp continues operating without it.

2. **SearXNG Wikidata** — Wikidata search engine fails with HTTP 403 (suspended_time=180). This is a non-critical engine; other engines work fine.

---

## Security Notes

- PostgreSQL `lightsrp` user password was synced to match `.env.api` (`PGPASSWORD`)
- OpenBao unseal keys were never backed up — this is a data loss risk
- All service passwords in `.env` and `.env.api` should be audited for strength

---

## Next Steps (Phase 0 Remaining)

1. **OpenBao Recovery:** Admin must re-initialize vault and securely store unseal keys
2. **DNS Fix for logtide:** Investigate why LightSerp tries to resolve `logtide` hostname
3. **Verify all services survive container restart** (add to Phase 1)
4. **Set up backup automation** (Phase 2)

---

## Git Commits

| Commit | Description |
|--------|-------------|
| `48b6b9f` | Add PostgreSQL init script and INFRA-CICD-PLAN |

Files added:
- `docker/postgres/init.sh` — PostgreSQL init script (WARNING: passwords must be synced with .env)
- `INFRA-CICD-PLAN.md` — Infrastructure and CI/CD roadmap
