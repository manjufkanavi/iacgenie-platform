#!/usr/bin/env bash
# ==============================================================================
# SSH Wrapper Script for VM (192.168.0.118)
# Provides resilient SSH connectivity with retry logic and password fallback.
# ==============================================================================
set -euo pipefail

VM_ALIAS="newvm"
MAX_RETRIES=3
BACKOFF_BASE=2   # seconds

usage() {
    cat >&2 <<EOF
Usage: $(basename "$0") [ssh-args...]

Connect to the VM (192.168.0.118) with automatic retry and password fallback.

    $(basename "$0")              Interactive SSH shell
    $(basename "$0") uptime       Run command on remote VM
    $(basename "$0") --help       Show this help

Environment:
    SSH_PASS  Override the default password (Murdock@12345).
EOF
    exit 0
}

# Parse --help before passing args to ssh
for arg in "$@"; do
    if [[ "$arg" == "--help" || "$arg" == "-h" ]]; then
        usage
    fi
done

echo "[ssh-vm] Connecting to ${VM_ALIAS} ..."

for attempt in $(seq 1 "$MAX_RETRIES"); do
    local_exit=0
    ssh "$VM_ALIAS" "$@" && local_exit=0 || local_exit=$?

    if [[ $local_exit -eq 0 ]]; then
        echo "[ssh-vm] connected"
        exit 0
    fi

    if [[ $attempt -lt $MAX_RETRIES ]]; then
        echo "[ssh-vm] attempt ${attempt}/${MAX_RETRIES} failed, retrying in ${BACKOFF_BASE}s ..." >&2
        sleep "$BACKOFF_BASE"
        BACKOFF_BASE=$(( BACKOFF_BASE * 2 ))
    fi
done

# ---- Password fallback ----
echo "[ssh-vm] All key-based attempts failed. Falling back to password auth ..." >&2

FALLBACK_PASS="${SSH_PASS:-Murdock@12345}"

if sshpass -p "$FALLBACK_PASS" ssh -o PreferredAuthentications=password \
     -o PubkeyAuthentication=no \
     "$VM_ALIAS" "$@"; then
    echo "[ssh-vm] connected via password auth" >&2
    exit 0
fi

echo "[ssh-vm] Connection to ${VM_ALIAS} failed after all retries and password fallback" >&2
exit 1
