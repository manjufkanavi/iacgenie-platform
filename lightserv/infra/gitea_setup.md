# Gitea Git Service and Actions CI/CD

## 1. Overview & Architecture

Gitea provides Git hosting with built-in Actions-based CI/CD for the iacgenie infrastructure. It replaced Jenkins as the primary Git platform and CI/CD orchestrator.

### Core Technologies:
- **Platform:** Gitea (latest stable, Dockerized)
- **Deployment:** Docker Compose (`docker-compose-newvm.yml`)
- **CI/CD:** Gitea Actions (self-hosted runners)
- **Ingress:** Cloudflared Zero Trust Tunnel
- **Authentication:** Gitea's built-in user system + SSH keys for git operations
- **Database:** SQLite3 (bundled)

---

## 2. Infrastructure Environment

Gitea runs on the same VM as the rest of the iacgenie infrastructure.

| Property | Value |
|----------|-------|
| VM Hostname | `vm.iacgenie.com` |
| Internal IP | `192.168.0.118` |
| OS | elementary OS 8 (Ubuntu 24.04 LTS) |
| Container Name | `iacgenie-gitea` |
| Web UI | `https://gitea.iacgenie.com` |
| SSH (git) | `127.0.0.1:2222` → container port 22 |
| Primary User | `manjufkanavi` (email: `manjufkanavi@gmail.com`) |
| User Password | `Test@1234` (see `services-secrets.md`) |

### SSH Access to VM

```bash
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118
```

---

## 3. Container Deployment

Gitea is defined in `iacgenie/docker-compose-newvm.yml` under service `gitea`.

### Configuration

```yaml
gitea:
  image: gitea/gitea:latest
  container_name: iacgenie-gitea
  environment:
    GITEA__security__INSTALL_LOCK: "true"
    GITEA__service__DISABLE_REGISTRATION: "true"
    GITEA__service__REQUIRE_SIGNIN_VIEW: "true"
    GITEA__admin__NAME: ${GITEA_ADMIN_USER}
    GITEA__admin__PASSWORD: ${GITEA_ADMIN_PASSWORD}
    GITEA__admin__EMAIL: ${GITEA_ADMIN_EMAIL}
  volumes:
    - gitea_data:/data
  ports:
    - "127.0.0.1:3000:3000"   # Web UI
    - "127.0.0.1:2222:22"     # SSH for git
  healthcheck:
    test: ["CMD-SHELL", "curl -f -s http://localhost:3000/ -o /dev/null || exit 1"]
  deploy:
    resources:
      limits:
        memory: 512M
        cpus: "0.25"
```

### Data Storage

- **Volume:** `iacgenie_gitea_data` (Docker named volume)
- **Mount:** `/data` inside container
- **Contents:** Database, repositories, SSH keys, logs, sessions, avatars
- **Host path:** Managed by Docker (not directly accessible)

### Security Settings

| Setting | Value | Purpose |
|---------|-------|---------|
| `INSTALL_LOCK` | `true` | Locks initial setup wizard |
| `DISABLE_REGISTRATION` | `true` | Blocks public sign-ups |
| `REQUIRE_SIGNIN_VIEW` | `true` | Requires login to view any content |
| `ENABLE_REGISTRATION` | `false` | Redundant with DISABLE_REGISTRATION |

---

## 4. Networking & Routing

### Direct Access (VM only)
- **Port 3000:** Gitea web UI (bound to `127.0.0.1` — unreachable from external networks)
- **Port 2222:** SSH for git clone/push (bound to `127.0.0.1`)

### Cloudflare Tunnel
The `cloudflared` systemd service (`cloudflared-tunnel.service`) exposes Gitea securely:

```yaml
ingress:
  - hostname: gitea.iacgenie.com
    path: /*
    service: http://127.0.0.1:3000
```

Traffic flow:
```
Internet → Cloudflare edge → cloudflared tunnel → 127.0.0.1:3000 → Gitea
```

No firewall ports are opened. All external access flows through the encrypted tunnel.

---

## 5. Git Mirroring (GitHub → Gitea)

Gitea serves as a secondary mirror of the primary GitHub repo (`https://github.com/manjufkanavi/iacgenie.git`). Both Mac and VM repos maintain two remotes.

### Remote Setup

| Remote | URL | Purpose |
|--------|-----|---------|
| `origin` | `https://<github-pat>@github.com/manjufkanavi/iacgenie.git` | Primary — GitHub |
| `gitea` | `https://manjufkanavi%40gmail.com:Test%401234@gitea.iacgenie.com/mkanavi/iacgenie.git` | Mirror |

### Initial Mirror (one-time)

Push all branches and tags from the local repo to Gitea:

```bash
git remote add gitea 'https://manjufkanavi%40gmail.com:Test%401234@gitea.iacgenie.com/mkanavi/iacgenie.git'
git config http.postBuffer 524288000
git push gitea --mirror --progress
```

If Gitea already has different refs, restore from the Mac's full repo:

```bash
git push gitea --mirror --force
```

### Automatic Sync via Pre-Push Hook

A pre-push hook (`git/.git/hooks/pre-push`) auto-syncs to Gitea whenever you push to origin (GitHub):

```
git push origin main  →  pushes to GitHub AND automatically to Gitea
git push gitea main   →  pushes to Gitea only (no push back to GitHub)
```

The hook is one-directional (`origin → gitea`) to prevent overwriting remote branches with unpushed local changes.

### Manual Sync

If you need to push to both remotes manually:

```bash
git push origin main && git push gitea main
```

For all branches:

```bash
git push origin --all && git push gitea --all
```

### SSH Key for Gitea (optional — for direct SSH access)

An SSH key pair was generated for Gitea authentication:
- **Private key:** `~/.ssh/gitea_iacgenie_key` (Mac) / `~/.ssh/gitea_iacgenie_key` (VM)
- **Public key:** `~/.ssh/gitea_iacgenie_key.pub`

To enable SSH-based git operations, add the public key to your Gitea profile:
1. Go to `https://gitea.iacgenie.com` → **Settings** → **SSH/GPG Keys** → **Add Key**
2. Paste the content of `~/.ssh/gitea_iacgenie_key.pub`
3. Give it a descriptive title (e.g., `mac-workstation`)

### VM SSH Key Setup

The SSH key files are stored on the VM at:
- `/home/mkanavi/.ssh/gitea_iacgenie_key` (private)
- `/home/mkanavi/.ssh/gitea_iacgenie_key.pub` (public)
- `/home/mkanavi/.ssh/gitea_ssh_key.pub` (copy for Gitea profile)

Add the public key to your Gitea profile via the web UI.

---

## 6. Gitea Actions CI/CD

### Workflow File Format

Workflows are stored in `.gitea/workflows/` in each repository. They follow the GitHub Actions YAML format.

**Example: `.gitea/workflows/ci.yml`**

```yaml
name: CI
on: [push, pull_request]

jobs:
  lint:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - name: Run linters
        run: |
          cd iacgenie/backend
          python -m ruff check .
          python -m mypy --config-file mypy.ini .

  test:
    runs-on: self-hosted
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: |
          cd iacgenie/backend
          python -m pytest tests/ -v
```

### Self-Hosted Runner

**Currently installed and running** on the VM:

| Property | Value |
|----------|-------|
| Binary | `~/gitea-runner/gitea-runner-1.0.8-linux-amd64` |
| Runner name | `iacgenie-runner-1` |
| Version | v1.0.8 |
| Labels | `self-hosted`, `linux` |
| Systemd service | `gitea-runner.service` |
| Enabled on boot | Yes (`enabled`) |
| Working dir | `/home/mkanavi` (where `.runner` config is stored) |

**Status:**

```bash
sudo systemctl status gitea-runner
sudo journalctl -u gitea-runner --no-pager -n 50
```

**Managing the runner service:**
```bash
sudo systemctl status gitea-runner
sudo systemctl restart gitea-runner
sudo systemctl stop gitea-runner
```

**Re-registration** (if runner needs to be recreated):
1. Log in to Gitea web UI
2. Navigate to **Settings → Actions → Runners**
3. Delete the old runner and click **Register Runner** to get a new token
4. On the VM:
   ```bash
   ~/gitea-runner/gitea-runner-1.0.8-linux-amd64 register \
     --instance https://gitea.iacgenie.com \
     --token <TOKEN> --labels self-hosted,linux --name iacgenie-runner-1 \
     --no-interactive
   sudo systemctl restart gitea-runner
   ```

### Migrating from Jenkinsfiles

| Jenkins | Gitea Actions |
|---------|--------------|
| `Jenkinsfile` | `.gitea/workflows/ci.yml` |
| `node { stage('name') { ... } }` | `jobs:` with `steps:` |
| `sh 'command'` | `run: command` |
| `docker build ...` | `runs-on: self-hosted` (Docker available on runner) |
| `github-webhook` trigger | `on: push` (native) |

---

## 7. Administration

### Check Status

```bash
# Container health
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118 "docker inspect --format='{{.State.Status}}' iacgenie-gitea"

# Verify tunnel access
curl -sI https://gitea.iacgenie.com | head -3
```

### Access Admin Shell

```bash
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118 "docker exec -it iacgenie-gitea /bin/bash"
```

### View Logs

```bash
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118 "docker logs -f iacgenie-gitea"
```

### Check Users

```bash
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118 \
  "docker exec -u git iacgenie-gitea sh -c \"sqlite3 /data/gitea/gitea.db \\\"SELECT id, name, email, is_admin FROM user;\\\"\""
```

### View Config Inside Container

```bash
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118 \
  "docker exec iacgenie-gitea cat /data/gitea/conf/app.ini | grep -A5 '\\[service\\]'"
```

---

## 8. Operations

### Restart Service

```bash
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118 \
  "cd ~/docker/iacgenie && docker-compose -f docker-compose-newvm.yml restart gitea"
```

### Update (Pull New Image)

```bash
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118 \
  "cd ~/docker/iacgenie && docker-compose -f docker-compose-newvm.yml pull gitea && docker-compose -f docker-compose-newvm.yml up -d gitea"
```

### Backup Data

The data is stored in a Docker named volume. To back it up:

```bash
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118 \
  "docker run --rm -v iacgenie_gitea_data:/data -v /tmp:/backup alpine tar czf /backup/gitea_backup.tar.gz -C /data ."
# Retrieve the backup
scp mkanavi@192.168.0.118:/tmp/gitea_backup.tar.gz ~/
```

### Restore Data

```bash
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118 \
  "docker run --rm -v iacgenie_gitea_data:/data -v /tmp:/backup alpine tar xzf /backup/gitea_backup.tar.gz -C /data"
# Then restart Gitea
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118 \
  "cd ~/docker/iacgenie && docker-compose -f docker-compose-newvm.yml restart gitea"
```

### Sync Local Config to VM

```bash
rsync -avz iacgenie/docker-compose-newvm.yml \
  -e "ssh -i ~/.ssh/newvm_key" mkanavi@192.168.0.118:~/docker/iacgenie/
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118 \
  "cd ~/docker/iacgenie && docker-compose -f docker-compose-newvm.yml restart gitea"
```

---

## 9. Troubleshooting

### Registration Still Allowed
Check the running config inside the container:
```bash
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118 \
  "docker exec iacgenie-gitea grep DISABLE_REGISTRATION /data/gitea/conf/app.ini"
# Expected: DISABLE_REGISTRATION = true
```

If the value is `false`, fix it in-place:
```bash
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118 \
  "docker run --rm -v iacgenie_gitea_data:/data alpine sed -i 's/DISABLE_REGISTRATION = false/DISABLE_REGISTRATION = true/' /data/gitea/conf/app.ini"
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118 \
  "cd ~/docker/iacgenie && docker-compose -f docker-compose-newvm.yml restart gitea"
```

### Container Not Healthy
```bash
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118 "docker inspect --format='{{.State.Health.Status}}' iacgenie-gitea"
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118 "docker logs iacgenie-gitea | tail -30"
```

### Runner Not Processing Jobs
```bash
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118 "sudo systemctl status gitea-runner"
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118 "sudo journalctl -u gitea-runner --no-pager -n 50"
```

### Push to Gitea Fails with Authentication Error
Verify the gitea remote URL includes credentials:
```bash
git remote -v | grep gitea
# Should show: https://manjufkanavi%40gmail.com:Test%401234@gitea.iacgenie.com/...
```

### Repository Out of Sync
Force-sync Gitea from Mac's full repo:
```bash
git push gitea --mirror --force
```

### 404 on gitea.iacgenie.com
```bash
# Verify Gitea is running locally
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118 "curl -sI http://127.0.0.1:3000/ | head -3"
# Verify cloudflared config has the Gitea ingress rule
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118 "grep -A3 'gitea.iacgenie.com' ~/docker/iacgenie/cloudflared/config.yml"
# Restart cloudflared if needed
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118 'echo "Murdock@12345" | sudo -S systemctl restart cloudflared-tunnel'
```

---

## 10. Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITEA_ADMIN_USER` | Yes | Admin username |
| `GITEA_ADMIN_PASSWORD` | Yes | Admin password |
| `GITEA_ADMIN_EMAIL` | Yes | Admin email |

All three must be set in `~/docker/iacgenie/.env` on the VM. No defaults — Gitea will refuse to start without them.

---

## 11. Comparison: Jenkins → Gitea

| Aspect | Jenkins | Gitea |
|--------|---------|-------|
| Git hosting | Separate (GitHub/GitLab) | Built-in |
| CI/CD | Jenkinsfile (Groovy pipeline) | `.gitea/workflows/*.yml` (YAML) |
| Runner | Jenkins agents | Gitea Actions runners |
| Config format | Groovy / JCasC YAML | YAML |
| Image size | ~1.5 GB | ~250 MB |
| Resource usage | ~512MB base | ~128MB idle |
| Single control plane | No (Git + CI/CD separate) | Yes (Git + CI/CD unified) |
