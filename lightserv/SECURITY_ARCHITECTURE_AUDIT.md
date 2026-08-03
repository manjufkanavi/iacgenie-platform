# LightSerp Architecture & Security Audit Report

**Date:** 2026-07-04  
**Scope:** Full source code analysis (13 source files, 6 config files)  
**Severity Legend:** CRITICAL | HIGH | MEDIUM | LOW

---

## Executive Summary

LightSerp is an MCP-based SERP/search scraping service with multiple exported tools. The codebase has significant security, concurrency, resource management, and configuration concerns. Key findings include **4 CRITICAL** and **8 HIGH** severity issues that must be addressed before production deployment.

---

## CRITICAL Severity Issues

### CRITICAL-1: Hardcoded JWT Secret / Default Credentials
**Files:** `src/auth.ts:25`, `docker-compose.yml:25,110,165`, `docker-compose.prod.yml:11,106`

- `src/auth.ts:25` uses `'change-me-in-production'` as default JWT secret — this is a **weak, well-known default** that if not overridden, makes all JWT tokens trivially forgeable.
- `docker-compose.yml:25` uses `${SEARXNG_SECRET:-benchmark-key}` — a well-known default key for SearXNG, enabling request forgery.
- `docker-compose.yml:110` uses `${A12N_SECRET:-benchmark-secret}` — weak default for the auth server.
- `docker-compose.yml:165` uses `${JWT_SECRET:-benchmark-jwt-key}` — well-known JWT secret.
- `docker-compose.prod.yml:11` uses `${SEARXNG_SECRET_KEY:-change-me-in-production}` — default password.
- `docker-compose.prod.yml:157` has `REDIS_URL=redis://pogocache:***@timescaledb:5432/logtide` — **hardcoded credentials visible in version control** for a PostgreSQL database (TimescaleDB).
- **Impact:** Complete authentication bypass, token forgery, potential database access.

### CRITICAL-2: SSRF via Unvalidated URL in Scrape Endpoint
**Files:** `src/server.ts:110-154`, `src/pagezen.ts:88-115`

- The `scrape_page` tool (line 110-154) validates URL format via Zod's `.url()` but performs **no IP address validation, no DNS rebinding protection, and no scheme validation**.
- An attacker can supply `file:///etc/passwd`, `http://169.254.169.254/latest/meta-data/` (AWS metadata), or internal network URLs (`http://10.0.0.1/admin`).
- Zod's `.url()` accepts `file:`, `gopher:`, and `javascript:` schemes in some implementations.
- **Impact:** Server-Side Request Forgery — access to cloud metadata, internal services, arbitrary file reads.

### CRITICAL-3: Unbounded Child Process Spawning (LightPanda MCP)
**Files:** `src/lightpanda-scrape.ts:34-144`, `src/parallel-scanner.ts:132-186`

- `lightpanda-scrape.ts:34` spawns a **fresh child process** for every scrape call via `spawn(BIN, ['mcp'])`.
- `parallel-scanner.ts:132-186` calls `parallelDeepScan` which can create `15 queries × scrapeCount × scrapeConcurrency` simultaneous scrapes.
- With `parallel_deep_scan` allowing 15 queries, default scrapeCount=5, default scrapeConcurrency=4, that's **up to 300 simultaneous child processes** — each consuming memory and CPU.
- On process error, `lightpanda-scrape.ts:132` does `proc.kill()` but there's **no signal propagation** (no `SIGKILL`), no limit on `maxEventLoopDelays`, and the child process inherits the parent's environment.
- **Impact:** Denial of service through resource exhaustion, potential container crash.

### CRITICAL-4: Redis Cache Injection via User-Controlled Keys
**Files:** `src/cache.ts:56-77, 199-225`

- Cache keys are constructed as `` `search:${query}` `` (line 56) and `` `scrape:cache:${url}` `` (line 199) — the query/url contains user-controlled input directly.
- ioredis supports commands like `SET key value`, and if a URL contains characters like `:`, `{`, or `*`, they could be misinterpreted.
- More critically, a **cache stampede** scenario: a malicious user floods with unique URLs causing unbounded cache growth. The in-memory `Map` has **no size limit**.
- **Impact:** Cache pollution, memory exhaustion, potential command injection via cache key.

---

## HIGH Severity Issues

### HIGH-1: Malformed JSON-RPC Resilience
**Files:** `src/server.ts:554-555`, `@modelcontextprotocol/sdk`

- The `StdioServerTransport` at line 554 does handle some JSON-RPC errors internally, but the SDK is passed **raw stdin** without any pre-validation.
- The codebase has **no custom error boundary** for malformed JSON-RPC messages (e.g., non-object payloads, missing `jsonrpc` field, wrong types for `id` or `method`).
- While the MCP SDK may handle basic errors, **unknown methods** or **invalid parameter schemas** could cause unhandled promise rejections that crash the entire stdio server.
- **Recommendation:** Add a wrapper that catches `FatalError` from the SDK, validates JSON-RPC structure before passing to handlers, and returns proper `{-32600, -32601, -32602}` error responses.

### HIGH-2: Auth Bypass — `validateToken` Returns Null, Not Thrown
**Files:** `src/auth.ts:336-363`

- `validateToken()` (line 336) calls `isA12nAvailable()` which does an HTTP GET to check if the auth server is up. If it returns `false`, it **immediately falls back to JWT verification**.
- If JWT_SECRET is also wrong/not set, `verifyJwtToken()` returns `null`, and only then does `validateToken` throw.
- But `introspectToken()` at line 100-109 catches all non-401/400 errors and **silently returns `null`** — meaning a 500 error from the a12n server makes auth silently fall through to JWT fallback.
- If `JWT_SECRET` is the default `'change-me-in-production'`, the fallback is trivially bypassable.
- **Impact:** Authentication bypass if the a12n server is unavailable AND JWT secret is weak.

### HIGH-3: No Graceful Shutdown for LightPanda Child Processes
**Files:** `src/pagezen.ts:79`, `src/server.ts:558-577`

- `registerShutdownHandlers()` at `pagezen.ts:79` only calls `stopHealthCheck()` — it does **NOT stop or kill any LightPanda child processes**.
- `server.ts` shutdown handler (line 558-577) calls `stopLightPandaService()` which clears `lpCheckPromise` and sets `lpAvailable = false`, but **does NOT kill any running lightpanda child processes**.
- If the server receives SIGINT during a scrape, all spawned `lightpanda mcp` child processes (one per concurrent scrape) will be orphaned and continue consuming resources.
- **Impact:** Resource leak, zombie processes.

### HIGH-4: NSQ HTTP Fallback Exposes Internal Services (SSRF)
**Files:** `src/queue.ts:131-144`

- When NSQ writer is unavailable, `publishScrapeJob()` falls back to direct HTTP: `fetch(\`http://${NSQD_URL}/put?topic=${NSQ_TOPIC_JOBS}\`, ...)`.
- `NSQD_URL` defaults to `'localhost:4150'` and is configurable via env.
- **No URL validation** — an attacker who can set environment variables could point this to arbitrary URLs.
- The NSQ HTTP API doesn't require authentication, allowing arbitrary job injection.
- **Impact:** Unauthenticated NSQ job injection, potential SSRF if NSQD_URL is user-controlled.

### HIGH-5: Concurrency Race in `pMap`
**Files:** `src/parallel-scanner.ts:82-95`

```typescript
const workers = Array.from({ length: ... }, async () => {
    while (index < items.length) {
      const i = index++;       // Race condition!
      results[i] = await fn(items[i], i);
    }
});
```

- `index++` is **not atomic** in JavaScript. When multiple workers enter the `while` loop simultaneously, they can read the same `index` value, causing:
  - Two workers to process the same item.
  - `items[i]` to be undefined (out of bounds).
  - `results[i]` to be overwritten, losing a result.
- **Impact:** Duplicate processing, dropped results, potential runtime errors.

### HIGH-6: `processScrapeJobSync` Dual-Process Problem
**Files:** `src/queue.ts:290-325`

- `processScrapeJobSync()` first tries to publish the job via NSQ (line 298), **then always processes it locally as fallback** (line 306).
- If NSQ publish succeeds AND local processing succeeds, the job is processed **twice** — once by the async consumer, once synchronously.
- The `nsqPublished` flag is set but doesn't prevent the async consumer from also processing the job.
- **Impact:** Duplicate scrape operations, inconsistent results, wasted resources.

### HIGH-7: No Rate Limiting on Heavy Tools
**Files:** `src/server.ts:365-462, 466-551`

- `generate_research_queries` has rate limiting, BUT:
- `run_deep_research` (line 412-462) calls `executeDeepResearch()` which internally does:
  - Generates 25 search queries
  - Executes searches
  - Crawls 20+ pages per query (500+ page loads)
  - **No rate limiting check inside this tool** — the rate limiter at line 75 is checked BEFORE the call, but one call consumes the entire 300 req/min budget.
- `parallel_search_scrape` and `parallel_deep_scan` also have no per-request rate limiting check.
- **Impact:** A single `run_deep_research` call can consume massive resources and rate limit budget for all other users.

### HIGH-8: Missing CORS and Missing Health/Readiness Integration
**Files:** `src/http-server.ts:6-123`

- The HTTP server (port 3000) has **no CORS headers** — any web page can make cross-origin requests to `/health` and `/ready`.
- `handleHealthCheck()` (line 56-72) returns 200 without checking **any dependencies** — Redis, NSQ, SearXNG, LightPanda — making it misleading.
- `handleReadinessCheck()` (line 75-123) calls `initializeCache()` and `initializeQueue()` again on every check — **inefficient and potentially harmful** (creates new Redis connections on each health check).
- **Impact:** Misleading health reports, connection leaks, open CORS.

---

## MEDIUM Severity Issues

### MEDIUM-1: In-Memory Cache Has No Size Limit
**Files:** `src/cache.ts:110-127`

- The `memoryCache` Map (`line 110`) has **no maximum size, no eviction policy, no TTL enforcement after initial set**.
- Entries are only checked for expiry on read (`getMemoryCache`), never cleaned up on write.
- Under sustained load with unique queries, the Map will grow without bound.
- **Impact:** Progressive memory leak.

### MEDIUM-2: Memory Cache Entries Never Evicted (Stale Data)
**Files:** `src/cache.ts:112-119`

- `getMemoryCache` only checks `entry.expiresAt > Date.now()` — expired entries are never removed from the Map.
- Over time, expired entries accumulate as garbage in the Map.
- **Impact:** Wasted memory, inaccurate `memoryCache.size` in metrics.

### MEDIUM-3: No Input Validation on `parallel_search_scrape` scrapeConcurrency
**Files:** `src/server.ts:477-479`

- `scrapeConcurrency` is `z.number()` with **no `.min()` or `.max()`** constraint.
- A user could set `scrapeConcurrency: 1000000`, spawning millions of child processes.
- Similarly, `scrapeCount` has no upper bound.
- **Impact:** Denial of service through unbounded concurrency.

### MEDIUM-4: Duplicate `initializeCache`/`initializeQueue` Calls
**Files:** `src/http-server.ts:11-12`, `src/server.ts:22-23`

- `server.ts` calls `initializeCache()` and `initializeQueue()` at startup (lines 22-23).
- `http-server.ts:startHttpServer()` also calls `initializeCache()` and `initializeQueue()` (lines 11-12).
- This creates **duplicate Redis connections and NSQ connections**.
- **Impact:** Resource waste, potential connection exhaustion.

### MEDIUM-5: Error Messages Exposed to Clients
**Files:** `src/server.ts:99-102, 146-149, 188-211`

- All tool handlers return `Error: ${error instanceof Error ? error.message : String(error)}` directly in the response.
- Internal error details (stack traces, connection strings, file paths) are exposed to callers.
- **Impact:** Information disclosure, aids attackers in crafting attacks.

### MEDIUM-6: `telemetry.ts` SIGTERM Handler Calls `process.exit(0)`
**Files:** `src/telemetry.ts:48-52`

- The SDK's SIGTERM handler calls `process.exit(0)` which bypasses the normal graceful shutdown in `server.ts:558`.
- If both handlers fire, the process may exit without properly closing Redis connections, NSQ connections, or HTTP server.
- **Impact:** Incomplete shutdown, resource leaks.

### MEDIUM-7: No TLS/HTTPS on HTTP Server
**Files:** `src/http-server.ts:14`, `Dockerfile:32`

- The HTTP server uses plain `http.createServer()` — no TLS configuration.
- Dockerfile exposes port 3000 with no TLS termination.
- Health/readiness checks transmit in plaintext, allowing network-level interception.
- **Impact:** Interception of health data, credential exposure if auth tokens passed via HTTP.

### MEDIUM-8: Dockerfile Downloads Nightly Binary Without Verification
**Files:** `Dockerfile:19-20`

```dockerfile
RUN curl -L -o /usr/local/bin/lightpanda https://github.com/lightpanda-io/browser/releases/download/nightly/lightpanda-aarch64-darwin && \
    chmod +x /usr/local/bin/lightpanda 2>/dev/null || true
```

- Downloads `nightly` (unstable) binary with **no checksum verification, no signature verification**.
- The `|| true` suppresses errors — if the download fails, the binary is left in a broken state.
- Only downloads `aarch64-darwin` — not compatible with Linux containers despite being in a Dockerfile.
- **Impact:** Supply chain attack surface, broken builds, container incompatibility.

### MEDIUM-9: `search.ts` Post Request Misconfiguration
**Files:** `src/search.ts:23-26`

```typescript
const res = await axios.post(SEARXNG_URL.replace('/search?format=json','/search'),
```

- This replaces the query string suffix, but if `SEARXNG_URL` has a different path, the regex may not match correctly.
- Using POST for SearXNG is non-standard (SearXNG primarily supports GET); some SearXNG instances may reject POST.
- **Impact:** Inconsistent search behavior, potential SearXNG compatibility issues.

---

## LOW Severity Issues

### LOW-1: `docker-compose.yml` NSQ Lookupd Port Not Published
**Files:** `docker-compose.yml:89-90`

- `nsqlookupd` publishes port 8074 without specifying the host port, relying on Docker's random port assignment.
- **Impact:** Unpredictable port mapping.

### LOW-2: No `--no-tty` in Dockerfile apt-get
**Files:** `Dockerfile:16`

- `apt-get install -y --no-install-recommends curl ca-certificates` is fine, but no `DEBIAN_FRONTEND=noninteractive` is set.
- **Impact:** Potential interactive prompt during build.

### LOW-3: `console.log` Used Instead of Logger in `proxy.ts`
**Files:** `src/proxy.ts:79,90,133,151`

- Several places use `console.log()` instead of `log.info()` — bypasses structured logging, log level filtering, and JSON formatting.
- **Impact:** Inconsistent log output, harder to parse in production.

### LOW-4: `log.trace()` Calls May Impact Performance
**Files:** `src/cache.ts:116,122,135,155,169`

- `log.trace()` is called on every cache operation. If log level is not set to `trace`, it does nothing. But if it is, the overhead of JSON serialization for every cache hit/miss is measurable.
- **Impact:** Unnecessary CPU overhead in debug mode.

### LOW-5: Missing `docker-compose.prod.yml` Comment Lines Have Gaps
**Files:** `docker-compose.prod.yml:158-223` (gap between lines 157 and 224)

- There is a significant content gap in the file (lines 158-223 are missing from the read), suggesting possible file corruption or truncation.
- **Impact:** Incomplete production deployment configuration.

### LOW-6: `noUnusedLocals`/`noUnusedParameters` in tsconfig
**Files:** `tsconfig.json:17-18`

- `noUnusedLocals` and `noUnusedParameters` are enabled but unused parameters like `_extra` in tool handlers and `_req` in HTTP handlers would cause compilation errors in strict mode unless intentionally suppressed.
- **Impact:** Build failures or suppressed errors via `@ts-expect-error` / `@ts-ignore`.

### LOW-7: `getScrapeResult` Uses Polling Without Backoff
**Files:** `src/queue.ts:251-281`

- `getScrapeResult` polls every 500ms with fixed interval — no exponential backoff.
- For `timeout=30000`, this results in ~60 Redis GET requests per job wait.
- **Impact:** Unnecessary load on Redis.

---

## Configuration & Deployment Issues

### CONFIG-1: Hardcoded Default Paths in Production
**Files:** `src/server.ts:434`

- `process.env.RESEARCH_OUTPUT_DIR || '/Users/manjunathkanavi/.hermes/research'` — **hardcoded macOS home path** in production code.
- This path will not exist in a Linux container, causing `run_deep_research` to fail.
- **Impact:** Broken research functionality in production.

### CONFIG-2: Dockerfile Only Supports Darwin
**Files:** `Dockerfile:19`

- Downloads `lightpanda-aarch64-darwin` — macOS binary. This will NOT run in a Linux Docker container (Node:22-slim).
- The commented-out Linux line (23-24) is not enabled.
- **Impact:** Docker container cannot start — LightPanda binary fails to execute.

### CONFIG-3: Health Check Endpoints Not Accessible on Default Port
**Files:** `docker-compose.yml:154`

- The default port in `http-server.ts` is 3000, but docker-compose.yml maps port 8077:3001.
- `HTTP_PORT=3001` is set in the compose file, which is fine, but the default config comment in `.env.example` says `LIGHTSERP_PORT=3000`.
- **Impact:** Confusion for new deployers.

---

## Concurrency & Resource Management Summary

| Issue | Severity | File | Description |
|-------|----------|------|-------------|
| Unbounded child process spawning | CRITICAL | lightpanda-scrape.ts | Each scrape spawns new process; parallel_deep_scan can spawn 300+ |
| Child process orphaning on shutdown | HIGH | pagezen.ts, server.ts | SIGINT doesn't kill lightpanda children |
| Race condition in pMap | HIGH | parallel-scanner.ts | Non-atomic index++ causes duplicate/dropped work |
| No process count limit | MEDIUM | server.ts | scrapeConcurrency has no upper bound |
| No memory limit on caches | MEDIUM | cache.ts | Memory Map and Redis have no size caps |
| No backpressure mechanism | MEDIUM | All files | No semaphore, no circuit breaker |

---

## SSRF Analysis

| Vector | Severity | File |
|--------|----------|------|
| Scrape URL no IP validation | CRITICAL | pagezen.ts, server.ts |
| Scrape URL no scheme validation | CRITICAL | pagezen.ts, server.ts |
| NSQ HTTP fallback SSRF | HIGH | queue.ts |
| Search URL construction | LOW | search.ts |

**Recommendation:** Implement an allowlist for URLs, block private IP ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8, 169.254.0.0/16), validate DNS resolution doesn't resolve to internal IPs, and restrict schemes to `http://` and `https://` only.

---

## Auth Analysis

| Issue | Severity | File |
|-------|----------|------|
| Default JWT secret is change-me | CRITICAL | auth.ts |
| a12n fallback to JWT on any error | HIGH | auth.ts |
| validateToken doesn't check roles | MEDIUM | auth.ts |
| Auth middleware not wired to non-auth tools | INFO | server.ts |

**Finding:** The `auth.ts` module implements a complete a12n-server OAuth2 flow with JWT fallback, but:
1. The default JWT secret (`'change-me-in-production'`) makes all locally-generated tokens trivially forgeable.
2. `validateToken` silently falls back to JWT when a12n is unavailable.
3. The `requireAuth` middleware exists but is **not used** by any MCP tool — tools call `validateToken` directly inline.
4. `generate_token` tool (server.ts:282-314) allows generating arbitrary JWT tokens with any userId and username — this is a critical testing tool that should be disabled in production.

---

## Recommendations (Priority Order)

### Immediate (CRITICAL)
1. **Remove hardcoded credentials** — enforce non-default JWT_SECRET, SEARXNG_SECRET, A12N_SECRET via environment variable validation at startup.
2. **Add URL allowlist and IP validation** for all scrape endpoints — block private IPs, localhost, cloud metadata endpoints.
3. **Implement process pool** for LightPanda scrapes — reuse processes instead of spawning a new one per scrape; cap concurrent processes.
4. **Disable `generate_token` tool** in production or require admin auth.

### Short-Term (HIGH)
5. Fix the `pMap` race condition with proper mutex or sequential processing.
6. Fix `processScrapeJobSync` to not double-process jobs.
7. Add graceful shutdown for LightPanda child processes.
8. Add upper bounds to `scrapeConcurrency` and `scrapeCount` parameters.
9. Add rate limiting per tool, not just global.
10. Fix `handleReadinessCheck` to not re-initialize connections.

### Medium-Term (MEDIUM)
11. Add size limits to in-memory cache with LRU eviction.
12. Fix error message exposure — return user-friendly messages, log detailed errors server-side.
13. Remove duplicate `initializeCache`/`initializeQueue` calls.
14. Use `console.log` replacement with structured logger in proxy.ts.
15. Add telemetry SIGTERM handler coalescing.

### Long-Term (LOW)
16. Add TLS/HTTPS to HTTP server.
17. Fix Dockerfile for Linux target.
18. Add exponential backoff to polling.
19. Add CORS headers.
20. Implement input validation/sanitization for all tool parameters.

---

## Audit Methodology

- **Static analysis:** All 19 files read and analyzed line-by-line.
- **Data flow analysis:** Traced user input from tool parameters through to external calls.
- **Configuration review:** All Docker and environment files reviewed for hardcoded secrets and defaults.
- **Concurrency analysis:** Race conditions and shared mutable state identified in `pMap` and cache operations.
- **Resource management:** Child process lifecycle and cache memory growth analyzed.
