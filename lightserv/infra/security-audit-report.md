# Security Audit Report — VM 192.168.0.118 (vm.iacgenie.com)

**Date:** 2026-06-13
**Auditor:** SecOps Engineer (Claude Code)
**Target:** elementary OS 8 (Ubuntu 24.04.3 LTS), Kernel 6.17.0-35-generic
**Scope:** Full security audit — processes, connections, open ports, container security, firewall, SSH, filesystem

---

## Executive Summary

The VM is running 10 Docker containers (plus 1 stale build artifact) with 14 services exposed via a Cloudflare Tunnel. While the infrastructure has a firewall (ufw) and fail2ban in place, several **critical security gaps** were identified that expose databases, secrets management, and admin panels to unnecessary risk.

| Severity | Count | Key Issues |
|----------|-------|------------|
| CRITICAL | 5 | PostgreSQL privileged, databases exposed, TCP passthrough, secrets world-readable |
| HIGH | 7 | OpenBao dev mode, no Cloudflare Access, services on 0.0.0.0, Jenkins as root |
| MEDIUM | 5 | ip_forward enabled, stale container, auto-update disabled, no kernel hardening |
| LOW | 3 | No seccomp, no resource limits on some services, logging minimal |

---

## 1. System Information

| Field | Value |
|-------|-------|
| Hostname | vm.iacgenie.com |
| OS | elementary OS 8 (Ubuntu 24.04.3 LTS, Noble Numbat) |
| Kernel | 6.17.0-35-generic (PREEMPT_DYNAMIC) |
| CPU | x86_64 |
| User | mkanavi (uid=1000, in docker and sudo groups) |
| SSH Key | Ed25519 (newvm_key) |

---

## 2. SSH Configuration

### Current State
```
X11Forwarding yes          # EXPLICITLY SET — should be no
```

All other directives use OpenSSH defaults:
- `PermitRootLogin prohibit-password` (root login with SSH key is ALLOWED)
- `PasswordAuthentication yes` (password auth is ENABLED)
- `PubkeyAuthentication yes`

### Findings

| Setting | Current | Recommended | Severity |
|---------|---------|-------------|----------|
| X11Forwarding | **yes** | **no** | HIGH |
| PermitRootLogin | prohibit-password (default) | no | HIGH |
| PasswordAuthentication | yes (default) | no | HIGH |
| MaxAuthTries | 6 (default) | 3 | MEDIUM |
| AllowUsers | not set | mkanavi | MEDIUM |
| fail2ban | Running (good) | Running | OK |

### Recommended SSH Hardening
Create `/etc/ssh/sshd_config.d/hardened.conf`:
```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
PermitEmptyPasswords no
MaxAuthTries 3
X11Forwarding no
AllowUsers mkanavi
```

---

## 3. Firewall Analysis

### Current State
- **ufw: ACTIVE** with default DROP policy on INPUT (good)
- **iptables INPUT policy: DROP** (good)
- **fail2ban: RUNNING** (good)

### ufw Rules
```
Port 22/tcp  ALLOW IN  Anywhere      (SSH only)
Port 22/tcp  ALLOW IN  Anywhere (v6)
```

### Critical Finding: Missing Cloudflare Inbound Rules
The firewall currently **only allows SSH (port 22)**. However, Cloudflare Tunnel works by establishing **outbound** connections from the VM to Cloudflare's edge — it does NOT require inbound port 80/443 on the VM. The cloudflared process connects outbound, so the firewall is actually correct.

However, the nginx service on port 80 is listening — this suggests there's **also an nginx reverse proxy for the Mac frontend** that may need the Cloudflare IP ranges whitelisted.

### Firewall Assessment

| Aspect | Status | Severity |
|--------|--------|----------|
| Default policy DROP | Yes | OK |
| fail2ban running | Yes | OK |
| SSH restricted to specific IPs | No (Any) | MEDIUM |
| Cloudflare IP ranges whitelisted | No (not needed for tunnel) | LOW |
| Only SSH port open to LAN | Yes (by default DROP) | OK |

---

## 4. Port Audit

### Listening Ports (Critical Findings)

| Port | Service | Binding | Severity | Note |
|------|---------|---------|----------|------|
| 22 | SSH | 0.0.0.0 | OK | Allowed by ufw, fail2ban active |
| **5432** | **PostgreSQL** | **0.0.0.0** | **CRITICAL** | `listen_addresses = *`, `privileged: true` |
| **6379** | **Redis** | **0.0.0.0** | **CRITICAL** | Should be 127.0.0.1 only |
| **8200** | **OpenBao** | **0.0.0.0** | **HIGH** | Dev mode, no TLS |
| **3001** | **Grafana** | **0.0.0.0** | **HIGH** | Admin dashboard exposed |
| **8080** | **Keycloak** | **0.0.0.0** | **HIGH** | Should be 127.0.0.1 only |
| **8085** | **Jenkins** | **0.0.0.0** | **HIGH** | Admin panel exposed, runs as root |
| **8089/8090** | **Coolify** | **0.0.0.0** | **HIGH** | PaaS panel exposed |
| **9000/9001** | **MinIO** | **0.0.0.0** | **HIGH** | API + Console exposed |
| 9090 | Prometheus | 127.0.0.1 | OK | Correctly localhost-only |
| 20241 | cloudflared | 127.0.0.1 | OK | Correctly localhost-only |

### Services NOT in Docker Compose (Unknown)

| Port | Process | Severity |
|------|---------|----------|
| 80 | nginx | MEDIUM | nginx running on VM (likely Mac frontend proxy via Cloudflare) |
| 5672, 25672 | beam.smp (Erlang) | LOW | From stale `gifted_joliot` container |
| 4369 | epmd | LOW | Erlang Port Mapper Daemon |
| 1053 | dnsmasq | OK | Local DNS resolver |
| 631 | cupsd | OK | CUPS printer service |

---

## 5. Container Security

### Container Inventory

| Container | Image | Ports | Privileged | User | Security Options |
|-----------|-------|-------|------------|------|-----------------|
| iacgenie-postgres-1 | postgres:15-alpine | 0.0.0.0:5432 | **YES** | default | label=disable |
| iacgenie-redis-1 | redis:7-alpine | 0.0.0.0:6379 | No | default | None |
| iacgenie-minio-1 | minio/minio:latest | 0.0.0.0:9000-9001 | No | default | None |
| iacgenie-openbao | quay.io/openbao/openbao:latest | 0.0.0.0:8200 | No | default | None |
| iacgenie-keycloak-1 | quay.io/keycloak/keycloak:26.0 | 0.0.0.0:8080 | No | 1000 | **no-new-privileges:true** |
| iacgenie-jenkins | iacgenie-jenkins | 0.0.0.0:8085 | No | **root** | None |
| iacgenie-prometheus-1 | prom/prometheus:latest | 127.0.0.1:9090 | No | 0 (root) | None |
| iacgenie-grafana-1 | grafana/grafana:latest | 0.0.0.0:3001 | No | 472 | None |
| iacgenie-coolify | ghcr.io/coollabsio/coolify:latest | 0.0.0.0:8089,8090 | No | www-data | None |
| gifted_joliot* | ae58d952c927 (Jenkins build) | 8080,50000 | No | root | None |

*`gifted_joliot` is a stale container from a `docker build` command — should be removed.

### Key Findings

| Issue | Containers Affected | Severity |
|-------|---------------------|----------|
| **Privileged mode** | PostgreSQL | CRITICAL |
| **Running as root** | Jenkins, Prometheus | HIGH |
| **No cap_drop: [ALL]** | All containers | MEDIUM |
| **No no-new-privileges** | 9 of 10 containers | MEDIUM |
| **No readonly rootfs** | All containers | LOW |
| **No seccomp profile** | All containers | LOW |

---

## 6. Cloudflare Tunnel Audit

### Ingress Rules Review

| Hostname | Service | Protocol | Issue |
|----------|---------|----------|-------|
| vm.iacgenie.com | http://127.0.0.1:80 | HTTP | OK (Mac nginx proxy) |
| mac.iacgenie.com | http://192.168.0.120:80 | HTTP | OK (Mac nginx proxy) |
| jenkins.iacgenie.com | http://127.0.0.1:8085 | HTTP | No Cloudflare Access |
| **postgres.iacgenie.com** | **tcp://postgres:5432** | **TCP** | **Databases directly exposed** |
| **redis.iacgenie.com** | **tcp://redis:6379** | **TCP** | **Databases directly exposed** |
| minio.iacgenie.com | http://127.0.0.1:9000 | HTTP | OK |
| console.minio.iacgenie.com | http://127.0.0.1:9001 | HTTP | No Cloudflare Access |
| **vault.iacgenie.com** | **http://127.0.0.1:8200** | **HTTP** | **No auth, dev mode** |
| auth.iacgenie.com | http://127.0.0.1:8080 | HTTP | OK (Keycloak) |
| metrics.iacgenie.com | http://127.0.0.1:9090 | HTTP | No auth |
| dashboards.iacgenie.com | http://127.0.0.1:3001 | HTTP | No Cloudflare Access |
| panel.iacgenie.com | http://127.0.0.1:8089 | HTTP | No Cloudflare Access |
| app.iacgenie.com | http://192.168.0.120:5173 | HTTP | OK |
| api.iacgenie.com | http://192.168.0.120:8000 | HTTP | OK |

### Critical Tunnel Findings

1. **Database TCP passthrough (ports 5432, 6379)** — Databases are directly reachable through the Cloudflare tunnel via raw TCP connections. Anyone who discovers the hostname can connect with NO application-layer authentication. This is the single biggest risk.

2. **OpenBao (vault.iacgenie.com)** — Running in dev mode (no TLS, no authentication), directly accessible. Anyone can read/write secrets.

3. **No Cloudflare Access policies** — Admin panels (Jenkins, Grafana, MinIO Console, Coolify) are reachable by anyone with the hostname. No identity-based authentication at the edge.

---

## 7. Service Configuration Audit

### PostgreSQL
- **listen_addresses = `*`** (all interfaces) — CONFIRMED
- **Running as privileged container** — CONFIRMED
- **No `cap_drop: [ALL]`** — CONFIRMED
- Password auth enabled (password stored in `.env` with 644 permissions)

### Redis
- **Binding: 0.0.0.0:6379** — CONFIRMED
- Password auth configured (`--requirepass`) but binding is wrong
- No `no-new-privileges`

### OpenBao
- **Dev mode: CONFIRMED**
  - `TLS: disabled`
  - `Storage: inmem` (no encryption at rest)
  - `BAO_DEV_ROOT_TOKEN_ID` in environment variables
  - All secrets stored in plaintext in memory
- **Binding: 0.0.0.0:8200** — CONFIRMED

### Keycloak
- Recently restarted (health: starting)
- Runs as user 1000 (good)
- Has `no-new-privileges:true` (good)
- May be running in dev mode based on compose config

### Jenkins
- **Runs as root** (USER root in Dockerfile)
- **No security options** (no cap_drop, no seccomp)
- Port 8085 bound to 0.0.0.0

### MinIO
- Ports 9000-9001 bound to 0.0.0.0
- `logs` bucket set to public in init script

---

## 8. Filesystem & Secrets Audit

### Sensitive File Permissions

| File | Current | Recommended | Severity |
|------|---------|-------------|----------|
| `cloudflared/auth.json` | **644** (world-readable) | **600** | **CRITICAL** |
| `.env` | **644** (world-readable) | **600** | **CRITICAL** |
| `docker/cloudflared/auth.json` | 644 (symlink/copied) | 600 | CRITICAL |

### Git-Exposed Secrets (from codebase review)

| File | Contents | Severity |
|------|----------|----------|
| `iacgenie/docker/.env.pi` | ALL production passwords | CRITICAL |
| `iacgenie/admin_credentials.txt` | Jenkins + Keycloak passwords | CRITICAL |
| `infra/services-secrets.md` | ALL secrets in plaintext | CRITICAL |
| `iacgenie/backend/.env` | SMTP2GO API key | HIGH |
| `iacgenie/infra/pi-infrastructure.md` | SMTP2GO API key | HIGH |
| `test_user_credentials.txt` | Test user password | HIGH |
| `iacgenie/backend/scripts/vault-digger-secrets.sh` | Hardcoded dev token | MEDIUM |
| `infra/iacgenie_vm_health.sh` | Hardcoded sudo password | CRITICAL |

### Cloudflare Tunnel Credentials
- `auth.json` on VM: **644 (world-readable)** — any local user or process can steal tunnel credentials
- `auth.json` in git repo: committed — needs to be gitignored immediately

---

## 9. Kernel Parameters

| Parameter | Current | Recommended | Severity |
|-----------|---------|-------------|----------|
| `net.ipv4.ip_forward` | **1** | **0** | **MEDIUM** |
| `net.ipv4.tcp_syncookies` | 1 | 1 | OK |
| `net.ipv4.conf.all.accept_redirects` | 0 | 0 | OK |
| `kernel.randomize_va_space` | 2 | 2 | OK |
| `kernel.kptr_restrict` | 1 | 2 | MEDIUM |
| `fs.protected_hardlinks` | 1 | 1 | OK |
| `fs.protected_symlinks` | 1 | 1 | OK |
| `kernel.unprivileged_bpf_disabled` | 2 | 2 | OK |

**`ip_forward = 1`** — The VM is acting as a router. This allows network traffic to be forwarded between interfaces. For a service-hosting VM, this should be disabled.

---

## 10. Running Processes

### Expected Services
- `cloudflared-tunnel` — Running (systemd)
- `docker` — Running
- `nginx` — Running (Mac frontend reverse proxy)
- `fail2ban` — Running
- `dnsmasq` — Running (local DNS caching)

### Suspicious/Unknown
- `gifted_joliot` — Stale Jenkins build container (9 hours old, running `ls /usr/share/jenkins/ref/`)
- `epmd` + `beam.smp` — Erlang from stale container (ports 4369, 5672, 25672)
- `nginx` on port 80 — Running on VM (port 80 not in docker-compose)

---

## 11. Remediation Priorities

### Phase 1: CRITICAL (Immediate — within 24 hours)

1. **Remove PostgreSQL `privileged: true`**
   - Replace with `cap_drop: [ALL]` + specific `cap_add`
   - Remove `label=disable` security option

2. **Bind database ports to 127.0.0.1**
   - `docker-compose-newvm.yml`: Change `5432:5432` to `127.0.0.1:5432:5432`
   - Change `6379:6379` to `127.0.0.1:6379:6379`

3. **Remove database TCP passthrough from cloudflared**
   - Delete `postgres.iacgenie.com` ingress rule
   - Delete `redis.iacgenie.com` ingress rule

4. **Fix file permissions**
   - `chmod 600 ~/docker/iacgenie/.env`
   - `chmod 600 ~/docker/iacgenie/cloudflared/auth.json`

5. **Remove stale container**
   - `docker rm gifted_joliot`

### Phase 2: HIGH (Within 48 hours)

6. **Configure Cloudflare Access** for all admin panels:
   - jenkins.iacgenie.com
   - vault.iacgenie.com
   - dashboards.iacgenie.com
   - console.minio.iacgenie.com
   - panel.iacgenie.com
   - auth.iacgenie.com

7. **Remove OpenBao from public tunnel** or add Cloudflare Access

8. **Bind service ports to 127.0.0.1**
   - MinIO: `9000` and `9001`
   - Grafana: `3001`
   - Keycloak: `8080`
   - Jenkins: `8085`
   - OpenBao: `8200`
   - Coolify: `8089` and `8090`

9. **Fix SSH configuration**
   - Disable X11Forwarding
   - Disable password authentication
   - Disable root login

10. **Remove `/home/mkanavi/workspace:/workspace:rw` from Jenkins** or make it read-only

### Phase 3: MEDIUM (Within 1 week)

11. **Disable `ip_forward`** via `/etc/sysctl.d/`
12. **Add `cap_drop: [ALL]` to all containers**
13. **Add `no-new-privileges:true` to all containers**
14. **Rotate all compromised secrets** (passwords in .env.pi, admin_credentials.txt, services-secrets.md)
15. **Add all secrets to `.gitignore` and remove from git history**
16. **Set `kernel.kptr_restrict = 2`**

### Phase 4: LOW (Within 1 month)

17. **Add seccomp profiles** to all containers
18. **Add resource limits** to all containers (memory, CPU)
19. **Run trivy container scanning** on all images
20. **Enable TLS** for internal service communication
21. **Switch OpenBao to production mode** with sealed storage

---

## 12. Files to Modify

| File | Location | Change |
|------|----------|--------|
| `docker-compose-newvm.yml` | `iacgenie/docker/` | Remove `privileged`, add `cap_drop`, fix port bindings |
| `cloudflared/config.yml` | `iacgenie/docker/` | Remove database TCP passthrough, remove OpenBao |
| `jenkins/Dockerfile` | `iacgenie/docker/jenkins/` | Change `USER root` to non-root |
| `minio/init.sh` | `iacgenie/docker/minio/` | Remove public bucket policy |
| `sshd_config.d/hardened.conf` | VM only | SSH hardening |
| `sysctl.d/99-hardening.conf` | VM only | Kernel hardening |
| `.gitignore` | repo root | Ensure all secrets are gitignored |
| `services-secrets.md` | `infra/` | Remove from repo, store locally |

---

## 13. Verification Checklist

After implementing Phase 1 fixes:

- [ ] `sudo ss -tlnp` shows PostgreSQL/Redis only on `127.0.0.1`
- [ ] `nc -zv vm.iacgenie.com 5432` fails from external host
- [ ] `nc -zv vm.iacgenie.com 6379` fails from external host
- [ ] `stat ~/docker/iacgenie/.env` shows `600`
- [ ] `stat ~/docker/iacgenie/cloudflared/auth.json` shows `600`
- [ ] `docker ps` shows no `gifted_joliot` container
- [ ] `postgres.iacgenie.com` no longer resolves/connects
- [ ] `redis.iacgenie.com` no longer resolves/connects

---

## Appendix A: Keycloak Dev Mode Verification

The Keycloak container was recently restarted (health: starting) which caused naming inconsistencies in earlier commands. Based on the docker-compose-newvm.yml configuration:
- Command includes `start-dev` flag (dev mode)
- Dev mode disables HTTPS, uses file-based user storage, skips email verification
- Should be changed to `start --import-realm` for production

## Appendix B: Secrets Rotation Requirements

The following secrets must be considered **potentially compromised** because they existed in plaintext in the git repository:
1. All PostgreSQL passwords
2. All Redis password
3. MinIO root password
4. OpenBao root token and app token
5. Keycloak admin password
6. Grafana admin password
7. JWT secret
8. Cloudflare tunnel credentials
9. SMTP2GO API key
10. Jenkins admin password

**Recommended action:** Rotate all these secrets immediately after the infrastructure is hardened.
