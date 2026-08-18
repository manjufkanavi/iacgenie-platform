# LightSerp v4.0 — HTTP MCP Transport + Proxy Rotation

## Changes Summary

### 1. HTTP MCP Transport (SSE)
- **`src/server.ts`**: Added `SSEServerTransport` import and SSE server startup
- **`src/http-server.ts`**: Added `startMcpsseServer()` function on port 7805
- MCP clients can now connect via `http://<host>:7805/mcp` (SSE) instead of only stdio
- JWT auth middleware on `/mcp` endpoints
- Session-based connection management with auto-cleanup

### 2. Proxy Rotation Integration
- **`src/search.ts`**: Integrated proxy pool from `proxy.ts`
  - Tries proxy first, falls back to direct connection
  - Records success/failure for health tracking
  - Auto-failover to healthy proxies
- **`src/lightpanda-scrape.ts`**: Already supports `--proxy` flag (no changes needed)

### 3. Docker Compose Updates
- **`docker-compose.yml`**:
  - Bind HTTP port to `0.0.0.0:3001` (was `127.0.0.1:3001`)
  - Added MCP SSE port `0.0.0.0:7805`
  - Added `HTTP_HOST=0.0.0.0`, `MCP_SSE_PORT=7805` env vars
  - Added `PROXY_URLS` env var for proxy pool configuration
  - Updated healthcheck to use wget

### 4. Benchmark Infrastructure
- **`benchmark-runner.js`**: 1000-query benchmark with:
  - 4 category pools (tech, science, business, general)
  - Search + scrape timing per query
  - Success/failure tracking by category
  - Error aggregation
  - JSON + HTML report generation

### 5. Version Bump
- MCP server version: `3.0.0` → `4.0.0`

## Deployment

```bash
# Build and deploy
cd /path/to/lightserv
docker compose build
docker compose up -d

# Verify
curl http://localhost:3001/health
curl http://localhost:7805/mcp  # SSE endpoint
```

## Hermes Configuration

```yaml
mcp_servers:
  lightserp:
    type: sse
    url: http://lightserp.iacgenie.com:7805/mcp
    headers:
      Authorization: Bearer <JWT_TOKEN>
```

## Benchmarks

```bash
# Run 1000-query benchmark
cd /path/to/lightserv
node benchmark-runner.js

# Output: benchmark-results/benchmark-report.json
#         benchmark-results/benchmark-report.html
```
