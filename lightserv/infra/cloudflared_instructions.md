# Cloudflared Tunnel Setup

## Prerequisites

- Cloudflare account with the `iacgenie.com` domain
- VM with Docker and internet access
- SSH access to the VM

## Installation

### 1. Add Cloudflare GPG key and repository

```bash
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-public-v2.gpg | sudo tee /usr/share/keyrings/cloudflare-public-v2.gpg >/dev/null

echo 'deb [signed-by=/usr/share/keyrings/cloudflare-public-v2.gpg] https://pkg.cloudflare.com/cloudflared any main' | sudo tee /etc/apt/sources.list.d/cloudflared.list

sudo apt-get update && sudo apt-get install cloudflared
```

### 2. Install the tunnel

Run on the VM as user `mkanavi`:

```bash
cloudflared service install <TUNNEL_TOKEN>
```

The tunnel credentials are stored in `/home/mkanavi/docker/iacgenie/docker/cloudflared/auth.json`.

### 3. Configure the tunnel

Tunnel config: `/home/mkanavi/docker/iacgenie/cloudflared/config.yml`

The tunnel name is `iacgenie-pi` and it exposes all services via wildcard DNS (`*.iacgenie.com` → `<tunnel-id>.cfargotunnel.com`).

### 4. Start as systemd service

The systemd service file is at `cloudflared.service`. Install it with:

```bash
sudo cp cloudflared.service /etc/systemd/system/cloudflared-tunnel.service
sudo systemctl daemon-reload
sudo systemctl enable --now cloudflared-tunnel
```

Verify:
```bash
sudo systemctl status cloudflared-tunnel
journalctl -u cloudflared-tunnel -f
```

---

## Optional: Add Cloudflare Access for Authentication

Cloudflared tunnel provides encrypted transport only — no user authentication. Add Cloudflare Access to require identity-based login before requests reach Jenkins.

See `infra/services-secrets.md` → "Cloudflare Access (Optional — Recommended Upgrade)" for step-by-step configuration.

---

## Tunnel Details

- **Tunnel name**: `iacgenie-pi`
- **Tunnel ID**: `1291108a-4e8d-4439-9fa6-316be7da5f97`
- **Protocol**: HTTP/2
- **Auto-updates**: Disabled (`NO_AUTOUPDATE=true`)
- **Auto-restart**: 5-second delay

## Ingress Rules

| Hostname | Backend | Protocol |
|----------|---------|----------|
| vm.iacgenie.com | http://127.0.0.1:80 | HTTP |
| mac.iacgenie.com | http://192.168.0.120:80 | HTTP |
| jenkins.iacgenie.com | http://127.0.0.1:8085 | HTTP |
| minio.iacgenie.com | http://127.0.0.1:9000 | HTTP |
| console.minio.iacgenie.com | http://127.0.0.1:9001 | HTTP |
| auth.iacgenie.com | http://127.0.0.1:8080 | HTTP |
| metrics.iacgenie.com | http://127.0.0.1:9090 | HTTP |
| dashboards.iacgenie.com | http://127.0.0.1:3001 | HTTP |
| panel.iacgenie.com | http://127.0.0.1:8089 | HTTP |
| app.iacgenie.com | http://192.168.0.120:5173 | HTTP |
| api.iacgenie.com | http://192.168.0.120:8000 | HTTP |

**Removed rules** (for security — databases and secrets must not be internet-exposed):
- `postgres.iacgenie.com` — TCP passthrough to PostgreSQL (removed 2026-06-13)
- `redis.iacgenie.com` — TCP passthrough to Redis (removed 2026-06-13)
- `vault.iacgenie.com` — HTTP to OpenBao (removed 2026-06-13)

