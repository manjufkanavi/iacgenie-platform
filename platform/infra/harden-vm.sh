#!/bin/bash
# =============================================================================
# VM Hardening Script for IacGenie (vm.iacgenie.com)
# =============================================================================
# Apply this script on the VM to harden the host-level configuration.
#
# Run as: sudo bash harden-vm.sh
#
# Changes applied:
#   - File permissions (.env, auth.json -> 600)
#   - SSH hardening (disable X11, root login, password auth)
#   - Kernel hardening (disable ip_forward, etc.)
#   - Cleanup stale containers
#   - Jenkins data ownership fix
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err() { echo -e "${RED}[ERR]${NC} $1"; }

echo "============================================"
echo "  IacGenie VM Hardening Script"
echo "  Target: $(hostname)"
echo "  Date: $(date)"
echo "============================================"
echo ""

# Must run as root
if [ "$EUID" -ne 0 ]; then
  echo "This script must be run as root (use sudo)"
  exit 1
fi

DOCKER_USER="mkanavi"
DOCKER_BASE="/home/${DOCKER_USER}/docker/iacgenie"

# =============================================================================
# 1. Fix sensitive file permissions
# =============================================================================
echo "--- 1. Fixing sensitive file permissions ---"

chmod 600 "${DOCKER_BASE}/.env" 2>/dev/null && log_ok ".env permissions fixed to 600" || log_warn ".env not found"
chmod 600 "${DOCKER_BASE}/cloudflared/auth.json" 2>/dev/null && log_ok "cloudflared/auth.json permissions fixed to 600" || log_warn "auth.json not found"
chmod 600 "${DOCKER_BASE}/docker/cloudflared/auth.json" 2>/dev/null && log_ok "docker/cloudflared/auth.json permissions fixed to 600" || log_warn "docker/cloudflared/auth.json not found"

# =============================================================================
# 2. SSH Hardening
# =============================================================================
echo ""
echo "--- 2. Hardening SSH configuration ---"

mkdir -p /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/hardened.conf << 'SSH_EOF'
# IacGenie SSH Hardening — applied by harden-vm.sh
# Disable root login, password auth, and X11 forwarding
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
PermitEmptyPasswords no
MaxAuthTries 3
X11Forwarding no
AllowUsers mkanavi
Protocol 2
SSH_EOF

chmod 644 /etc/ssh/sshd_config.d/hardened.conf
log_ok "SSH hardening config written to /etc/ssh/sshd_config.d/hardened.conf"

# Reload SSH to apply changes (non-destructive — won't kill current sessions)
systemctl reload ssh 2>/dev/null && log_ok "SSH configuration reloaded" || log_warn "SSH reload failed (may need full restart)"

# =============================================================================
# 3. Kernel Hardening
# =============================================================================
echo ""
echo "--- 3. Hardening kernel parameters ---"

cat > /etc/sysctl.d/99-hardening.conf << 'SYSCTL_EOF'
# IacGenie Kernel Hardening — applied by harden-vm.sh

# Disable IP forwarding (VM is not a router)
net.ipv4.ip_forward = 0

# TCP SYN cookies (anti-SYN flood)
net.ipv4.tcp_syncookies = 1

# Disable ICMP redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.accept_redirects = 0

# Enable kernel pointer protection
kernel.kptr_restrict = 2

# Disable unprivileged BPF
kernel.unprivileged_bpf_disabled = 1

# Hardlink/symlink protection
fs.protected_hardlinks = 1
fs.protected_symlinks = 1
SYSCTL_EOF

chmod 644 /etc/sysctl.d/99-hardening.conf
sysctl -p /etc/sysctl.d/99-hardening.conf 2>/dev/null && log_ok "Kernel parameters applied" || log_warn "sysctl application failed"

# =============================================================================
# 4. Cleanup stale Docker containers
# =============================================================================
echo ""
echo "--- 4. Cleaning up stale Docker containers ---"

# List all stopped/stale containers
STALE=$(docker ps -a --format '{{.Names}}' 2>/dev/null | grep -v '^iacgenie-')
if [ -n "$STALE" ]; then
  for container in $STALE; do
    echo "  Removing stale container: $container"
    docker rm -f "$container" 2>/dev/null && log_ok "Removed $container" || log_warn "Could not remove $container"
  done
else
  log_ok "No stale containers found"
fi

# =============================================================================
# 5. PostgreSQL data ownership fix (postgres uid=999)
# =============================================================================
echo ""
echo "--- 5. Fixing PostgreSQL data ownership ---"

PG_DATA="${DOCKER_BASE}/postgres_data"
if [ -d "$PG_DATA" ]; then
  chown -R 999:999 "$PG_DATA" && log_ok "PostgreSQL data ownership set to uid 999:999" || log_warn "Could not change PostgreSQL data ownership"
else
  log_warn "PostgreSQL data directory not found at $PG_DATA"
fi

# =============================================================================
# 6. Jenkins data ownership fix
# =============================================================================
echo ""
echo "--- 5. Fixing Jenkins data ownership ---"

JENKINS_DATA="${DOCKER_BASE}/jenkins_data"
if [ -d "$JENKINS_DATA" ]; then
  chown -R 1000:1000 "$JENKINS_DATA" && log_ok "Jenkins data ownership set to uid 1000:1000" || log_warn "Could not change Jenkins data ownership"
else
  log_warn "Jenkins data directory not found at $JENKINS_DATA"
fi

# =============================================================================
# 6. Verify firewall status
# =============================================================================
echo ""
echo "--- 6. Verifying firewall status ---"

if ufw status 2>/dev/null | grep -q "Status: active"; then
  log_ok "ufw firewall is active"
  ufw status verbose 2>/dev/null | head -10
else
  log_warn "ufw firewall is NOT active"
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "============================================"
echo "  Hardening Complete"
echo "============================================"
echo ""
echo "NEXT STEPS:"
echo ""
echo "  1. Edit and review these files:"
echo "     - ${DOCKER_BASE}/docker-compose-newvm.yml"
echo "     - ${DOCKER_BASE}/cloudflared/config.yml"
echo "     - ${DOCKER_BASE}/docker/minio/init.sh"
echo ""
echo "  2. Rebuild Jenkins image (runs as non-root now):"
echo "     cd ${DOCKER_BASE}"
echo "     docker compose -f docker-compose-newvm.yml build jenkins"
echo ""
echo "  3. Restart services with hardened configuration:"
echo "     cd ${DOCKER_BASE}"
echo "     docker compose -f docker-compose-newvm.yml down"
echo "     docker compose -f docker-compose-newvm.yml up -d"
echo ""
echo "  4. Restart Cloudflare tunnel:"
echo "     sudo systemctl restart cloudflared-tunnel"
echo ""
echo "  5. Verify services are accessible:"
echo "     curl -sI https://jenkins.iacgenie.com | head -3"
echo "     curl -sI https://dashboards.iacgenie.com | head -3"
echo ""
echo "  6. VERIFY databases are NOT reachable:"
echo "     nc -zv $(hostname -f) 5432   # Should FAIL"
echo "     nc -zv $(hostname -f) 6379   # Should FAIL"
echo ""
echo "  7. ROTATE all secrets (they were exposed in git):"
echo "     - PostgreSQL, Redis, MinIO, OpenBao passwords"
echo "     - Cloudflare tunnel credentials"
echo "     - JWT secret"
echo "     - SMTP2GO API key"
