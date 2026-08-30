# Kokoro TTS — Architecture & Usage Guide

Deployment and API usage reference for the **Kokoro-82M** text-to-speech service on
homeserver `192.168.0.116`. This complements [`README.md`](./README.md) (deployment
quickstart) and [`KOKORO_HANDOFF.md`](./KOKORO_HANDOFF.md) (offline/deploy internals).

---

## 1. Deployment Architecture

### Topology

```
                          ┌──────────────────────────────────────────────┐
   Internet                │  Homeserver 192.168.0.116                     │
   (Cloudflare Tunnel)     │                                             │
        │                 │  ┌─────────────── nginx :80 (host-mode)      │
        ▼                 │  │   limit_req_zone = kokoro_limit          │
┌─────────────┐           │  │   burst=20 nodelay (429 on overuse)      │
│ *.iacgenie  ├──────────►│  └──────┬─────────────────────────┐         │
│ .com          │  :80     │        ▼                         │ (bind)  │
└─────────────┘           │  ┌─────────────────── kokoro-1   ├─────────►
                          │  │  hwdsl2/kokoro-server          │           │
                          │  │   image: kokoro-1 (bridge)     │           │
                          │  │   ports → 127.0.0.1:8881       │           │
                          │  │   KOKORO_LOCAL_ONLY=true        │           │
                          │  │   bind-mount: host cache → /var/lib/kokoro/hub ┐
                          │  │   cpus=1.0 memory=2g                        │
                          └──────────────────────────┬─────────────────────┘
                                                      │
                                              [KOKORO_API_KEY]  ← bearer auth (native)

   Persistent model cache (host bind-mount, survives restarts):
   /home/mkanavi/kokoro_hub/hub/models--hexgrad--Kokoro-82M
```

### Component breakdown

| Layer | Container / Path | Image | Role | Network mode |
|-------|------------------|-------|------|---------------|
| Proxy | `kokoro-nginx` | `nginx:1.27-alpine` | Reverse proxy, rate limiting, health endpoint | **host** (binds `:80`) |
| TTS engine | `kokoro-1` | `hwdsl2/kokoro-server:latest` | Audio synthesis (Kokoro-82M) | **bridge** → `127.0.0.1:8881` |

> **Why two containers?** The proxy is in `host` mode so it binds the host's
> port 80 (reachable by Cloudflare Tunnel). The TTS engine is in `bridge` mode
> publishing **only** on `127.0.0.1:8881` so the synthesis API is never exposed
> on a public interface — even though it runs in `host` networking context.

### Key design decisions (with rationale)

1. **Single container by default** — Kokoro-82M needs ~2 GB RAM; a single replica
   is sufficient for homeserver traffic. Set `kokoro_replicas: 3` in
   [`defaults/main.yml`](./roles/kokoro/defaults/main.yml) to scale out (nginx
   load-balances across replicas).

2. **Loopback-only bind** — the TTS engine publishes on `127.0.0.1:8881` only,
   never `0.0.0.0`. This keeps the API unreachable from outside even though
   nginx uses `host` networking on port 80.

3. **Host bind-mount, not Docker volume** — weights live on the host at
   `kokoro_model_cache_host_path` so they survive `docker compose down`. A named
   volume would be wiped on teardown.

4. **No OpenBao dependency** — the role auto-generates a random API key (or accepts
   `-e kokoro_api_key=...`) and stores it at `~/.api_key` (mode 0600). OpenBao is
   not reachable from the homeserver.

5. **Native bearer auth** — enforced inside `hwdsl2/kokoro-server` via
   `KOKORO_API_KEY`, not at the proxy layer. Requests without a valid token get
   `401` from the replica; nginx passes them through.

---

## 2. Data flow (request lifecycle)

```
Client ──GET /health──► nginx :80 ──(no rate limit)──► kokoro-1 /health ──► 200
Client ──POST /v1/audio/speech──► nginx :80
                              │  limit_req (rate limited)
                              ▼
                         kokoro-1 /v1/audio/speech ──► validates bearer token
                              │  (401 if missing/invalid)
                              ▼
                         loads weights from bind-mounted cache ──► synthesizes .mp3/.wav
                              │
                              ▼
                         returns audio stream ◄── Client saves file
```

**Rate limiting:** nginx `limit_req_zone` uses `$binary_remote_addr` (per client IP),
default sustained rate 10 r/s with burst allowance of 20 (`nodelay`). Exceeding the
rate returns `429 Too Many Requests`.

---

## 3. API Usage Examples

All examples target the **proxy** at `http://127.0.0.1:80` (or the Cloudflare URL
`https://*.iacgenie.com`). The proxy forwards to `kokoro-1:8881`.

### 3.0 Prerequisites — obtain the API key

The role stores the generated (or pinned) key at:

```
/home/mkanavi/docker/kokoro/.api_key     # mode 0600, single line
```

Read it into a shell variable:

```bash
KEY=$(cat /home/mkanavi/docker/kokoro/.api_key)
echo "key length: ${#KEY}"   # 32 chars for a random key
```

> **Security:** never paste this value into chat, logs, or commit it. It grants
> full API access to the TTS engine.

### 3.1 List available voices

```bash
curl -s http://127.0.0.1/v1/voices \
  -H "Authorization: Bearer ${KEY}" | jq '.voices[]'
```

**Response (verified):** a JSON array of `{"id", "description"}` objects. Full list:

| Voice ID | Description |
|----------|-------------|
| `af_heart` | American female — warm, natural (**recommended default**) |
| `af_aoede` | American female |
| `af_bella` | American female — expressive |
| `af_jessica` | American female — energetic |
| `af_kore` | American female |
| `af_nicole` | American female — friendly |
| `af_nova` | American female — clear |
| `af_river` | American female — calm |
| `af_sarah` | American female — conversational |
| `af_sky` | American female — neutral, versatile |
| `am_adam` | American male — deep |
| `am_michael` | American male — clear |
| `am_echo` | American male — neutral |
| `am_eric` | American male — authoritative |
| `am_fenrir` | American male — distinctive |
| `am_liam` | American male — conversational |
| `am_onyx` | American male — rich |
| `bm_george` | British male — authoritative |
| `jm_kumo` | Japanese male |
| `jf_alpha` | Japanese female |
| `zf_xiaobei` | Mandarin Chinese female |
| `zm_yunxi` | Mandarin Chinese male |
| `if_sara` | Italian female |
| `im_nicola` | **Italian male** (matches user preference) |
| `pf_dora` | Brazilian Portuguese female |

> See [`KOKORO_HANDOFF.md`](./KOKORO_HANDOFF.md) for the complete voice inventory.

### 3.2 List available models

```bash
curl -s http://127.0.0.1/v1/models \
  -H "Authorization: Bearer ${KEY}" | jq '.data[].id'
```

**Verified models:** `tts-1`, `tts-1-hd`, `kokoro`.

### 3.3 Basic speech synthesis (minimum)

```bash
curl -s http://127.0.0.1/v1/audio/speech \
  -H "Authorization: Bearer ${KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "Hello world. This is a test.",
    "voice": "af_heart"
  }' -o /tmp/test.mp3

file /tmp/test.mp3   # → MPEG audio (or WAV), valid file
```

### 3.4 With speed adjustment

The `speed` parameter (0.25–4.0) controls speech rate and is supported:

```bash
curl -s http://127.0.0.1/v1/audio/speech \
  -H "Authorization: Bearer ${KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "This speech will be read slower.",
    "voice": "af_heart",
    "speed": 0.85
  }' -o /tmp/slow.mp3

# Verify speed was accepted (HTTP 200, valid audio):
curl -s http://127.0.0.1/v1/audio/speech \
  -H "Authorization: Bearer ${KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "This speech will be read slower.",
    "voice": "af_heart",
    "speed": 0.85
  }' -o /tmp/slow.mp3 && file /tmp/slow.mp3

# Expected: HTTP 200, valid audio (b'ID3...' header), ~7 KB for short text
```

### 3.5 Health check (no auth required)

For load balancers / health probes:

```bash
curl -s http://127.0.0.1/health   # → {"status":"ok","engine":"kokoro"}
```

> `/health` is exempt from rate limiting and does **not** require the bearer token.

### 3.6 Error handling examples

| Scenario | HTTP code | Response body (`jq .detail`) |
|----------|-----------|------------------------------|
| No `Authorization` header | **401** | Unauthenticated / unauthorized |
| Invalid/missing voice id | **422** | Voice not found (see §3.1) |
| Rate limit exceeded (> burst 20) | **429** | Too Many Requests (nginx `limit_req`) |
| Server error / model load fail | **500** | Internal server error |

```bash
# Confirm 401 without a key:
curl -s http://127.0.0.1/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input":"no key","voice":"af_heart"}'

# Confirm 429 with a rapid burst loop (default rate limit):
for i in $(seq 1 50); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    http://127.0.0.1/v1/audio/speech \
    -H "Authorization: Bearer ${KEY}" \
    -d '{"input":"x","voice":"af_heart"}' | sort | uniq -c
done
# → mostly 200s, then a run of 429s once burst is exhausted
```

---

## 4. Scaling & configuration knobs

All tunables live in [`defaults/main.yml`](./roles/kokoro/defaults/main.yml).

| Variable | Default | Purpose |
|----------|---------|---------|
| `kokoro_replicas` | 1 | Replica count. Set >1 to scale out (nginx load-balances). |
| `kokoro_host_port_start` | 8881 | First host port; replicas get consecutive ports. |
| `kokoro_rate_limit_zone` | 10r/s | Sustained rate per client IP. |
| `kokoro_rate_limit_burst` | 20 | Burst allowance (`nodelay`). |
| `kokoro_voice` | im_nicola | Default voice (set via env). |
| `kokoro_speed` | 0.85 | Default speech speed (matches user preference). |
| `kokoro_cpu_limit` | 1.0 | CPU limit per container (`deploy.resources.limits.cpus`). |
| `kokoro_mem_limit` | 2g | Memory limit per container (512m triggers OOM). |
| `kokoro_local_only` | true | Offline-only weight loading. |

### Example: deploy with custom voice and pinned key

```bash
ansible-playbook -i inventory.ini playbooks/deploy.yml \
  -e kokoro_api_key="your-secret-key-here" \
  -e kokoro_voice="im_nicola" \
  -e kokoro_speed=0.95 \
  -e kokoro_replicas=3
```

### Example: scale down to single container (default)

```bash
ansible-playbook -i inventory.ini playbooks/deploy.yml \
  -e kokoro_replicas=1
```

---

## 5. Troubleshooting quick reference

| Symptom | Cause / fix |
|---------|-------------|
| `401 Unauthorized` on `/v1/audio/speech` | Missing/invalid bearer token. Read key from `~/.api_key`. |
| `/health` returns 200 but synthesis fails | Model cache incomplete — see `KOKORO_HANDOFF.md §2`. |
| Rapid requests → 429 | Rate limit hit (burst=20). Increase `kokoro_rate_limit_burst`. |
| Container restarts / OOM kill | Raise `kokoro_mem_limit` (needs ~2 GB for Kokoro-82M). |
| `refs/main` trailing newline → load fail | Strip to 40 hex bytes, no `\n`. See `KOKORO_HANDOFF.md §2-3`. |
| Model cache path mismatch | Must be `.../models--hexgrad--Kokoro-82M` (not `.../Kokoro-82M`). |

---

## 6. Verification checklist (post-deploy)

```bash
# On homeserver:
docker ps --format '{{.Names}}\t{{.Status}}' | grep -i kokoro
curl http://127.0.0.1/health                                   # → 200 ok
KEY=$(cat /home/mkanavi/docker/kokoro/.api_key)

# Synthesis with valid key:
curl -s http://127.0.0.1/v1/audio/speech \
  -H "Authorization: Bearer ${KEY}" \
  -d '{"model":"tts-1","input":"Hello world.","voice":"af_heart"}' -o /tmp/test.mp3
file /tmp/test.mp3    # → valid audio file

# Rate limit behavior:
for i in $(seq 1 50); do curl -s -o /dev/null \
  http://127.0.0.1/v1/audio/speech -d '{"input":"x","voice":"af_heart"}'; done
```

Expected: `kokoro-1` + `kokoro-nginx` running; `/health` → 200; synthesis returns
a valid audio file (b'ID3…' header for MP3); rapid bursts eventually yield 429s.
