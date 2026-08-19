/**
 * LightSerp MCP Server — main entry point.
 *
 * SECURITY: enforceSecrets() runs FIRST, before any module that reads env vars.
 * This prevents default credentials from being used anywhere.
 */

// 1. Enforce secrets BEFORE any other import (ESM init order matters)
import './secrets.js'; // Side-effect import — runs enforceSecrets at startup

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import { RateLimiterMemory } from "rate-limiter-flexible";
import { z } from "zod";
import { search } from "./search.js";
import { scrapePage } from "./scrape.js";
import { validateToken, generateToken } from "./auth.js";
import { initializeCache, getCacheMetrics, getScrapeCacheMetrics } from "./cache.js";
import { initializeDb, shutdownDb } from "./db.js";
import { initializeQueue, registerConsumer, getQueueMetrics, shutdownQueue, cleanupResult } from "./queue.js";
import { initializeProxyPool, getMetrics as getProxyMetrics, shutdownProxyPool, isProxyConfigured, getProxyPoolSize } from "./proxy.js";
import { startHealthCheck, getLightPandaHealth, stopHealthCheck, startLightPandaService, stopLightPandaService, registerShutdownHandlers } from "./pagezen.js";
import { initializeTelemetry } from "./telemetry.js";
import { log } from './logger.js';
import * as os from 'os';
import { startHttpServer, startMcpsseServer } from './http-server.js';
import { executeDeepResearch, generateSearchQueries, generateReportMarkdown } from "./deep-research.js";
import { parallelSearchScrape, parallelDeepScan } from "./parallel-scanner.js";
import { RateLimitError, formatMcpError } from './errors.js';

// 2. Initialize services (after secrets enforced)
const telemetrySdk = initializeTelemetry();

await initializeCache();
await initializeQueue();
initializeProxyPool(process.env.PROXY_URLS ? process.env.PROXY_URLS.split(',') : undefined);
startHealthCheck();

try {
  const dbOk = await initializeDb();
  if (dbOk) {
    log.info('PostgreSQL initialized for multi-tenant auth');
  } else {
    log.warn('PostgreSQL unavailable — API key management and usage logging disabled');
  }
} catch (err) {
  log.warn('PostgreSQL initialization skipped:', err);
}

startLightPandaService().catch((err) => {
  log.warn(`LightPanda initialization skipped: ${err}`);
});
registerShutdownHandlers();

// Register NSQ queue consumer
if (process.env.NSQD_URL) {
  registerConsumer(async (_jobId: string, url: string) => {
    const { scrapePage } = await import("./scrape.js");
    return scrapePage(url, true);
  });
}

// Start HTTP server (health + API)
let httpServer = null;
try {
  httpServer = await startHttpServer();
} catch (e) {
  log.info(`HTTP server not started (port already in use or error): ${formatMcpError(e).text}`);
}

// Start MCP-over-SSE server (HTTP-based MCP transport for remote clients)
let sseTransports: Record<string, SSEServerTransport> = {};
let sseSessions: Record<string, McpServer> = {};
let sseServer = null;

try {
  sseServer = await startMcpsseServer(async (req, res) => {
    const url = new URL(req.url || '', `http://${req.headers.host}`);
    const sessionId = url.searchParams.get('sessionId');

    if (req.method === 'GET' && url.pathname === '/mcp') {
      // New SSE connection
      if (!sessionId) {
        // Generate new session ID
        const { randomUUID } = await import('crypto');
        const newSessionId = randomUUID();
        const transport = new SSEServerTransport(`/mcp/messages?sessionId=${newSessionId}`, res);
        const mcpServer = new McpServer({
          name: "lightserp",
          version: "4.0.0",
          description: "Self-hosted SERP and content extraction with HTTP transport + proxy rotation"
        });

        // Re-register all tools on the new server instance
        registerToolsOnServer(mcpServer);

        sseTransports[newSessionId] = transport;
        sseSessions[newSessionId] = mcpServer;

        await mcpServer.connect(transport);

        // SSEServerTransport already writes headers and endpoint event
        // res.writeHead(200, { 'Content-Type': 'text/event-stream' });
        // res.write(`event: endpoint\ndata: /mcp/messages?sessionId=${newSessionId}\n\n`);
        // res.write('event: open\ndata: connected\n\n');

        // Clean up on disconnect
        res.on('close', () => {
          delete sseSessions[newSessionId];
          delete sseTransports[newSessionId];
          log.info(`SSE session ${newSessionId} disconnected`);
        });

        return true;
      } else {
        // Handle reconnect if needed (not fully supported by basic SSEServerTransport without custom logic)
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Reconnect not implemented' }));
        return true;
      }
    }

    if (req.method === 'POST' && url.pathname === `/mcp/messages` && sessionId && sseTransports[sessionId]) {
      // Message for existing session
      await sseTransports[sessionId].handlePostMessage(req, res);
      return true;
    }

    return false;
  });
} catch (e) {
  log.error('Failed to start MCP SSE server', e);
}

// ── Rate Limiters ────────────────────────────────────────────────────

// Global rate limiter
const heavyRateLimiter = new RateLimiterMemory({ points: 10, duration: 60 });

// ── Create MCP Server ────────────────────────────────────────────────

const server = new McpServer({
  name: "lightserp",
  version: "3.0.0",
  description: "Self-hosted SERP and content extraction service with observability, scaling, and production monitoring"
});

// Keep old tool registrations for stdio server (they get registered via registerToolsOnServer now)
// The registerToolsOnServer function above handles both stdio and SSE server instances

// ── Helper: register tools on a server instance ──────────────────────

function registerToolsOnServer(s: McpServer) {
  s.tool(
    "search_web",
    "Search the web using SearXNG with proxy rotation",
    {
      query: z.string().min(2, "Query must be at least 2 characters").max(200, "Query must be less than 200 characters"),
    },
    async ({ query }) => {
      log.info(`Search request received: "${query}"`);
      const limiter = new RateLimiterMemory({ points: 30, duration: 60 });
      try { await limiter.consume('default'); } catch { throw new RateLimitError('Rate limit exceeded (30 requests/minute)'); }
      const result = await search(query);
      const json = JSON.stringify(result, null, 2);
      log.info(`Search completed for "${query}"`, { resultCount: result.length });
      return { content: [{ type: "text" as const, text: json }] };
    }
  );

  s.tool(
    "scrape_page",
    "Scrape and extract readable content from a webpage using LightPanda",
    {
      url: z.string().url("Invalid URL format").max(2048, "URL too long"),
      async: z.boolean().optional(),
    },
    async ({ url, async: useAsync = false }) => {
      log.info(`Scrape request received`, { url, async: useAsync });
      const limiter = new RateLimiterMemory({ points: 30, duration: 60 });
      try { await limiter.consume('default'); } catch { throw new RateLimitError('Rate limit exceeded (30 requests/minute)'); }
      const result = await scrapePage(url, useAsync);
      const json = JSON.stringify(result, null, 2);
      log.info(`Scrape completed`, { url, contentLength: result.content?.length || 0 });
      return { content: [{ type: "text" as const, text: json }] };
    }
  );

  s.tool(
    "search_web_auth",
    "Authenticated search the web using SearXNG",
    {
      query: z.string().min(2, "Query must be at least 2 characters").max(200, "Query must be less than 200 characters"),
      token: z.string(),
    },
    async ({ query, token }) => {
      log.info(`Authenticated search request received: "${query}"`);
      await validateToken(token);
      const limiter = new RateLimiterMemory({ points: 30, duration: 60 });
      try { await limiter.consume('default'); } catch { throw new RateLimitError('Rate limit exceeded (30 requests/minute)'); }
      const result = await search(query);
      const json = JSON.stringify(result, null, 2);
      log.info(`Authenticated search completed for "${query}"`);
      return { content: [{ type: "text" as const, text: json }] };
    }
  );

  s.tool(
    "scrape_page_auth",
    "Authenticated scrape and extract readable content from a webpage",
    {
      url: z.string().url("Invalid URL format").max(2048, "URL too long"),
      token: z.string(),
      async: z.boolean().optional(),
    },
    async ({ url, token, async: useAsync = false }) => {
      log.info(`Authenticated scrape request received`, { url, async: useAsync });
      await validateToken(token);
      const limiter = new RateLimiterMemory({ points: 30, duration: 60 });
      try { await limiter.consume('default'); } catch { throw new RateLimitError('Rate limit exceeded (30 requests/minute)'); }
      const result = await scrapePage(url, useAsync);
      const json = JSON.stringify(result, null, 2);
      log.info(`Authenticated scrape completed`, { url, contentLength: result.content?.length || 0 });
      return { content: [{ type: "text" as const, text: json }] };
    }
  );

  s.tool(
    "generate_token",
    "Generate a JWT token for testing authentication",
    {
      userId: z.string().optional(),
      username: z.string().optional(),
    },
    async ({ userId = 'test-user', username = 'testuser' }) => {
      log.info(`Token generation request`, { userId, username });
      const token = generateToken(userId, username, ['user']);
      log.info(`Token generated successfully`, { userId });
      return { content: [{ type: "text" as const, text: `Generated token: ${token}` }] };
    }
  );

  s.tool(
    "get_metrics",
    "Get system metrics and statistics",
    {},
    async () => {
      const metrics = {
        timestamp: new Date().toISOString(),
        version: "4.0.0",
        uptime: process.uptime(),
        memoryUsage: process.memoryUsage(),
        nodeEnv: process.env.NODE_ENV || 'development',
        transport: { stdio: 'active', sse: sseServer ? 'active' : 'inactive' },
        dependencies: {
          cache: 'connected',
          queue: process.env.NSQD_URL ? 'configured' : 'not_configured',
          proxy: isProxyConfigured() ? `active (${getProxyPoolSize()} proxies)` : 'not_configured',
          searxng: process.env.SEARXNG_URL ? 'configured' : 'not_configured',
        },
        proxyPool: getProxyMetrics(),
        queue: getQueueMetrics(),
        cache: getCacheMetrics(),
        scrapeCache: getScrapeCacheMetrics(),
        pageZen: getLightPandaHealth(),
      };
      log.info('Metrics request received');
      return { content: [{ type: "text" as const, text: JSON.stringify(metrics, null, 2) }] };
    }
  );
}

// ── Stdio MCP Server (primary transport) ──────────────────────────────

registerToolsOnServer(server);

const transport = new StdioServerTransport();
await server.connect(transport);

// ── Graceful Shutdown with Drain ──────────────────────────────────────

let shuttingDown = false;
const drainTimeout = 30_000; // 30s grace period for in-flight requests

process.on('SIGINT', async () => {
  if (shuttingDown) return;
  shuttingDown = true;
  log.info('Shutting down gracefully...');
  const start = Date.now();

  try {
    cleanupResult('__shutdown__');
    shutdownQueue();
    stopHealthCheck();
    stopLightPandaService();
    shutdownProxyPool();

    if (sseServer) {
      // Close all SSE sessions
      for (const sid of Object.keys(sseSessions)) {
        try { await sseSessions[sid].close(); } catch {}
      }
      sseSessions = {};
      sseServer.close();
    }
    if (httpServer) {
      httpServer.close();
    }

    const elapsed = Date.now() - start;
    const remaining = Math.max(0, drainTimeout - elapsed);
    if (remaining > 0) {
      await new Promise<void>(r => setTimeout(r, remaining));
    }

    if (telemetrySdk) {
      await telemetrySdk.shutdown();
      log.info('Telemetry shutdown');
    }
    await shutdownDb();
    process.exit(0);
  } catch (e) {
    log.error('Shutdown error', formatMcpError(e));
    process.exit(1);
  }
});

process.on('SIGTERM', () => {
  process.emit('SIGINT');
});
