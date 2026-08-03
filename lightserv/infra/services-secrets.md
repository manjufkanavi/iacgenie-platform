# IacGenie Services Secrets

> **DO NOT commit this file to git.** Add to `.gitignore` if necessary.
> Generated: 2026-06-03
> **Updated:** 2026-07-22 (OpenBao upgraded to production mode with new credentials)
> Environment: VM 192.168.0.118

## Generated Secrets (Core Stack)

| # | Service | Key | Value |
|---|---------|-----|-------|
| 1 | PostgreSQL (superuser) | `POSTGRES_SUPER_PASSWORD` | `T4i2ColvZjKvHYCp2WM2Up-yz5NCZI1jvbWvlpn_0Ww` |
| 2 | PostgreSQL (iacgenie app) | `POSTGRES_APP_PASSWORD` | `qG52RfEBvjzZWd7ePOKFtfAKU8jchHd26eGDoUXxkfo` |
| 3 | PostgreSQL (Keycloak DB) | `POSTGRES_KC_PASSWORD` | `swgJ9lj1xvCQa4igqbTcsYxdbyFhPB9_XyX5s7NINgk` |
| 4 | MinIO | `MINIO_ROOT_PASSWORD` | `4ourQBTbywTA5Hg3NF8o__6QI_vVw2ZmZibz3P5COA0` |
| 5 | OpenBao (root) | `OPENBAO_ROOT_TOKEN` | `s.rSbMYziTmxxIi7BRnJ4kxM7D` |
| 6 | OpenBao (application) | `OPENBAO_TOKEN` | `s.rSbMYziTmxxIi7BRnJ4kxM7D` |
| 7 | OpenBao admin user | `OPENBAO_ADMIN_PASSWORD` | `3bWLGXFwEQVtFXFOKDbTg` |
| 8 | Keycloak admin | `KEYCLOAK_ADMIN_PASSWORD` | `p58-PWVqWN8qbkzSGyyIrXh2IT1h2kxddW1edHkKb0A` |
| 9 | Grafana admin | `GRAFANA_ADMIN_PASSWORD` | `ZiaEtKRnDguVxhMWBJClQoU-vPC4tesTsrEPNHx9PGA` |
| 10 | JWT (backend) | `JWT_SECRET` | `8B59kYTtqJ6naCIhrZFIUaOufzzumZaOFHTj5GEgzXDMQDnWTcLJnXzx5W7UcfFT1Aa2rrm_sXtih8J8z0XLBw` |
| 11 | Redis | `REDIS_PASSWORD` | `wQhAAiMf5BbU8fN9E9Dc3yXMe22uJ0lIy3ybv5V4xtQ` |
| 12 | Gitea admin | `GITEA_ADMIN_PASSWORD` | `O4cZWjXPbVwgwFbtahfGrms4MjkzProUhcqt1IsoOJw=` |
| 13 | Gitea user | Account credentials | User: `manjufkanavi` (`manjufkanavi@gmail.com`), Password: `Test@1234` |

## External Secrets (Obtain Manually)

| # | Service | Key | Where to Obtain |
|---|---------|-----|-----------------|
| 13 | Cloudflare Tunnel | `CLOUDFLARE_TUNNEL_TOKEN` | Cloudflare Zero Trust Dashboard → Networks → Access → Tunnels |
| 14 | SMTP (SMTP2GO) | `SMTP2GO_API_KEY` | SMTP2GO Dashboard → Settings → API Keys |
| 15 | Sentry | `SENTRY_DSN` | Sentry Dashboard → Project Settings → DSN |
| 16 | GitHub (Jenkins SCM) | `GITHUB_TOKEN` | GitHub → Settings → Developer settings → Personal access tokens (classic) → Select `repo` scope |

## Deferred Secrets (Phase 3b — ELK/Digger/Jaeger)

| # | Service | Key | When to Generate |
|---|---------|-----|------------------|
| 17 | Elasticsearch | `ELASTIC_PASSWORD` | When adding ELK stack |
| 18 | Digger DB | `DIGGER_DB_PASSWORD` | When adding Digger |
| 19 | Alertmanager | `ALERTMANAGER_PASSWORD` | When adding alerting |

---

## Jenkins Credential Management

### How Jenkins Credentials Are Stored

Jenkins uses a **three-file cryptographic model** for credential storage. All files live in the persistent bind mount at `/home/mkanavi/docker/iacgenie/jenkins_data/` (`/var/jenkins_home` inside the container):

| File | Purpose | Encryption |
|------|---------|------------|
| `credentials.xml` | Stores credential definitions (IDs, usernames, URLs) | Plaintext — do NOT back up as-is |
| `secrets/master.key` | Master encryption key for the credential store | Encrypted by Jenkins instance ID |
| `secrets/secret.key` | Secondary key used in the decryption chain | Combined with master.key |

**Critical:** The `secrets/master.key` and `secrets/secret.key` files are the keys that decrypt `credentials.xml`. If these are lost or regenerated (e.g., fresh Jenkins install), all previously stored credentials become **permanently unrecoverable**.

### Files to Back Up Separately

These files must be included in off-site backups, stored **separately** from regular Jenkins data backups:

```
/home/mkanavi/docker/iacgenie/jenkins_data/secrets/master.key
/home/mkanavi/docker/iacgenie/jenkins_data/secrets/secret.key
/home/mkanavi/docker/iacgenie/jenkins_data/secrets/hudson.util.Secret
```

### Pre-Configured Credentials

| ID | Type | Description | Configured Via |
|----|------|-------------|----------------|
| `github-token` | Secret Text | GitHub Personal Access Token (SCM access) | JCasC (`jenkins.config.yml`) — set via `GITHUB_TOKEN` env var |
| `github-ssh` | SSH Username with Private Key | SSH key for `git@github.com:manjufkanavi/iacgenie.git` | Must be added via Jenkins UI → Manage Credentials |

### How to Add SSH Credentials for GitHub Access

1. Navigate to `https://jenkins.iacgenie.com` → Manage Jenkins → Credentials
2. Click the system domain (left sidebar, first icon)
3. Click "Add Credentials"
4. Select **SSH Username with private key**
5. ID: `github-ssh` (must match what Jenkinsfiles reference)
6. Username: `git`
7. Private Key: Paste your SSH private key content (e.g., `~/.ssh/id_ed25519`)
8. Description: `GitHub SSH Key — terragenius repo access`
9. Click OK

### How to Add API Tokens via JCasC

For service-level credentials (CI pipelines, external APIs), add them to `jenkins.config.yml` under the `credentials:` section:

```yaml
credentials:
  system:
    domainCredentials:
      - credentials:
          - string:
              scope: SYSTEM
              id: docker-registry-creds
              secret: "${DOCKER_REGISTRY_TOKEN:-}"
              description: "Docker Registry Token"
          - usernamePassword:
              scope: SYSTEM
              id: mail-credentials
              username: "${MAIL_USER:-}"
              password: "${MAIL_PASSWORD:-}"
              description: "SMTP Credentials"
```

These are injected from environment variables at Jenkins startup and persist in the encrypted credential store.

### Jenkins Data Persistence

Jenkins data is stored in a Docker bind mount:

```yaml
volumes:
  - /home/mkanavi/docker/iacgenie/jenkins_data:/var/jenkins_home
```

This ensures credentials and configuration persist across:
- Container recreation (`docker compose up -d --force-recreate`)
- VM reboot
- Docker daemon restarts

**Never delete** `/home/mkanavi/docker/iacgenie/jenkins_data/` without first backing up the `secrets/` directory.

---

## Cloudflare Access (Optional — Recommended Upgrade)

### Why Add Cloudflare Access?

Cloudflared tunnel provides encrypted transport (like TLS) but does NOT authenticate users. Anyone who knows `jenkins.iacgenie.com` can reach Jenkins' login page. Cloudflare Access adds a mandatory identity check at Cloudflare's edge before any request reaches Jenkins.

### Configuration Steps

These steps are performed in the **Cloudflare Zero Trust Dashboard** (https://one.dash.cloudflare.com), not in code:

1. **Navigate** to Access → Applications → Add an application
2. **Select** "Add a SaaS or custom application" → "Custom App"
3. **Application name**: `IacGenie Jenkins`
4. **Domain**: `jenkins.iacgenie.com` (must match the existing cloudflared ingress rule)
5. **Add a policy**:
   - Name: `Require Jenkins Users`
   - Include: People using the IacGenie account at Cloudflare (or configure specific identity providers)
   - Decision: Allow
6. **Choose an Identity Provider**:
   - **GitHub** (recommended for dev teams): Users log in with their GitHub account
   - **Keycloak OIDC**: Uses your existing Keycloak deployment (requires OIDC app setup in Keycloak first)
   - **Google**: Google Workspace accounts
7. **Enable MFA**: Toggle on "Require multi-factor authentication"
8. **Save** the application

### After Configuration

- All requests to `https://jenkins.iacgenie.com` will first hit Cloudflare Access
- Users see a login page backed by their chosen identity provider
- After successful auth, Cloudflare issues a session cookie and forwards the request to the cloudflared tunnel
- No changes needed to Jenkins itself — the login page remains functional for local Jenkins-level auth

### Identity Provider Setup

**GitHub (simplest):**
- Go to GitHub → Settings → Developer settings → OAuth apps → New OAuth app
- Application callback URL: `https://jenkins.iacgenie.com/oauth/redirect/signin-with-github`
- Copy Client ID and Client Secret into Cloudflare Access → Identity Providers → GitHub

**Keycloak OIDC (existing infrastructure):**
- In Keycloak admin console, create a new client of type "OpenID Connect"
- Redirect URI: `https://jenkins.iacgenie.com/oauth/redirect/signin-with-keycloak`
- Copy Client ID and Client Secret into Cloudflare Access → Identity Providers → Generic OIDC
