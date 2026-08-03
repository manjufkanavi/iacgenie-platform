#!/usr/bin/env node
/**
 * LightSerp MCP Benchmark — Search & Scrape
 *
 * Benchmarks the MCP server by:
 * 1. Searching 8 queries about local LLMs
 * 2. Collecting unique URLs from search results
 * 3. Scraping up to 1000 pages
 * 4. Publishing detailed results to benchmarks/YYYY-MM-DD/
 *
 * Uses MCP stdio JSON-RPC protocol via child_process.
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');

// ── Configuration ───────────────────────────────────────────────────────

const SCRIPT_DIR = __dirname;
const LIGHTSERP_PATH = path.join(SCRIPT_DIR, 'dist', 'server.js');
const DATE = new Date().toISOString().slice(0, 10);
const OUTPUT_DIR = path.join(SCRIPT_DIR, 'benchmarks', DATE);
const SCRAPE_DETAIL_DIR = path.join(OUTPUT_DIR, 'scrape-detail');
const TOTAL_TARGET = 1000;
const SCRAPE_CONCURRENCY = 3;
const CALL_TIMEOUT_MS = 45000;

const QUERIES = [
  'local LLM inference',
  'running LLMs locally',
  'local LLM deployment',
  'self-hosted LLM',
  'local LLM setup guide',
  'running AI models on consumer hardware',
  'local large language model',
  'open source LLM deployment',
];

// ── MCP Client ──────────────────────────────────────────────────────────

class McpClient {
  constructor() {
    this.child = null;
    this.nextId = 2;
    this.pending = new Map();
    this.buffer = '';
    this.initialized = false;
  }

  async spawn() {
    this.child = spawn('node', [LIGHTSERP_PATH], {
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env },
    });

    this.child.stdout.on('data', (data) => {
      this.buffer += data.toString();
      this._processBuffer();
    });

    this.child.stderr.on('data', (data) => {
      const lines = data.toString().split('\n');
      for (const line of lines) {
        if (line) process.stderr.write(`[server] ${line}\n`);
      }
    });

    return new Promise((resolve, reject) => {
      this.child.on('spawn', () => resolve());
      this.child.on('error', reject);
      setTimeout(() => reject(new Error('MCP server spawn timeout')), 10000);
    });
  }

  _processBuffer() {
    const lines = this.buffer.split('\n').filter(l => l.trim());
    this.buffer = '';

    for (const line of lines) {
      try {
        const msg = JSON.parse(line);
        if (msg.id && this.pending.has(msg.id)) {
          const { resolve, reject } = this.pending.get(msg.id);
          this.pending.delete(msg.id);

          if (msg.error) {
            reject(new Error(msg.error.message || JSON.stringify(msg.error)));
          } else if (msg.result) {
            resolve(msg.result);
          }
        }
      } catch {
        // Not valid JSON, skip
      }
    }
  }

  _send(method, params) {
    const id = this.nextId++;
    const msg = JSON.stringify({ jsonrpc: '2.0', id, method, params });
    this.child.stdin.write(msg + '\n');
    return id;
  }

  async callTool(name, args) {
    const startTime = Date.now();

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(this.nextId - 1);
        reject(new Error(`Timeout after ${CALL_TIMEOUT_MS}ms`));
      }, CALL_TIMEOUT_MS);

      const id = this._send('tools/call', { name, arguments: args });
      this.pending.set(id, {
        resolve: (result) => {
          clearTimeout(timer);
          const timeMs = Date.now() - startTime;
          resolve({ result, timeMs });
        },
        reject: (err) => {
          clearTimeout(timer);
          reject(err);
        },
      });
    });
  }

  async initialize() {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Init timeout')), 10000);
      const id = this._send('initialize', {
        protocolVersion: '2024-11-05',
        capabilities: {},
        clientInfo: { name: 'lightserp-benchmark', version: '1.0.0' },
      });
      this.pending.set(id, {
        resolve: () => {
          clearTimeout(timer);
          this.initialized = true;
          resolve();
        },
        reject,
      });
    });
  }

  async close() {
    return new Promise((resolve) => {
      if (this.child) {
        this.child.on('close', resolve);
        this.child.kill('SIGTERM');
      } else {
        resolve();
      }
    });
  }
}

// ── Result Parsing ──────────────────────────────────────────────────────

function parseToolResult(result) {
  const text = result.content?.[0]?.text;
  if (!text) return { structured: null, raw: null, error: true, message: 'Empty result' };

  // Try JSON parse — structured results are JSON strings
  try {
    const parsed = JSON.parse(text);
    // Search returns array, scrape returns object
    return { structured: parsed, raw: text, error: false, message: null };
  } catch {
    // Plain text — likely an error message
    return { structured: null, raw: text, error: true, message: text };
  }
}

function categorizeError(message) {
  if (!message) return 'unknown';
  if (message.includes('Rate limit exceeded')) return 'rate_limit';
  if (message.includes('Scraping failed')) return 'scrape_failed';
  if (message.includes('Scrape job failed')) return 'scrape_failed';
  if (message.includes('Timeout')) return 'timeout';
  if (message.includes('Invalid or expired token')) return 'auth_failed';
  if (message.includes('Authentication failed')) return 'auth_failed';
  if (message.includes('Cannot consume')) return 'rate_limit';
  if (message.includes('Invalid URL')) return 'invalid_url';
  return 'scrape_failed';
}

// ── File Writing Helpers ────────────────────────────────────────────────

function writeJSON(filePath, data) {
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
}

function safeFilename(url) {
  return url.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 60);
}

// ── Main Benchmark ──────────────────────────────────────────────────────

async function main() {
  const wallStart = Date.now();
  console.log('=== LightSerp MCP Benchmark ===');
  console.log(`Output: ${OUTPUT_DIR}`);
  console.log(`Queries: ${QUERIES.length}, Target URLs: ${TOTAL_TARGET}\n`);

  // Ensure output directory
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  fs.mkdirSync(SCRAPE_DETAIL_DIR, { recursive: true });

  // Spawn MCP server
  console.log('Phase 0: Starting MCP server...');
  const client = new McpClient();
  try {
    await client.spawn();
  } catch (err) {
    console.error(`Failed to start MCP server: ${err.message}`);
    process.exit(1);
  }

  await client.initialize();
  console.log('MCP server initialized.\n');

  // ── Phase 1: Search ─────────────────────────────────────────────────

  console.log('Phase 1: Searching...');
  const perQueryResults = [];
  const allUrlMap = new Map(); // url -> { foundBy: string[] }
  let searchTotalMs = 0;

  for (let i = 0; i < QUERIES.length; i++) {
    const query = QUERIES[i];
    const qStart = Date.now();
    console.log(`  [${i + 1}/${QUERIES.length}] "${query}"`);

    try {
      const { result, timeMs } = await client.callTool('search_web', { query });
      searchTotalMs += timeMs;

      const { structured, error, message } = parseToolResult(result);

      if (error) {
        console.log(`    ERROR: ${message}`);
        perQueryResults.push({
          query,
          timeMs,
          success: false,
          resultCount: 0,
          urls: [],
          errorReason: categorizeError(message),
        });
        continue;
      }

      const searchResults = Array.isArray(structured) ? structured : [];
      const urls = [];

      for (const r of searchResults) {
        if (r.url && r.url.startsWith('http')) {
          urls.push(r.url);
          if (!allUrlMap.has(r.url)) {
            allUrlMap.set(r.url, { foundBy: [] });
          }
          allUrlMap.get(r.url).foundBy.push(query);
        }
      }

      console.log(`    OK: ${searchResults.length} results in ${timeMs}ms, ${urls.length} URLs`);
      perQueryResults.push({
        query,
        timeMs,
        success: true,
        resultCount: searchResults.length,
        urls,
        errorReason: null,
      });
    } catch (err) {
      const timeMs = Date.now() - qStart;
      console.log(`    ERROR: ${err.message}`);
      perQueryResults.push({
        query,
        timeMs,
        success: false,
        resultCount: 0,
        urls: [],
        errorReason: 'timeout',
      });
    }
  }

  const searchTiming = {
    totalMs: searchTotalMs,
    avgMs: QUERIES.length > 0 ? Math.round(searchTotalMs / QUERIES.length) : 0,
    minMs: Math.min(...perQueryResults.filter(r => r.success).map(r => r.timeMs)),
    maxMs: Math.max(...perQueryResults.filter(r => r.success).map(r => r.timeMs)),
  };

  if (searchTiming.minMs === Infinity) searchTiming.minMs = 0;
  if (searchTiming.maxMs === -Infinity) searchTiming.maxMs = 0;

  const urls = Array.from(allUrlMap.entries()).map(([url, info]) => ({ url, foundBy: info.foundBy }));
  console.log(`\nPhase 1 complete: ${urls.length} unique URLs found from ${QUERIES.length} queries.\n`);

  // ── Phase 2: Scrape ──────────────────────────────────────────────────

  console.log('Phase 2: Scraping...');
  const scrapeTargets = urls.slice(0, TOTAL_TARGET);
  console.log(`  Target: ${scrapeTargets.length} URLs\n`);

  const scrapeResults = [];
  const errorBreakdown = {};
  let scrapeTotalMs = 0;
  let scrapeSuccess = 0;
  let scrapeFailed = 0;
  let pendingCount = 0;
  let completedCount = 0;
  const scrapeStartTime = Date.now();

  async function scrapeOne(index) {
    if (index >= scrapeTargets.length) return;

    const { url, foundBy } = scrapeTargets[index];
    const scrapeStart = Date.now();

    try {
      const { result, timeMs } = await client.callTool('scrape_page', { url });
      scrapeTotalMs += timeMs;

      const { structured, error, message } = parseToolResult(result);

      if (error) {
        const reason = categorizeError(message);
        errorBreakdown[reason] = (errorBreakdown[reason] || 0) + 1;
        scrapeFailed++;

        scrapeResults.push({
          url,
          foundBy,
          success: false,
          timeMs,
          errorReason: reason,
          errorMessage: message || null,
          contentLength: 0,
          title: null,
          content: null,
          extractionMethod: null,
        });

        console.log(`  [${index + 1}/${scrapeTargets.length}] FAILED (${timeMs}ms) ${url.substring(0, 60)} — ${reason}: ${message?.substring(0, 80)}`);
      } else {
        const contentLen = structured.content?.length || 0;
        const extractionMethod = structured.metadata?.extractionMethod || 'unknown';

        scrapeSuccess++;

        scrapeResults.push({
          url,
          foundBy,
          success: true,
          timeMs,
          errorReason: null,
          errorMessage: null,
          contentLength: contentLen,
          title: structured.title,
          content: structured.content,
          excerpt: structured.excerpt,
          byline: structured.byline,
          siteName: structured.siteName,
          length: structured.length,
          publishedTime: structured.publishedTime,
          metadata: structured.metadata,
          extractionMethod,
        });

        // Save detail file
        const safeName = safeFilename(url);
        writeJSON(
          path.join(SCRAPE_DETAIL_DIR, `${String(index + 1).padStart(4, '0')}_${safeName}.json`),
          { url, ...structured, scrapedAt: new Date().toISOString(), benchmarkTimeMs: timeMs }
        );

        console.log(`  [${index + 1}/${scrapeTargets.length}] OK (${timeMs}ms) ${url.substring(0, 60)} — ${contentLen} chars (${extractionMethod})`);
      }
    } catch (err) {
      const timeMs = Date.now() - scrapeStart;
      scrapeTotalMs += timeMs;
      const reason = categorizeError(err.message);
      errorBreakdown[reason] = (errorBreakdown[reason] || 0) + 1;
      scrapeFailed++;

      scrapeResults.push({
        url,
        foundBy,
        success: false,
        timeMs,
        errorReason: reason,
        errorMessage: err.message.substring(0, 200),
        contentLength: 0,
        title: null,
        content: null,
        extractionMethod: null,
      });

      console.log(`  [${index + 1}/${scrapeTargets.length}] ERROR (${timeMs}ms) ${url.substring(0, 60)} — ${err.message.substring(0, 80)}`);
    }

    completedCount++;

    // Schedule next scrape if concurrency slot available
    pendingCount--;
    const nextIndex = index + 1;
    if (nextIndex < scrapeTargets.length && pendingCount < SCRAPE_CONCURRENCY) {
      pendingCount++;
      scrapeOne(nextIndex).catch(() => {});
    }
  }

  // Kick off first batch
  for (let i = 0; i < Math.min(SCRAPE_CONCURRENCY, scrapeTargets.length); i++) {
    pendingCount++;
    scrapeOne(i).catch(() => {});
  }

  // Wait for all to complete
  await new Promise((resolve) => {
    const check = setInterval(() => {
      if (completedCount >= scrapeTargets.length) {
        clearInterval(check);
        resolve();
      }
    }, 500);
  });

  const scrapeTiming = {
    totalMs: scrapeTotalMs,
    avgMs: scrapeResults.length > 0 ? Math.round(scrapeTotalMs / scrapeResults.length) : 0,
    minMs: scrapeResults.length > 0 ? Math.min(...scrapeResults.map(r => r.timeMs)) : 0,
    maxMs: scrapeResults.length > 0 ? Math.max(...scrapeResults.map(r => r.timeMs)) : 0,
  };

  const wallMs = Date.now() - wallStart;

  // ── Phase 3: Compute Stats ───────────────────────────────────────────

  const contentLengths = scrapeResults.filter(r => r.success).map(r => r.contentLength);
  const avgLength = contentLengths.length > 0
    ? Math.round(contentLengths.reduce((a, b) => a + b, 0) / contentLengths.length)
    : 0;

  const sortedLengths = [...contentLengths].sort((a, b) => a - b);
  const medianLength = sortedLengths.length > 0
    ? sortedLengths[Math.floor(sortedLengths.length / 2)]
    : 0;

  // ── Phase 4: Write Results ───────────────────────────────────────────

  const summary = {
    runId: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
    serverVersion: '3.0.0',
    totalWallTimeMs: wallMs,
    queries: QUERIES,
    totalSearchTimeMs: searchTotalMs,
    searchTiming: searchTiming,
    totalUrlsFound: allUrlMap.size,
    urlsScraped: scrapeResults.length,
    urlsScrapedTarget: TOTAL_TARGET,
    scrapesSucceeded: scrapeSuccess,
    scrapesFailed: scrapeFailed,
    scrapeSuccessRate: scrapeResults.length > 0
      ? (scrapeSuccess / scrapeResults.length * 100).toFixed(2)
      : '0.00',
    totalScrapeTimeMs: scrapeTotalMs,
    scrapeTiming: scrapeTiming,
    errorBreakdown,
    contentLengthStats: {
      avg: avgLength,
      min: contentLengths.length > 0 ? Math.min(...contentLengths) : 0,
      max: contentLengths.length > 0 ? Math.max(...contentLengths) : 0,
      median: medianLength,
    },
    perQueryResults,
    perScrapeResults: scrapeResults.map(r => ({
      url: r.url,
      foundBy: r.foundBy,
      success: r.success,
      timeMs: r.timeMs,
      errorReason: r.errorReason,
      errorMessage: r.errorMessage,
      contentLength: r.contentLength,
      title: r.title,
      extractionMethod: r.extractionMethod,
    })),
  };

  // Write all output files
  writeJSON(path.join(OUTPUT_DIR, 'summary.json'), summary);
  writeJSON(path.join(OUTPUT_DIR, 'search-results.json'), perQueryResults);
  writeJSON(path.join(OUTPUT_DIR, 'scrape-results.json'),
    scrapeResults.map(r => ({
      url: r.url,
      foundBy: r.foundBy,
      success: r.success,
      timeMs: r.timeMs,
      errorReason: r.errorReason,
      errorMessage: r.errorMessage,
      contentLength: r.contentLength,
      title: r.title,
      extractionMethod: r.extractionMethod,
    }))
  );

  // Failed URLs list
  const failedUrls = scrapeResults.filter(r => !r.success).map(r => r.url);
  fs.writeFileSync(path.join(OUTPUT_DIR, 'failed-urls.txt'), failedUrls.join('\n') + (failedUrls.length > 0 ? '\n' : ''));

  // ── Print Summary ────────────────────────────────────────────────────

  console.log('\n' + '='.repeat(60));
  console.log('BENCHMARK RESULTS');
  console.log('='.repeat(60));

  console.log(`\n  Wall time:           ${Math.round(wallMs / 1000)}s`);
  console.log(`  Queries run:         ${QUERIES.length}`);
  console.log(`  Search total time:   ${searchTotalMs}ms (avg ${searchTiming.avgMs}ms/query)`);
  console.log(`  Unique URLs found:   ${allUrlMap.size}`);
  console.log(`  URLs scraped:        ${scrapeResults.length} / ${TOTAL_TARGET}`);

  console.log(`\n  Scraping:`);
  console.log(`    Successful:        ${scrapeSuccess} (${summary.scrapeSuccessRate}%)`);
  console.log(`    Failed:            ${scrapeFailed}`);
  console.log(`    Total time:        ${scrapeTotalMs}ms (avg ${scrapeTiming.avgMs}ms/page)`);
  console.log(`    Avg content:       ${avgLength} chars`);
  console.log(`    Median content:    ${medianLength} chars`);

  console.log(`\n  Error breakdown:`);
  for (const [reason, count] of Object.entries(errorBreakdown)) {
    console.log(`    ${reason}: ${count}`);
  }

  if (contentLengths.length > 0) {
    console.log(`\n  Content length stats:`);
    console.log(`    Min: ${Math.min(...contentLengths)} chars`);
    console.log(`    Max: ${Math.max(...contentLengths)} chars`);
    console.log(`    Median: ${medianLength} chars`);
  }

  console.log(`\n  Per-query results:`);
  for (const qr of perQueryResults) {
    const status = qr.success ? 'OK' : 'ERR';
    console.log(`    [${status}] "${qr.query}" -> ${qr.resultCount} results (${qr.timeMs}ms)`);
  }

  console.log(`\n  Results saved to: ${OUTPUT_DIR}`);
  console.log(`    summary.json`);
  console.log(`    search-results.json`);
  console.log(`    scrape-results.json`);
  console.log(`    scrape-detail/ (${scrapeSuccess} files)`);
  console.log(`    failed-urls.txt (${failedUrls.length} URLs)`);
  console.log('='.repeat(60));

  await client.close();
}

main().catch((err) => {
  console.error('Benchmark failed:', err);
  process.exit(1);
});
