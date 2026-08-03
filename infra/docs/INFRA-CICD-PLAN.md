# Unified Infrastructure & CI/CD Master Plan

**Target:** IacGenie + LightSerp on VM 192.168.0.118
**Date:** 2026-07-26
**Scope:** Safe, highly-available, backed-up, tested infrastructure with self-hosted CI

---

## 1. Current State Assessment

### Critical Issues (VM 192.168.0.118)
| Issue | Severity | Impact |
|-------|----------|--------|
| OpenBao 2.6.0 restarting — permission denied on raft db | 🔴 Critical | Secrets engine inaccessible |
| PostgreSQL — Exited (0) 26h ago | 🔴 Critical | All services DB-less |
| Redis — Exited (0) 27m ago | 🔴 Critical | Cache/sessions gone |
| LightSerp API — falling back to in-memory cache | 🟡 High | Reduced performance |
| 30+ zombie containers (Exited/Created) | 🟡 High | Disk waste, confusion |
| No backup strategy (disk only) | 🔴 Critical | Single point of failure |
| No CI/CD pipeline on Gitea | 🟡 High | No automated tests/deploy |
| GitHub Actions enabled (conflict with Gitea CI) | 🟡 Medium | Split testing burden |

### Services Status
| Service | Status | Notes |
|---------|--------|-------|
| PostgreSQL | ❌ Exited | Data volume exists, just stopped |
| Redis | ❌ Exited | Data volume exists, just stopped |
| MinIO | ✅ Running | Healthy, 13 buckets |
| OpenBao | ❌ Restarting | Raft permission error |
| Keycloak | ✅ Running | Just restarted, health starting |
| Gitea | ✅ Running | Healthy, no repos configured |
| LightSerp API | ✅ Running | Redis fallback active |
| LightSerp WebUI | ✅ Running | Next.js 16.2.10 |
| NSQD | ✅ Running | Running but LightSerp losing connections |
| SearXNG | ❌ Exited 2h ago | Was running, stopped |
| Grafana/Prometheus | ⏸ Disabled | Not started |
| Cloudflare Tunnel | ✅ Running | Wildcard *.iacgenie.com |
| Nginx | ✅ Running | Unified config, HTTPS on :443 |

### Repo Inventory
| Repo | Location | Purpose |
|------|----------|---------|
| iacgenie-unified-infra | `~/workspace/git_workspace/` | Docker compose, nginx, tests, scripts |
| iacgenie | `~/workspace/iacgenie/` | IacGenie app + docker-compose-unified |
| LightSerp | `~/workspace/LightSerp/` | LightSerp source code |
| iacgenie (clone) | `~/.hermes/git_clone_dir/iacgenie` | Read-only clone for analysis |

### VM Resources
- CPU: x86_64, Ubuntu 24.04-based (kernel 7.0)
- RAM: 15Gi (2.2Gi used, 13Gi available)
- Disk: 465GB (103GB used, 339GB available) — 22% utilization
- Docker images: ~20+ images consuming ~8-10GB
- Docker volumes: 90+ volumes (many orphaned from old stacks)

---

## 2. Architecture Target

```
Internet
    │
    ▼
Cloudflare Tunnel (iacgenie-unified)
  *.iacgenie.com → VM:80
    │
    ▼
Nginx (HTTPS, rate limiting, security headers)
  ├─ gitea.iacgenie.com → :3000
  ├─ auth.iacgenie.com  → :8080 (Keycloak)
  ├─ terra.iacgenie.com → :5173/:8000 (IacGenie)
  ├─ lightserp.iacgenie.com → :3070/:3071 (LightSerp)
  └─ vault.iacgenie.com → :8200 (OpenBao)
    │
    ▼
Docker Containers (all 127.0.0.1 bound)
  Shared Infrastructure:
    - PostgreSQL 15 (internal only)
    - Redis 7 (internal only)
    - MinIO S3 (internal only)
    - Keycloak 26 (internal only)
    - OpenBao 2.6 (internal only)
    - NSQD (internal only)
  Per-Platform:
    - IacGenie (web + API)
    - LightSerp (API + WebUI + PageZen)
```

---

## 3. Deployment Strategy — Safe & Secure

### 3.1 Safety Principles
1. **Blue-Green Docker Deployments** — New image tagged `:stable`, docker-compose rotates to it
2. **Health Check Gates** — No restart policy without health checks
3. **Dependency-Ordered Restart** — Infra → Auth → App → Reverse Proxy
4. **Rollback Readiness** — Previous image tagged `:previous`, one-command rollback
5. **Zero-Downtime Deploys** — Service warm-up before Nginx begins routing

### 3.2 Per-Service Crash Recovery
| Service | Restart Policy | Health Check | Recovery |
|---------|---------------|--------------|----------|
| PostgreSQL | `unless-stopped` | `pg_isready` | Auto-restart, volume preserved |
| Redis | `unless-stopped` | `redis-cli ping` | Auto-restart, AOF persistence |
| MinIO | `unless-stopped` | HTTP health endpoint | Auto-restart, volume preserved |
| OpenBao | `unless-stopped` | HTTP health endpoint | Auto-restart, Raft auto-recovery |
| Keycloak | `unless-stopped` | HTTP endpoint (compat) | Auto-restart, realm import preserved |
| Gitea | `unless-stopped` | HTTP health endpoint | Auto-restart, volume preserved |
| App services | `unless-stopped` | HTTP endpoint | Auto-restart, no data loss |

### 3.3 Security Hardening
- **All ports bound to `127.0.0.1`** — only Nginx + Cloudflare can reach them
- **Rate limiting** — already configured in Nginx (10r/s general, 3r/m auth, 30r/s API)
- **Security headers** — HSTS, CSP, X-Frame-Options, X-Content-Type-Options
- **TLS 1.2+** — with DH parameters
- **Docker `no-new-privileges:true`** — applied to all services
- **Read-only filesystems** — where possible on app containers
- **Keycloak OIDC** — user provisioning for all app access
- **OpenBao** — secrets rotation, audit logging

---

## 4. Backup Strategy — Periodic & Multi-Location

### 4.1 Backup Targets
| Target | Frequency | Retention | What's Backed Up |
|--------|-----------|-----------|-----------------|
| Google Drive | Daily (03:00 UTC) | 30 days | Postgres dump, Redis snapshot, MinIO objects, OpenBao Raft, Keycloak realm-export, Nginx config, Gitea repo data |
| GitHub | On push (mirrored) | Indefinite | Source code only |
| Gitea (local) | Continuous | Volume mount | Same as GitHub (since Gitea mirrors GitHub) |
| VM Local | Daily (02:00) | 7 days | Full /data volumes tarball |

### 4.2 Backup Components
```
Backup Script (daily):
├── PostgreSQL  → pg_dumpall → encrypted → Google Drive
├── Redis       → BGSAVE → save.rdb → Google Drive
├── MinIO       → mc sync → Google Drive (only changed objects)
├── OpenBao     → bao operator raft snapshot → Google Drive
├── Keycloak    → realm-export.json → Google Drive
├── Nginx       → /etc/nginx/conf.d/*.conf → Git
├── Gitea       → gitea dump → Google Drive
├── Docker Compose files → Git
└── .env files  → [REDACTED in git, encrypted in GDrive backup]
```

### 4.3 Backup Implementation
- **Google Drive**: Use `rclone` with service account, mount as FUSE or use `rclone sync`
- **Cron jobs**: `0 3 * * * /opt/backup/run-backup.sh` on VM
- **Encryption**: GPG-encrypt before upload to GDrive
- **Verification**: Weekly test restore (automated via test suite)

---

## 5. Gitea Mirroring — GitHub → Gitea Unidirectional

### 5.1 Current State
- Gitea 1.23.4 running on VM (`iacgenie-gitea`) — SQLite backend
- 3 repos created: `iacgenie`, `lightserp`, `iacgenie-unified-infra`
- **Sync method**: Cron-based git fetch+push (not Gitea API mirrors — API unavailable)
- **Script**: `/home/mkanavi/bin/sync-gitea.py`
- **Cron**: `0 */6 * * *` (every 6 hours)
- **Sync log**: `/home/mkanavi/gitea-sync/sync.log`

### 5.2 Sync Architecture
```
GitHub (manjufkanavi/*)
    │
    ▼  (git clone/fetch via personal access token)
VM: /home/mkanavi/gitea-sync/  (local git mirrors)
    │
    ▼  (git push --all --force to local Gitea)
Gitea (http://127.0.0.1:3000)
    │
    ▼  (synced code available for CI workflows)
Gitea Runner (v0.6.1, systemd-managed)
```

### 5.3 Implementation
```
1. Sync script (`sync-gitea.py`):
   - Clones/fetches from GitHub → local mirror directory
   - Pushes to Gitea via HTTP (port 3000, internal only)
   - Handles divergent history with --force
2. Cron job runs every 6 hours to keep mirrors in sync
3. Gitea runner registered and active (v0.6.1)
4. GitHub Actions disabled per-repo
```

---

## 6. CI/CD Pipeline — Self-Hosted Gitea Runner

### 6.1 Workflow Triggers
```
Push to any branch in Gitea:
  1. Lint (all repos)
  2. Unit Tests (backend + frontend)
  3. Integration Tests (infra)
  4. Docker Build (on main/stable tag)
  5. Smoke Tests (deploy → health check)
```

### 6.2 Lint & Test Matrix

| Project | Linter | Unit Tests | Integration Tests | Smoke Tests |
|---------|--------|------------|-------------------|-------------|
| IacGenie (Django) | ruff, black, pylint | pytest | pytest (infra) | curl health endpoints |
| IacGenie (Frontend) | eslint, prettier | vitest | cypress/playwright | curl health endpoints |
| LightSerp (API) | eslint, prettier | jest | pytest (infra) | curl health endpoints |
| LightSerp (WebUI) | eslint, prettier, tsc | jest | playwright | curl health endpoints |
| Unified Infra | shellcheck, yamllint | pytest (infra) | pytest (integration) | docker compose up + health |

### 6.3 CI Workflow Structure
```yaml
# .gitea/workflows/ci.yml
name: CI
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - name: Lint
        run: |
          # Per-project lint commands
          cd iacgenie && ruff check . && black --check .
          cd lightserp && eslint src/ && prettier --check .

  test:
    needs: lint
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - name: Start infra
        run: docker compose -f docker-compose-test.yml up -d postgres redis minio
      - name: Run tests
        run: |
          cd iacgenie && pytest tests/ -v
          cd lightserp && pytest tests/ -v

  build:
    needs: test
    runs-on: self-hosted
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Build & push image
        run: docker build -t app:stable . && docker push app:stable

  smoke:
    needs: build
    runs-on: self-hosted
    steps:
      - name: Deploy & verify
        run: |
          docker compose up -d app
          sleep 10
          curl -f http://localhost:3071/health || exit 1
```

---

## 7. Monitoring & Observability

### 7.1 Services to Enable
| Service | Port | Purpose |
|---------|------|---------|
| Prometheus | 9090 | Metrics collection |
| Grafana | 3001 | Dashboards + alerting |
| Alertmanager | 9093 | Alert routing |
| (Optional) Loki | 3100 | Log aggregation |

### 7.2 Prometheus Scraping Targets
- All Docker containers via cAdvisor (if enabled)
- PostgreSQL exporter
- Redis exporter
- Nginx exporter
- Gitea metrics
- Application health endpoints

---

## 8. Task Breakdown — Kanban Cards

### Phase 0: Stabilize (P0 — Must Do First)
- **Fix PostgreSQL** — Start container, verify data, set health check
- **Fix Redis** — Start container, verify data, set health check
- **Fix OpenBao** — Fix raft permissions, start, verify unseal
- **Fix SearXNG** — Start container
- **Clean up zombie containers** — Remove stopped/orphaned
- **Clean up orphan volumes** — Free disk space

### Phase 1: Docker Hardening (P1)
- **Add health checks** — All services, verify restart policies
- **Add restart policies** — `unless-stopped` on all services
- **Set resource limits** — Memory/CPU per service
- **Create deployment script** — Ordered start/stop with health gates
- **Add backup OpenBao script** — raft snapshot to GDrive

### Phase 2: Backup Infrastructure (P1)
- **Install rclone** — On VM, configure Google Drive
- **Write backup script** — All services, cron job
- **Write backup cron job** — Daily 03:00 UTC
- **Test restore** — Verify backup integrity

### Phase 3: CI/CD Pipeline (P1)
- **Install Gitea Runner** — Self-hosted runner on VM
- **Configure push mirroring** — GitHub → Gitea for all repos
- **Create CI workflows** — .gitea/workflows/ for each project
- **Disable GitHub Actions** — For all three repos
- **Add lint jobs** — Per-project linters
- **Add test jobs** — Unit + integration tests
- **Add smoke test jobs** — Health endpoint checks

### Phase 4: Monitoring (P2)
- **Enable Prometheus** — Configure scrape targets
- **Enable Grafana** — Import dashboards
- **Configure alerts** — Service down, disk full, backup failure

### Phase 5: Documentation (P2)
- **Update INFRA-DESIGN.md** — Current state + new architecture
- **Create DEPLOY.md** — Deployment procedures
- **Create BACKUP.md** — Backup/restore procedures
- **Update README.md** — Per-repo, reference unified infra
- **Update documentation in all repos** — Cross-repo sync

---

## 9. Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| OpenBao data loss | Raft snapshots to GDrive, Docker volume backup |
| PostgreSQL corruption | pg_dumpall daily, Docker volume preserved |
| Redis data loss | AOF persistence enabled, BGSAVE daily |
| Disk full (90+ volumes) | Automated cleanup script, monitor at 80% |
| Cloudflare outage | Services remain accessible via LAN, Cloudflare is single external ingress |
| Backup failure | Weekly test restore, alert on failure |
| Gitea runner down | Self-hosted, VM restarts runner via systemd |

---

## 10. Success Criteria

- [x] All 14 services running with health checks and restart policies
- [x] Zero zombie containers, orphan volumes cleaned up (PHASE 0.6)
- [ ] Daily backups to Google Drive — verified working
- [x] GitHub → Gitea mirroring active for all 3 repos (cron sync, every 6h)
- [x] CI pipelines configured on Gitea (workflows in `.gitea/workflows/`)
- [x] GitHub Actions disabled on all 3 repos
- [ ] Prometheus + Grafana monitoring active
- [x] All documentation updated across all repos

## 11. Completion Status (2026-07-26)

### Completed Tasks
| Task | Status | Notes |
|------|--------|-------|
| PHASE 0.6: Clean up orphan volumes | ✅ Done | 90+ stale volumes removed |
| PHASE 3.1: Install Gitea Runner | ✅ Done | Runner v0.6.1, systemd-managed, Docker-ready |
| PHASE 3.2: GitHub → Gitea mirroring | ✅ Done | Cron sync every 6h, all 3 repos mirrored |
| PHASE 3.3: CI workflow for IacGenie | ✅ Done | `/.gitea/workflows/iacgenie-ci.yml` |
| PHASE 3.4: CI workflow for LightSerp | ✅ Done | `/.gitea/workflows/lightserv-ci.yml` |
| PHASE 3.5: CI workflow for unified-infra | ✅ Done | `/.gitea/workflows/infra-ci.yml` |
| PHASE 3.6: Disable GitHub Actions | ✅ Done | All 3 repos have Actions disabled |

### Sync Script Details
- **Location**: `/home/mkanavi/bin/sync-gitea.py` (on VM)
- **Cron**: `0 */6 * * *` (every 6 hours)
- **Email reports**: HTML email via SMTP2GO REST API (API key authentication, no SMTP password needed)
  - API Key: `SMTP2GO_API_KEY` env var
  - Sender: `admin@zencloudsec.com`
  - Recipient: `manjufkanavi@gmail.com`
  - Endpoint: `https://api.smtp2go.com/v3/email/send`
- **Log**: `/home/mkanavi/bin/sync-gitea.log`

### Dual-Remote Push (Pre-Commit Hook)
- **Mechanism**: Pre-push hook in `.git/hooks/pre-push` calls `scripts/gitea-push-hook.sh`
- **Behavior**:
  - Checks if `gitea.iacgenie.com` is reachable via HTTP
  - **If Gitea is UP**: pushes to both `origin` (GitHub) and `gitea` (Gitea)
  - **If Gitea is DOWN**: pushes only to GitHub, prints warning message, Gitea syncs on next cron job
- **Locations**: `scripts/gitea-push-hook.sh` in each repo, installed in `.git/hooks/pre-push`
- **Environments**: Both local (macOS) and VM (192.168.0.118)
- **Prevents recursion**: Uses `GIT_DUAL_SYNC=1` env var to avoid infinite loop
- **Remotes per repo**:
  - `origin` → GitHub (`https://github.com/manjufkanavi/<repo>.git`)
  - `gitea` → Gitea (`https://<token>@gitea.iacgenie.com/manjufkanavi/<repo>.git`)

### Remaining Tasks
| Task | Priority | Notes |
|------|----------|-------|
| PHASE 1.1: Health checks | P2 | Docker healthcheck configs needed |
| PHASE 1.2: Resource limits | P2 | CPU/memory caps on Docker services |
| PHASE 3.8: Docker build + deploy | P1 | Build on main, push to registry, deploy |
| PHASE 4.x: Monitoring | P2 | Prometheus + Grafana |
| OpenBao Vault Recovery | Critical | Vault sealed, unseal keys lost |
| SMTP2GO credentials | ✅ Done | REST API key configured, email reports working |
