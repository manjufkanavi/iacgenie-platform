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
import { startHttpServer } from './http-server.js';
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

// Start HTTP server
let httpServer = null;
try {
  httpServer = await startHttpServer();
} catch (e) {
  log.info(`HTTP server not started (port already in use or error): ${formatMcpError(e).text}`);
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

// ── search_web ────────────────────────────────────────────────────────

server.tool(
  "search_web",
  "Search the web using SearXNG",
  {
    query: z.string().min(2, "Query must be at least 2 characters").max(200, "Query must be less than 200 characters"),
  },
  async ({ query }) => {
    log.info(`Search request received: "${query}"`);
    const limiter = new RateLimiterMemory({ points: 30, duration: 60 });
    try {
      await limiter.consume('default');
    } catch {
      throw new RateLimitError('Rate limit exceeded (30 requests/minute)');
    }
    const result = await search(query);
    const json = JSON.stringify(result, null, 2);
    log.info(`Search completed for "${query}"`, { resultCount: result.length });
    return { content: [{ type: "text" as const, text: json }] };
  }
);

// ── scrape_page ───────────────────────────────────────────────────────

server.tool(
  "scrape_page",
  "Scrape and extract readable content from a webpage",
  {
    url: z.string().url("Invalid URL format").max(2048, "URL too long"),
    async: z.boolean().optional(),
  },
  async ({ url, async: useAsync = false }) => {
    log.info(`Scrape request received`, { url, async: useAsync });
    const limiter = new RateLimiterMemory({ points: 30, duration: 60 });
    try {
      await limiter.consume('default');
    } catch {
      throw new RateLimitError('Rate limit exceeded (30 requests/minute)');
    }
    const result = await scrapePage(url, useAsync);
    const json = JSON.stringify(result, null, 2);
    log.info(`Scrape completed`, { url, contentLength: result.content?.length || 0 });
    return { content: [{ type: "text" as const, text: json }] };
  }
);

// ── search_web_auth ──────────────────────────────────────────────────

server.tool(
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
    try {
      await limiter.consume('default');
    } catch {
      throw new RateLimitError('Rate limit exceeded (30 requests/minute)');
    }
    const result = await search(query);
    const json = JSON.stringify(result, null, 2);
    log.info(`Authenticated search completed for "${query}"`);
    return { content: [{ type: "text" as const, text: json }] };
  }
);

// ── scrape_page_auth ─────────────────────────────────────────────────

server.tool(
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
    try {
      await limiter.consume('default');
    } catch {
      throw new RateLimitError('Rate limit exceeded (30 requests/minute)');
    }
    const result = await scrapePage(url, useAsync);
    const json = JSON.stringify(result, null, 2);
    log.info(`Authenticated scrape completed`, { url, contentLength: result.content?.length || 0 });
    return { content: [{ type: "text" as const, text: json }] };
  }
);

// ── generate_token ───────────────────────────────────────────────────

server.tool(
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

// ── get_metrics ───────────────────────────────────────────────────────

server.tool(
  "get_metrics",
  "Get system metrics and statistics",
  {},
  async () => {
    const metrics = {
      timestamp: new Date().toISOString(),
      version: "3.0.0",
      uptime: process.uptime(),
      memoryUsage: process.memoryUsage(),
      nodeEnv: process.env.NODE_ENV || 'development',
      dependencies: {
        cache: 'connected',
        queue: process.env.NSQD_URL ? 'configured' : 'not_configured',
        proxy: isProxyConfigured() ? `active (${getProxyPoolSize()} proxies)` : 'not_configured',
        searxng: process.env.SEARXNG_URL ? 'configured' : 'not_configured',
        pageZen: 'removed (LightPanda only since v4.0)',
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

// ── generate_research_queries ─────────────────────────────────────────

server.tool(
  "generate_research_queries",
  "Generate diverse search queries for deep research on a topic. Returns 15-30 queries covering definition, technical, applications, comparison, trends, challenges, and data dimensions.",
  {
    topic: z.string().min(2, "Topic must be at least 2 characters").max(200, "Topic must be less than 200 characters"),
  },
  async ({ topic }) => {
    const queries = generateSearchQueries(topic, 25);
    const data = {
      topic,
      queryCount: queries.length,
      queries,
      categories: [
        "definition_overview", "technical_deep_dive", "industry_applications",
        "comparative_analysis", "trends_future", "challenges_limitations",
        "data_statistics", "case_studies", "resources_tools", "expert_perspectives",
      ],
      note: "Use 'run_deep_research' tool to execute these queries and generate a full report",
    };
    return { content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }] };
  }
);

// ── run_deep_research ─────────────────────────────────────────────────

server.tool(
  "run_deep_research",
  "Execute a full deep research pipeline: generates search queries, executes searches via LightSerp MCP, crawls 20+ pages per query with deduplication, and produces a structured Gemini-style deep research report. Output saved to ~/.hermes/research/{topic_slug}_research.md. Returns the report markdown content.",
  {
    topic: z.string().min(2, "Topic must be at least 2 characters").max(200, "Topic must be less than 200 characters"),
  },
  async ({ topic }) => {
    log.info(`Deep research started: "${topic}"`);
    try {
      await heavyRateLimiter.consume('deep-research');
    } catch {
      throw new RateLimitError('Rate limit exceeded (10 requests/minute for heavy tools)');
    }
    const report = await executeDeepResearch(topic);
    const markdown = generateReportMarkdown(report);
    const fs = await import('fs');
    const path = await import('path');
    const outputDir = process.env.RESEARCH_OUTPUT_DIR || path.join(os.homedir(), '.hermes', 'research');
    const outputPath = path.join(outputDir, `${report.slug}_research.md`);
    if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });
    fs.writeFileSync(outputPath, markdown, 'utf-8');
    log.info(`Deep research completed: ${report.sourcesCrawled} sources, saved to ${outputPath}`);
    const summary = `## Research Complete\n\n**Topic:** ${topic}\n**Queries Executed:** ${report.searchQueries.length}\n**Sources Crawled:** ${report.sourcesCrawled}\n**Output:** ${outputPath}\n\n${markdown.substring(0, 3000)}... [truncated, full report saved to ${outputPath}]\n\nUse 'generate_research_queries' first to see queries, then 'run_deep_research' for full pipeline.`;
    return { content: [{ type: "text" as const, text: summary }] };
  }
);

// ── parallel_search_scrape ───────────────────────────────────────────

server.tool(
  "parallel_search_scrape",
  "Execute parallel search and scrape: generates search queries for a topic, searches in parallel, then scrapes top N results with configurable concurrency. Each URL gets its own LightPanda MCP process.",
  {
    query: z.string().min(2, "Query must be at least 2 characters").max(200, "Query must be less than 200 characters"),
    scrapeCount: z.number().min(1).max(20).optional(),
    scrapeConcurrency: z.number().min(1).max(10).optional(),
    maxResults: z.number().min(1).max(100).optional(),
  },
  async ({ query, scrapeCount = 5, scrapeConcurrency = 4, maxResults = 20 }) => {
    log.info(`Parallel search + scrape: query="${query}", scrapeCount=${scrapeCount}`);
    const result = JSON.stringify(await parallelSearchScrape({ query, scrapeCount, scrapeConcurrency, maxResults }), null, 2);
    const data = JSON.parse(result);
    log.info(`Parallel scan completed: ${data.stats?.pagesSucceeded}/${data.stats?.pagesCrawled} succeeded`);
    return { content: [{ type: "text" as const, text: result }] };
  }
);

// ── parallel_deep_scan ───────────────────────────────────────────────

server.tool(
  "parallel_deep_scan",
  "Execute deep parallel scan: runs multiple search queries, scrapes top results for each with concurrency control. Ideal for comprehensive research topics.",
  {
    queries: z.array(z.string()).min(1).max(15),
    scrapeCount: z.number().min(1).max(20).optional(),
    scrapeConcurrency: z.number().min(1).max(10).optional(),
  },
  async ({ queries, scrapeCount = 5, scrapeConcurrency = 4 }) => {
    log.info(`Deep scan: ${queries.length} queries, scrapeCount=${scrapeCount}`);
    const result = JSON.stringify(await parallelDeepScan({ queries, scrapeCount, scrapeConcurrency }), null, 2);
    const data = JSON.parse(result);
    log.info(`Deep scan completed: ${data.stats?.pagesSucceeded}/${data.stats?.pagesCrawled} succeeded`);
    return { content: [{ type: "text" as const, text: result }] };
  }
);

// ── Connect & Start ─────────────────────────────────────────────────

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
