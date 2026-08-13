# SSH & Fail2Ban Hardening Guide

## Problem: Self-Lockout via Fail2Ban

**Date:** 2026-08-06  
**Affected:** VM `192.168.0.118` (vm.iacgenie.com)  
**Root Cause:** `fail2ban` banning the admin Mac IP after repeated SSH auth failures

### What Happened

The Mac (using multiple SSH keys in the SSH agent) was connecting to the VM, but fail2ban was counting the failures as brute-force attempts and banning the Mac's IP. This created a self-reinforcing lockout cycle:

1. Mac has multiple keys in SSH agent
2. SSH client tries keys one by one → each failure counts as "failed auth"
3. After `maxretry` (5) failures in `findtime` (300s) window → **IP gets banned**
4. Mac gets kicked off → can't re-deploy the fix

### Fail2Ban Configuration

**File:** `infra/ansible/roles/common/templates/jail.local.j2`

The jail.local uses a Jinja2 template to build the `ignoreip` list:

```ini
[DEFAULT]
ignoreip = 127.0.0.1/8 ::1 {% for ip in fail2ban_admin_ips | default([]) %}{{ ip }} {% endfor %}
bantime   = {{ fail2ban_bantime | default(3600) }}s
findtime  = {{ fail2ban_findtime | default(300) }}s
maxretry  = {{ fail2ban_maxretry | default(5) }}
```

**Admin IPs (from `defaults/main.yml`):**
```yaml
fail2ban_admin_ips:
  - "192.168.0.101"   # Mac dev machine (mkanavi)
```

### Current VM State (2026-08-06)

| Setting | Value |
|---------|-------|
| fail2ban status | ✅ Running |
| sshd jail | ✅ Active (0 banned) |
| ignoreip | `127.0.0.1/8 ::1 192.168.0.101` |
| bantime | 3600s (1 hour) |
| findtime | 300s (5 min) |
| maxretry | 5 |
| recidive jail | ✅ Enabled (7-day ban) |

### SSH Hardening Settings

**File:** `infra/ansible/roles/common/tasks/hardening.yml`

| Setting | Value |
|---------|-------|
| Port | 22 |
| PermitRootLogin | no |
| PasswordAuthentication | no |
| PubkeyAuthentication | yes |
| AuthenticationMethods | publickey |
| MaxAuthTries | 3 |
| LoginGraceTime | 60s |
| ClientAliveInterval | 60s |
| ClientAliveCountMax | 3 |
| UseDNS | no |
| X11Forwarding | no |

**SSHD systemd auto-restart:**
```ini
# /etc/systemd/system/ssh.service.d/restart-on-failure.conf
[Service]
Restart=always
RestartSec=5
```

## SSH Agent Management

### Current State

```
$ ssh-add -l
256 SHA256:Bw+F0A/tUQlH3LJo0TdOeMAM0b9IATzfOZPzDbnV3jo newvm (ED25519)
```

Only `newvm` key is loaded — **clean**.

### SSH Keys on Disk

| Key | Purpose |
|-----|---------|
| `newvm_key` | VM access (192.168.0.118) |
| `gitea_iacgenie_key` | Gitea SSH (proxy through VM) |
| `raspberry_key` | Raspberry Pi access (192.168.0.101) |

### Preventing Key Auto-Load

The `.ssh/config` has `AddKeysToAgent yes` on both `rpi` and `newvm` host blocks. This means keys get auto-loaded when connecting. If you want to prevent this:

```bash
# Remove all keys from agent
ssh-add -D

# Remove specific key
ssh-add -d ~/.ssh/raspberry_key
ssh-add -d ~/.ssh/gitea_iacgenie_key
```

To permanently prevent auto-loading, change `AddKeysToAgent yes` to `AddKeysToAgent no` in `~/.ssh/config` for the relevant host blocks.

## Emergency Recovery

### If Locked Out

**Option 1: Re-deploy jail.local via scp**
```bash
scp /path/to/correct/jail.local mkanavi@192.168.0.118:/tmp/jail.local
ssh mkanavi@192.168.0.118 "sudo cp /tmp/jail.local /etc/fail2ban/jail.local && sudo systemctl reload fail2ban"
```

**Option 2: Use the SSH health playbook**
```bash
cd ~/iacgenie-platform/infra/ansible
ansible-playbook -i inventory/hosts.ini playbooks/ssh-health.yml --tags unban
```

**Option 3: Unban IP directly from VM**
```bash
sudo fail2ban-client set sshd unbanip 2406:7400:11d:585b:d9e8:ea21:d75:fd0d
```

**Option 4: Disable fail2ban temporarily**
```bash
sudo systemctl stop fail2ban
sudo systemctl disable fail2ban
```

## Pre-Deploy Checklist

Before running the bootstrap playbook to avoid lockout:

1. **Verify SSH key auth works** — `ssh -o ConnectTimeout=10 mkanavi@192.168.0.118 "echo ok"`
2. **Verify SSH agent has the right key** — `ssh-add -l` (should show `newvm`)
3. **Keep a backup terminal session** open as a safety net
4. **Deploy jail.local BEFORE hardening** — this ensures ignoreip is set before any SSH changes
5. **Set `ssh_apply_changes_reboot: false`** in defaults — prevents auto-restart of sshd

## Key Files Reference

| File | Purpose |
|------|---------|
| `infra/ansible/roles/common/defaults/main.yml` | Default vars including `fail2ban_admin_ips` |
| `infra/ansible/roles/common/templates/jail.local.j2` | fail2ban jail.local template |
| `infra/ansible/roles/common/tasks/hardening.yml` | SSH hardening + fail2ban config tasks |
| `infra/ansible/roles/common/handlers/main.yml` | Service restart handlers |
| `infra/ansible/playbooks/ssh-health.yml` | SSH health check + auto-remediation |
| `~/.ssh/config` | SSH client config with AddKeysToAgent |
| `~/.bash_profile` | Environment variables (no SSH key loading) |

## Files Modified in This Fix (2026-08-06)

| File | Change |
|------|--------|
| `infra/ansible/roles/common/templates/jail.local.j2` | Already had `ignoreip` (from commit `4fe44a7`) |
| `infra/ansible/roles/common/defaults/main.yml` | Verified `fail2ban_admin_ips` includes `192.168.0.101` |
| VM: `/etc/fail2ban/jail.local` | **Deployed** with correct `ignoreip` line |

## Notes

- `.bash_profile` does NOT load any SSH keys — only environment variables
- `.bashrc` has no SSH key loading (only safehouse agent tool)
- The `~/.ssh/agent` directory contains only a socket file (no persistent keys)
- SSH keys on disk (`gitea_iacgenie_key`, `raspberry_key`) are NOT in the agent — they're loaded on demand by `.ssh/config`
