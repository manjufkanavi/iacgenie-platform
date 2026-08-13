# OpenBao Deployment Audit Report

## VM State vs Ansible Script Audit

### Current VM State
- **OpenBao**: v2.6.0, running, Raft storage, TLS via Let's Encrypt
- **HCL**: `/etc/letsencrypt/live/vault.iacgenie.com/` (certs), `0.0.0.0:8200` listener
- **Secret Engines**: `iacgenie/`, `lightserp/`, `terraform/` (all kv v2)
- **Policies**: `default`, `iacgenie-backend-svc`, `lightserp-api-svc`, `openbao-backup`, `root-admin`, `root`
- **AppRoles**: `iacgenie-backend-svc` (7200s TTL), `lightserp-api-svc` (7200s TTL)
- **Nginx**: Rate limiting, security headers, vHost routing, `/v1/auth/` rate limit
- **Cloudflare**: vHost passthrough, TLS at edge, HTTP→HTTPS passthrough (no redirect loop)

### Drifts Found
| # | File | Ansible (drifted) | VM (current) | Impact |
|---|------|-------------------|--------------|--------|
| 1 | prod.hcl | TLS certs: `/etc/openbao/tls/` | `/etc/letsencrypt/live/vault.iacgenie.com/` | ❌ Deploy will break TLS |
| 2 | prod.hcl | Raft: no snapshot_interval | No snapshot_interval (matches) | OK |
| 3 | prod.hcl | listener: `0.0.0.0:8200` | `0.0.0.0:8200` (matches) | OK |
| 4 | Both policies | Identical content | Identical content | ⚠️ No service scoping |
| 5 | openbao-init.yml | AppRole: `iacgenie-backend` | `iacgenie-backend-svc` | ❌ Wrong role name |
| 6 | openbao-init.yml | AppRole: `lightserp` | `lightserp-api-svc` | ❌ Wrong role name |
| 7 | openbao-init.yml | Phase 7.5: only KC secrets | 14+ secrets stored | ❌ Missing secrets |
| 8 | backup_openbao.py | `h.update(h)` bug | Has `h.update(h)` bug | ⚠️ Wrong checksums |
| 9 | .env.j2 | Generic template | Actual content differs | ⚠️ Misleading |
| 10 | Nginx config | Missing rate limiting | Has rate limiting | ❌ Deploy will remove rate limiting |
| 11 | openbao-backup policy | Missing | Exists on VM | ❌ Not in Ansible |
| 12 | root-admin policy | Missing | Exists on VM | ❌ Not in Ansible |

### Security Audit Findings (Antares)
| Severity | Finding | Fix |
|---|---------|-----|
| P1 | .env world-readable | chmod 600 |
| P1 | No audit logging enabled | Enable file-based audit via API |
| P2 | TLS cert for remote use | Bind to 127.0.0.1:8200 in container |
| P3 | Single-node Raft (not HA) | Accept for single-server; improve backups |
| P2 | AppRole no CIDR restriction | Add token_bound_cidrs (future) |
| P2 | Backup checksum bug | Fix `h.update(h)` → `h.update(chunk)` |
| P1 | OpenBao-accessible via `0.0.0.0` | Bind to `127.0.0.1` in HCL |

### HA Assessment
**Current**: Single-node Raft (no HA)
**Assessment**: Acceptable for single-server. Improvements:
- 6-hourly snapshots (✅ already exists)
- Off-box backup to MinIO (✅ already exists via backup script)
- No automated failover (expected for single-node)

### Backup Assessment
**Current**: 6-hourly snapshot via cron, 30-day retention, SHA256 checksums
**Issues**: 
1. Checksum bug (fixed in plan)
2. No off-box replication to external storage (MinIO push missing)
3. No verification of snapshot validity

### Plan Summary
1. ✅ Fix prod.hcl (TLS paths, bind to 127.0.0.1)
2. ✅ Fix policies (scoped per-service + create missing)
3. ✅ Fix AppRole names in playbook
4. ✅ Add all KV secrets in Phase 7.5
5. ✅ Create missing policies (openbao-backup, root-admin)
6. ✅ Fix backup checksum bug + add MinIO push
7. ✅ Sync injector configs with actual .env
8. ✅ Add Nginx rate limiting config
9. ✅ Add backup AppRole creation
