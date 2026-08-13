#!/bin/bash
# ssh-recover.sh — Emergency SSH recovery script for 192.168.0.118 (vm.iacgenie.com)
#
# Run this from your Mac when SSH to the VM is failing.
# It covers all known failure modes and attempts auto-recovery.
#
# Usage:
#   ./infra/scripts/ssh-recover.sh           # full recovery attempt
#   ./infra/scripts/ssh-recover.sh --check   # diagnose only, no changes
#
# Author: Managed by iacgenie-platform IaC

set -euo pipefail

VM_HOST="192.168.0.118"
VM_USER="mkanavi"
VM_KEY="${HOME}/.ssh/newvm_key"
VM_ALIAS="newvm"
ANSIBLE_CP="${HOME}/.ansible/cp"

RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[1;33m'
BLU='\033[0;34m'
NC='\033[0m'

CHECK_ONLY="${1:-}"

log()  { echo -e "${BLU}[INFO]${NC}  $*"; }
ok()   { echo -e "${GRN}[OK]${NC}    $*"; }
warn() { echo -e "${YLW}[WARN]${NC}  $*"; }
err()  { echo -e "${RED}[ERR]${NC}   $*"; }
hdr()  { echo -e "\n${BLU}══════════════════════════════════════════════${NC}"; echo -e "${BLU}  $*${NC}"; echo -e "${BLU}══════════════════════════════════════════════${NC}"; }

# ─── Step 1: Ping check ──────────────────────────────────────────────────────
hdr "Step 1 — Network reachability"
if ping -c 2 -W 1000 "${VM_HOST}" &>/dev/null; then
    ok "VM is reachable (ping OK)"
else
    err "VM is NOT reachable via ping. Check network/power."
    exit 1
fi

# ─── Step 2: Port 22 check ───────────────────────────────────────────────────
hdr "Step 2 — Port 22 status"
if nc -zw3 "${VM_HOST}" 22 2>/dev/null; then
    ok "Port 22 is OPEN — sshd is running"
else
    err "Port 22 is CLOSED or REFUSED"
    echo ""
    warn "Possible causes:"
    echo "  A) fail2ban banned your IP (${BLU}$(ifconfig en1 | grep 'inet ' | awk '{print $2}')${NC})"
    echo "  B) sshd crashed (OOM killer, config error)"
    echo "  C) UFW is blocking port 22"
    echo ""
    warn "Recommended: access VM via physical console/IPMI and run:"
    echo "  sudo systemctl start sshd"
    echo "  sudo fail2ban-client set sshd unbanip <your-ip>"
    echo ""
    if [[ "${CHECK_ONLY}" == "--check" ]]; then
        exit 1
    fi
fi

# ─── Step 3: Load SSH key into agent ─────────────────────────────────────────
hdr "Step 3 — SSH agent key"
if ssh-add -l 2>/dev/null | grep -q "newvm\|${VM_KEY##*/}"; then
    ok "newvm_key already loaded in SSH agent"
else
    warn "newvm_key NOT in SSH agent — adding now..."
    if [[ "${CHECK_ONLY}" != "--check" ]]; then
        ssh-add --apple-use-keychain "${VM_KEY}" 2>/dev/null \
            || ssh-add "${VM_KEY}"
        ok "newvm_key added to agent"
    fi
fi

# ─── Step 4: Clear stale ControlPersist sockets ──────────────────────────────
hdr "Step 4 — ControlPersist socket cleanup"
STALE=$(ls "${ANSIBLE_CP}"/ 2>/dev/null | wc -l | tr -d ' ')
if [[ "${STALE}" -gt 0 ]]; then
    warn "Found ${STALE} stale Ansible ControlPersist socket(s) — removing..."
    if [[ "${CHECK_ONLY}" != "--check" ]]; then
        rm -f "${ANSIBLE_CP}"/*
        ok "Stale sockets cleared"
    fi
else
    ok "No stale ControlPersist sockets"
fi

# ─── Step 5: Test SSH connection ─────────────────────────────────────────────
hdr "Step 5 — SSH connection test"
if [[ "${CHECK_ONLY}" == "--check" ]]; then
    log "Check-only mode — skipping live SSH test"
    exit 0
fi

SSH_OPTS="-o ConnectTimeout=10 -o BatchMode=yes -o StrictHostKeyChecking=no"
SSH_RESULT=$(ssh ${SSH_OPTS} -i "${VM_KEY}" "${VM_USER}@${VM_HOST}" \
    "echo SSH_OK; uptime; systemctl is-active sshd; fail2ban-client status sshd 2>/dev/null || echo 'fail2ban not available'" 2>&1) \
    && SSH_EXIT=0 || SSH_EXIT=$?

if [[ "${SSH_EXIT}" -eq 0 ]]; then
    ok "SSH connected successfully!"
    echo ""
    echo "${SSH_RESULT}"
else
    err "SSH FAILED (exit ${SSH_EXIT})"
    echo "${SSH_RESULT}"
    echo ""
    warn "Manual steps required:"
    echo "  1. Access VM via physical console"
    echo "  2. sudo systemctl status sshd"
    echo "  3. sudo fail2ban-client set sshd unbanip \$(your-ip)"
    echo "  4. sudo systemctl start sshd"
    exit 1
fi

hdr "Recovery Complete"
ok "VM ${VM_HOST} is healthy and SSH is working"
echo ""
log "Run Ansible health playbook to apply structural fixes:"
echo "  cd infra/ansible"
echo "  ansible-playbook playbooks/ssh-health.yml"
