# IaCGenie Infrastructure Admin Guide

This guide is intended for Platform Administrators who are responsible for maintaining, troubleshooting, and securing the IaCGenie infrastructure.

---

## 🔐 Secrets Management (OpenBao)

OpenBao (a HashiCorp Vault fork) is the central authority for all secrets in the platform.

### Unsealing OpenBao

OpenBao uses Shamir's Secret Sharing. It is initialized with 5 keys and requires 3 to unseal.
If the VM reboots or the OpenBao container restarts, it will start in a **sealed** state.

1. Obtain the unseal keys (stored in `init_keys.json` during initial setup, or from your secure password manager).
2. Connect to the VM and unseal:
   ```bash
   docker exec -it iacgenie-openbao bao operator unseal <key-1>
   docker exec -it iacgenie-openbao bao operator unseal <key-2>
   docker exec -it iacgenie-openbao bao operator unseal <key-3>
   ```

### Managing Policies and RBAC

By default, services operate under **read-only** policies (e.g., `iacgenie-service`, `lightserp-service`). Only the `admin` policy has write access.

To update policies:
1. Edit the Ansible templates in `infra/ansible/roles/openbao/templates/policies/`.
2. Run the OpenBao Ansible role to apply changes:
   ```bash
   ansible-playbook -i inventory/hosts.ini playbooks/services.yml --tags openbao
   ```

### Managing Bootstrap Secrets with `git-secret`

The Ansible Vault password and OpenBao unseal keys are GPG-encrypted in the repository using `git-secret`.

- **To encrypt new files:**
  ```bash
  git secret add <path-to-file>
  git secret hide
  git commit -m "chore: add new encrypted secret"
  ```
- **To decrypt (requires authorized GPG key):**
  ```bash
  git secret reveal
  ```

For more details, see the [OpenBao Secrets Skill](../../.agents/skills/openbao-secrets/SKILL.md).

---

## 💾 Backups & Restore

### Automated Backups
Currently, backups should be performed daily. Focus areas:
1. **PostgreSQL Database**: Contains all application state, Keycloak users, and Gitea metadata.
2. **OpenBao Raft Storage**: Located at `~/docker/iacgenie/data/openbao_raft/`.
3. **Gitea Repositories**: Located at `~/docker/iacgenie/data/gitea/git/`.

*(Note: See [BACKUP.md](BACKUP.md) for detailed snapshot scripts once fully implemented).*

---

## 🔄 Service Lifecycle & Drift Detection

### Checking Service Health
To monitor the health of the Docker Compose stack on the VM:
```bash
cd ~/iacgenie-platform/infra/docker-compose
docker compose ps
docker compose logs --tail=100 -f <service_name>
```

### Applying Infrastructure Updates
If changes are made to Ansible roles (e.g., adding a new environment variable, updating an Nginx config), apply them via Ansible:
```bash
ansible-playbook -i inventory/hosts.ini playbooks/services.yml
```
Ansible will template the changes, push them to the VM, and automatically recreate the affected Docker containers to apply the new state.

### Drift Detection
To check if the live VM has drifted from the Ansible definitions without applying changes:
```bash
ansible-playbook -i inventory/hosts.ini playbooks/services.yml --check --diff
```

---

## 🛡️ Security Posture

- **No Public Inbound Ports**: The VM firewall should block all inbound traffic except SSH (Port 22, ideally restricted to VPN IPs).
- **Cloudflare Tunnels**: All web traffic (`https://api.iacgenie.com`, `https://vault.iacgenie.com`) enters via Cloudflare Tunnels (the `cloudflared` container).
- **Zero Trust**: Services authenticate to OpenBao using short-lived tokens or OIDC. Databases require strong, generated passwords.

If a compromise is suspected:
1. Shut down the Cloudflare tunnel container (`docker compose stop cloudflared`).
2. Rotate OpenBao unseal keys and the root token.
3. Rotate all database passwords via OpenBao and restart the stack.
