# Jenkins CI/CD — Credentials & Configuration Reference

> **DO NOT commit this file to git.**
> Created: 2026-06-13
> Environment: elementary OS 8 VM (192.168.0.118)

## Admin Account

| Field | Value |
|-------|-------|
| URL | `https://jenkins.iacgenie.com` |
| Username | `admin` |
| Password | `91Y53bvH8VcSlOtPAngfgE1LVdD95pjwguoLU9SWpfM` |
| Auth Strategy | `ProjectMatrix` (admin only) |
| Security Realm | Jenkins' own user database (local) |
| Signup | Disabled |
| Remember Me | Enabled |

## Authorization

| User | Permissions |
|------|-------------|
| `admin` | Administer, Create, Configure, Workspace, Delete, Upgrade, RunAs |

**NOTE**: The `projectMatrix` authorization is defined in JCasC but is currently overridden by Jenkins' default `FullControlOnceLoggedIn` from `config.xml`. To fix, run:
```bash
ssh newvm "sudo rm ~/docker/iacgenie/jenkins_data/config.xml && docker compose -f docker-compose-newvm.yml restart jenkins"
```
After removal, JCasC will fully control both security realm and authorization.

## Pre-Configured Credentials (via JCasC)

| ID | Type | Source | Description |
|----|------|--------|-------------|
| `github-token` | Secret Text | JCasC (`${GITHUB_TOKEN:-}`) | GitHub Personal Access Token for SCM access |

## Credentials to Add Manually via Jenkins UI

### GitHub SSH Key (`github-ssh`)

1. Navigate to **Manage Jenkins** → **Credentials** → **System** → **Global Credentials**
2. Click **Add Credentials**
3. **Kind**: SSH Username with private key
4. **ID**: `github-ssh` (must match Jenkinsfiles)
5. **Username**: `git`
6. **Private Key**: Paste your SSH private key content (e.g., `~/.ssh/id_ed25519`)
7. **Description**: `GitHub SSH Key — terragenius repo access`
8. Click **OK**

### GitHub API Token (`github-token` via UI)

1. Navigate to **Manage Jenkins** → **Credentials** → **System** → **Global Credentials**
2. Click **Add Credentials**
3. **Kind**: Secret text
4. **ID**: `github-token`
5. **Secret**: Your GitHub Personal Access Token (classic, with `repo` scope)
6. **Description**: `GitHub PAT for API access`

To generate a GitHub PAT: https://github.com/settings/tokens → **New (classic)** → Select `repo` scope.

## Jenkins Configuration

### JCasC Config

Location: `iacgenie/docker/jenkins/jenkins.config.yml`

```yaml
jenkins:
  systemMessage: "IacGenie CI/CD Platform"
  numExecutors: 2
  mode: NORMAL
  globalSecurityConfig:
    authorizationStrategy:
      projectMatrix:
        entries:
          - user: admin
            permissions: [Administer, Create, Configure, Workspace, Delete, Upgrade, RunAs]
    securityRealm:
      local:
        allowsSignup: false
        users:
          - id: "admin"
            passwordHash: "#jbcrypt:$2b$12$pNWD1sObt1gzqzV8DZIpPOTDj7v4xEZa/gy73czB95RV0rXflxtla"
  disableRememberMe: false
  mailerConfig:
    smtpHost: "smtp.smtp2go.com"
    smtpPort: 587
    smtpPassword: "${SMTP2GO_API_KEY:-}"
    from: "jenkins@iacgenie.com"
    useSsl: true
    useTls: true

credentials:
  system:
    domainCredentials:
      - credentials:
          - string:
              scope: SYSTEM
              id: github-token
              secret: "${GITHUB_TOKEN:-}"
              description: "GitHub Personal Access Token (SCM)"
```

### Password Management

To generate a new admin password hash:
```bash
python3 iacgenie/docker/jenkins/generate_hash.py "new-password"
```

Update the `passwordHash` in `jenkins.config.yml`, then:
```bash
# On VM
cd ~/docker/iacgenie
docker compose -f docker-compose-newvm.yml build jenkins
docker compose -f docker-compose-newvm.yml up -d jenkins
sleep 120
```

## Data Persistence

All Jenkins data is in `/home/mkanavi/docker/iacgenie/jenkins_data/` (bind-mounted from container).

### Encryption Keys (BACK UP SEPARATELY)

These files decrypt stored credentials. If lost, all credentials become unrecoverable:

```
/home/mkanavi/docker/iacgenie/jenkins_data/secrets/master.key
/home/mkanavi/docker/iacgenie/jenkins_data/secrets/secret.key
```

### Backup

```bash
# Backup all Jenkins data
tar czf /tmp/jenkins-backup-$(date +%Y%m%d).tar.gz -C /home/mkanavi/docker/iacgenie jenkins_data/

# Backup encryption keys separately
tar czf /tmp/jenkins-encryption-keys-$(date +%Y%m%d).tar.gz -C /home/mkanavi/docker/iacgenie/jenkins_data secrets/
```

## Pipeline Jobs

| Job | Description |
|-----|-------------|
| `terragenius-full-cicd` | Full CI/CD: lint + build + smoke + unit tests + Playwright E2E |
| `terragenius-full-sanity` | Lint/build + DB/Redis smoke tests |
| `terragenius-full-unit-tests` | All lint/build + backend unit + frontend vitest |
| `terragenius-backend-lint-build` | Ruff check, Mypy type check, pip-audit, backend tests |
| `terragenius-frontend-lint-build` | TypeScript check, Vitest, Vite build |

## GitHub Webhook

Configure in GitHub repo → Settings → Webhooks:

| Setting | Value |
|---------|-------|
| Payload URL | `https://jenkins.iacgenie.com/github-webhook/` |
| Content type | `application/json` |
| Events | `push`, `Pull Request` |

## Cloudflare Access (Optional Upgrade)

Currently Jenkins uses built-in local auth. For MFA and external identity providers, configure Cloudflare Access:

1. Cloudflare Zero Trust → Access → Applications → Add an application
2. Application name: `IacGenie Jenkins`, Domain: `jenkins.iacgenie.com`
3. Policy: Require authentication via chosen identity provider
4. Supported IdP: GitHub (simplest), Keycloak OIDC, Google, Okta

See `services-secrets.md` for detailed Cloudflare Access configuration steps.
