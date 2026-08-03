# LightSerp — Architecture Task Specification

> **Date:** 2026-07-18
> **Author:** Architect (Hermes Agent)
> **Source:** PRODUCTION_READINESS_TASK_PLAN.md, Task T-050
> **Scope:** Horizontal scaling architecture, in-memory-to-distributed state migration strategy, Docker Compose multi-instance configuration
> **Target Environment:** Single VM (192.168.0.118) with Docker Compose, Nginx reverse proxy, Cloudflare Tunnel

---

## Table of Contents

1. [Current Architecture Assessment](#1-current-architecture-assessment)
2. [Horizontal Scaling Architecture Design](#2-horizontal-scaling-architecture-design)
3. [Migration Strategy: In-Memory to Distributed State](#3-migration-strategy-in-memory-to-distributed-state)
4. [Docker Compose Multi-Instance Configuration](#4-docker-compose-multi-instance-configuration)
5. [T-050 Detailed Task Specification](#5-t-050-detailed-task-specification)
6. [Architectural Dependencies Map](#6-architectural-dependencies-map)
7. [Risk Assessment & Mitigations](#7-risk-assessment--mitigations)

---

## 1. Current Architecture Assessment

### 1.1 Existing Topology

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Cloudflare  │────▶│    Nginx     │────▶│   LightSerp  │
│    Tunnel     │     │ Reverse      │     │   Single     │
│              │     │   Proxy      │     │   Instance   │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                    ┌─────────────────────────────┤
                    │                             │
              ┌─────▼──────┐             ┌───────▼────────┐
              │  SearXNG   │             │  PostgreSQL     │
              │  (8070)    │             │  (5432)         │
              └────────────┘             └────────────────┘
                    │
              ┌─────▼──────┐
              │    Redis   │
              │  (6379)    │
              └────────────┘
                    │
              ┌─────▼──────┐
              │    NSQ     │
              │  (4150/41) │
              └────────────┘
```

### 1.2 In-Memory State Inventory (Blocking Horizontal Scaling)

| # | Module | File | State Type | Impact on Scaling | Severity |
|---|--------|------|------------|-------------------|----------|
| 1 | **Rate Limiter** | `server.ts` | `RateLimiterMemory` (per-process counters) | Each instance has independent rate limit counters — users bypass limits by hitting different instances | 🔴 Critical |
| 2 | **In-Memory Cache** | `cache.ts` | `LRUCache(1000)` fallback when Redis fails | Redis is shared, but fallback is per-instance — inconsistent cache hit rates; metrics reporting is per-instance | 🟡 Medium |
| 3 | **Pending Results Store** | `queue.ts` | `Map<string, pendingResult>` for NSQ-unavailable mode | When NSQ is down, in-memory pending results are instance-local — results from one instance invisible to others | 🟡 Medium |
| 4 | **Queue Metrics** | `queue.ts` | `queueMetrics` object (counters) | Per-instance counters make aggregate metrics unreliable | 🟢 Low |
| 5 | **Scrape Cache Metrics** | `cache.ts` | `scrapeCacheMetrics` object (counters) | Per-instance counters | 🟢 Low |
| 6 | **dbInitialized** | `auth.ts` | `let dbInitialized = false` | Module-level boolean; harmless for scaling but indicates shared-state pattern | 🟢 Low |
| 7 | **Redlock/Concurrent** | Various | No distributed locking on cache refresh | Cache stampede: N instances all compute same result on cache miss | 🔴 Critical |

### 1.3 Key Architectural Gaps

1. **No distributed session affinity** — but there is no server-side session either (good: JWT-based stateless auth)
2. **No connection pool tuning** — `pg` pool is `max: 10` per instance; with N instances, total connections = N × 10, which could overwhelm a single PostgreSQL
3. **No HTTP metrics endpoint** — Prometheus scraping exists in prod compose but no `/metrics` HTTP endpoint
4. **No health check integration with load balancer** — Nginx doesn't perform active health checks on upstreams
5. **Nginx config only has single upstream** — needs to be parameterized for multiple instances

---

## 2. Horizontal Scaling Architecture Design

### 2.1 Design Principles

| Principle | Application |
|-----------|-------------|
| **Stateless compute** | All Node.js instances must be functionally identical; no instance-local state affects correctness |
| **Shared everything else** | PostgreSQL, Redis, NSQ are shared resources — accessed by all instances |
| **Cloud-agnostic** | Design works on a single VM with Docker Compose; extensible to Kubernetes |
| **Gradual migration** | Preserve in-memory fallbacks during transition; deprecate them incrementally |
| **Config-driven scaling** | Scale factor controlled by a single `SCALE_FACTOR` environment variable |

### 2.2 Target Topology (Production Horizontal Scale)

```
                          ┌──────────────┐
                          │   Cloudflare  │
                          │    Tunnel     │
                          └──────┬───────┘
                                 │
                          ┌──────▼───────┐
                          │    Nginx      │  ← Health-checked upstream pool
                          │  Load Balancer│    (round-robin, no stickiness)
                          └──┬─────┬─────┘
                               │     │
                    ┌──────────▼─┐ ┌─▼──────────┐
                    │ LightSerp  │ │ LightSerp  │
                    │ Instance 1 │ │ Instance 2 │  ← SCALE_FACTOR (default: 2)
                    │  (3071)    │ │  (3072)    │
                    └──────┬─────┘ └──────┬─────┘
                           │               │
                    ┌──────▼───────────────▼───────┐
                    │    Shared Infrastructure       │
                    │                                │
              ┌─────▼────┐  ┌──────┐  ┌──────┐  ┌─▼──────┐
              │ PostgreSQL│  │ Redis│  │ NSQ  │  │ SearXNG│
              │  (5432)  │  │(6379) │  │(4150) │  │ (8070) │
              └──────────┘  └──────┘  └──────┘  └────────┘
```

### 2.3 Component Changes

#### 2.3.1 Application Layer (LightSerp Instance)

| Component | Current Behavior | Target Behavior | Migration Notes |
|-----------|-----------------|-----------------|-----------------|
| **Rate Limiter** | `RateLimiterMemory` (per-process) | `RateLimiterRedis` (shared via Redis) | Must use Redis-backed counter with atomic INCR/EXPIRE |
| **Cache Fallback** | `LRUCache(1000)` in-memory | Same as-is, but marked `DEPRECATED` | Redis is the primary; memory cache becomes read-only transient overlay with no write path |
| **Pending Results** | `Map<string, pendingResult>` | Redis Stream (`pending:results:*`) | Use Redis Streams for distributed pending result waiting |
| **Queue Metrics** | In-memory counters | Redis Hash (`lightserp:metrics:queue`) | All instances increment the same Redis hash |
| **Database Pool** | `max: 10` per instance | `max: 10 / SCALE_FACTOR` (min 2) | Pool size must be capacity-planned against total instances |
| **Service Discovery** | None | Environment-based (docker-compose networks) | Instances discover shared services via Docker DNS |

#### 2.3.2 Redis Data Model for Distributed State

```
Key Pattern                  Type       Purpose                         TTL
───────────────────────────────────────────────────────────────────────
ratelimit:{type}:{identifier}    String    Atomic rate limit counter        Configurable
ratelimit:{type}:{identifier}:meta  Hash    Last-throttle timestamp            Same as counter
ratelimit:{type}:{identifier}:failures  Integer    Consecutive failures              1h

cache:search:{query}             String    Cached search results              300s
cache:scrape:{url}               String    Cached scrape result               3600s

pending:results:{jobId}          String    Scrape result (set by producer)    3600s
pending:results:{jobId}:owner    String    Which instance claimed this        30s

stream:pending:results:*         Stream  Async pending result queue         N/A

metrics:queue:global             Hash    Aggregate job metrics              N/A (TTL-cleanup by cron)
metrics:cache:global             Hash    Aggregate cache metrics            N/A

lock:cache:refresh:{hash}        String  Distributed lock for cache refresh  60s
lock:cache:refresh:{hash}:holder String  Instance holding the lock          60s
```

#### 2.3.3 Redis Pub/Sub for Cross-Instance Events

```
Channel                    Purpose
───────────────────────────┼───────────────────────────────────────────
lightserp:cache:invalidate  Broadcast cache invalidation across instances
lightserp:config:reload     Signal configuration reload
lightserp:health:heartbeat  Periodic health broadcast for LB feedback
```

#### 2.3.4 Nginx Load Balancer Design

```nginx
upstream lightserp_instances {
    # Docker Compose defines 'lightserp-instance-1' and 'lightserp-instance-2'
    # on the same Docker network, each mapped to a different port.
    server lightserp-instance-1:3071;
    server lightserp-instance-2:3071;
    # Future: server lightserp-instance-3:3071;  // Add as SCALE_FACTOR grows

    # No sticky sessions — fully stateless
    # Nginx round-robin distributes requests evenly
}

# Active health check via location /health (proxied to instances)
# Nginx will remove unhealthy upstreams automatically
```

### 2.4 Connection Pool Sizing Formula

```
PostgreSQL max connections = ceil(Target Max RPS / 50) + (SCALE_FACTOR × idle_buffer)
where:
  - 50 = expected max queries per second per pool connection
  - idle_buffer = 5 connections per instance (for maintenance queries)
  - Example: SCALE_FACTOR=3, Target RPS=200 → max_connections = ceil(200/50) + 3×5 = 25

Per-instance pool.max = max(2, ceil(total_pg_max_connections / SCALE_FACTOR))
Example: pg_max=25, SCALE=3 → per-instance = ceil(25/3) = 9 (but use 8 to leave headroom)
```

---

## 3. Migration Strategy: In-Memory to Distributed State

### 3.1 Migration Phases

#### Phase 0: Preparation (Days 1-2) — *No behavior change*

**Tasks:**
- Create `src/rate-limiter-redis.ts` — Redis-backed rate limiter using `RateLimiterRedis` from `rate-limiter-flexible`
- Add Redis pub/sub subscriber module (`src/pubsub.ts`)
- Add distributed lock utility (`src/distributed-lock.ts`) using Redis `SETNX` with TTL
- Write unit tests for all new modules
- Add new environment variables to `.env.example`

**Acceptance Criteria:**
- All new modules have >90% unit test coverage
- New Redis keys follow the naming convention defined in §2.3.2
- Pub/sub module handles reconnection automatically

#### Phase 1: Rate Limiter Migration (Days 3-4) — *Dual-write transition*

**Tasks:**
- Replace `RateLimiterMemory` with `RateLimiterRedis` in `server.ts`
- Implement per-user AND per-IP rate limiting using Redis-backed `RateLimiterFlexible`
- Add rate limit response headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`)
- Keep in-memory rate limiter as a *fallback* during initial deployment (config flag)

**Migration Strategy:**
```
Config flag: RATE_LIMITER_MODE=redis  (fallback: memory)

Day 1-2: RATE_LIMITER_MODE=memory    ← current behavior
Day 3:   RATE_LIMITER_MODE=redis     ← switch to Redis
Week 1:  Monitor error rate — if stable, proceed
Week 2:  Remove memory fallback code
```

**Acceptance Criteria:**
- Rate limiting works identically across 2+ instances
- Per-user rate limits use `userId` from JWT (authenticated) or IP (anonymous)
- Rate limit headers present in all API responses
- Redis-backed limiter handles Redis connection failure gracefully (fallback to per-instance `RateLimiterMemory` with warning log)

#### Phase 2: Pending Results Distribution (Days 5-6)

**Tasks:**
- Replace `pendingResults` Map with Redis-backed pending result store
- Use Redis Streams (`pending:results:{jobId}`) for async waiting
- Implement `publishPendingResult()` and `waitForPendingResult()` with timeout
- Use Redis pub/sub to notify waiters when result is ready

**Migration Strategy:**
```
Architecture change:
  OLD: Instance A stores pending result → Instance A polls → Instance A returns result
  NEW: Instance A stores pending result to Redis → Instance B waits on Redis Stream → Redis pub/sub wakes up waiters → Instance B returns result

  This enables any instance to retrieve a result published by any other instance.
```

**Acceptance Criteria:**
- Results published by Instance A are retrievable by Instance B
- Pending result timeout expires correctly
- Redis Stream entries are cleaned up (max len policy)

#### Phase 3: Metrics Aggregation (Day 7)

**Tasks:**
- Move `queueMetrics` and `scrapeCacheMetrics` from process-local to Redis Hash
- Add `/metrics` HTTP endpoint for Prometheus scraping
- Implement Prometheus exposition format (text/plain)

**Acceptance Criteria:**
- Prometheus scrapes aggregate metrics from any instance
- Metrics include per-component (cache, queue, proxy) counters and histograms
- `/metrics` endpoint supports `text/plain` content type

#### Phase 4: Cache Stampede Protection (Day 8)

**Tasks:**
- Implement distributed cache lock using `SETNX` (see `src/distributed-lock.ts`)
- Only one instance fetches data on cache miss; others wait
- Lock timeout prevents deadlocks (TTL-based)

**Acceptance Criteria:**
- Concurrent cache misses for the same URL result in exactly ONE fetch
- Stamped waiting instances receive the result within the fetch timeout
- Lock expiry prevents indefinite blocking

#### Phase 5: Cleanup (Day 9)

**Tasks:**
- Remove all in-memory fallback code paths
- Remove `LRUCache` class (keep as a development-only tool)
- Clean up unused memory-cache exports
- Update `AGENTS.md` to reflect new architecture

### 3.2 Rollback Plan

| Phase | Rollback Method | Risk |
|-------|----------------|------|
| Phase 1 | Set `RATE_LIMITER_MODE=memory`, restart instance | Low — rate limits become per-instance (not distributed) |
| Phase 2 | Revert to Map-based pending results | Medium — async jobs may hang during transition |
| Phase 3 | Remove `/metrics` endpoint, revert to MCP metrics | Low — metrics are supplementary |
| Phase 4 | Disable stampede protection (direct cache miss) | Low — acceptable under low concurrency |
| Phase 5 | Re-introduce memory fallback if Redis is down | High — only after full validation |

---

## 4. Docker Compose Multi-Instance Configuration

### 4.1 `docker-compose.scale.yml` — Standalone Scaling Compose File

This file is designed to be used alongside the existing `docker-compose.yml` or `docker-compose.prod.yml` to scale LightSerp instances. It uses **extends** or **profiles** to avoid duplicating shared infrastructure.

```yaml
# docker-compose.scale.yml
#
# Usage: docker compose -f docker-compose.yml -f docker-compose.scale.yml up -d
#
# Environment variables (must be set):
#   SCALE_FACTOR       — Number of LightSerp instances (default: 2)
#   POSTGRES_URL       — PostgreSQL connection string (shared)
#   REDIS_URL          — Redis connection string (shared)
#   NSQD_URL           — NSQ daemon URL (shared)
#   SEARXNG_URL        — SearXNG search URL (shared)
#   JWT_SECRET         — Must be set (enforced by secrets.js)

version: "3.8"

x-common-env: &common-env
  NODE_ENV: production
  SCALE_FACTOR: "${SCALE_FACTOR:-2}"

services:
  # ── LightSerp Instances (horizontal scale) ──────────────────────────
  # Each instance runs on a different port but uses the same base image.
  # Ports are assigned sequentially: 3071, 3072, 3073, ...

  lightserp:
    # Dynamic service names: lightserp-instance-1, lightserp-instance-2
    image: lightserp/mcp-server:latest
    environment:
      <<: *common-env
      HTTP_PORT: ${INSTANCE_HTTP_PORT:-3071}
      POSTGRES_URL: "${POSTGRES_URL}"
      REDIS_URL: "${REDIS_URL}"
      NSQD_URL: "${NSQD_URL:-nsqd:4150}"
      SEARXNG_URL: "${SEARXNG_URL}"
      JWT_SECRET: "${JWT_SECRET}"
      # New: rate limiter mode
      RATE_LIMITER_MODE: "redis"
      # New: Redis-backed rate limiter config
      RATE_LIMIT_MAX_POINTS: "30"
      RATE_LIMIT_DURATION: "60"
      RATE_LIMIT_PER_USER: "true"
      # New: connection pool sizing
      DB_POOL_MAX: "${DB_POOL_MAX:-8}"
      DB_POOL_IDLE_TIMEOUT: "30000"
      DB_POOL_CONNECTION_TIMEOUT: "5000"
      # New: distributed cache lock
      CACHE_LOCK_TTL: "60"
      # New: NSQ consumer count (one per instance = better parallelism)
      NSQ_CONSUMER_MAX_IN_FLIGHT: "10"
    networks:
      - lightserp-shared
      - lightserp-frontend
    restart: unless-stopped
    # Health check — Nginx uses this to detect unhealthy instances
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:${INSTANCE_HTTP_PORT:-3071}/health"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 30s
    # Scale dynamically
    deploy:
      replicas: ${SCALE_FACTOR:-2}
      resources:
        limits:
          cpus: "1.0"
          memory: 512M
        reservations:
          cpus: "0.25"
          memory: 128M

# ── Shared Nginx Load Balancer ────────────────────────────────────────
  nginx-lb:
    image: nginx:1.25-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.scale.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      lightserp:
        condition: service_healthy
    networks:
      - lightserp-frontend
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 128M

networks:
  lightserp-shared:
    external: true  # Shared with existing docker-compose
    name: lightserp_default
  lightserp-frontend:
    driver: bridge
```

### 4.2 `nginx/nginx.scale.conf` — Load Balancer Configuration

```nginx
# Nginx configuration for LightSerp horizontal scaling
# This file replaces/extends the existing nginx.conf for multi-instance deployments

upstream lightserp_instances {
    # Instances defined via Docker Compose scale
    # Docker Compose assigns sequential port mappings:
    #   lightserp-instance-1 → 3071
    #   lightserp-instance-2 → 3072
    #   etc.

    # Round-robin load balancing (default Nginx behavior)
    # No sticky sessions — all instances are stateless

    # Health-checked upstreams
    server lightserp-instance-1:3071 max_fails=3 fail_timeout=30s;
    server lightserp-instance-2:3071 max_fails=3 fail_timeout=30s;
    # Uncomment for additional instances:
    # server lightserp-instance-3:3071 max_fails=3 fail_timeout=30s;

    keepalive 32;
}

upstream lightserp_webui {
    server lightserp-instance-1:3070;
    # Add: server lightserp-instance-2:3070;  if webui is also scaled
}

server {
    listen 80;
    server_name lightserp.iacgenie.com;

    client_max_body_size 10m;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    # TODO (T-057): Content-Security-Policy
    # add_header Content-Security-Policy "default-src 'self';" always;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;
    gzip_min_length 1000;

    # ── API routes (auth, keys, usage, tools) ─────────────────────
    location /api/ {
        proxy_pass http://lightserp_instances/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-ID $request_id;

        # Proxy timeouts (scraping can be slow)
        proxy_connect_timeout 10s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;

        # Connection management
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }

    # ── MCP server (JSON-RPC over HTTP) ───────────────────────────
    location /mcp/ {
        proxy_pass http://lightserp_instances/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # MCP uses SSE/streaming — longer timeouts
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_buffering off;
    }

    # ── Web UI ────────────────────────────────────────────────────
    location / {
        proxy_pass http://lightserp_webui;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # ── Health check endpoint (internal monitoring) ───────────────
    location /nginx-health {
        access_log off;
        return 200 "ok\n";
        add_header Content-Type text/plain;
    }

    # ── Metrics endpoint (proxied to any instance) ────────────────
    location /metrics {
        proxy_pass http://lightserp_instances/metrics;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # ── Prometheus / Grafana ──────────────────────────────────────
    # (Handled by separate Grafana/Prometheus containers)
}
```

### 4.3 Environment Variable Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `SCALE_FACTOR` | `2` | Number of LightSerp instances to run |
| `INSTANCE_HTTP_PORT` | `3071` | Base HTTP port for the first instance |
| `RATE_LIMITER_MODE` | `redis` | `redis` or `memory` (fallback) |
| `RATE_LIMIT_MAX_POINTS` | `30` | Rate limit: max requests per duration |
| `RATE_LIMIT_DURATION` | `60` | Rate limit: duration in seconds |
| `RATE_LIMIT_PER_USER` | `true` | Enable per-user rate limiting |
| `DB_POOL_MAX` | `8` | PostgreSQL pool max connections (per instance) |
| `DB_POOL_IDLE_TIMEOUT` | `30000` | PostgreSQL pool idle timeout (ms) |
| `DB_POOL_CONNECTION_TIMEOUT` | `5000` | PostgreSQL pool connect timeout (ms) |
| `CACHE_LOCK_TTL` | `60` | Distributed cache lock TTL (seconds) |
| `NSQ_CONSUMER_MAX_IN_FLIGHT` | `10` | NSQ consumer max concurrent messages |

### 4.4 Scaling Operation

```bash
# Scale up to 3 instances
SCALE_FACTOR=3 INSTANCE_HTTP_PORT=3071 docker compose -f docker-compose.yml -f docker-compose.scale.yml up -d --scale lightserp=3

# Scale down to 1 instance
SCALE_FACTOR=1 docker compose -f docker-compose.yml -f docker-compose.scale.yml up -d --scale lightserp=1

# Check instance status
docker compose -f docker-compose.yml -f docker-compose.scale.yml ps

# View individual instance logs
docker compose -f docker-compose.yml -f docker-compose.scale.yml logs lightserp-instance-1
docker compose -f docker-compose.yml -f docker-compose.scale.yml logs lightserp-instance-2

# Health check all instances
curl http://localhost:80/health   # Nginx aggregates upstream health
```

---

## 5. T-050 Detailed Task Specification

### T-050 — Implement Horizontal Scaling Architecture

**Priority:** 🔵 P3 — Advanced
**Assignee:** DEV + ARCHITECT
**Category:** Scalability
**Effort:** 3 days
**Dependencies:** T-013 (Redis-backed rate limiter), T-020 (Health check with DB), T-010 (NSQ DLQ — impacts queue metrics)

### 5.1 Task Breakdown

| Sub-Task | Description | Owner | Effort | Dependencies |
|----------|-------------|-------|--------|-------------|
| **T-050-A** | Create `src/rate-limiter-redis.ts` — Redis-backed sliding window rate limiter | DEV | 0.5 day | — |
| **T-050-B** | Create `src/distributed-lock.ts` — Redis SETNX lock with TTL, retry, and deadlock detection | DEV | 0.5 day | — |
| **T-050-C** | Create `src/pubsub.ts` — Redis pub/sub subscriber for cross-instance cache invalidation | DEV | 0.5 day | — |
| **T-050-D** | Replace `RateLimiterMemory` in `server.ts` with `RateLimiterRedis` (dual-mode with fallback) | DEV | 0.5 day | T-050-A |
| **T-050-E** | Migrate `pendingResults` Map to Redis-backed store (Redis Stream) in `queue.ts` | DEV | 0.5 day | T-050-B |
| **T-050-F** | Migrate `queueMetrics` and `scrapeCacheMetrics` to Redis Hash; add `/metrics` endpoint | DEV | 0.5 day | T-050-C |
| **T-050-G** | Add distributed cache stampede protection to `cache.ts` | DEV | 0.5 day | T-050-B |
| **T-050-H** | Create `docker-compose.scale.yml`, `nginx/nginx.scale.conf`, update `.env.example` | DEVOPS | 1 day | T-050-A through T-050-G (but can be developed in parallel) |
| **T-050-I** | Integration test: spin 3 instances, verify rate limits are enforced across all | TEST | 1 day | T-050-A through T-050-H |
| **T-050-J** | Performance test: validate 2x throughput with 2 instances, measure latency impact | TEST | 1 day | T-050-I |
| **T-050-K** | Update `AGENTS.md` and architecture documentation | ARCHITECT | 0.5 day | All sub-tasks |

### 5.2 Acceptance Criteria

#### Functional Acceptance
- [ ] All rate limiting uses Redis-backed `RateLimiterRedis` — no `RateLimiterMemory` in production path
- [ ] Per-user and per-IP rate limits are consistent across 2+ running instances
- [ ] Pending scrape results from any instance are retrievable from any instance
- [ ] Cache stampede protection: concurrent cache misses produce exactly ONE fetch
- [ ] Metrics endpoint (`/metrics`) returns Prometheus-format metrics aggregating across all instances
- [ ] Nginx load balancer distributes traffic across instances using round-robin
- [ ] Unhealthy instances are automatically removed from the upstream pool by Nginx

#### Performance Acceptance
- [ ] 2 instances handle 2x the throughput of 1 instance (linear scaling within ±15%)
- [ ] P99 latency does not increase more than 10% when scaling from 1 to 2 instances
- [ ] PostgreSQL connection pool does not exceed configured max under full load
- [ ] Redis memory usage increases by less than 50MB per additional instance (overhead)

#### Operational Acceptance
- [ ] Single command (`docker compose -f ... up --scale lightserp=N`) scales to N instances
- [ ] Rollback to 1 instance works without data loss or configuration drift
- [ ] Health checks detect instance failures within 30 seconds
- [ ] All new modules have unit tests (>90% coverage)
- [ ] Integration test validates multi-instance behavior (T-050-I)

#### Non-Functional Acceptance
- [ ] No instance affinity — any instance can handle any request
- [ ] Database pool configuration documented with sizing formula (§2.4)
- [ ] Redis data model documented (§2.3.2)
- [ ] Nginx configuration supports dynamic addition of instances
- [ ] Rollback plan documented (§3.2)

### 5.3 Out of Scope (handled by other tasks)

| Task | Reason |
|------|--------|
| Kubernetes deployment | Different orchestration model; Docker Compose is sufficient for current target (single VM) |
| Auto-scaling based on metrics | Requires external autoscaler; beyond current scope |
| Database read replicas | Single PostgreSQL instance is adequate for current scale; future enhancement |
| Redis clustering | Single Redis instance suffices; Redis Sentinel for HA is separate |
| NSQ replication | NSQ lookupd already provides basic HA; not scaled independently |

---

## 6. Architectural Dependencies Map

```
                    T-050: Horizontal Scaling Architecture
                    │
                    ├── T-013: Redis-backed rate limiter  ──▶ T-050-A, T-050-D
                    ├── T-020: Health check with DB        ──▶ T-050-G (health-aware LB)
                    ├── T-010: NSQ DLQ                     ──▶ T-050-E (queue metrics)
                    ├── T-051: Cache stampede protection   ──▶ T-050-G (reuse lock module)
                    ├── T-012: DB connection pool config   ──▶ T-050-D (pool sizing)
                    ├── T-019: CI/CD                       ──▶ T-050-H (Docker builds)
                    └── T-054: OpenTelemetry business spans ─▶ T-050-F (metrics endpoint)

              Existing infrastructure (shared, no changes):
                    ├── PostgreSQL (single instance)
                    ├── Redis (single instance)
                    ├── NSQ (nsqd + nsqlookupd)
                    ├── SearXNG
                    └── a12n-server (Keycloak)

              New infrastructure (scale only):
                    ├── Nginx load balancer (T-050-H)
                    └── Multiple LightSerp instances (T-050-H)
```

---

## 7. Risk Assessment & Mitigations

| # | Risk | Probability | Impact | Mitigation |
|---|------|-------------|--------|------------|
| 1 | Redis connection exhaustion with multiple instances | Medium | High | Set `DB_POOL_MAX` per instance; use Redis connection pooling in ioredis (`maxRetriesPerRequest`, `lazyConnect`) |
| 2 | PostgreSQL connection pool overflow | High | Critical | Implement connection pool sizing formula (§2.4); use PgBouncer as connection pooler if needed |
| 3 | Nginx becoming a single point of failure | Medium | High | Deploy behind Cloudflare Tunnel (already in place); Nginx is lightweight and crashes auto-restart |
| 4 | Cache stampede with distributed locks causing timeout | Low | Medium | Set cache lock TTL to 60s; implement lock retry with exponential backoff |
| 5 | Redis latency increase under load from new keys | Medium | Medium | Monitor Redis memory; use Redis streams with `MAXLEN` trimming |
| 6 | Inconsistent metrics during migration | Medium | Low | Run dual-mode metrics during transition; compare values before promoting |
| 7 | Docker Compose `deploy.replicas` not supported on Compose V2 | Low | Low | Use `--scale` flag instead of `deploy.replicas`; use `docker compose up --scale` |
| 8 | Nginx upstream discovery fails with dynamic containers | Low | Medium | Use Docker DNS; ensure all instances are on the same Docker network |

---

## Appendix A: Redis-Specific Implementation Notes

### A.1 Rate Limiter Implementation (Redis-backed)

```typescript
// src/rate-limiter-redis.ts — key algorithms

/**
 * Sliding window counter using Redis.
 *
 * Key: ratelimit:{type}:{identifier}
 * Value: integer counter (INCR)
 * TTL: duration (EXPIRE)
 *
 * Algorithm:
 *   1. Redis INCR counter key
 *   2. If INCR == 1, set TTL = duration (first request in window)
 *   3. If INCR > limit, return error (rate exceeded)
 *   4. Otherwise, allow request
 *
 * This is a simple fixed-window counter. For true sliding window,
 * use Redis sorted sets (ZADD/ZREMRANGEBYSCORE) for precision.
 */

/**
 * Sliding window implementation using Redis sorted sets.
 * More accurate but higher Redis load.
 *
 * ZADD ratelimit:{type}:{identifier} {timestamp} {unique_id}
 * ZREMRANGEBYSCORE ratelimit:{type}:{identifier} 0 {now - duration}
 * ZCARD ratelimit:{type}:{identifier}
 */
```

### A.2 Distributed Lock Implementation

```typescript
// src/distributed-lock.ts — Redis SETNX with TTL

/**
 * Acquire a distributed lock using Redis SETNX with TTL.
 *
 * Key: lock:{resource}
 * Value: "instance-id:timestamp"
 * TTL: TTL seconds
 *
 * Algorithm:
 *   1. Try SETNX lock:{resource} {instance-id}:{timestamp}
 *   2. If SETNX succeeds (returns 1), lock acquired
 *   3. If SETNX fails (returns 0), lock held by another
 *   4. Check if lock is expired (TTL check)
 *   5. If expired, try SETNX again (race condition window exists)
 *   6. If not expired, wait and retry (backoff)
 */
```

### A.3 Pending Results via Redis Streams

```typescript
// src/queue.ts — pending results as Redis Stream

/**
 * When NSQ is available:
 *   - Producer publishes to NSQ, stores result in Redis after processing
 *   - Consumer waits on Redis Stream pending:results:{jobId}
 *   - Pub/Sub notification when result is ready
 *
 * When NSQ is unavailable:
 *   - Process synchronously, store in Redis Stream
 *   - Consumer waits on Redis Stream
 *   - Same code path regardless of NSQ status → consistency
 */
```

---

## Appendix B: File Changes Summary

| File | Change |
|------|--------|
| `src/rate-limiter-redis.ts` | **NEW** — Redis-backed sliding window rate limiter |
| `src/distributed-lock.ts` | **NEW** — Redis SETNX distributed lock |
| `src/pubsub.ts` | **NEW** — Redis pub/sub subscriber |
| `server.ts` | **MODIFY** — Replace `RateLimiterMemory` with `RateLimiterRedis` |
| `cache.ts` | **MODIFY** — Add distributed lock, add deprecation warning for memory cache |
| `queue.ts` | **MODIFY** — Replace `pendingResults` Map with Redis Stream |
| `queue.ts` | **MODIFY** — Move metrics to Redis Hash |
| `api-routes.ts` | **MODIFY** — Add `/metrics` endpoint (Prometheus format) |
| `docker-compose.scale.yml` | **NEW** — Multi-instance Docker Compose override |
| `nginx/nginx.scale.conf` | **NEW** — Nginx load balancer config |
| `.env.example` | **MODIFY** — Add new environment variables |
| `AGENTS.md` | **MODIFY** — Update architecture section |
| `ARCHITECTURE_TASK_SPEC.md` | **THIS FILE** |

---

*End of Architecture Task Specification*
