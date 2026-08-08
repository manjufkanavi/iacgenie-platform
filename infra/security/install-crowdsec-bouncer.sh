#!/bin/bash
# =============================================================================
# CrowdSec Nginx Bouncer - Host Installation Script
# =============================================================================
# Since Nginx runs as a host-level systemd service, the bouncer must be
# installed on the host directly (not in Docker).
# =============================================================================

set -euo pipefail

echo "=== CrowdSec Nginx Bouncer Installation ==="

# 1. Install CrowdSec
echo "[1/4] Installing CrowdSec..."
curl -fsSL https://packagecloud.io/crowdsec/crowdsec/gpgkey | sudo gpg --dearmor -o /etc/apt/keyrings/crowdsec.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/crowdsec.gpg] https://packagecloud.io/crowdsec/crowdsec/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/crowdsec.list > /dev/null
sudo apt-get update -qq
sudo apt-get install -y crowdsec

# 2. Register with CrowdSec Cloud
echo "[2/4] Registering with CrowdSec Cloud..."
sudo cscli registrations

# 3. Install collections
echo "[3/4] Installing collections (nginx, http-cve, whitelist)..."
sudo cscli collections install crowdsecurity/nginx
sudo cscli collections install crowdsecurity/http-cve
sudo cscli collections install crowdsecurity/whitelist-good-actors
sudo cscli collections install crowdsecurity/scrapy

# 4. Install Nginx bouncer
echo "[4/4] Installing Nginx bouncer..."
sudo apt-get install -y cs-nginx-bouncer

# 5. Configure CrowdSec to read Nginx logs
echo "[+] Configuring Nginx log acquisition..."
cat > /etc/crowdsec/acquis.yaml << EOF
filenames:
  - /var/log/nginx/access.log
  - /var/log/nginx/error.log
type: File
EOF

# 6. Restart CrowdSec
echo "[+] Restarting CrowdSec..."
sudo systemctl restart crowdsec
sudo systemctl enable crowdsec

# 7. Generate bouncer API key
echo "[+] Generating bouncer API key..."
BOUNCER_KEY=$(sudo cscli bouncers add nginx-bouncer 2>/dev/null | grep -oP 'api key: \K.*' || echo "")
echo "Nginx bouncer API key: $BOUNCER_KEY"
echo "$BOUNCER_KEY" > /etc/crowdsec/bouncer-api-key.txt 2>/dev/null || true

echo ""
echo "=== Installation Complete ==="
echo "CrowdSec is now monitoring Nginx logs."
echo "Check status: sudo systemctl status crowdsec"
echo "View decisions: sudo cscli decisions list"
