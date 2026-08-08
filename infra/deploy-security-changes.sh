#!/bin/bash
# =============================================================================
# Quick deploy: nginx + security changes
# =============================================================================
set -euo pipefail

VM_USER="mkanavi"
VM_IP="192.168.0.118"

echo "=== Deploying Security Changes ==="

# 1. Deploy security docker-compose to VM
echo "[1/4] Deploying security docker-compose..."
scp -o StrictHostKeyChecking=no \
    "ansible/roles/security/templates/docker-compose.security.yml.j2" \
    "${VM_USER}@${VM_IP}:/home/mkanavi/docker/iacgenie/docker-compose.security.yml"

# 2. Deploy updated nginx config to VM
echo "[2/4] Deploying updated nginx reverse-proxy.conf..."
scp -o StrictHostKeyChecking=no \
    "ansible/roles/nginx/templates/reverse-proxy.conf.j2" \
    "${VM_USER}@${VM_IP}:/tmp/iacgenie.conf.new"

# 3. Copy nginx config and create nginx-logs symlink
echo "[3/4] Configuring nginx and nginx-logs symlink..."
ssh -o StrictHostKeyChecking=no "${VM_USER}@${VM_IP}" << 'ENDSSH'
sudo cp /tmp/iacgenie.conf.new /etc/nginx/conf.d/iacgenie.conf && rm /tmp/iacgenie.conf.new
sudo mkdir -p /home/mkanavi/docker/iacgenie/nginx-logs
ln -sf /var/log/nginx/access.log /home/mkanavi/docker/iacgenie/nginx-logs/access.log
ln -sf /var/log/nginx/error.log /home/mkanavi/docker/iacgenie/nginx-logs/error.log
sudo systemctl restart nginx
sudo nginx -t
ENDSSH

# 4. Deploy security services via docker-compose
echo "[4/4] Deploying security services (ClamAV + CrowdSec)..."
ssh -o StrictHostKeyChecking=no "${VM_USER}@${VM_IP}" << 'ENDSSH'
cd /home/mkanavi/docker/iacgenie
docker compose -f docker-compose.security.yml down --remove-orphans 2>/dev/null || true
docker compose -f docker-compose.security.yml up -d
ENDSSH

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Services deployed:"
echo "  ✓ Grafana: grafana.iacgenie.com"
echo "  ✓ ClamAV Web Client: clamav.iacgenie.com"
echo "  ✓ CrowdSec Web UI: crowdsec.iacgenie.com"
echo ""
echo "Check services: ssh mkanavi@${VM_IP} 'docker compose -f docker-compose.security.yml ps'"
