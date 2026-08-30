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

Every endpoint below works **both** locally (proxy on `http://127.0.0.1:80`) and
over the public Internet (Cloudflare Tunnel at `https://kokoro.iacgenie.com`). The
examples below use the public HTTPS endpoint; swap `https://kokoro.iacgenie.com` for
`http://127.0.0.1:80` to run them against the local proxy instead.

```bash
BASE="https://kokoro.iacgenie.com"        # public (Cloudflare Tunnel)
# BASE="http://127.0.0.1:80"              # local proxy on the homeserver
KEY=$(cat /home/mkanavi/docker/kokoro/.api_key)   # or: KEY="your-pinned-key"
```

> **Verified** (2026-08-31): `GET /health` → 200, and `POST /v1/audio/speech`
> (voice `af_heart`) → 200 with a valid MP3 over public HTTPS.

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

### 3.1 List available voices (public endpoint)

```bash
curl -s https://kokoro.iacgenie.com/v1/voices \
  -H "Authorization: Bearer $KEY" | jq '.voices[]'
```

**Response (verified):** a JSON array of `{"id", "description"}` objects. Full list:

| Voice ID | Description (language) |
|----------|------------------------|
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

### 3.2 List available models (public endpoint)

```bash
curl -s https://kokoro.iacgenie.com/v1/models \
  -H "Authorization: Bearer $KEY" | jq '.data[].id'
```

**Verified models:** `tts-1`, `tts-1-hd`, `kokoro`.

### 3.3 Basic speech synthesis (public endpoint)

```bash
curl -s https://kokoro.iacgenie.com/v1/audio/speech \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "kokoro",
    "input": "Hello world. This is a test.",
    "voice": "af_heart"
  }' -o /tmp/test.mp3

file /tmp/test.mp3   # → MPEG audio (or WAV), valid file
```

### 3.4 With speed adjustment

The `speed` parameter (0.25–4.0) controls speech rate and is supported:

```bash
curl -s https://kokoro.iacgenie.com/v1/audio/speech \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "kokoro",
    "input": "This speech will be read slower.",
    "voice": "af_heart",
    "speed": 0.85
  }' -o /tmp/slow.mp3

# Verify speed was accepted (HTTP 200, valid audio):
file /tmp/slow.mp3

# Expected: HTTP 200, valid audio (b'ID3...' header), ~7 KB for short text
```

### 3.5 Health check (no auth required)

For load balancers / health probes:

```bash
curl -s https://kokoro.iacgenie.com/health   # → {"status":"ok","engine":"kokoro"}
```

> `/health` is exempt from rate limiting and does **not** require the bearer token.

### 3.6 Error handling examples (public endpoint)

| Scenario | HTTP code | Response body (`jq .detail`) |
|----------|-----------|------------------------------|
| No `Authorization` header | **401** | Unauthenticated / unauthorized |
| Invalid/missing voice id | **422** | Voice not found (see §3.1) |
| Rate limit exceeded (> burst 20) | **429** | Too Many Requests (nginx `limit_req`) |
| Server error / model load fail | **500** | Internal server error |

```bash
# Confirm 401 without a key:
curl -s https://kokoro.iacgenie.com/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input":"no key","voice":"af_heart"}'

# Confirm 429 with a rapid burst loop (default rate limit):
for i in $(seq 1 50); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    https://kokoro.iacgenie.com/v1/audio/speech \
    -H "Authorization: Bearer $KEY" \
    -d '{"input":"x","voice":"af_heart"}' | sort | uniq -c
done
# → mostly 200s, then a run of 429s once burst is exhausted
```

### 3.7 Voice language reference (all languages)

Kokoro-82M is a multilingual model. Voices are tagged by language and gender:

| Language | Female voices | Male voices |
|----------|----------------|-------------|
| **American English** | `af_heart`, `af_aoede`, `af_bella`, `af_jessica`, `af_kore`, `af_nicole`, `af_nova`, `af_river`, `af_sarah`, `af_sky` | `am_adam`, `am_michael`, `am_echo`, `am_eric`, `am_fenrir`, `am_liam`, `am_onyx` |
| **British English** | — | `bm_george` |
| **Japanese** | `jf_alpha` | `jm_kumo` |
| **Mandarin Chinese** | `zf_xiaobei` | `zm_yunxi` |
| **Italian** | `if_sara` | `im_nicola` |
| **Brazilian Portuguese** | `pf_dora` | — |

> Prefer a slower, clearer voice with an Italian accent? Use `im_nicola` (Italian male)
> or `if_sara` (Italian female), with `speed: 0.85–0.95`.

### 3.8 Tuning options reference

| Field | Type | Range / values | Purpose |
|-------|------|----------------|---------|
| `model` | string | `tts-1`, `tts-1-hd`, `kokoro` | Model family to use (`kokoro` is the multilingual default) |
| `input` | string | any text | Text to synthesize (UTF-8) |
| `voice` | string | see §3.1 / §3.7 | Voice ID; invalid → **422** |
| `speed` | number | 0.25–4.0 (default 1.0) | Speech rate multiplier (< 1 slower, > 1 faster) |

**Tuning examples:**

```bash
# Slower, clearer delivery (user preference) — Italian male voice
curl -s https://kokoro.iacgenie.com/v1/audio/speech \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"kokoro","input":"Buongiorno, come stai?","voice":"im_nicola","speed":0.85}' \
  -o /tmp/italian.mp3

# Faster delivery — American female voice
curl -s https://kokoro.iacgenie.com/v1/audio/speech \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"kokoro","input":"Let us go! We are late.","voice":"af_jessica","speed":1.5}' \
  -o /tmp/fast.mp3

# British male voice, normal speed
curl -s https://kokoro.iacgenie.com/v1/audio/speech \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"kokoro","input":"A fine day, isn'"'"'t it?","voice":"bm_george"}' \
  -o /tmp/british.mp3

# Mandarin Chinese, normal speed
curl -s https://kokoro.iacgenie.com/v1/audio/speech \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"kokoro","input":"你好，世界。","voice":"zf_xiaobei"}' \
  -o /tmp/mandarin.mp3

# Japanese, normal speed
curl -s https://kokoro.iacgenie.com/v1/audio/speech \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"kokoro","input":"こんにちは世界。","voice":"jf_alpha"}' \
  -o /tmp/japanese.mp3

# Brazilian Portuguese, normal speed
curl -s https://kokoro.iacgenie.com/v1/audio/speech \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"kokoro","input":"Olá, mundo!","voice":"pf_dora"}' \
  -o /tmp/portuguese.mp3
```

### 3.9 Multi-language batch synthesis (public endpoint)

Generate one audio file per language in a loop:

```bash
declare -A VOICE=(
  [en_us]=af_heart   [en_gb]=bm_george   [ja]=jf_alpha
  [zh]=zf_xiaobei    [it]=im_nicola      [pt]=pf_dora
)
declare -A TEXT=(
  [en_us]="Hello world."   [en_gb]="A fine day, is it not?"
  [ja]="こんにちは世界。"   [zh]="你好，世界。"
  [it]="Buongiorno."       [pt]="Olá, mundo!"
)

for lang in "${!VOICE[@]}"; do
  curl -s https://kokoro.iacgenie.com/v1/audio/speech \
    -H "Authorization: Bearer $KEY" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"kokoro\",\"input\":\"${TEXT[$lang]}\",\"voice\":\"${VOICE[$lang]}\"}" \
    -o /tmp/$lang.mp3
  echo "$lang -> /tmp/$lang.mp3"
done

file /tmp/*.mp3   # verify each is valid audio
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
# On homeserver (local proxy):
docker ps --format '{{.Names}}\t{{.Status}}' | grep -i kokoro
curl http://127.0.0.1/health                                   # → 200 ok
KEY=$(cat /home/mkanavi/docker/kokoro/.api_key)

# Synthesis with valid key (local proxy):
curl -s http://127.0.0.1/v1/audio/speech \
  -H "Authorization: Bearer $KEY" \
  -d '{"model":"kokoro","input":"Hello world.","voice":"af_heart"}' -o /tmp/test.mp3
file /tmp/test.mp3    # → valid audio file

# Rate limit behavior:
for i in $(seq 1 50); do curl -s -o /dev/null \
  http://127.0.0.1/v1/audio/speech -d '{"input":"x","voice":"af_heart"}'; done

# Public Internet endpoint (Cloudflare Tunnel) — from any machine:
curl https://kokoro.iacgenie.com/health                              # → 200 ok
curl https://kokoro.iacgenie.com/v1/audio/speech \
  -H "Authorization: Bearer $KEY" -d '{"model":"kokoro","input":"Hello.","voice":"af_heart"}' \
  -o /tmp/test.mp3                                                   # → valid MP3

# Tunnel service on the homeserver:
systemctl status cloudflared-kokoro.service        # → active (running)
```

Expected: `kokoro-1` + `kokoro-nginx` running; `/health` → 200; synthesis returns
a valid audio file (b'ID3…' header for MP3); rapid bursts eventually yield 429s.
The `kokoro.iacgenie.com` public endpoint routes through the dedicated Cloudflare
tunnel (`cloudflared-kokoro.service`) to nginx :80 → kokoro-1:8881.
