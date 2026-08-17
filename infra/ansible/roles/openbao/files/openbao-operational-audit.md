# OpenBao Operational Risk Assessment
## IaCGenie Platform — Reliability & Operational Readiness Audit

**Date:** 2026-08-17  
**OpenBao Version:** 2.6.0  
**Architecture:** Single-node Docker container, raft-based storage, Shamir 3/3 seal  
**Audit Scope:** Backups, health checks, monitoring, recovery, resource management, token lifecycle, disaster recovery

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Overall Risk Level | **HIGH** |
| Critical Findings | 4 |
| Warnings | 6 |
| Passed Checks | 5 |
| Total Checks | 15 |

The OpenBao deployment has a solid foundation — automated backups with checksums, KV bootstrap via Ansible, and AppRole-based secret injection are well-architected. However, **single-node architecture without auto-unseal, no external backup replication, a corrupted backup file, empty service token persistence, and minimal health monitoring** create unacceptable operational risk for a production secrets management system.

---

## 1. Backup Strategy

### ✅ PASS — Backup tooling is comprehensive
- `backup_openbao.py` implements a robust 5-step backup process:
  1. Health verification (sealed/unsealed state check)
  2. API-based raft snapshot (with >1KB validation)
  3. Raw raft database copy (`vault.db`)
  4. Configuration file backup (`openbao-prod.hcl`)
  5. 30-day retention rotation
- SHA256 checksums are generated for every snapshot and DB copy
- Email alerts configured via SMTP (Gdefaults to Gmail)
- Cron runs 4x daily (0, 6, 12, 18)

### ❌ FAIL — No backup replication/external storage
- **All backups stored locally** on the same VM (`/home/mkanavi/docker/iacgenie/openbao_raft/backups/`)
- No S3/GCS/Azure Blob offsite copy
- No cross-region or cross-availability-zone replication
- A single VM failure destroys both the live data AND all backups

### ❌ FAIL — Corrupted backup present
- `raft.bak.corrupted` (396KB) exists in the backup directory
- Indicates a past backup failure that was acknowledged but not remediated
- No automated integrity verification of backup restore capability
- No backup restore drill performed or documented

### ⚠️ WARN — Backup token uses service policy, not dedicated backup policy
- `backup_token.txt` uses `iacgenie-service` policy (line 127 of service_tokens.yml)
- This is broader than needed; a dedicated `backup-read` policy with only `sys/storage/raft/snapshot` access would follow least-privilege

### ⚠️ WARN — Backup email configuration uses hardcoded defaults
- `backup_openbao.py` defaults to `smtp.gmail.com:587` with `openbao-backup@iacgenie.com`
- No environment variable validation for email config before cron execution
- If `BACKUP_EMAIL_TO` is empty (default), alerts are silently dropped

---

## 2. Recovery Procedures

### ✅ PASS — Restore function exists
- `backup_openbao.py restore <file>` implements snapshot upload via `PUT /v1/sys/storage/raft/snapshot`
- Checksum verification before restore
- Proper error handling for missing files and checksum mismatches

### ❌ FAIL — No documented recovery runbook
- No playbook or script for full disaster recovery sequence
- No automated config restoration after snapshot restore
- Config file (`openbao-prod.hcl`) is backed up but no mechanism to ensure it matches the restored state
- No test/restore drill procedure documented

### ❌ FAIL — No config version control
- `openbao-prod.hcl` is a static file — changes to it are not tracked in Git
- If the config is modified manually, there's no audit trail or ability to roll back
- The Ansible role doesn't manage the config file (it's a bind mount from the host)

### ⚠️ WARN — Snapshot-only restore doesn't support partial recovery
- Raft snapshot captures the entire state, which is correct, but there's no ability to:
  - Restore individual KV secrets without full restore
  - Export/import specific secrets (no `export`/`import` commands in seed script)

---

## 3. Health Monitoring

### ❌ FAIL — Health check is trivially simple
The `openbao-health-cron.sh` (9 lines) only checks:
```bash
STATUS=$(docker inspect --format="{{ .State.Status }}" iacgenie_openbao 2>/dev/null || echo "stopped")
```

**What it misses:**
- Container running but OpenBao sealed → not detected
- Container running but OpenBao process crashed → not detected
- OpenBao responding but returning errors → not detected
- Raft snapshot failures → not detected
- Disk space exhaustion → not detected
- Memory pressure → not detected

### ⚠️ WARN — No Docker healthcheck configured
- No `HEALTHCHECK` directive in Dockerfile or docker-compose healthcheck
- No `/v1/sys/health` endpoint being monitored
- The Ansible unseal task checks health, but that's only during deployment

### ⚠️ WARN — No monitoring integration
- No Prometheus metrics endpoint exposed
- No Grafana dashboards
- No PagerDuty/OpsGenie/Slack integration for alerts
- No centralized log aggregation (ELK/Loki)

### ✅ PASS — Backup health verification
- `backup_openbao.py` verifies seal status before each backup attempt
- Fails the backup job and sends email alert if OpenBao is sealed

---

## 4. Resource Management

### ❌ FAIL — No resource limits configured
- **No memory limits** defined in docker-compose (1GB is current usage, not a limit)
- **No CPU limits** defined
- OpenBao can consume all host resources if it enters a memory leak or log loop
- No OOM kill protection

### ❌ FAIL — No log rotation
- No `logrotate` configuration for OpenBao logs
- Container logs (`docker logs`) grow indefinitely
- No `max-size` or `max-file` in docker-compose logging driver config
- Risk of disk exhaustion over time

### ⚠️ WARN — Disk usage not monitored
- No alerting on disk space thresholds
- Raft snapshots accumulate until 30-day rotation kicks in
- `vault.db` at 16MB currently but grows unbounded
- No monitoring of `/home/mkanavi/docker/iacgenie/openbao_raft/` disk usage

### ✅ PASS — Raft auto-snapshot configured
- Auto-snapshot every 5 minutes reduces RPO to ~5 minutes
- Snapshot index at 119 shows regular operation

---

## 5. High Availability

### ❌ FAIL — Single-node architecture
- **No replication**, no clustering, no standby node
- Single point of failure: if the VM goes down, OpenBao is unavailable
- Raft quorum requires at least 1 node, but there's no fault tolerance
- No load balancing or VIP for failover

### ❌ FAIL — No standby/DR node
- No second VM or container for failover
- No cross-region replication
- No cold standby with periodic snapshot replication

### ⚠️ WARN — Raft on single node has no quorum benefit
- Raft consensus is valuable for multi-node clusters but provides no HA on single node
- The raft snapshot feature is the only HA benefit (point-in-time recovery)

---

## 6. Token Lifecycle

### ❌ FAIL — Service tokens directory is empty
- `service_tokens/` directory exists but is **EMPTY**
- Tokens are generated during Ansible bootstrap but appear to not persist
- If the container restarts or the directory is cleaned, tokens are lost
- No mechanism to regenerate tokens if lost (requires root token)

### ⚠️ WARN — Service tokens have long TTLs with no rotation
- IaCGenie token: 720h (30 days)
- LightSerp token: 720h (30 days)
- Terraform token: 720h (30 days)
- Backup token: 168h (7 days)
- No automated rotation process
- No token expiration notification
- Long-lived tokens increase blast radius if compromised

### ⚠️ WARN — AppRole credentials not managed
- The `openbao_injector.py` expects AppRole credentials at `/var/run/approle/`
- No mechanism to rotate AppRole secret IDs
- No audit of AppRole login attempts
- No rate limiting on AppRole authentication

### ❌ FAIL — Root token management
- Root token stored in `init_keys.json` on the host
- Root token also in `defaults/main.yml` as `CHANGE_ME_SEE_GITHUB_SECRETS`
- No automatic root token rotation
- Root token used for all bootstrap operations (should use dedicated admin token)

---

## 7. Lease Management

### ⚠️ WARN — Default lease TTL is very long
- Default lease TTL: 768h (32 days)
- Max lease TTL: 768h (32 days)
- Long-lived leases increase exposure window if tokens are compromised
- No lease monitoring or automatic revocation for expired leases
- No TTL enforcement on KV secrets (they don't expire)

### ✅ PASS — Lease restoration configured
- OpenBao raft storage automatically restores leases from snapshot
- No manual lease re-issuance needed after restore

---

## 8. Recovery from Corruption

### ❌ FAIL — Corrupted backup not addressed
- `raft.bak.corrupted` (396KB) exists — indicates a failed backup
- No automated detection of backup corruption
- No verification that backups are restorable
- No backup integrity testing procedure

### ⚠️ WARN — No backup verification pipeline
- SHA256 checksums are generated but never verified against a known-good baseline
- No automated restore test (e.g., weekly restore to ephemeral instance)
- No backup encryption — backups are stored in plaintext

### ⚠️ WARN — No backup immutability
- Backups can be modified or deleted by anyone with access to the directory
- No WORM (Write Once Read Many) protection
- No versioning or immutability policy

---

## 9. Seal/Unseal Procedures

### ❌ FAIL — No auto-unseal configured
- `openbao_auto_unseal: false` in `defaults/main.yml`
- Manual Shamir 3/3 unseal required after every restart
- Unseal keys provided via `--extra-vars` on Ansible playbook execution
- Container restarts require manual intervention or Ansible re-run

### ⚠️ WARN — Unseal keys not stored securely
- Unseal keys passed via command-line arguments (`--extra-vars`)
- Visible in process listing (`ps aux`)
- Not stored in a secrets manager themselves (paradoxically)
- No hardware security module (HSM) or cloud KMS integration

### ⚠️ WARN — No automatic unseal after power failure
- If the VM loses power and reboots, OpenBao will be sealed
- Container may start but OpenBao process will be in sealed state
- The health cron only checks container status, not OpenBao seal status
- Service restart would be delayed until someone notices

---

## 10. Disaster Recovery

### ❌ FAIL — No disaster recovery plan
- No documented DR procedure
- No RTO (Recovery Time Objective) defined
- No RPO (Recovery Point Objective) defined
- No DR runbook for full VM failure scenario

### ❌ FAIL — No backup offsite replication
- All data on single VM
- No S3/GCS backup bucket
- No cross-region snapshot replication
- No immutable backup storage

### ❌ FAIL — No infrastructure as code for OpenBao
- OpenBao configuration is not managed by Ansible (bind mount from host)
- Docker-compose file changes may not be tracked
- No Terraform/Pulumi definition for the OpenBao infrastructure

### ⚠️ WARN — Single user account dependency
- Everything tied to `mkanavi` user account
- If this account is compromised or locked, OpenBao access is impacted
- No service account or shared credentials for operations

---

## Risk Summary Matrix

| Area | Status | Severity | Impact |
|------|--------|----------|--------|
| Backup Strategy | FAIL | HIGH | Data loss possible on VM failure |
| Recovery Procedures | FAIL | HIGH | Cannot guarantee recovery |
| Health Monitoring | FAIL | HIGH | Failures may go unnoticed |
| Resource Management | FAIL | MEDIUM | Disk exhaustion, OOM possible |
| High Availability | FAIL | HIGH | Single point of failure |
| Token Lifecycle | FAIL | HIGH | Token loss = service outage |
| Lease Management | WARN | LOW | Extended exposure window |
| Recovery from Corruption | FAIL | HIGH | Corrupted backups unusable |
| Seal/Unseal Procedures | FAIL | HIGH | Service unavailable after restart |
| Disaster Recovery | FAIL | HIGH | No recovery plan exists |

---

## Recommended Improvements (Priority Order)

### Critical (Implement Immediately)

1. **Add offsite backup replication** — rsync or aws s3 sync to external storage every 6 hours
2. **Implement proper health monitoring** — Add `/v1/sys/health` checks with seal status
3. **Configure auto-unseal** — Use AWS KMS, GCP KMS, or HashiCorp Vault's built-in auto-unseal
4. **Fix service token persistence** — Investigate why `service_tokens/` is empty; ensure tokens survive restarts
5. **Remove corrupted backup** — Delete `raft.bak.corrupted` and verify backup integrity

### High Priority (Implement Within 1 Week)

6. **Create DR runbook** — Document full recovery procedure with RTO/RPO targets
7. **Add Docker healthcheck** — Configure `HEALTHCHECK` with `/v1/sys/health` endpoint
8. **Implement log rotation** — Configure `logrotate` or docker logging driver limits
9. **Set resource limits** — Add memory and CPU limits in docker-compose
10. **Add dedicated backup policy** — Create `backup-read` policy with minimal permissions

### Medium Priority (Implement Within 1 Month)

11. **Multi-node raft cluster** — Add 2-4 more nodes for HA
12. **Token rotation automation** — Implement automated token renewal before TTL expiry
13. **Backup verification pipeline** — Automated weekly restore test
14. **Monitoring integration** — Prometheus metrics + Grafana dashboards
15. **Config version control** — Track `openbao-prod.hcl` in Git with change management

---

## Disaster Recovery Checklist

### Pre-Recovery Preparation
- [ ] Verify offsite backups exist and are accessible
- [ ] Have root token available (from `init_keys.json` or secure backup)
- [ ] Have unseal keys available (from Ansible vault or secure backup)
- [ ] Have `openbao-prod.hcl` config from Git or last known good copy
- [ ] Verify target VM/container has sufficient resources (16GB+ RAM, 4+ CPU)

### Recovery Steps

1. **Provision target infrastructure**
   - [ ] Deploy new VM or container host
   - [ ] Install Docker, Docker Compose, required packages
   - [ ] Configure networking and firewall rules

2. **Restore configuration**
   - [ ] Copy `openbao-prod.hcl` to target data directory
   - [ ] Verify configuration matches expected state
   - [ ] Set correct file permissions (0644 for config, 0700 for data dir)

3. **Restore data**
   - [ ] Stop any running OpenBao instance
   - [ ] Clear existing raft data directory (if corrupted)
   - [ ] Copy latest valid snapshot to raft directory
   - [ ] Verify snapshot checksum matches `.sha256` file
   - [ ] Restore using: `openbao operator raft snapshot-restore -path=<snapshot>`

4. **Start and unseal**
   - [ ] Start OpenBao container
   - [ ] Wait for OpenBao to initialize
   - [ ] Provide unseal keys (3/3 Shamir)
   - [ ] Verify unsealed status via `/v1/sys/health`

5. **Verify restoration**
   - [ ] Check all KV engines are accessible
   - [ ] Verify critical secrets are present (postgresql, redis, minio)
   - [ ] Validate service tokens are functional
   - [ ] Test AppRole authentication for each service
   - [ ] Verify OIDC integration (if configured)

6. **Post-recovery**
   - [ ] Rotate root token (generate new, store securely)
   - [ ] Regenerate all service tokens
   - [ ] Resume backup cron jobs
   - [ ] Re-enable health monitoring
   - [ ] Document recovery time and any issues encountered

### Post-DR Review
- [ ] Measure actual RTO against target
- [ ] Verify data integrity (RPO compliance)
- [ ] Update runbook with lessons learned
- [ ] Schedule next DR test

---

## Appendix: File Inventory

| File | Purpose | Risk |
|------|---------|------|
| `backup_openbao.py` | Backup automation (snapshot + DB copy + rotation) | Low — well-designed |
| `openbao-health-cron.sh` | Health check (container status only) | HIGH — insufficient |
| `inject-secrets.sh` | Docker entrypoint wrapper | Low |
| `openbao_injector.py` | AppRole auth + secret injection | Low |
| `seed_openbao_kv.py` | KV bootstrap from .env | Low |
| `service_tokens.yml` | Service token generation | HIGH — tokens not persisting |
| `kv_bootstrap.yml` | KV engine + secret seeding | Low |
| `unseal.yml` | Manual Shamir unseal | HIGH — no auto-unseal |
| `defaults/main.yml` | Role defaults and variables | Low |

---

*Audit performed by DevOps Engineer AI — iacgenie-platform*
*Next review recommended: 2026-09-17 (30 days)*
