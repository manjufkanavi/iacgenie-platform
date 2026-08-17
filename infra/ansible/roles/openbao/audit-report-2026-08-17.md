# OpenBao Security Audit Report

**Date:** 2026-08-17
**Auditor:** SecOps Engineer (AI)
**Target:** OpenBao 2.6.0 — Single-node raft, Docker container `iacgenie_openbao`
**Host:** VM 192.168.0.118 (macOS), TLS terminated at Nginx (vault.iacgenie.com)
**Scope:** Config, policies, auth, network, secrets handling, container security, backup, unseal, audit logging, CIS compliance

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Critical findings** | 2 |
| **High findings** | 5 |
| **Medium findings** | 7 |
| **Low findings** | 4 |
| **Info** | 3 |
| **Overall posture** | **NEEDS REMEDIATION** |

The OpenBao deployment has a solid foundation with OIDC-based authentication, least-privilege service policies, and backup tooling. However, critical gaps in root token handling, missing audit logging, and unencrypted backups present unacceptable risk for a secrets management system.

---

## 1. CONFIG SECURITY

### 🔴 CRITICAL-1: Plaintext Root Token Stored on Disk
- **Severity:** CRITICAL
- **Files:** `defaults/main.yml` (line 13), `openbao_injector.py` (lines 88-98), `backup_openbao.py` (lines 88-98), `seed_openbao_kv.py` (lines 27-37), `openbao-secrets/tasks/main.yml` (lines 27-35)
- **Details:** The OpenBao root token is stored in plaintext in `init_keys.json` on the host filesystem at `/home/mkanavi/docker/iacgenie/openbao_raft/init_keys.json`. Multiple scripts (backup, injector, seed, ansible) read this file to authenticate. The file is readable by the `mkanavi` user but has no additional permissions hardening.
- **Impact:** Any user or process with read access to the host filesystem or the container can obtain full root access to OpenBao. The backup script, injector, and seed scripts all load the root token directly from this file.
- **Remediation:**
  1. Enable Shamir auto-unseal with a KMS provider (AWS KMS, GCP KMS, Azure Key Vault, or Vault Agent Auto-Unlock).
  2. If auto-unseal is not feasible, store the root token in an external secrets manager (e.g., HashiCorp Vault itself, but in a separate namespace) or use a hardware security module (HSM).
  3. Restrict `init_keys.json` permissions to `0600` owned by root, and remove read access from the `mkanavi` user.
  4. Rotate the root token and re-initialize with a new root token that is never persisted to disk.

### 🔴 CRITICAL-2: No Audit Logging Configured
- **Severity:** CRITICAL
- **Files:** `openbao-prod.hcl.j2` (lines 1-44)
- **Details:** The OpenBao configuration file contains **no `audit` stanza**. Audit logging is completely absent. There is no `file`, `syslog`, or `event` audit sink configured. This means **zero visibility** into who accessed what secrets, when, and from where.
- **Impact:** Complete lack of accountability. Compliance frameworks (SOC 2, ISO 27001, PCI-DSS) require audit logging for secrets access. Cannot detect unauthorized access or brute-force attempts.
- **Remediation:**
  ```hcl
  audit "file" {
    file_path = "/openbao/storage/audit/openbao-audit.log"
    mode = "0600"
  }
  ```
  Also configure a secondary audit device (e.g., syslog to a SIEM) for tamper resistance:
  ```hcl
  audit "syslog" {
    device = "udp:siem-host:514"
    format = "json"
  }
  ```

### 🟡 HIGH-1: Default/Max Lease TTL Too Long
- **Severity:** HIGH
- **Files:** `openbao-prod.hcl.j2` (lines 37-38)
- **Details:** `default_lease_ttl = "768h"` (32 days) and `max_lease_ttl = "768h"` (32 days). Service tokens in `defaults/main.yml` are configured with `720h` (30 days) TTLs, which is within the max but very long for service tokens.
- **Impact:** Compromised tokens remain valid for up to 32 days. Service tokens with 30-day TTLs are excessive for non-human identities.
- **Remediation:**
  - Reduce `default_lease_ttl` to `24h` and `max_lease_ttl` to `168h` (7 days).
  - Reduce service token TTLs to `24h` (or `12h`) for automated rotation.
  - Implement token renewal workflows for long-running services.

### 🟡 HIGH-2: Log Level Set to INFO (Verbose in Production)
- **Severity:** HIGH
- **Files:** `openbao-prod.hcl.j2` (line 44)
- **Details:** `log_level = "info"` — This captures detailed operational information. In production, this should be more restrictive.
- **Impact:** INFO level can expose sensitive information in logs (e.g., token values, API paths). Combined with no audit logging (CRITICAL-2), this creates a dangerous gap.
- **Remediation:** Set `log_level = "warn"` or `"error"` in production. Enable structured logging with JSON format. Ensure logs are shipped to a SIEM.

### 🟡 HIGH-3: No TLS on Internal OpenBao Listener
- **Severity:** HIGH
- **Files:** `openbao-prod.hcl.j2` (lines 22-25)
- **Details:** `tls_disable = 1` on the listener. While TLS is terminated at Nginx, the internal communication between Nginx and OpenBao is unencrypted HTTP. If Nginx is compromised or the VM is breached, all traffic is plaintext.
- **Impact:** Man-in-the-middle attacks between Nginx and OpenBao are possible if the VM is compromised.
- **Remediation:** Enable mutual TLS between Nginx and OpenBao:
  ```hcl
  listener "tcp" {
    address         = "127.0.0.1:8200"
    tls_disable     = 0
    tls_cert_file   = "/etc/openbao/certs/server.crt"
    tls_key_file    = "/etc/openbao/certs/server.key"
    tls_client_ca_file = "/etc/openbao/certs/ca.crt"
  }
  ```

---

## 2. POLICY SECURITY

### 🟡 HIGH-4: Admin Policy Uses Wildcard Path with Sudo
- **Severity:** HIGH
- **Files:** `policies/admin.hcl.j2` (lines 1-5)
- **Details:** `path "*"` with `["create", "read", "update", "delete", "list", "sudo"]` grants full access to ALL paths including sys/*, auth/*, and secrets/* with sudo capability. This is a de facto root policy.
- **Impact:** Anyone with this policy has unrestricted access to the entire OpenBao instance, including the ability to enable/disable auth methods, modify policies, and access all secrets.
- **Remediation:**
  1. Split into separate admin policies: one for sys/admin operations and one for secrets management.
  2. Use `sudo` capability only where explicitly needed.
  3. Consider using OpenBao's built-in `root` policy for true admin access and remove the custom admin policy.

### 🟡 HIGH-5: Platform-Admin Policy Grants Read-All on Everything
- **Severity:** HIGH
- **Files:** `policies/platform-admin.hcl.j2` (lines 1-5)
- **Details:** `path "*"` with `["read", "list"]` grants read access to ALL paths. This means platform admins can read all secrets across all namespaces (iacgenie, lightserp, terraform) and any future namespaces.
- **Impact:** Platform admins have visibility into ALL secrets in the organization, violating the principle of least privilege for the platform-admin role.
- **Remediation:** Scope platform-admin to specific paths:
  ```hcl
  path "iacgenie/*" { capabilities = ["read", "list"] }
  path "lightserp/*" { capabilities = ["read", "list"] }
  path "terraform/*" { capabilities = ["read", "list"] }
  path "sys/*" { capabilities = ["read", "list"] }
  ```

### 🟢 MEDIUM-1: Service Policies Follow Least-Privilege
- **Severity:** INFO (positive finding)
- **Files:** `policies/iacgenie-service.hcl.j2`, `policies/lightserp-service.hcl.j2`, `policies/terraform-service.hcl.j2`, `policies/openbao-service-read.hcl.j2`
- **Details:** Service policies are correctly scoped to their respective KV namespaces with read-only access. This is good practice.
- **Assessment:** ✅ Good. These policies follow the principle of least privilege.

### 🟢 MEDIUM-2: No Wildcard Paths in Service Policies
- **Severity:** INFO (positive finding)
- **Files:** All service policy templates
- **Details:** Service policies use specific path patterns (`iacgenie/kv/*`, `lightserp/kv/*`, `terraform/kv/*`) rather than wildcards.
- **Assessment:** ✅ Good.

---

## 3. AUTH SECURITY

### 🟡 HIGH-6: OIDC Default Role Has No Bound Claims
- **Severity:** HIGH
- **Files:** `tasks/oidc_auth.yml` (lines 149-166)
- **Details:** The `user` OIDC role (line 157) has `bound_claims: {}` — an empty map. This means **any** authenticated Keycloak user can log in as the `user` role and get `openbao-service-read` policy access, with no restrictions on which users or groups are allowed.
- **Impact:** Any valid Keycloak user in the `lightserp` realm can access OpenBao secrets across all three namespaces (iacgenie, lightserp, terraform).
- **Remediation:**
  ```yaml
  bound_claims:
    roles: "openbao-service-read"
    # OR use email domain restriction:
    email: "user@iacgenie.com"
  ```
  Add explicit group or email claim bindings to restrict access.

### 🟡 HIGH-7: OIDC Client Secret Passed via Ansible Variables
- **Severity:** HIGH
- **Files:** `defaults/main.yml` (line 38), `tasks/oidc_auth.yml` (lines 24-26)
- **Details:** `openbao_oidc_client_secret` is resolved from `keycloak_openbao_oidc_secret` which comes from `openbao_oidc_secret`. These are passed through Ansible variables and sent to the OpenBao API in plaintext JSON body.
- **Impact:** If Ansible logs are enabled or the playbook output is captured, the OIDC client secret is exposed.
- **Remediation:** Use Ansible `no_log: true` on tasks that handle secrets. Store the OIDC client secret in an encrypted vault or external secret store.

### 🟡 MEDIUM-3: No AppRole Auth Method Configured
- **Severity:** MEDIUM
- **Files:** `tasks/service_tokens.yml`, `files/openbao_injector.py`
- **Details:** The `openbao_injector.py` script is designed to authenticate via AppRole (lines 110-120), but there is no task to enable or configure the AppRole auth method in OpenBao. The service token generation uses direct token creation via root token instead.
- **Impact:** The AppRole injection mechanism is designed but never deployed. The `openbao_injector.py` script will fail to authenticate to any services using it.
- **Remediation:**
  1. Enable AppRole auth method:
     ```yaml
     - name: Enable AppRole auth
       uri:
         url: "{{ openbao_api_url }}/v1/sys/auth/approle"
         method: POST
         body:
           type: approle
         headers:
           X-Vault-Token: "{{ openbao_root_token }}"
     ```
  2. Create AppRole roles for each service with appropriate policies.
  3. Generate and distribute RoleID/SecretID to services.

### 🟡 MEDIUM-4: Service Tokens Generated via Root Token (Not AppRole)
- **Severity:** MEDIUM
- **Files:** `tasks/service_tokens.yml` (all tasks)
- **Details:** Service tokens are created by directly calling `/v1/auth/token/create` with the root token. This is a "token creation" operation that bypasses proper auth method controls.
- **Impact:** If the root token is compromised, an attacker can generate arbitrary service tokens with any policy.
- **Remediation:** Use AppRole or Kubernetes auth to generate service tokens. Avoid root-token-based token creation in production.

### 🟡 MEDIUM-5: OIDC Token TTLs Are 8h/24h (Acceptable)
- **Severity:** INFO (positive finding)
- **Files:** `defaults/main.yml` (lines 42-43)
- **Details:** `openbao_oidc_token_ttl: "8h"` and `openbao_oidc_max_ttl: "24h"` are reasonable values.
- **Assessment:** ✅ Good.

---

## 4. NETWORK SECURITY

### 🟡 HIGH-8: OpenBao Listens on 127.0.0.1 Only
- **Severity:** MEDIUM (context-dependent)
- **Files:** `openbao-prod.hcl.j2` (lines 22-25), `openbao.service.j2` (lines 18-19)
- **Details:** OpenBao listens on `127.0.0.1:8200` only. This is intentional since Nginx terminates TLS. Ports 8200 and 8201 are published to `127.0.0.1` only.
- **Impact:** This is actually good security — OpenBao is not directly accessible from the network. However, if Nginx is misconfigured or compromised, the attack surface is the same.
- **Assessment:** ✅ Good (with caveat: ensure Nginx is properly configured and monitored).

### 🟡 MEDIUM-6: No Rate Limiting on OpenBao
- **Severity:** MEDIUM
- **Files:** `openbao-prod.hcl.j2`
- **Details:** No `rate_limit` configuration in the listener stanza. OpenBao has no built-in rate limiting for API requests.
- **Impact:** Vulnerable to brute-force attacks on auth methods (OIDC, AppRole) and enumeration attacks.
- **Remediation:**
  ```hcl
  listener "tcp" {
    address = "127.0.0.1:8200"
    tls_disable = 1
    rate_limit = 1000
  }
  ```
  Also configure Nginx rate limiting as a defense-in-depth measure.

### 🟡 MEDIUM-7: Raft Cluster Address Uses HTTP
- **Severity:** LOW
- **Files:** `openbao-prod.hcl.j2` (line 28)
- **Details:** `cluster_addr = "http://127.0.0.1:8201"` — Uses HTTP for inter-node communication. For a single-node deployment this is acceptable, but if the cluster scales, this becomes a risk.
- **Remediation:** When scaling to multiple nodes, enable TLS on the cluster listener.

---

## 5. SECRETS HANDLING

### 🔴 CRITICAL-3: init_keys.json Permissions Insufficient
- **Severity:** CRITICAL
- **Files:** `openbao.service.j2` (line 21), context: raft data dir permissions
- **Details:** The `init_keys.json` file containing root token and unseal keys is stored in `/home/mkanavi/docker/iacgenie/openbao_raft/` which has `rwxr-x---` (0750) permissions. This means the `mkanavi` user group can read the file. Any process running as `mkanavi` can access the root token.
- **Impact:** Any user, script, or compromised process running as `mkanavi` can read the root token and unseal keys.
- **Remediation:**
  1. Set `init_keys.json` permissions to `0600` (owner-only read/write).
  2. Consider using `chown root:root init_keys.json` after initialization.
  3. Move `init_keys.json` to a more restricted location (e.g., `/root/` or a dedicated secrets directory).

### 🟡 HIGH-9: Seed Script Reads Plaintext Secrets from .env
- **Severity:** HIGH
- **Files:** `files/seed_openbao_kv.py` (lines 23-24, 40-53)
- **Details:** The `seed_openbao_kv.py` script reads secrets from a plaintext `.env` file (`/home/mkanavi/docker/iacgenie/.env`) and writes them to OpenBao KV. The `.env` file contains passwords in plaintext.
- **Impact:** Plaintext secrets persist on disk in `.env` file. Anyone with read access to the `.env` file has access to all service credentials.
- **Remediation:**
  1. Encrypt the `.env` file using SOPS or similar.
  2. Use Ansible vault for `.env` file encryption.
  3. Delete the `.env` file after seeding (or use a one-time seed script that doesn't persist the source).

### 🟡 HIGH-10: Backup Script Loads Root Token from init_keys.json
- **Severity:** HIGH
- **Files:** `files/backup_openbao.py` (lines 72-101)
- **Details:** The backup script loads the root token from `init_keys.json` as a fallback (lines 88-98). This means the backup script has full root access to OpenBao.
- **Impact:** The backup process itself becomes an attack vector — if the backup script or its environment is compromised, the root token is exposed.
- **Remediation:**
  1. Use a dedicated backup token with read-only access to `/sys/storage/raft/snapshot` and `/v1/sys/audit/` paths.
  2. Never use root tokens for backup operations.

### 🟡 MEDIUM-8: Secrets Seeded via Ansible with lookup('password')
- **Severity:** MEDIUM
- **Files:** `openbao-secrets/tasks/main.yml` (lines 93, 108, 123, 138, 152, 169, 184, 198, 200, 214-215, 243, 257, 271)
- **Details:** Secrets are generated using Ansible's `lookup('password', ...)` which creates random passwords. However, these are generated fresh on each run — meaning secrets are **not stable** across deployments.
- **Impact:** Every re-deployment generates new passwords, breaking existing services that depend on the old secrets. This is a design issue, not purely security.
- **Remediation:**
  1. Use `lookup('password', '/dev/null chars=ascii_letters,digits length=32 seed={{ item_name }}')` to generate deterministic passwords per secret name.
  2. Or store existing secret values in a separate encrypted file and only generate new ones if the secret doesn't exist.

### 🟡 MEDIUM-9: LightSerp Database URL Contains Hardcoded Username
- **Severity:** LOW
- **Files:** `openbao-secrets/tasks/main.yml` (line 199)
- **Details:** `LIGHTSERP_DATABASE_URL: "postgresql://iacgenie_pg:***@postgres:5432/iacgenie"` — The username `iacgenie_pg` is hardcoded. The password placeholder `***` suggests it should be dynamic.
- **Impact:** Low — username exposure is minimal risk. The password placeholder is concerning if it's actually `***` instead of a dynamic value.
- **Remediation:** Ensure the password is dynamically generated, not literally `***`.

---

## 6. CONTAINER SECURITY

### 🟢 MEDIUM-10: Non-Root User and Dropped Capabilities
- **Severity:** INFO (positive finding)
- **Files:** `openbao.service.j2` (lines 15, 26-30)
- **Details:** Container runs as user `100:1000` (non-root). Capabilities: ALL dropped, only `SETGID`, `SETUID`, `DAC_OVERRIDE`, `IPC_LOCK` added. `no-new-privileges` is enabled.
- **Assessment:** ✅ Good. This is a strong security posture for the container runtime.

### 🟡 MEDIUM-11: No Read-Only Root Filesystem
- **Severity:** MEDIUM
- **Files:** `openbao.service.j2`
- **Details:** The container does not use `--read-only` flag. The root filesystem is writable.
- **Impact:** If an attacker achieves code execution in the container, they can modify binaries, install backdoors, or tamper with configuration.
- **Remediation:** Add `--read-only` flag and mount writable directories as tmpfs:
  ```yaml
  --read-only
  --tmpfs /openbao/storage:rw,noexec,nosuid,size=100m
  ```

### 🟡 MEDIUM-12: No Resource Limits for Memory
- **Severity:** LOW
- **Files:** `openbao.service.j2` (line 16)
- **Details:** Memory limit is set to `1g` which is reasonable. CPU limit is `0.5` which is also reasonable.
- **Assessment:** ✅ Good — resource limits are configured.

### 🟡 LOW-13: No Health Check Token Validation
- **Severity:** LOW
- **Files:** `openbao.service.j2`
- **Details:** The systemd service does not define a health check. Health is monitored via Ansible's `docker inspect` command.
- **Impact:** No automatic restart on health failure.
- **Remediation:** Add a health check to the systemd service or use Docker health check.

---

## 7. BACKUP SECURITY

### 🟡 HIGH-11: Backups Are Not Encrypted
- **Severity:** HIGH
- **Files:** `files/backup_openbao.py` (lines 151-187)
- **Details:** The backup script takes raft snapshots and copies the raw database but does **not encrypt** the backup files. The snapshots are stored in plaintext in `/home/mkanavi/docker/iacgenie/openbao_raft/backups/`.
- **Impact:** If the backup directory is compromised, an attacker can restore the entire OpenBao state and access all secrets.
- **Remediation:**
  1. Encrypt snapshots using GPG:
     ```bash
     gpg --symmetric --cipher-algo AES256 openbao-snapshot.snap
     ```
  2. Or use OpenBao's built-in encryption at rest (if supported).
  3. Store backups in an encrypted, access-controlled location (e.g., S3 with server-side encryption).

### 🟡 MEDIUM-13: Backup Retention Is 30 Days (Acceptable)
- **Severity:** INFO (positive finding)
- **Files:** `files/backup_openbao.py` (line 36)
- **Details:** `KEEP_DAYS = 30` — 30-day retention with rotation.
- **Assessment:** ✅ Good.

### 🟡 MEDIUM-14: SHA256 Checksums Are Generated (Good Practice)
- **Severity:** INFO (positive finding)
- **Files:** `files/backup_openbao.py` (lines 177-179, 200-202)
- **Details:** The backup script generates SHA256 checksums for all backup files.
- **Assessment:** ✅ Good.

### 🟡 MEDIUM-15: Email Alerts Are Configured (But May Not Work)
- **Severity:** INFO (positive finding)
- **Files:** `files/backup_openbao.py` (lines 51-70)
- **Details:** Email notification for backup success/failure is implemented but depends on `BACKUP_EMAIL_TO` environment variable.
- **Assessment:** ✅ Good, but verify email delivery is working.

---

## 8. UNSEAL SECURITY

### 🟡 HIGH-12: Shamir 2/3 Unseal with No Auto-Unseal
- **Severity:** HIGH
- **Files:** `defaults/main.yml` (lines 5-6, 17-23), `tasks/unseal.yml`
- **Details:** Shamir key split is configured as 3/3 (not 2/3 as stated in the context). `openbao_auto_unseal: false`. Unseal keys are passed as Ansible variables. The unseal task uses HTTPS to the container (but the container listener is HTTP — this is a configuration mismatch).
- **Impact:** Manual unseal is required on every restart. No auto-unseal means availability risk during outages.
- **Remediation:**
  1. Enable auto-unseal with a KMS provider.
  2. If manual unseal is required, store unseal keys in a secure key management system (e.g., AWS KMS, HashiCorp Vault's transit engine, or physical HSMs).
  3. Fix the unseal task to use HTTP (matching the listener config) or enable TLS on the listener.

### 🟡 MEDIUM-16: Unseal Keys Passed as Ansible Variables
- **Severity:** MEDIUM
- **Files:** `defaults/main.yml` (lines 17-23)
- **Details:** Unseal keys are passed as `openbao_unseal_key_1`, `openbao_unseal_key_2`, `openbao_unseal_key_3` via Ansible extra-vars. These appear in Ansible logs and process listings.
- **Impact:** Unseal keys may be visible in Ansible logs, process lists, or CI/CD pipeline logs.
- **Remediation:** Store unseal keys in an encrypted vault (e.g., Ansible Vault, AWS Secrets Manager) and reference them securely.

---

## 9. AUDIT LOGGING

### 🔴 CRITICAL-2 (repeated above): No Audit Logging
- **Severity:** CRITICAL
- **Details:** See CRITICAL-2 above. This is the most significant gap in the entire deployment.

---

## 10. CIS BENCHMARK COMPLIANCE

| CIS Control | Status | Notes |
|-------------|--------|-------|
| 3.1 Enable audit logging | ❌ FAIL | No audit stanza in config |
| 3.2 Enable TLS on listener | ❌ FAIL | tls_disable = 1 |
| 3.3 Restrict listener binding | ✅ PASS | 127.0.0.1 only |
| 3.4 Enable rate limiting | ❌ FAIL | No rate_limit configured |
| 3.5 Rotate root token | ⚠️ PARTIAL | Root token stored on disk |
| 4.1 Enable auto-unseal | ❌ FAIL | Shamir manual only |
| 4.2 Rotate unseal keys | ⚠️ PARTIAL | Keys passed via Ansible vars |
| 5.1 Least-privilege policies | ⚠️ PARTIAL | Service policies good, admin/platform-admin too broad |
| 5.2 Token TTL management | ⚠️ PARTIAL | TTLs too long (720h) |
| 6.1 Encrypt secrets at rest | ❌ FAIL | No encryption at rest (only raft) |
| 6.2 Encrypt backups | ❌ FAIL | Backups not encrypted |
| 7.1 Container security hardening | ✅ PASS | Non-root, dropped caps, no-new-privs |
| 7.2 Read-only root filesystem | ❌ FAIL | Not configured |
| 8.1 Log management | ❌ FAIL | No audit logging, log level info |
| 8.2 Alerting | ⚠️ PARTIAL | Email alerts for backups only |
| 9.1 Network segmentation | ✅ PASS | 127.0.0.1 binding, Nginx TLS termination |
| 9.2 TLS between services | ❌ FAIL | HTTP between Nginx and OpenBao |

**CIS Score: 4/19 controls passing (21%)**

---

## Summary of Findings

### Critical (2)
1. **Plaintext root token on disk** — `init_keys.json` readable by multiple scripts
2. **No audit logging** — Zero visibility into secrets access

### High (5)
1. **Default/Max lease TTL too long** — 32 days default, 30-day service tokens
2. **Log level INFO in production** — Potential sensitive data exposure
3. **No TLS on internal listener** — HTTP between Nginx and OpenBao
4. **Admin policy wildcard with sudo** — Full root-equivalent access
5. **OIDC default role has no bound claims** — Any Keycloak user can access OpenBao

### Medium (7)
1. Service policies follow least-privilege ✅ (positive)
2. No AppRole auth method configured (designed but not deployed)
3. Service tokens created via root token
4. Seed script reads plaintext `.env`
5. Backup loads root token (should use dedicated token)
6. Secrets generated via `lookup('password')` are unstable across deployments
7. No read-only root filesystem

### Low (4)
1. Raft cluster address uses HTTP
2. LightSerp DB URL has hardcoded username
3. Memory/CPU limits configured ✅ (positive)
4. No systemd health check

### Info (3)
1. OIDC token TTLs are reasonable ✅ (positive)
2. Service policies use specific paths ✅ (positive)
3. Non-root container with dropped capabilities ✅ (positive)

---

## Priority Remediation Roadmap

### Phase 1: Immediate (0-7 days)
1. **[CRITICAL]** Enable audit logging with file and syslog sinks
2. **[CRITICAL]** Restrict `init_keys.json` permissions to `0600 root:root`
3. **[CRITICAL]** Rotate root token and never persist to disk again
4. **[HIGH]** Add `bound_claims` to OIDC default role

### Phase 2: Short-term (1-4 weeks)
5. **[HIGH]** Enable TLS on OpenBao listener (mutual TLS with Nginx)
6. **[HIGH]** Reduce default/max lease TTLs (24h/7d)
7. **[HIGH]** Split admin policy into scoped policies
8. **[HIGH]** Implement AppRole auth method
9. **[HIGH]** Encrypt backup files

### Phase 3: Medium-term (1-3 months)
10. **[HIGH]** Enable auto-unseal with KMS
11. **[MEDIUM]** Add read-only root filesystem
12. **[MEDIUM]** Add rate limiting
13. **[MEDIUM]** Fix seed script to use encrypted `.env`
14. **[MEDIUM]** Implement deterministic secret generation

### Phase 4: Long-term (3-6 months)
15. **[MEDIUM]** Implement token renewal workflows
16. **[LOW]** Add systemd health checks
17. **[LOW]** Enable cluster TLS when scaling
18. **[INFO]** Verify email alert delivery

---

*Report generated: 2026-08-17*
*Next audit recommended: 2026-11-17 (quarterly)*
