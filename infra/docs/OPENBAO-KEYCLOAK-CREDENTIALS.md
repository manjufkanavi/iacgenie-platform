# OpenBao & Keycloak — Credentials, Unseal, and Password Storage

**Platform:** iacgenie-platform
**VM:** `192.168.0.118` (user `mkanavi`)
**Scope:** OpenBao secrets vault + Keycloak IAM — where credentials live, how to unseal the vault, and how passwords are stored.

---

## Table of Contents
1. [Quick Reference](#quick-reference)
2. [OpenBao Unseal Procedure](#openbao-unseal-procedure)
3. [OpenBao Where Secrets Live](#openbao-where-secrets-live)
4. [Keycloak Password Storage](#keycloak-password-storage)
5. [Ansible Source-of-Truth Mapping](#ansible-source-of-truth-mapping)
6. [Troubleshooting](#troubleshooting)

---

## Quick Reference

| Item | Location / Value |
|------|------------------|
| OpenBao container | `iacgenie_openbao` (port 8200) |
| OpenBao unseal keys + root token | `/home/mkanavi/docker/iacgenie/openbao_raft/init_keys.json` |
| OpenBao unseal threshold | **2 of 3** (Shamir) |
| OpenBao env file | `/home/mkanavi/docker/iacgenie/.env.openbao` |
| OpenBao KV secret root (app view) | `iacgenie/kv/` |
| Keycloak admin password file (container) | `/run/secrets/keycloak_admin_password` |
| Keycloak DB password file (container) | `/run/secrets/keycloak_db_password` |
| Keycloak admin password source (OpenBao) | `iacgenie/kv/keycloak/admin_password` |
| Keycloak container | `iacgenie_keycloak` (host port 8083) |

---

## OpenBao Unseal Procedure

OpenBao uses **Shamir secret sharing** with a threshold of **2 out of 3 keys**.
The vault starts *sealed* on boot and must be unsealed before it serves any request.
There is **no auto-unseal** configured on this host (see `OPENBAO_AUTO_UNSEAL` in `.env.openbao`).

### Where the unseal keys come from

The unseal keys and root token are generated once by Ansible (`openbao-init.yml`), which runs `operator init -key-shares=3 -key-threshold=2`. The output is saved to:

```
/home/mkanavi/docker/iacgenie/openbao_raft/init_keys.json
```

Structure (values are base64 / opaque — do **not** edit):

```json
{
  "unseal_keys_b64": ["<key1>", "<key2>", "<key3>"],
  "root_token": "s.xxxxx",
  "generated_at": "<date>",
  "unseal_threshold": 2
}
```

> The same `root_token` is also present in `.env.openbao` as `OPENBAO_ROOT_TOKEN`.

### Check seal status

```bash
ssh mkanavi@192.168.0.118
docker exec iacgenie_openbao bao status            # shows Seal: true/false
# or via REST (plain HTTP on 127.0.0.1:8200):
docker exec iacgenie_openbao sh -c \
  'wget -qO- http://127.0.0.1:8200/v1/sys/seal-status'
```

### Unseal (manual, one-time or after reboot)

You need **at least 2 of the 3 unseal keys** plus the root token.
Read them from `init_keys.json`:

```bash
cat /home/mkanavi/docker/iacgenie/openbao_raft/init_keys.json
```

Then unseal using 2 keys (any two of the three):

```bash
# From inside an interactive shell on the VM:
docker exec -it iacgenie_openbao bash

# Inside the container (bash is available):
export ROOT_TOKEN="<from init_keys.json>"
KEY1="<unseal key 1 or 2>"
KEY2="<unseal key 2 (a different one)>"

# HTTP (default listener is plaintext on 127.0.0.1:8200)
printf 'POST /v1/sys/unseal HTTP/1.0\r\nHost: localhost\r\nX-Vault-Token: %s\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{"key":"%s"}' "$ROOT_TOKEN" "$KEY1" | \
  { exec 3<>/dev/tcp/127.0.0.1/8200; tee >&3; } | head -c 400
# repeat with KEY2, then:
wget -qO- http://127.0.0.1:8200/v1/sys/seal-status
```

Or using the CLI directly (simplest):

```bash
docker exec iacgenie_openbao bao operator unseal --address=http://127.0.0.1:8200 "$KEY1"
docker exec iacgenie_openbao bao operator unseal --address=http://127.0.0.1:8200 "$KEY2"
docker exec iacgenie_openbao bao status   # Seal: false
```

> **Note:** The Ansible `unseal.yml` task targets `https://127.0.0.1:8200`, but this host's OpenBao listens on **plain HTTP** at `127.0.0.1:8200`. That mismatch is why the automated unseal silently fails here — use the manual/CLI method above, or fix `unseal.yml` to match HTTP.

---

## OpenBao Where Secrets Live

Credentials are stored in **two layers**:

### 1. Vault bootstrap material (host filesystem)
- File: `/home/mkanavi/docker/iacgenie/openbao_raft/init_keys.json`
- Contains: 3 unseal keys + root token (the "master key" material)
- Owner: `mkanavi`, mode `0750` — treat as highly sensitive
- Back this file up offline. Losing it + losing the running vault = unrecoverable unless auto-unseal is set up.

### 2. KV v2 secret engines (the app-facing secrets)
After bootstrap, Ansible seeds all service credentials into KV-v2 engines:

```
iacgenie/kv/      # iacgenie app secrets (postgres, redis, minio, keycloak, ...)
lightserp/kv/     # LightSerp secrets
terraform/kv/     # Terraform CI/CD credentials
```

Inspect from the VM:

```bash
docker exec iacgenie_openbao bao kv list  iacgenie/kv/
docker exec iacgenie_openbao bao kv get  iacgenie/kv/keycloak/
docker exec iacgenie_openbao bao kv list  lightserp/kv/
```

The Keycloak admin password is stored here at:
`iacgenie/kv/keycloak/admin_password`

### 3. Environment file (convenience copy)
`/home/mkanavi/docker/iacgenie/.env.openbao` holds:
- `OPENBAO_ROOT_TOKEN` (same root token)
- `OPENBAO_ADDR` = `http://127.0.0.1:8200`
- `OPENBAO_DATA_DIR`, `OPENBAO_STORAGE_TYPE=raft`
- `OPENBAO_AUTO_UNSEAL` (currently **not** functional — see note above)

---

## Keycloak Password Storage

Keycloak 26.x uses **Docker secrets** (not inline env vars) for the admin and DB passwords.
This is per the Antares security audit (2026-08-17) — plaintext credential exposure is avoided.

### Files referenced in `.env.keycloak`
```ini
KC_BOOTSTRAP_ADMIN_PASSWORD_FILE=/run/secrets/keycloak_admin_password
KC_DB_PASSWORD_FILE=              /run/secrets/keycloak_db_password
```

### What is actually mounted (inside the container)
| Secret | Container path | Source value in OpenBao |
|--------|----------------|-------------------------|
| Admin password | `/run/secrets/keycloak_admin_password` | `iacgenie/kv/keycloak/admin_password` |
| DB password    | `/run/secrets/keycloak_db_password`    | `iacgenie/kv/keycloak/...db password` |

These `/run/secrets/*` files are bind-mounted by Docker Compose from host secret
files that Ansible renders. To view the mounted files (read-only, do not print secrets in shared channels):

```bash
docker exec iacgenie_keycloak ls -la /run/secrets/
wc -c /run/secrets/keycloak_admin_password      # confirm non-empty, do not cat
```

### Rotating the Keycloak admin password
```bash
# 1. New password (strong, no special shell chars to avoid escaping issues)
NEW_PASS=$(python3 -c "import secrets; print(''.join(secrets.choice('abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(32)))")

# 2. Store it back into OpenBao
docker exec iacgenie_openbao bao kv put iacgenie/kv/keycloak/admin_password="$NEW_PASS"

# 3. Refresh the mounted secret + recreate Keycloak
docker compose -f /home/mkanavi/docker/iacgenie/docker-compose.yml up -d --force-recreate keycloak
```

---

## Ansible Source-of-Truth Mapping

All of the above is generated from these Ansible files (the true source):

| Secret | Ansible variable / file |
|--------|-------------------------|
| Keycloak admin password | `roles/keycloak/defaults/main.yml` → `keycloak_pass` (default `CHANGE_ME_IN_VAULT`) |
| Keycloak DB password    | same role, `keycloak_db_password` |
| OpenBao root token      | `roles/openbao/defaults/main.yml` → `openbao_root_token` (default `CHANGE_ME_SEE_GITHUB_SECRETS`) |
| OpenBao unseal keys     | `playbooks/openbao-init.yml` → written to host `init_keys.json` on init |
| Compose healthchecks    | `roles/docker-compose-generator/templates/docker-compose.yml.j2` |

> **Rule:** Never hand-edit deployed files (e.g. `docker-compose.yml`, `.env.*`).
> Edit the Ansible template, re-run the playbook (`ansible-playbook site.yml`), then redeploy.
> The deployed files persist but will be overwritten on the next Ansible run.

---

## Troubleshooting

| Symptom | Cause / Fix |
|---------|-------------|
| `docker logs iacgenie_openbao` shows nothing / API 503 | Vault is **sealed**. Unseal with 2 of 3 keys (see procedure). |
| Automated unseal fails but manual works | `unseal.yml` uses HTTPS; this host listens on plain HTTP. Fix the URL or use CLI unseal. |
| `docker exec iacgenie_keycloak` healthcheck "unhealthy" but service works | Health check was using `wget`, which is absent in the Keycloak image. Fixed to a bash `/dev/tcp/127.0.0.1:8080` probe (see Ansible template). |
| Lost `init_keys.json` and vault is sealed | Re-run `openbao-init.yml` **only if** storage was wiped; otherwise the current vault's keys are unrecoverable. Prevent by enabling auto-unseal or backing up `init_keys.json` offline. |
| Keycloak "somethingWentWrongDescription" | H2/PostgreSQL driver conflict. Ensure `--db=postgres` and clear `/home/mkanavi/docker/iacgenie/data/keycloak/h2/`. |

---

## Verification (post-fix status)
- OpenBao: `sealed:false`, Docker health = healthy.
- Keycloak: Docker health = healthy (healthcheck uses bash TCP probe, port 8080).
