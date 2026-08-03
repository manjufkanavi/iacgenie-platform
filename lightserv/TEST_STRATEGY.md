# LightSerp — Comprehensive Test Strategy

> **Date:** 2026-07-18  
> **Author:** QA / Tester (Hermes Agent)  
> **Framework:** Jest + Supertest + ts-jest (native ESM)  
> **Target:** ≥ 60% code coverage (per PRODUCTION_READINESS_TASK_PLAN.md, T-018)  
> **Scope:** Backend (Node.js/Express), MCP Server, Queue, Scraping, Auth, SSRF

---

## 1. Test Architecture Overview

### Technology Stack
| Layer | Framework / Tool | Purpose |
|-------|-----------------|---------|
| Unit & Integration | Jest + ts-jest | Test runner, mocking, coverage |
| HTTP API | Supertest | Express endpoint testing |
| SSRF | Jest + node:dns mock | URL validation test cases |
| Load Testing | k6 or autocannon | Concurrent request performance |
| E2E | Playwright (recommended) or Jest+Supertest | Critical user journey validation |
| Security | OWASP ZAP (Docker) + custom test suites | OWASP Top 10 scan |

### Directory Structure (Proposed)
```
tests/
├── unit/                          # Unit tests for individual modules
│   ├── auth.test.ts
│   ├── password-hashing.test.ts
│   ├── ssrf.test.ts
│   ├── cache.test.ts
│   ├── queue.test.ts
│   ├── errors.test.ts
│   ├── search.test.ts
│   ├── scrape.test.ts
│   ├── email-service.test.ts
│   ├── health.test.ts
│   └── api-routes.test.ts
├── integration/                   # Supertest API endpoint tests
│   ├── auth-flow.test.ts
│   ├── search-api.test.ts
│   ├── scrape-api.test.ts
│   ├── mcp-proxy.test.ts
│   ├── api-keys.test.ts
│   └── health.test.ts
├── security/                      # Security-specific tests
│   ├── ssrf-bypass.test.ts
│   ├── input-validation.test.ts
│   ├── csrf-protection.test.ts
│   ├── jwt-manipulation.test.ts
│   └── xss-payloads.test.ts
├── load/                          # Load / performance tests
│   ├── search-concurrent.test.ts
│   ├── scrape-concurrent.test.ts
│   └── auth-endpoint-load.test.ts
├── e2e/                           # End-to-end user journey tests
│   ├── auth-to-deep-research.test.ts
│   ├── session-persistence.test.ts
│   └── offline-fallback.test.ts
├── fixtures/                      # Shared test data
│   ├── mock-users.json
│   ├── mock-search-results.json
│   └── mock-scrape-results.json
├── helpers/                       # Shared test utilities
│   ├── create-app.ts              # Builds Express app with mocks
│   ├── mock-suppress-logs.ts      # Suppress Pino during tests
│   └── seed-database.ts           # Seeds PostgreSQL for integration tests
└── setup.ts                       # Jest global setup (mock external services)
```

---

## 2. Unit Testing Plan

### 2.1 Module-by-Module Test Matrix

#### `src/ssrf.ts` — SSRF Protection
| Test ID | Description | Expected Behavior | Priority |
|---------|-------------|-------------------|----------|
| USR-001 | Validate valid HTTP URL | Returns SafeUrl with protocol, hostname, href | P0 |
| USR-002 | Validate valid HTTPS URL | Returns SafeUrl correctly | P0 |
| USR-003 | Reject `file://` URLs | Throws with "Scheme not allowed" | P0 |
| USR-004 | Reject `data:` URLs | Throws with "Scheme not allowed" | P0 |
| USR-005 | Reject `javascript:` URLs | Throws with "Scheme not allowed" | P0 |
| USR-006 | Reject `gopher://` URLs | Throws with "Scheme not allowed" | P0 |
| USR-007 | Reject `127.0.0.1` directly | Throws with "Private/reserved IP blocked" | P0 |
| USR-008 | Reject `10.0.0.1` | Throws with "Private/reserved IP blocked" | P0 |
| USR-009 | Reject `192.168.1.1` | Throws with "Private/reserved IP blocked" | P0 |
| USR-010 | Reject `172.16.0.1` | Throws with "Private/reserved IP blocked" | P0 |
| USR-011 | Reject `169.254.169.254` | Throws with "Private/reserved IP blocked" | P0 |
| USR-012 | Reject `::1` (IPv6 loopback) | Throws with "Private/reserved IP blocked" | P0 |
| USR-013 | Reject IPv6 mapped private IPs | Throws appropriately | P0 |
| USR-014 | Accept external public IP | Returns SafeUrl | P1 |
| USR-015 | Accept public domain with DNS resolution | Returns SafeUrl | P0 |
| USR-016 | Reject DNS rebinding to private IP | Throws with "DNS rebinding blocked" | P0 |
| USR-017 | Handle invalid URL strings | Throws "Invalid URL" | P1 |
| USR-018 | Handle DNS resolution failure | Throws "DNS resolution failed" | P1 |
| USR-019 | `validateUrlSync` with private IP | Throws appropriately | P1 |
| USR-020 | `validateUrlSync` with public domain | Returns SafeUrl | P1 |

**Test Pattern:** Property-based validation using a URL fixture table of valid/invalid cases.

#### `src/password-hashing.ts` — Argon2 Password Hashing
| Test ID | Description | Expected Behavior | Priority |
|---------|-------------|-------------------|----------|
| USR-021 | Hash returns argon2id format | Hash starts with `$argon2id$` | P0 |
| USR-022 | Verify correct password | Returns `true` | P0 |
| USR-023 | Verify wrong password | Returns `false` | P0 |
| USR-024 | Memory cost = 64 (current), time cost = 2, parallelism = 1 | Config matches task plan current state | P0 |
| USR-025 | `isArgon2Hash` detects argon2id | Returns `true` for valid argon2 hash | P1 |
| USR-026 | `isArgon2Hash` rejects SHA-256 | Returns `false` for 128-char hex | P1 |
| USR-027 | `isSha256Hash` detects old format | Returns `true` for 128-char hex | P1 |
| USR-028 | Hash is unique for same password (different salts) | Two hashes differ | P1 |
| USR-029 | Short password (1 char) | Hashes successfully (not rejected at hashing layer) | P1 |
| USR-030 | Long password (128+ chars) | Hashes successfully | P1 |
| USR-031 | Unicode password characters | Hashes and verifies correctly | P2 |
| USR-032 | Benchmark hash time < 300ms | Confirmed in CI (post T-004 fix) | P0 |

#### `src/errors.ts` — Error Hierarchy
| Test ID | Description | Expected Behavior | Priority |
|---------|-------------|-------------------|----------|
| USR-033 | AppError has correct statusCode | statusCode = 500 default | P1 |
| USR-034 | AppError has code = "INTERNAL_ERROR" | Code set correctly | P1 |
| USR-035 | AppError `toJson()` returns correct shape | `{ error, code, statusCode }` | P1 |
| USR-036 | ValidationError → 400 | `new ValidationError("msg").statusCode === 400` | P1 |
| USR-037 | AuthenticationError → 401 | Correct status code | P1 |
| USR-038 | AuthorizationError → 403 | Correct status code | P1 |
| USR-039 | NotFoundError → 404 | Correct status code | P1 |
| USR-040 | RateLimitError → 429 | Correct status code | P1 |
| USR-041 | ServiceUnavailableError → 503 | Correct status code | P1 |
| USR-042 | `formatMcpError` with AppError | Returns `{ text: userMessage }` | P1 |
| USR-043 | `formatMcpError` with generic Error | Returns truncated message | P1 |
| USR-044 | `formatMcpError` with non-Error | Returns stringified, truncated | P1 |
| USR-045 | `formatMcpError` multiline truncation | Only first line, max 200 chars | P1 |

#### `src/cache.ts` — Redis + Memory Fallback Cache
| Test ID | Description | Expected Behavior | Priority |
|---------|-------------|-------------------|----------|
| USR-046 | Set and get simple key-value | Store and retrieve correctly | P0 |
| USR-047 | Get non-existent key | Returns `null` / `undefined` | P0 |
| USR-048 | TTL enforcement on scrape cache | Result expires after TTL | P0 |
| USR-049 | Memory fallback when Redis unavailable | `getRedisCache` returns from memory | P0 |
| USR-050 | `deleteRedisCache` removes key | Key no longer retrievable | P1 |
| USR-051 | `getCacheMetrics` returns correct shape | Includes `redisConnected`, `memorySize`, `hitRate` | P1 |
| USR-052 | Large value caching (>1MB) | Caches without error | P2 |
| USR-053 | JSON serialization of complex objects | Search results serialize/deserialize correctly | P0 |

#### `src/queue.ts` — NSQ Queue
| Test ID | Description | Expected Behavior | Priority |
|---------|-------------|-------------------|----------|
| USR-054 | `initializeQueue` succeeds with NSQ | Sets up writer + reader | P0 |
| USR-055 | `initializeQueue` handles NSQ unavailable | Logs warning, sets writer = null | P0 |
| USR-056 | `publishScrapeJob` succeeds | Job published to NSQ | P0 |
| USR-057 | `publishScrapeJob` when NSQ unavailable | Falls back to HTTP or silently returns | P0 |
| USR-058 | `registerConsumer` registers handler | Consumer starts listening | P0 |
| USR-059 | Consumer handles successful job | Stores result in Redis, msg.finish() | P0 |
| USR-060 | Consumer handles failed job | Requeues with exponential backoff, increments retry count | P0 |
| USR-061 | `getScrapeResult` retrieves result | Returns ScrapeResult from Redis | P0 |
| USR-062 | `getScrapeResult` timeout | Rejects after timeout period | P0 |
| USR-063 | `getQueueMetrics` returns correct counts | jobsPublished, jobsProcessed, jobsFailed accurate | P1 |
| USR-064 | `shutdownQueue` cleans up resources | No memory leaks, timers cleared | P1 |
| USR-065 | `processScrapeJobSync` when NSQ available | Publishes to NSQ, waits for async result | P1 |
| USR-066 | `processScrapeJobSync` when NSQ unavailable | Processes locally synchronously | P1 |
| USR-067 | Double `registerConsumer` protection | Second call warns and skips | P1 |
| USR-068 | Exponential backoff calculation | delay = min(1000 × 2^n, 30000) | P0 |

#### `src/api-routes.ts` — API Route Handlers
| Test ID | Description | Expected Behavior | Priority |
|---------|-------------|-------------------|----------|
| USR-069 | `readBody` resolves with body string | Returns concatenated chunks | P1 |
| USR-070 | `readBody` rejects on stream error | Rejects with error | P1 |
| USR-071 | `jsonResponse` sets correct headers | Content-Type: application/json, status code | P1 |
| USR-072 | `attachReqId` generates UUID | Returns new UUID if none in request | P1 |
| USR-073 | `attachReqId` preserves existing | Returns existing X-Request-Id | P1 |

#### `src/search.ts` — SearXNG Search
| Test ID | Description | Expected Behavior | Priority |
|---------|-------------|-------------------|----------|
| USR-074 | `search` returns results from SearXNG | Array of SearchResult objects | P0 |
| USR-075 | `search` returns cached results | Returns from cache, no SearXNG call | P0 |
| USR-076 | `search` applies limit | Returns at most `limit` results | P0 |
| USR-077 | `search` on SearXNG failure | Throws "Search failed" | P0 |
| USR-078 | `search` with empty query | Handles gracefully | P1 |
| USR-079 | `search` timeout on slow SearXNG | Throws after 15s timeout | P1 |
| USR-080 | Search result parsing | Correctly extracts title, url, snippet, engine | P0 |

#### `src/lightpanda-scrape.ts` — LightPanda MCP Scraper
| Test ID | Description | Expected Behavior | Priority |
|---------|-------------|-------------------|----------|
| USR-081 | `scrape` parses markdown response | Extracts title and content from JSON-RPC | P0 |
| USR-082 | `scrape` handles timeout | Returns `null` after timeout | P0 |
| USR-083 | `scrape` handles spawn error | Returns `null` with error logged | P0 |
| USR-084 | Concurrency cap enforced | No more than MAX_CONCURRENT_SCRAPE active | P1 |
| USR-085 | `isAvailable` returns true | Healthy LightPanda → `true` | P1 |
| USR-086 | `isAvailable` returns false | Unhealthy/lightpanda missing → `false` | P1 |
| USR-087 | `getMetrics` returns correct shape | Contains binary path, timeout, active | P1 |

#### `src/health.ts` — Health Check
| Test ID | Description | Expected Behavior | Priority |
|---------|-------------|-------------------|----------|
| USR-088 | All dependencies healthy | Returns `{ status: 'healthy' }` | P0 |
| USR-089 | Cache unavailable | Returns `{ status: 'degraded' }` | P0 |
| USR-090 | Any dependency error | Returns `{ status: 'unhealthy' }` | P0 |
| USR-091 | Response includes timestamp, version, uptime | All fields present | P1 |

#### `src/auth-config.ts` — Auth Configuration
| Test ID | Description | Expected Behavior | Priority |
|---------|-------------|-------------------|----------|
| USR-092 | `config.JWT_SECRET` reads env var | Returns value from `JWT_SECRET` env | P1 |
| USR-093 | `config.KEYCLOAK_URL` has fallback | Returns `'http://localhost:8080'` if unset | P1 |
| USR-094 | `isJwtConfigured` when set | Returns `true` | P1 |
| USR-095 | `isJwtConfigured` when empty | Returns `false` | P1 |
| USR-096 | `isKeycloakConfigured` when secret present | Returns `true` | P1 |

---

### 2.2 Unit Test Patterns

All unit tests follow the **AAA** pattern: **Arrange → Act → Assert**.

```typescript
// Example: SSRF validateUrl test
import { validateUrl } from '../src/ssrf.js';

describe('validateUrl', () => {
  describe('scheme validation', () => {
    it('rejects file:// URLs', async () => {
      await expect(validateUrl('file:///etc/passwd')).rejects.toThrow('Scheme not allowed');
    });
    it('rejects data: URLs', async () => {
      await expect(validateUrl('data:text/html,<script>alert(1)</script>')).rejects.toThrow('Scheme not allowed');
    });
    it('accepts http:// URLs', async () => {
      const result = await validateUrl('http://example.com/page');
      expect(result.protocol).toBe('http:');
    });
  });

  describe('IP validation', () => {
    it('rejects 127.0.0.1', async () => {
      await expect(validateUrl('http://127.0.0.1:8080')).rejects.toThrow('Private/reserved IP blocked');
    });
    it('rejects 169.254.169.254', async () => {
      await expect(validateUrl('http://169.254.169.254/latest/meta-data/')).rejects.toThrow('Private/reserved IP blocked');
    });
  });
});
```

**Mocking strategy for unit tests:**
- `node:net` / `node:dns` → Mock with Jest manual mocks
- `ioredis` → Mock with Jest `jest.mock('ioredis')`
- `nsqjs` → Mock with Jest `jest.mock('nsqjs')`
- `argon2` → Mock with Jest `jest.mock('argon2')`
- `jsonwebtoken` → Mock with Jest `jest.mock('jsonwebtoken')`
- `pg` → Mock with Jest `jest.mock('pg')`
- External HTTP (SearXNG, LightPanda, Keycloak) → Mock with `nock` or `jest.spyOn(axios, 'get')`

---

## 3. Integration Testing Plan

### 3.1 API Endpoint Test Matrix (Supertest)

All integration tests use **Supertest** against a real Express app instance with mocked dependencies (SearXNG, LightPanda, NSQ, Redis, PostgreSQL).

#### Authentication Flow Tests (`tests/integration/auth-flow.test.ts`)

| Test ID | Endpoint | Scenario | Mocks | Expected | Priority |
|---------|----------|----------|-------|----------|----------|
| INT-001 | POST `/api/register` | Valid registration | Keycloak Admin API, SMTP | 201, userId, requiresVerification | P0 |
| INT-002 | POST `/api/register` | Duplicate email | Keycloak Admin API | 400, "already exists" | P0 |
| INT-003 | POST `/api/register` | Invalid email format | — | 400, validation error | P0 |
| INT-004 | POST `/api/register` | Password < 8 chars | — | 400, validation error | P0 |
| INT-005 | POST `/api/register` | Oversized email (1000 chars) | — | 400, validation error | P0 |
| INT-006 | POST `/api/login` | Valid login | Keycloak introspection | 200, userId + token | P0 |
| INT-007 | POST `/api/login` | Wrong password | Argon2 verify | 401, error message | P0 |
| INT-008 | POST `/api/login` | Non-existent user | — | 401, error message | P0 |
| INT-009 | POST `/api/login` | Empty body | — | 400, validation error | P0 |
| INT-010 | GET `/api/verify-email?token=xxx` | Valid token | JWT verify, DB | 200, verified | P0 |
| INT-011 | GET `/api/verify-email?token=invalid` | Invalid JWT | — | 400, error | P0 |
| INT-012 | GET `/api/verify-email` | Missing token | — | 400, "token required" | P0 |
| INT-013 | POST `/api/password-reset` | Valid email | SMTP send | 200, "link sent" (always) | P0 |
| INT-014 | POST `/api/password-reset` | Non-existent email | — | 200, "link sent" (no enumeration) | P0 |
| INT-015 | POST `/api/password-reset` | Invalid email format | — | 400, validation error | P1 |
| INT-016 | POST `/api/reset-password` | Valid reset | JWT verify, argon2 | 200, "password reset" | P0 |
| INT-017 | POST `/api/reset-password` | Expired token | JWT verify | 400, "expired" | P0 |
| INT-018 | POST `/api/change-password` | Authenticated, valid | JWT verify, argon2 | 200, "password changed" | P0 |
| INT-019 | POST `/api/change-password` | Unauthenticated | — | 401, "invalid token" | P0 |
| INT-020 | GET `/api/api-keys` | Authenticated | DB query | 200, { keys: [] } | P0 |
| INT-021 | GET `/api/api-keys` | Unauthenticated | — | 401 | P0 |
| INT-022 | POST `/api/api-keys` | Create key | argon2 hash, DB | 201, { id, key, prefix } | P0 |
| INT-023 | DELETE `/api/api-keys/:keyId` | Revoke key | DB update | 200, { success: true } | P0 |
| INT-024 | POST `/api/token-gen` | Generate JWT | JWT sign | 200, { token } | P1 |
| INT-025 | POST `/api/verify-email` | URL parameter injection | — | Error handled, no XSS | P0 |

#### Search API Tests (`tests/integration/search-api.test.ts`)

| Test ID | Endpoint | Scenario | Mocks | Expected | Priority |
|---------|----------|----------|-------|----------|----------|
| INT-026 | POST `/api/search` | Valid query | SearXNG mock | 200, search results | P0 |
| INT-027 | POST `/api/search` | Empty query | — | 400 | P1 |
| INT-028 | POST `/api/search` | Query > 500 chars | — | 400, "too long" | P1 |
| INT-029 | POST `/api/search` | SearXNG unavailable | SearXNG mock → 503 | 503, "service unavailable" | P0 |
| INT-030 | POST `/api/search` | Cached result | Redis → cached data | 200, cached results | P0 |
| INT-031 | POST `/api/search` | SSRF attempt in URL param | SSRF validator | 400, "URL blocked" | P0 |
| INT-032 | POST `/api/search` | Rate limited | Rate limiter → full | 429, "rate limited" | P1 |

#### Scrape API Tests (`tests/integration/scrape-api.test.ts`)

| Test ID | Endpoint | Scenario | Mocks | Expected | Priority |
|---------|----------|----------|-------|----------|----------|
| INT-033 | POST `/api/scrape` | Valid URL | LightPanda mock | 200, { title, content } | P0 |
| INT-034 | POST `/api/scrape` | SSRF — localhost URL | SSRF validator | 400, "IP blocked" | P0 |
| INT-035 | POST `/api/scrape` | File URL | SSRF validator | 400, "scheme not allowed" | P0 |
| INT-036 | POST `/api/scrape` | Oversized URL (>2048 chars) | URL validator | 400, "URL too long" | P0 |
| INT-037 | POST `/api/scrape` | LightPanda timeout | LightPanda mock → timeout | 504 or 500, error | P0 |
| INT-038 | POST `/api/scrape` | Async job | NSQ mock, Redis mock | 202, jobId, poll for result | P1 |
| INT-039 | GET `/api/scrape/result/:jobId` | Result available | Redis mock | 200, scrape result | P1 |
| INT-040 | GET `/api/scrape/result/:jobId` | Result not ready | Redis mock → null | 200, { status: "processing" } | P1 |
| INT-041 | GET `/api/scrape/result/:jobId` | Result expired | Redis mock → expired | 404, "not found" | P1 |

#### MCP Proxy Tests (`tests/integration/mcp-proxy.test.ts`)

| Test ID | Endpoint | Scenario | Mocks | Expected | Priority |
|---------|----------|----------|-------|----------|----------|
| INT-042 | POST `/api/mcp/proxy` | Valid MCP request | MCP server mock | 200, MCP response | P0 |
| INT-043 | POST `/api/mcp/proxy` | Unauthenticated | — | 401 | P0 |
| INT-044 | POST `/api/mcp/proxy` | API key auth | API key validate | 200, MCP response | P1 |
| INT-045 | POST `/api/mcp/proxy` | MCP server down | MCP mock → ECONNREFUSED | 502, error | P1 |

#### Health Check Tests (`tests/integration/health.test.ts`)

| Test ID | Endpoint | Scenario | Mocks | Expected | Priority |
|---------|----------|----------|-------|----------|----------|
| INT-046 | GET `/health` | All healthy | All deps connected | 200, status=healthy | P0 |
| INT-047 | GET `/health` | Redis disconnected | Redis mock → fail | 200, status=degraded | P0 |
| INT-048 | GET `/health` | NSQ disconnected | NSQ mock → fail | 200, status=degraded | P0 |
| INT-049 | GET `/ready` | Not ready | Dependencies failing | 503 | P0 |
| INT-050 | GET `/ready` | Ready | All dependencies up | 200 | P0 |

---

### 3.2 Supertest Test Template

```typescript
import request from 'supertest';
import { app } from '../helpers/create-app';

describe('Authentication API Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('POST /api/register', () => {
    it('registers a new user and returns 201', async () => {
      (jwt.sign as jest.Mock).mockReturnValue('mock-jwt-token');
      (redisClient.set as jest.Mock).mockResolvedValue('OK');

      const res = await request(app)
        .post('/api/register')
        .send({ email: 'user@example.com', password: 'SecurePass123', username: 'testuser' });

      expect(res.status).toBe(201);
      expect(res.body).toHaveProperty('userId');
      expect(res.body).toHaveProperty('requiresVerification', true);
    });

    it('rejects invalid email', async () => {
      const res = await request(app)
        .post('/api/register')
        .send({ email: 'not-an-email', password: 'SecurePass123' });

      expect(res.status).toBe(400);
      expect(res.body).toHaveProperty('error');
    });
  });
});
```

---

## 4. Security Testing Plan

### 4.1 OWASP Top 10 Test Cases for LightSerp

#### A1:2021 — Broken Access Control

| Test ID | Test | Method | Priority |
|---------|------|--------|----------|
| SEC-001 | Unauthenticated user accesses `/api/api-keys` | GET without Authorization | P0 |
| SEC-002 | User A accesses User B's API keys | GET with User A's token for User B's resource | P0 |
| SEC-003 | API key with scope 'search' attempts 'scrape' | POST /api/scrape with search-only key | P0 |
| SEC-004 | Direct token reuse from different user agent | Same token, different IP | P1 |

#### A2:2021 — Cryptographic Failures

| Test ID | Test | Method | Priority |
|---------|------|--------|----------|
| SEC-005 | Verify Argon2 parameters (post-T-004) | `memoryCost=65536, timeCost=3, parallelism=4` | P0 |
| SEC-006 | Verify JWT signed with HS256 + valid secret | Decode and verify | P0 |
| SEC-007 | Verify JWT not signed with "none" algorithm | Try alg=none attack | P0 |
| SEC-008 | Verify tokens not stored in localStorage (post-T-003) | Audit code for localStorage usage | P0 |
| SEC-009 | Verify refresh tokens in HttpOnly cookies | Check Set-Cookie flags | P0 |

#### A3:2021 — Injection (SSRF + URL Injection)

| Test ID | Test | Method | Priority |
|---------|------|--------|----------|
| SEC-010 | SSRF via localhost URL | POST /api/scrape with `http://127.0.0.1:6379` | P0 |
| SEC-011 | SSRF via private IP | POST /api/scrape with `http://10.0.0.1` | P0 |
| SEC-012 | SSRF via cloud metadata | POST /api/scrape with `http://169.254.169.254` | P0 |
| SEC-013 | SSRF via DNS rebinding | Mock DNS to resolve to private IP | P0 |
| SEC-014 | SSRF via IPv6 mapping | `http://[::ffff:127.0.0.1]` | P0 |
| SEC-015 | URL injection via callback parameter | `http://evil.com?redirect=http://127.0.0.1` | P0 |
| SEC-016 | File protocol bypass | `file:///etc/passwd` | P0 |
| SEC-017 | Data URL injection | `data:text/html,<script>alert(1)</script>` | P0 |
| SEC-018 | JavaScript URL injection | `javascript:alert(1)` | P0 |
| SEC-019 | SQL injection in search query | `' OR 1=1 --` | P1 |

#### A4:2021 — Insecure Design

| Test ID | Test | Method | Priority |
|---------|------|--------|----------|
| SEC-020 | OAuth state not validated (pre-T-002) | Callback without state → CSRF | P0 |
| SEC-021 | No brute-force on login (pre-T-005) | 100 login attempts → account accessible | P0 |
| SEC-022 | No CSRF tokens on state-changing endpoints | POST without CSRF header → succeeds | P0 |
| SEC-023 | Rate limit bypass via different IPs | Each IP bypasses per-IP rate limit | P1 |

#### A5:2021 — Security Misconfiguration

| Test ID | Test | Method | Priority |
|---------|------|--------|----------|
| SEC-024 | Default credentials in a12n-config.yaml | Read and check | P0 |
| SEC-025 | Missing security headers | Check response headers | P0 |
| SEC-026 | Debug endpoints exposed in production | Check /debug, /debug/pprof | P1 |
| SEC-027 | CORS wildcard (*) in production | Check Access-Control-Allow-Origin | P0 |

#### A6:2021 — Vulnerable and Outdated Components

| Test ID | Test | Method | Priority |
|---------|------|--------|----------|
| SEC-028 | Run `npm audit` — zero critical/high | Run audit command | P0 |
| SEC-029 | Check dependency versions against CVE database | Automated scan | P1 |

#### A7:2021 — Authentication Failures

| Test ID | Test | Method | Priority |
|---------|------|--------|----------|
| SEC-030 | Brute-force: 5 failed logins in 15 min | Send 5+ failed login requests | P0 |
| SEC-031 | Brute-force: account lockout after threshold | 6th attempt → 429 | P0 |
| SEC-032 | Brute-force: lockout duration enforcement | Try during lockout window | P0 |
| SEC-033 | Brute-force: lockout reset after 15 min | Wait, then retry | P0 |
| SEC-034 | OAuth callback CSRF (no state validation) | Redirect to callback with forged state | P0 |
| SEC-035 | JWT token manipulation | Modify claims, verify rejection | P0 |
| SEC-036 | Email enumeration via login | Login with existing vs. non-existing email | P0 |
| SEC-037 | Password reset email enumeration protection | Reset for non-existent email returns same response | P0 |

#### A8:2021 — Software and Data Integrity Failures

| Test ID | Test | Method | Priority |
|---------|------|--------|----------|
| SEC-038 | Upgrade hash after login (SHA→Argon2) | Login with SHA-256 password, verify rehash | P1 |
| SEC-039 | API key is hashed, not stored in plaintext | Query DB for API keys | P1 |
| SEC-040 | No hardcoded credentials in codebase | Search for "change-me", "admin", "password123" | P0 |

#### A9:2021 — Security Logging and Monitoring Failures

| Test ID | Test | Method | Priority |
|---------|------|--------|----------|
| SEC-041 | Failed login attempts logged | Attempt login, check logs | P0 |
| SEC-042 | SSRF attempt logged | SSRF request, check logs | P0 |
| SEC-043 | Rate limit violation logged | Trigger rate limit, check logs | P1 |

#### A10:2021 — Server-Side Request Forgery via MCP Proxy

| Test ID | Test | Method | Priority |
|---------|------|--------|----------|
| SEC-044 | MCP proxy SSRF via mcp_port parameter | `?mcp_port=6379` to reach Redis | P0 |
| SEC-045 | MCP proxy restricted to localhost | Only 127.0.0.1 accessible | P0 |

---

### 4.2 SSRF Bypass Test Suite

```typescript
// tests/security/ssrf-bypass.test.ts
import { validateUrl } from '../../src/ssrf.js';

const SSRF_ATTACK_VECTORS = [
  // Direct IP addresses
  { url: 'http://127.0.0.1/', expectBlocked: true, name: 'loopback IPv4' },
  { url: 'http://10.0.0.1/', expectBlocked: true, name: 'private 10/8' },
  { url: 'http://172.16.0.1/', expectBlocked: true, name: 'private 172.16/12' },
  { url: 'http://192.168.1.1/', expectBlocked: true, name: 'private 192.168/16' },
  { url: 'http://169.254.169.254/', expectBlocked: true, name: 'cloud metadata' },
  { url: 'http://0.0.0.0/', expectBlocked: true, name: 'wildcard IPv4' },

  // IPv6 addresses
  { url: 'http://[::1]/', expectBlocked: true, name: 'loopback IPv6' },
  { url: 'http://[::ffff:127.0.0.1]/', expectBlocked: true, name: 'IPv4-mapped IPv6 loopback' },
  { url: 'http://[fc00::1]/', expectBlocked: true, name: 'IPv6 unique local' },

  // Protocol abuse
  { url: 'file:///etc/passwd', expectBlocked: true, name: 'file protocol' },
  { url: 'data:text/html,<script>alert(1)</script>', expectBlocked: true, name: 'data protocol' },
  { url: 'javascript:alert(1)', expectBlocked: true, name: 'javascript protocol' },

  // URL encoding tricks
  { url: 'http://127.0.0.1.nip.io/', expectBlocked: false, name: 'nip.io (DNS resolves to 127.0.0.1)' },

  // Valid URLs that should pass
  { url: 'http://example.com/', expectBlocked: false, name: 'valid HTTP' },
  { url: 'https://example.com/path?q=value', expectBlocked: false, name: 'valid HTTPS' },
];

describe('SSRF Bypass Test Suite', () => {
  for (const { url, expectBlocked, name } of SSRF_ATTACK_VECTORS) {
    it(`${name}: ${url}`, async () => {
      if (expectBlocked) {
        await expect(validateUrl(url)).rejects.toThrow();
      } else {
        await expect(validateUrl(url)).resolves.toBeDefined();
      }
    });
  }
});
```

---

## 5. Load Testing Plan

### 5.1 Load Testing Tools
- **Primary:** `autocannon` (lightweight, CLI-based, built on ekvantage)
- **Advanced:** `k6` for multi-stage ramp-up tests and detailed metrics
- **Metrics tracked:** p50/p95/p99 latency, error rate, throughput (req/s), concurrent connections

### 5.2 Load Test Scenarios

#### Scenario LDT-001: Search Endpoint — Concurrent Load
| Parameter | Value |
|-----------|-------|
| Target | `POST /api/search` |
| Duration | 60 seconds |
| Concurrency | 10, 25, 50, 100 |
| Load pattern | Steady-state |
| Expected | p99 < 2s, error rate < 1% |
| Mocks | SearXNG → 50ms response time |

```bash
# autocannon command
autocannon -c 50 -d 60 -m POST -b '{"query":"test"}' http://localhost:3000/api/search -H "Authorization: Bearer test-token"
```

#### Scenario LDT-002: Scrape Endpoint — Burst Load
| Parameter | Value |
|-----------|-------|
| Target | `POST /api/scrape` |
| Duration | 30 seconds |
| Concurrency | 5, 10, 20 |
| Load pattern | Burst (all at once) |
| Expected | p99 < 30s, errors only from concurrency cap |
| Mocks | LightPanda → 500ms mock response |

#### Scenario LDT-003: Auth Endpoint — Brute-Force Simulation
| Parameter | Value |
|-----------|-------|
| Target | `POST /api/login` |
| Duration | 60 seconds |
| Concurrency | 10 |
| Requests | 100 login attempts with wrong password |
| Expected | Rate limiting kicks in, 429 after 5 attempts/IP |

#### Scenario LDT-004: Mixed Traffic (Realistic)
| Parameter | Value |
|-----------|-------|
| Mix | 60% search, 25% scrape, 15% health/auth |
| Duration | 120 seconds |
| Concurrency | 25 |
| Expected | Overall error rate < 0.1%, p99 < 3s |

#### Scenario LDT-005: Cache Stress Test
| Parameter | Value |
|-----------|-------|
| Target | `POST /api/search` (same query repeated) |
| Duration | 30 seconds |
| Concurrency | 100 |
| Expected | > 90% cache hit rate, response < 10ms |

#### Scenario LDT-006: Queue Throughput
| Parameter | Value |
|-----------|-------|
| Target | `POST /api/scrape` (async mode) |
| Duration | 60 seconds |
| Concurrency | 50 |
| Expected | All jobs processed, no DLQ overflow |

### 5.3 Load Test Metrics Thresholds

| Metric | Threshold | Fail Condition |
|--------|-----------|----------------|
| p50 latency | < 500ms | > 1s |
| p95 latency | < 2s | > 5s |
| p99 latency | < 3s | > 10s |
| Error rate | < 0.1% | > 1% |
| Throughput | > 50 req/s (search) | < 20 req/s |
| Memory growth | < 10% over test | > 25% |

---

## 6. E2E Testing Plan

### 6.1 Critical User Journeys

#### Journey E2E-001: Auth → Search → Scrape → Deep Research

```
1. User registers (POST /api/register)
   ↓
2. User verifies email (GET /api/verify-email?token=xxx)
   ↓
3. User logs in (POST /api/login) — receives token
   ↓
4. User searches (POST /api/search) — receives results
   ↓
5. User scrapes a result URL (POST /api/scrape) — receives content
   ↓
6. User triggers deep-research (POST /api/deep-research?query=xxx) — async job
   ↓
7. User polls for result (GET /api/deep-research/status/:jobId) — receives final report
```

| Step | Endpoint | Assertion | Priority |
|------|----------|-----------|----------|
| 1 | POST /api/register | 201, user created | P0 |
| 2 | GET /api/verify-email | 200, verified | P0 |
| 3 | POST /api/login | 200, token received | P0 |
| 4 | POST /api/search | 200, results array | P0 |
| 5 | POST /api/scrape | 200, content extracted | P0 |
| 6 | POST /api/deep-research | 202, job ID returned | P0 |
| 7 | GET /api/deep-research/status | 200, report complete | P1 |

#### Journey E2E-002: API Key Management

```
1. User registers and logs in
   ↓
2. User creates API key (POST /api/api-keys)
   ↓
3. User lists API keys (GET /api/api-keys) — key visible
   ↓
4. User makes search with API key (POST /api/search -H "x-api-key: xxx")
   ↓
5. User revokes key (DELETE /api/api-keys/:keyId)
   ↓
6. User tries to use revoked key — 401
```

| Step | Endpoint | Assertion | Priority |
|------|----------|-----------|----------|
| 1 | Register + Login | 200, token | P0 |
| 2 | POST /api/api-keys | 201, key returned | P0 |
| 3 | GET /api/api-keys | 200, key in list | P0 |
| 4 | POST /api/search with key | 200, results | P0 |
| 5 | DELETE /api/api-keys/:id | 200, revoked | P0 |
| 6 | POST /api/search with revoked key | 401 | P0 |

#### Journey E2E-003: Token Migration (localStorage → Cookie Auth)

```
Pre-migration:
1. Login returns token
2. Token stored in localStorage (old behavior)

Post-migration:
3. Login returns token in HttpOnly cookie
4. API calls use cookie automatically
5. Token refresh rotates cookie
```

| Step | Assertion | Priority |
|------|-----------|----------|
| Set Cookie: HttpOnly, Secure, SameSite=Strict | Cookie flags correct | P0 |
| Cookie not accessible via JavaScript | `document.cookie` does not show token | P0 |
| XHR/fetch sends cookie automatically | Cookie included in requests | P0 |
| Token refresh updates cookie | New cookie value on refresh | P1 |
| Token expiry clears cookie | Cookie absent after expiry | P1 |

#### Journey E2E-004: Error Handling & Recovery

```
1. User is logged in
2. API server returns 500 on search
   ↓
3. User sees error message (not crash)
   ↓
4. User retries — succeeds
   ↓
5. Circuit breaker: rapid failures → fallback response
   ↓
6. After cooldown, service resumes normally
```

| Step | Assertion | Priority |
|------|-----------|----------|
| 500 response on search | 500, error message shown | P0 |
| Retry after 500 | Success on retry | P0 |
| Circuit breaker triggers | 503 after threshold failures | P1 |
| Circuit breaker half-open | 1 probe request after 30s | P1 |
| Graceful recovery | Service resumes after fix | P1 |

---

### 6.2 E2E Test Template (Supertest-based)

```typescript
// tests/e2e/auth-to-deep-research.test.ts
import request from 'supertest';
import { app } from '../helpers/create-app';

describe('E2E: Full User Journey', () => {
  const email = `e2e-user-${Date.now()}@example.com`;
  const password = 'SecurePass123!';

  let authToken: string;

  beforeAll(async () => {
    jest.clearAllMocks();
  });

  it('1. registers a new user', async () => {
    const res = await request(app)
      .post('/api/register')
      .send({ email, password, username: 'e2euser' });
    expect(res.status).toBe(201);
    expect(res.body).toHaveProperty('userId');
  });

  it('2. logs in and receives token', async () => {
    const res = await request(app)
      .post('/api/login')
      .send({ email, password });
    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty('token');
    authToken = res.body.token;
  });

  it('3. performs a search', async () => {
    const res = await request(app)
      .post('/api/search')
      .set('Authorization', `Bearer ${authToken}`)
      .send({ query: 'test search query' });
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body.results)).toBe(true);
  });

  it('4. scrapes a URL', async () => {
    const res = await request(app)
      .post('/api/scrape')
      .set('Authorization', `Bearer ${authToken}`)
      .send({ url: 'http://example.com' });
    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty('content');
    expect(res.body).toHaveProperty('title');
  });

  it('5. creates an API key', async () => {
    const res = await request(app)
      .post('/api/api-keys')
      .set('Authorization', `Bearer ${authToken}`)
      .send({ name: 'E2E Test Key' });
    expect(res.status).toBe(201);
    expect(res.body).toHaveProperty('key');
  });
});
```

---

## 7. CI Pipeline Test Gates

### 7.1 Gate Definitions

All gates must **PASS** before a PR can be merged to `main`/`master`. Branch protection rules enforce these gates.

| Gate # | Gate Name | Trigger | Pass Criteria | Run Time Target |
|--------|-----------|---------|---------------|-----------------|
| G-01 | Lint | All | `npm run lint` exits 0, zero warnings | < 15s |
| G-02 | Type Check | All | `tsc --noEmit` exits 0, zero errors | < 30s |
| G-03 | Unit Tests (SSRF) | All | All SSRF test cases pass (USR-001 to USR-020) | < 10s |
| G-04 | Unit Tests (Auth) | All | All auth/password tests pass (USR-021 to USR-032, USR-033 to USR-045) | < 20s |
| G-05 | Unit Tests (Core) | All | Cache, queue, errors, search tests pass (USR-046 to USR-096) | < 15s |
| G-06 | Integration Tests | All | All Supertest API tests pass (INT-001 to INT-050) | < 60s |
| G-07 | Security Tests | All | OWASP test cases pass (SEC-001 to SEC-045) | < 30s |
| G-08 | Load Test (Smoke) | Merge to main | LDT-001 (10 concurrent) passes all thresholds | < 90s |
| G-09 | Coverage Threshold | All | ≥ 60% overall coverage; ≥ 80% for auth/ssrf/queue | < 30s |
| G-10 | Build | All (post-merge to main) | `tsc` compiles to `dist/` without errors | < 60s |

### 7.2 Test Execution Order in CI

```yaml
# .github/workflows/ci.yml (proposed)
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres: { image: postgres:16, env: { POSTGRES_DB: lightserp_test } }
      redis: { image: redis:7 }
      nsqd: { image: nsqio/nsq }
      searxng: { image: searxng/searxng }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: npm ci  # no dev deps by default
      - run: npm run lint          # G-01
      - run: npx tsc --noEmit      # G-02
      - run: npx jest --testPathPattern=tests/unit --coverage --ci  # G-03 through G-05
      - run: npx jest --testPathPattern=tests/integration --ci   # G-06
      - run: npx jest --testPathPattern=tests/security --ci       # G-07
      - name: Coverage gate
        run: npx jest --coverage --coverageThreshold='{"global":{"branches":60,"functions":60,"lines":60,"statements":60}}'  # G-09
  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - run: npm ci && npm run build  # G-10
```

### 7.3 Pre-Merge Checklist

| Requirement | Status |
|-------------|--------|
| All 10 CI gates passing | ☐ |
| Test coverage ≥ 60% overall | ☐ |
| Zero unit test regressions | ☐ |
| Zero SSRF bypass successful | ☐ |
| Zero auth bypass successful | ☐ |
| Lint clean | ☐ |
| TypeScript compile clean | ☐ |
| No new `any` types introduced | ☐ |
| No hardcoded secrets in tests | ☐ |
| Test files follow naming convention (`*.test.ts`) | ☐ |
| Test setup uses isolated test database | ☐ |
| Seed data cleaned up after tests | ☐ |

---

## 8. Specific Test Cases — Detailed Scenarios

### 8.1 Authentication Flows

#### Login Flow
| Test ID | Description | Request | Expected |
|---------|-------------|---------|----------|
| AUTH-001 | Valid login | `POST /api/login {email, password}` | 200, token + userId |
| AUTH-002 | Wrong password | `POST /api/login {email, wrongPassword}` | 401 |
| AUTH-003 | Non-existent user | `POST /api/login {nonexist@test.com, pass}` | 401 (same message as wrong pw) |
| AUTH-004 | Email case normalization | `POST /api/login {USER@TEST.COM, pass}` | 200 (case-insensitive email) |
| AUTH-005 | Password with special chars | `POST /api/login {email, P@$$w0rd!123#abc}` | 200 |
| AUTH-006 | Login with existing SHA-256 hash | `POST /api/login` for user with old hash | 200, re-hashes to argon2 |

#### Register Flow
| Test ID | Description | Request | Expected |
|---------|-------------|---------|----------|
| AUTH-007 | Valid registration | `POST /api/register {email, password, username}` | 201, userId |
| AUTH-008 | Duplicate registration | Same email again | 400 |
| AUTH-009 | Weak password | `POST /api/register {email, "123"}` | 400, min-length error |
| AUTH-010 | No username (optional) | `POST /api/register {email, password}` | 201, username defaults to email prefix |
| AUTH-011 | Unicode username | `POST /api/register {email, password, username: "用户"}` | 201 |
| AUTH-012 | Email injection in username | `POST /api/register {email, password, username: "attacker\\nBcc: x@y.com"}` | 400 / sanitized |

#### OAuth Callback
| Test ID | Description | Expected |
|---------|-------------|----------|
| AUTH-0013 | OAuth callback with valid state | Auth succeeds, token issued |
| AUTH-0014 | OAuth callback with wrong state | Rejected, CSRF prevented |
| AUTH-0015 | OAuth callback with missing state | Rejected |
| AUTH-0016 | OAuth callback with expired state (>10 min) | Rejected |

#### Token Refresh
| Test ID | Description | Expected |
|---------|-------------|----------|
| AUTH-0017 | Refresh with valid token | New token issued |
| AUTH-0018 | Refresh with revoked token | 401 |
| AUTH-0019 | Refresh with expired token | 401 |
| AUTH-0020 | Refresh with tampered token | 401, invalid signature |
| AUTH-0021 | Token storage verification (post-T-003) | Cookie HttpOnly, Secure, SameSite=Strict |

#### Brute-Force Protection (T-005)
| Test ID | Description | Expected |
|---------|-------------|----------|
| AUTH-0022 | First 5 login failures | 401, no lockout |
| AUTH-0023 | 6th failure within 15 min | 429, rate limited |
| AUTH-0024 | Lockout persists for 15 min | Continued 429 |
| AUTH-0025 | After 15 min, attempt succeeds (correct pw) | 200 |
| AUTH-0026 | Different IP bypasses per-IP limit | Independent counters per IP |

### 8.2 Input Validation Edge Cases

#### URL Injection
| Test ID | Description | Expected |
|---------|-------------|----------|
| IV-001 | URL with query parameter containing `&` | Parsed correctly |
| IV-002 | URL with encoded localhost `%61%64%6D69%6E` | Blocked (decoded to localhost) |
| IV-003 | URL with port specification `http://evil.com:6379` | Blocked (non-standard port for HTTP) |
| IV-004 | URL with trailing slash variations | Handled consistently |
| IV-005 | Double-encoded SSRF `http://%252e%252e%252f` | Blocked |

#### Oversized Payloads
| Test ID | Description | Expected |
|---------|-------------|----------|
| IV-006 | JSON body > 1MB | rejected by bodyParser, 413 |
| IV-007 | URL > 2048 chars | 400, "URL too long" |
| IV-008 | Search query > 500 chars | 400, "query too long" |
| IV-009 | Massive headers (header injection) | 400, rejected |

### 8.3 Error Handling

#### 500 Errors
| Test ID | Description | Expected |
|---------|-------------|----------|
| EH-001 | Uncaught exception in handler | 500, logged with stack |
| EH-002 | Database connection error | 503, "service unavailable" |
| EH-003 | Redis connection error | Fallback to memory cache |
| EH-004 | NSQ connection error | Fallback to sync processing |
| EH-005 | LightPanda binary not found | 500, "scraper unavailable" |
| EH-006 | SearXNG returns malformed JSON | 500, graceful error |

#### Timeout Handling
| Test ID | Description | Expected |
|---------|-------------|----------|
| EH-007 | SearXNG search timeout (15s) | Error returned, not hanging |
| EH-008 | LightPanda scrape timeout (30s) | Error returned |
| EH-009 | DB query timeout (30s) | Error returned |
| EH-010 | SMTP send timeout (10s) | Error logged, email queued |
| EH-011 | Unhandled promise rejection | Processed by global handler |

#### Circuit Breaker (T-014)
| Test ID | Description | Expected |
|---------|-------------|----------|
| EH-012 | 5 consecutive SearXNG failures | Circuit opens |
| EH-013 | Request during open circuit | Fallback/cache immediately |
| EH-014 | After 30s cooldown | Circuit transitions to half-open |
| EH-015 | Probe request succeeds | Circuit closes |
| EH-016 | Probe request fails | Circuit re-opens |

### 8.4 Queue Reliability

| Test ID | Description | Expected |
|---------|-------------|----------|
| QR-001 | Job succeeds → Redis result stored | getScrapeResult returns data |
| QR-002 | Job fails once → requeued with 2s delay | msg.requeue(2000) |
| QR-003 | Job fails 3 times → DLQ | Job moves to DLQ channel |
| QR-004 | DLQ consumers log failures | Error logged to pino |
| QR-005 | DLQ admin API returns dead jobs | GET /api/queue/dlq returns array |
| QR-006 | DLQ reprocessing | POST /api/queue/dlq/reprocess works |
| QR-007 | NSQ down → sync fallback works | Job completes synchronously |
| QR-008 | Multiple consumers, job delivered once | Exactly-once (or at-least-once) |
| QR-009 | Result polling timeout | Rejects after configured timeout |
| QR-010 | Duplicate result cleanup | cleanupResult removes stale entries |

### 8.5 Token Migration (localStorage → Cookie Auth)

| Test ID | Description | Expected |
|---------|-------------|----------|
| TM-001 | Post-migration: token in HttpOnly cookie | Cookie has HttpOnly flag |
| TM-002 | Post-migration: cookie Secure flag | Cookie has Secure flag |
| TM-003 | Post-migration: SameSite=Strict | Cookie has SameSite=Strict |
| TM-004 | Post-migration: document.cookie no token | JS cannot access auth token |
| TM-005 | Post-migration: fetch sends cookie | Cookie auto-included in requests |
| TM-006 | Post-migration: CSRF token on state-changing endpoints | Double-submit pattern |
| TM-007 | Token refresh rotates cookie | New cookie, old invalidated |
| TM-008 | Cross-origin: cookie NOT sent | SameSite=Strict blocks cross-site |

---

## 9. Test Data Management

### 9.1 Fixtures

```typescript
// tests/fixtures/mock-users.json
{
  "valid": { "email": "user@example.com", "password": "SecurePass123!", "username": "testuser" },
  "withSpecialChars": { "email": "user+tag@example.com", "password": "P@$$w0rd!123#abc" },
  "existingUser": { "email": "existing@test.com", "password": "ExistingPass123" }
}
```

### 9.2 Mock Definitions

| Dependency | Mock Strategy | Mock Object |
|------------|---------------|-------------|
| SearXNG | `axios.get` → resolved with fixture data | `[{ title: "Test", url: "http://example.com", content: "Snippet", engine: "searx" }]` |
| LightPanda | `spawn` → stub returns JSON-RPC mock responses | Pre-built JSON-RPC response strings |
| NSQ | `jest.mock('nsqjs')` → mock Writer/Reader | `mockWriter: { send: jest.fn() }`, `mockReader: { on: jest.fn() }` |
| Redis | `jest.mock('ioredis')` → mock client | `{ get: jest.fn(), set: jest.fn(), del: jest.fn(), info: jest.fn() }` |
| PostgreSQL | `jest.mock('pg')` → mock pool | `{ query: jest.fn(), connect: jest.fn() }` |
| SMTP | `jest.mock('nodemailer')` → mock transporter | `{ sendMail: jest.fn().mockResolvedValue({ messageId: 'x' }) }` |
| Argon2 | `jest.mock('argon2')` | `{ hash: jest.fn().mockResolvedValue('$argon2id$...'), verify: jest.fn().mockResolvedValue(true) }` |
| JWT | `jest.mock('jsonwebtoken')` | `{ verify: jest.fn(), sign: jest.fn().mockReturnValue('mock-jwt') }` |
| DNS | Mock `node:dns.lookup` | Returns controlled IPs for SSRF tests |

### 9.3 Test Environment

```bash
# tests/setup.ts
process.env.NODE_ENV = 'test';
process.env.JWT_SECRET = 'test-jwt-secret-for-unit-tests-only';
process.env.KEYCLOAK_URL = 'http://localhost:18080';
process.env.SEARXNG_URL = 'http://localhost:18070';
process.env.NSQD_URL = '127.0.0.1:14150';
process.env.REDIS_URL = 'redis://127.0.0.1:16379';
process.env.POSTGRES_URL = 'postgres://postgres:postgres@127.0.0.1:15432/lightserp_test';

// Suppress pino logs during tests
jest.mock('../src/logger.js', () => ({
  log: { debug: jest.fn(), info: jest.fn(), warn: jest.fn(), error: jest.fn() },
  generateUuid: jest.fn(() => 'mock-uuid'),
}));
```

---

## 10. Risk Assessment & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| NSQ mock unreliable (callback-based API) | Medium | Medium | Use wrapper adapter pattern for NSQ |
| LightPanda binary dependency in CI | High | Medium | Mock spawn in CI, test LightPanda integration separately |
| Redis/PostgreSQL availability in CI | High | Low | Use GitHub Actions service containers |
| SSRF tests requiring real DNS resolution | Medium | Medium | Mock `node:dns.lookup` for controlled responses |
| Argon2 hashing slow in CI | Medium | High | Limit hash tests to 2-3 per suite |
| OAuth flow requires real Keycloak | High | High | Mock Keycloak Admin API completely |
| NSQ DLQ testing requires real NSQ instance | Medium | Medium | Mock DLQ channel switching |

---

## 11. Execution Timeline (Aligned with Phase 1)

| Week | Phase | Activities | Deliverable |
|------|-------|------------|-------------|
| W1 | Setup | Install Jest + Supertest, create directory structure, setup mocks | Working test harness |
| W1 | Unit | SSRF tests (USR-001 to USR-020), Error hierarchy (USR-033 to USR-045) | 35 unit tests |
| W2 | Unit | Password hashing (USR-021 to USR-032), Cache (USR-046 to USR-053), Config (USR-092 to USR-096) | 65 unit tests |
| W2 | Unit | Queue (USR-054 to USR-068), Search (USR-074 to USR-080), Health (USR-088 to USR-091) | 85 unit tests |
| W2 | Security | SSRF bypass suite (SEC-010 to SEC-019), CSRF (SEC-020 to SEC-023) | 14 security tests |
| W3 | Integration | Auth flow (INT-001 to INT-025), Search API (INT-026 to INT-032) | 32 integration tests |
| W3 | Integration | Scrape API (INT-033 to INT-041), MCP proxy (INT-042 to INT-045), Health (INT-046 to INT-050) | 50 integration tests |
| W3 | Security | Auth failures (SEC-030 to SEC-037), Crypto (SEC-005 to SEC-009) | 13 more security tests |
| W4 | E2E | Full user journey (E2E-001 to E2E-004) | 4 E2E test suites |
| W4 | Load | Basic load tests (LDT-001 to LDT-003) | 3 load test configs |
| W4 | CI | GitHub Actions workflow, coverage gates, merge requirements | CI pipeline |

---

## 12. Coverage Targets by Module

| Module | Target Coverage | Rationale |
|--------|----------------|-----------|
| `ssrf.ts` | ≥ 95% | Security-critical, many edge cases |
| `auth.ts` | ≥ 90% | Core security surface |
| `password-hashing.ts` | ≥ 95% | Cryptographic correctness |
| `errors.ts` | ≥ 90% | Error handling reliability |
| `queue.ts` | ≥ 85% | Data integrity, async processing |
| `cache.ts` | ≥ 80% | Performance correctness |
| `search.ts` | ≥ 80% | External dependency heavy, use mocks |
| `scrape.ts` | ≥ 70% | Heavy integration with LightPanda |
| `api-routes.ts` | ≥ 85% | Full request/response cycle |
| `health.ts` | ≥ 90% | Production readiness signal |
| **Overall** | **≥ 60%** | Per T-018 acceptance criteria |

---

## 13. Glossary

| Term | Definition |
|------|-----------|
| SSRF | Server-Side Request Forgery — attacker crafts requests from server to internal resources |
| NSQ | Lightweight messaging platform used for async job queuing |
| SearXNG | Privacy-respecting metasearch engine |
| LightPanda | Headless browser for content extraction |
| Keycloak | Open-source identity and access management (OAuth2/OIDC) |
| Argon2id | Memory-hard password hashing algorithm |
| DLQ | Dead Letter Queue — for failed jobs after max retries |
| Circuit Breaker | Pattern to prevent cascading failures to external services |
| CSRF | Cross-Site Request Forgery — unauthorized commands from trusted user |
| JWT | JSON Web Token — stateless auth token |
