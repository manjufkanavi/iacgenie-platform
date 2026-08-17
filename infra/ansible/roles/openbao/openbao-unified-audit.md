# OpenBao Service — Unified Audit Report

**Date:** 2026-08-17 | **Service:** OpenBao 2.6.0 | **Host:** VM 192.168.0.118
**Container:** `iacgenie_openbao` | **Storage:** Raft (single-node)
**Scope:** Configuration, Security, Reliability, Operations

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **CRITICAL** | 4 |
| **HIGH** | 8 |
| **MEDIUM** | 7 |
| **LOW** | 4 |
| **INFO** | 3 |
| **Overall Status** | 🚨 **NEEDS REMEDIATION** |

**CIS Benchmark Score:** 4/19 passing (21%)
**Operational Risk:** HIGH

---

## 🔴 CRITICAL Findings

### C1 — No Audit Logging
- **Config:** `openbao-prod.hcl.j2` has zero `audit` stanza
- **Impact:** Complete invisibility into secrets access — violates SOC 2, ISO 27001, PCI-DSS
- **Fix:** Add `audit "file"` sink to `/openbao/storage/audit/openbao-audit.log`

### C2 — Plaintext Root Token on Disk
- **File:** `init_keys.json` at `/home/mkanavi/docker/iacgenie/openbao_raft/`
- **Impact:** Any process with host read access gets full OpenBao root control
- **Fix:** Enable auto-unseal (KMS) or rotate token and remove from disk

### C3 — Unseal Task Uses HTTPS Against HTTP-Only Listener
- **File:** `tasks/unseal.yml` lines 10–11
- **Impact:** Unseal task will fail — `https://` vs listener `tls_disable=1`
- **Fix:** Change all API URLs to `http://127.0.0.1:8200`

### C4 — No Auto-Unseal + No Offsite Backup
- **Impact:** Manual Shamir unseal required after every restart; single VM failure = data + backups lost
- **Fix:** Configure auto-unseal (KMS) + S3/rsync offsite replication

---

## 🟠 HIGH Findings

| # | Finding | Severity | File |
|---|---------|----------|------|
| H1 | Lease TTLs too long (32d default, 30d service tokens) | HIGH | `defaults/main.yml` |
| H2 | No TLS on internal listener (HTTP only between Nginx→OpenBao) | HIGH | `openbao-prod.hcl.j2` |
| H3 | Admin policy uses wildcard + sudo (`path * { sudo }`) | HIGH | `policies/admin.hcl.j2` |
| H4 | OIDC default role has no bound claims (any Keycloak user can access) | HIGH | `oidc_auth.yml` |
| H5 | Backups not encrypted (SHA256 checksums only, no encryption) | HIGH | `backup_openbao.py` |
| H6 | No Docker HEALTHCHECK with seal-status validation | HIGH | `docker-compose.yml.j2` |
| H7 | `service_tokens/` directory is EMPTY — tokens not persisted | HIGH | Live state |
| H8 | Corrupted backup `raft.bak.corrupted` present, no integrity verification | HIGH | Live state |

---

## 🟡 MEDIUM Findings

| # | Finding | File |
|---|---------|------|
| M1 | No AppRole auth method deployed (injector expects it but it's not enabled) | `oidc_auth.yml` |
| M2 | Service tokens created via root token (should use AppRole) | `service_tokens.yml` |
| M3 | Seed script reads plaintext `.env` file | `seed_openbao_kv.py` |
| M4 | Secrets via `lookup('password')` are unstable across runs | `kv_bootstrap.yml` |
| M5 | No read-only rootfs on container | `docker-compose.yml.j2` |
| M6 | Config file `prod.hcl` missing from `files/` (template exists but `copy` task references non-existent file) | `tasks/main.yml` |
| M7 | `openbao-secrets` role path mismatch (`data/openbao_raft` vs `openbao_raft`) | `openbao-secrets/defaults/main.yml` |

---

## 🟢 PASSED (Good)

- ✅ Service policies follow least-privilege (read-only KV access per namespace)
- ✅ Container runs as non-root user (`openbao`)
- ✅ Capabilities dropped (`ALL`), only essential ones added
- ✅ `no-new-privileges:true` enforced
- ✅ Memory/CPU limits set (1GB/1CPU)
- ✅ Backup tooling well-designed (API snapshot + raw DB copy + config + SHA256 + 30-day rotation + 4x daily cron)
- ✅ Raft auto-snapshot every 5 minutes (RPO ~5 min)
- ✅ OIDC TTLs reasonable (1h access, 8h refresh)
- ✅ Injector script has retry logic and fallback behavior

---

## 📊 Risk Matrix

| Area | Status | Priority |
|------|--------|----------|
| **Audit logging** | ❌ Missing | 🔴 Immediate |
| **Root token handling** | ❌ Insecure | 🔴 Immediate |
| **Unseal task** | ❌ Broken (HTTPS vs HTTP) | 🔴 Immediate |
| **Backup integrity** | ⚠️ Corrupted backup present | 🟠 High |
| **Offsite backup** | ❌ None | 🟠 High |
| **Auto-unseal** | ❌ Manual only | 🟠 High |
| **Service tokens** | ❌ Empty directory | 🟠 High |
| **Health monitoring** | ⚠️ Trivial check only | 🟠 High |
| **Container security** | ✅ Good | — |
| **Policy design** | ✅ Least-privilege | — |

---

## 🔧 Immediate Action Plan

### Phase 1 — Critical (Do Now)
1. **Add audit logging** to `openbao-prod.hcl.j2`:
   ```hcl
   audit "file" {
     file_path = "/openbao/storage/audit/openbao-audit.log"
     mode = "0600"
   }
   ```
2. **Fix unseal task** — change all `https://` to `http://` in `tasks/unseal.yml`
3. **Rotate root token** — remove `init_keys.json`, re-init, never persist to disk
4. **Delete corrupted backup** — `rm -rf /home/mkanavi/docker/iacgenie/openbao_raft/raft.bak.corrupted`

### Phase 2 — High (This Week)
5. **Add Docker HEALTHCHECK** with seal-status validation
6. **Fix service token persistence** — investigate why `service_tokens/` is empty
7. **Add offsite backup** — S3 or rsync to remote
8. **Enable AppRole auth method** — deploy to OpenBao for injector
9. **Reduce lease TTLs** — 768h → 72h default, 30d → 7d service tokens

### Phase 3 — Medium (This Month)
10. **Add TLS between Nginx and OpenBao** (internal mTLS or self-signed)
11. **Restrict OIDC default role** with bound claims
12. **Encrypt backups** with GPG or AES
13. **Fix openbao-secrets path mismatch**
14. **Add read-only rootfs** to container

### Phase 4 — Strategic
15. **Configure auto-unseal** (AWS KMS / GCP KMS / HSM)
16. **Add multi-node raft** for HA
17. **Implement backup rotation cleanup** (excessive vault.db copies consuming disk)

---

## 📁 Audit Reports Generated

| Report | Location |
|--------|----------|
| Security Audit | `infra/ansible/roles/openbao/audit-report-2026-08-17.md` (462 lines) |
| Operational Audit | `infra/ansible/roles/openbao/files/openbao-operational-audit.md` (396 lines) |
| Config/DevOps Audit | `infra/ansible/roles/openbao/audit-report-2026-08-17.md` |

---

## 🔄 Live State Summary

| Item | Value |
|------|-------|
| **Container** | `iacgenie_openbao` — Up 12h (healthy) |
| **Version** | OpenBao 2.6.0 |
| **Storage** | Raft (single-node, index=119) |
| **Unseal** | Shamir 2/3, unsealed |
| **Mounts** | identity, sys, cubbyhole, terraform/kv, iacgenie/kv, lightserp/kv, token |
| **Listener** | 127.0.0.1:8200 (HTTP, TLS at Nginx) |
| **Vault DB** | 16MB |
| **Backups** | 30-day retention, 4x daily cron |
| **Service tokens** | EMPTY |
| **Cron** | Backup (0,6,12,18), Health check (*/5) |
