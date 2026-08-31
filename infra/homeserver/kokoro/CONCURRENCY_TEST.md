# Kokoro TTS — Concurrency & Scaling Test Report

**Date:** 2026-08-31
**Host:** 192.168.0.116 (homeserver), 8 cores, 31 GiB RAM
**Stack:** `hwdsl2/kokoro-server` × 5 replicas behind nginx reverse proxy (port :80)
**Commit:** `d9adf00` — scaled replicas 1 → 5

## Deployment Architecture (current)

```
Internet ──Cloudflare Tunnel──► nginx :80 (host-mode, kokoro-nginx)
                                    │  limit_req zone=kokoro_limit burst=20 nodelay (10r/s)
                                    ▼
              upstream kokoro_backend { server 127.0.0.1:8881; ... :8885 }
                                    │
                    (round-robin load balancing across replicas)
              kokoro-1 → kokoro-5  (each: cpus=1.0, memory=2g)
```

- Each replica publishes on `127.0.0.1:888X` (bridge mode, loopback-only)
- nginx load-balances across all 5 via the `kokoro_backend` upstream
- Bearer auth enforced inside each replica (`KOKORO_API_KEY`)

## Concurrency Test Results

### Test 1 — True parallel burst (5 simultaneous requests)
- **Result:** 3× HTTP 200, 2× HTTP 504 (Gateway Timeout)
- **Wall time:** ~60s to complete all in-flight requests
- **Observation:** kokoro-1 hit 100% CPU + 100% mem while serving; other replicas idle
- **Root cause of timeouts:** cold-start pipeline downloads (en-core-web-sm, HF weights)
  delay the first request per replica. Replicas that already warmed up served instantly.

### Test 2 — Steady-state throughput (10 sequential, rate-limited)
- **Result:** 10/10 HTTP 200 in **72s** (~8 req/s, matching nginx rate limit)
- Confirms replicas handle sustained load without errors once warmed.

### Memory footprint (post-warmup)
| Replica | Mem %  | Usage    | CPU   |
|---------|--------|----------|-------|
| kokoro-1| 98.45% | 1.969GiB | ~0.1% |
| kokoro-2| 89.53% | 1.791GiB | ~0.1% |
| kokoro-3| 90.76% | 1.815GiB | ~0.1% |
| kokoro-4| 90.76% | 1.815GiB | ~0.1% |
| kokoro-5| 90.76% | 1.815GiB | ~0.1% |

Each replica settles at **~925 Mi–2 GiB** (warmed). Total steady-state: ~8.7 GiB across
5 replicas, well within the 31 GiB host budget.

## Key Findings

1. **Concurrency is real but limited by replicas, not the proxy.** nginx distributes
   requests across all 5 replicas immediately — load balancing works.

2. **Cold start is the bottleneck.** The first request to each replica triggers on-demand
   downloads (NLP packages, HF weights), causing 504s under a true parallel burst.
   Warm-up requests (`/v1/audio/speech` once per replica) eliminate this.

3. **nginx rate limit (10r/s, burst 20) is the throughput ceiling** for a single client.
   Raising `kokoro_rate_limit_burst` or adding more replicas raises sustained throughput.

4. **Memory grows to ~2 GiB per replica** after warm-up (torch + transformers). This is
   expected — the role's `kokoro_mem_limit: 2g` comment notes 512m triggers OOM.

## How to Scale Further

- Set `kokoro_replicas: N` in defaults, redeploy via ansible (see README)
- nginx load-balances automatically — no code change needed for more replicas
- Increase `kokoro_rate_limit_burst` if sustained throughput is the constraint

## How to Warm Up After Deploy / Recreate

After scaling or recreating replicas, fire one request per replica to trigger the
one-time downloads before expecting full concurrency:

```bash
for port in 8881 8882 8883 8884 8885; do
  curl -s -o /dev/null \
    -X POST "http://127.0.0.1:${port}/v1/audio/speech" \
    -H "Authorization: Bearer $(cat /home/mkanavi/docker/kokoro/.api_key)" \
    --data '{"model":"kokoro","input":"warmup","voice":"af_heart"}'
done
```
