# Kokoro TTS — homeserver (192.168.0.116)

Ansible-managed Kokoro TTS deployment: **3 HA replicas** of `hwdsl2/kokoro-server`
behind an nginx reverse proxy with **rate limiting** and native **API-key auth**.

## Architecture
```
Cloudflare tunnel (127.0.0.1:80) → nginx proxy :80
  └─ limit_req (rate limited, per client IP)
       └─ upstream kokoro_backend { 127.0.0.1:8881, :8882, :8883 }
            └─ hwdsl2/kokoro-server ×3 (Bearer auth via KOKORO_API_KEY)
```

- **HA**: 3 replicas; nginx `upstream` load-balances. If one dies, traffic routes to the other two.
- **Auth**: native `Authorization: Bearer <key>` enforced by hwdsl2/kokoro-server via the `KOKORO_API_KEY` env var.
- **Rate limiting**: nginx `limit_req_zone` (default 10r/s, burst 20).
- **Just Docker**: single `docker-compose.yml`, no Kubernetes.

## Files
```
kokoro/
├── ansible.cfg              # SSH sudo, inventory path
├── inventory.ini            # homeserver target (192.168.0.116)
├── playbooks/
│   ├── deploy.yml           # ansible-playbook -i inventory.ini playbooks/deploy.yml
│   └── teardown.yml         # ansible-playbook -i inventory.ini playbooks/teardown.yml
└── roles/kokoro/
    ├── defaults/main.yml    # tunables (replicas, ports, rate limits, cache paths)
    ├── tasks/
    │   ├── main.yml         # deploy logic (idempotent)
    │   └── teardown.yml     # remove stack + volumes
    ├── templates/
    │   ├── nginx.conf.j2        # reverse proxy + rate limiting + upstream
    │   └── docker-compose.kokoro.j2  # 3 replicas + nginx
```

## Model cache (required before deploy)

The image ships **no weights**. The 327 MB `kokoro-v1_0.pth` is downloaded on the
host via [`hfdl`](https://github.com/huggingface-hub-sync/HFDownload) into
`/home/mkanavi/kokoro_hub/hub/models--hexgrad--Kokoro-82M/` (hfdl names the repo
directory `models--hexgrad--Kokoro-82M` automatically — **not**
`.../hub/Kokoro-82M`). Then it is bind-mounted into the container at
`/var/lib/kokoro/hub/models--hexgrad--Kokoro-82M`. The role fails fast if the
cache is missing.

```bash
# On homeserver (token from container env: docker inspect ... | grep HF_TOKEN)
export HF_TOKEN="hf_xxx"   # 37-char HuggingFace token (read_access)
mkdir -p /home/mkanavi/kokoro_hub/hub
/opt/hfdl-venv/bin/hfdl hexgrad/Kokoro-82M \
  --directory /home/mkanavi/kokoro_hub/hub \
  --threads 6

# Verify: blobs/496dba118d…e4 must be exactly 327,212,226 bytes.
# sha256 (authoritative): 496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4
sha256sum /home/mkanavi/kokoro_hub/hub/models--hexgrad--Kokoro-82M/blobs/496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4

# ⚠️ CRITICAL: refs/main MUST contain the 40-hex commit hash with NO trailing
# newline. HuggingFace Hub's hf_file_download reads refs/main via f.read(), which
# keeps the newline → commit_hash becomes "<hash>\n" and no snapshot folder matches.
python3 -c "print(repr(open('/home/mkanavi/kokoro_hub/hub/models--hexgrad--Kokoro-82M/refs/main','rb').read()))"
# Expected: b'f3ff3571791e39611d31c381e3a41a3af07b4987'   (len 40)
# If it ends with '\n', strip it: printf "%s" "$(cat refs/main)" > refs/main
```

## Offline resolution (why the newline matters)
Kokoro loads offline via `snapshot_download("hexgrad/Kokoro-82M", local_files_only=True)`.
Empirically verified on the host: with a trailing newline in `refs/main` it raises
`LocalEntryNotFoundError`; without one, resolution succeeds. The container sets
`HF_HUB_CACHE=/var/lib/kokoro/hub`, so the bind-mounted cache must mirror this layout:
`<cache>/models--hexgrad--Kokoro-82M/{blobs/, refs/main, snapshots/<hash>/}`.

## Usage

### Deploy (first run generates a random API key, stored at docker/kokoro/.api_key)
```bash
cd ~/.hermes/git_clone_dir/iacgenie-platform/infra/homeserver/kokoro
ansible-playbook -i inventory.ini playbooks/deploy.yml

# Pin a specific key instead of auto-generating:
ansible-playbook -i inventory.ini playbooks/deploy.yml \
  -e kokoro_api_key="your-secret-key-here"
```

### Tear down (removes containers + volumes)
```bash
ansible-playbook -i inventory.ini playbooks/teardown.yml
```

### Verify after deploy
```bash
# On homeserver, check replicas + proxy:
docker ps --format '{{.Names}}\t{{.Status}}' | grep -i kokoro

# Health check through the proxy:
curl http://127.0.0.1/health

# Without a key → expect 401; with the generated key:
KEY=$(cat /home/mkanavi/docker/kokoro/.api_key)
curl -s http://127.0.0.1/v1/audio/speech \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"input":"Hello world","voice":"im_nicola"}' -o /tmp/test.mp3

# Rate limit test:
for i in $(seq 1 50); do curl -s -o /dev/null -w "%{http_code}\n" \
  http://127.0.0.1/v1/audio/speech -d '{"input":"x","voice":"im_nicola"}'; done
```

## Tunables (defaults/main.yml)
| Var | Default | Meaning |
|-----|---------|---------|
| `kokoro_replicas` | 3 | HA replica count |
| `kokoro_host_port_start` | 8881 | First host port (replicas get consecutive ports) |
| `kokoro_rate_limit_zone` | 10r/s | Sustained rate per client IP |
| `kokoro_rate_limit_burst` | 20 | Burst allowance (nodelay) |
| `kokoro_voice` | im_nicola | Default voice |
| `kokoro_speed` | 0.85 | Speech speed (matches user preference) |
| `kokoro_cpu_limit` | 1.0 | CPU limit per replica |
| `kokoro_mem_limit` | 512m | Memory limit per replica |

## Notes
- The host-downloaded model cache at `kokoro_model_cache_host_path` is bind-mounted;
  it persists across restarts because the weights live on the host, not in a volume.
- The generated API key is stored at `/home/mkanavi/docker/kokoro/.api_key` (mode 0600).
- No dependency on OpenBao (not reachable from homeserver) — keeps this self-contained.
- Model download must complete before `deploy.yml` runs (the role fails fast otherwise).
