#!/usr/bin/env node
'use strict';

// Override console.log to force flush after each call
const _origLog = console.log.bind(console);
function log(...args) {
  _origLog(...args);
  process.stdout.write('\n');
  process.stdout.flush?.();
}

import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const LIGHTSERP_PATH = path.join('/Users/manjunathkanavi/workspace/git_workspace/LightSerp', 'dist', 'server.js');
const OUTPUT_DIR = path.join(__dirname, 'benchmarks');
const LOG_FILE = path.join(OUTPUT_DIR, 'benchmark-progress.log');

// Ensure log directory exists
fs.mkdirSync(OUTPUT_DIR, { recursive: true });

function logLine(msg) {
  const line = `[${new Date().toISOString()}] ${msg}\n`;
  fs.appendFileSync(LOG_FILE, line);
  log(msg);
}

const TOTAL_PAGES = parseInt(process.env.BENCHMARK_PAGES || '100', 10);
const COOLDOWN_MS = parseInt(process.env.BENCHMARK_COOLDOWN || '2000', 10);

const SEARCH_KEYWORDS = [
  'artificial intelligence', 'machine learning algorithms', 'deep neural networks',
  'quantum computing advances', 'blockchain technology', 'renewable energy solutions',
  'space exploration missions', 'climate change research', 'biotechnology breakthroughs',
  'cybersecurity threats', 'cloud computing trends', 'autonomous vehicles',
  'genomics research', 'robotics innovation', 'telecommunications 5G',
  'financial technology', 'sustainable agriculture', 'neuroscience findings',
  'environmental conservation', 'materials science', 'natural language processing',
  'computer vision systems', 'edge computing infrastructure', 'distributed systems design',
  'microservices architecture', 'container orchestration', 'devops automation tools',
  'data engineering pipelines', 'knowledge graph databases', 'federated learning approaches',
  'reinforcement learning', 'transformer architectures', 'graph neural networks',
  'neural architecture search', 'federated database systems', 'realtime stream processing',
  'serverless computing', 'evidence based medicine', 'vaccine development',
  'public health policies',
];

// ── State ──────────────────────────────────────────────────────────
const results = {
  total: TOTAL_PAGES,
  succeeded: 0,
  failed: 0,
  searchTimes: [],
  scrapeTimes: [],
  searchFailures: [],
  scrapeFailures: [],
  pages: [],
  startTime: null,
  endTime: null,
};

let server = null;
let requestId = 1;
let stdoutBuffer = '';
const pendingRequests = new Map(); // id -> { resolve, reject }

const localEnv = {
  ...process.env,
  NODE_ENV: 'production',
  HTTP_PORT: '3002',
  SEARXNG_URL: 'http://127.0.0.1:8070/search?format=json',
  REDIS_URL: 'redis://127.0.0.1:8071',
  NSQD_URL: 'http://127.0.0.1:8072',
  NSQ_LOOKUPD_URL: 'http://127.0.0.1:8074',
  PROXY_URLS: 'http://93.115.200.159:8001,http://93.115.200.158:8002,http://93.115.200.157:8003,http://93.115.200.156:8004,http://93.115.200.155:8005',
  PAGEZEN_URL: 'http://127.0.0.1:8076',
  JWT_SECRET: 'mcp-client-local-secret',
  PAGEZEN_TIMEOUT: '30000',
  PAGEZEN_HEALTH_INTERVAL: '60000',
};

function sendRequest(method, params) {
  const id = requestId++;
  const req = JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n';
  server.stdin.write(req);
  return id;
}

function waitForResponse(id, timeout = 35000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pendingRequests.delete(id);
      reject(new Error(`Timeout after ${timeout}ms`));
    }, timeout);

    pendingRequests.set(id, { resolve, reject, timer });
  });
}

function processStdout(data) {
  stdoutBuffer += data.toString();
  
  // Process complete lines
  let newlineIdx;
  while ((newlineIdx = stdoutBuffer.indexOf('\n')) !== -1) {
    const line = stdoutBuffer.substring(0, newlineIdx).trim();
    stdoutBuffer = stdoutBuffer.substring(newlineIdx + 1);
    
    if (!line) continue;
    
    try {
      const msg = JSON.parse(line);
      
      // Match on id
      if (msg.id !== undefined && pendingRequests.has(msg.id)) {
        const { resolve, reject, timer } = pendingRequests.get(msg.id);
        pendingRequests.delete(msg.id);
        clearTimeout(timer);
        
        if (msg.error) {
          reject(new Error(`MCP Error: ${msg.error.message || JSON.stringify(msg.error)}`));
        } else if (msg.result && msg.result.content) {
          const text = msg.result.content[0]?.text;
          if (typeof text === 'string') {
            try {
              resolve(JSON.parse(text));
            } catch {
              resolve({ _raw: text });
            }
          } else {
            resolve(msg.result);
          }
        } else {
          resolve(msg.result);
        }
      }
    } catch {
      // Not JSON, ignore
    }
  }
}

// ── Helpers ────────────────────────────────────────────────────────
function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

function parseJSON(data) {
  if (typeof data === 'string') {
    try { return JSON.parse(data); } catch { return null; }
  }
  return data;
}

// ── Benchmark Loop ─────────────────────────────────────────────────
async function runBenchmark() {
  logLine('\n========================================');
  logLine('  LightSerp Search + Scrape Benchmark');
  logLine(`  Pages: ${TOTAL_PAGES}`);
  logLine(`  Start: ${new Date().toISOString()}`);
  logLine('========================================\n');
  
  results.startTime = Date.now();
  
  for (let page = 0; page < TOTAL_PAGES; page++) {
    const keyword = SEARCH_KEYWORDS[page % SEARCH_KEYWORDS.length];
    const pageData = {
      index: page,
      keyword,
      searchResult: null,
      scrapeResult: null,
      searchTime: null,
      scrapeTime: null,
      searchUrls: null,
      scrapeTitle: null,
      scrapeUrl: null,
      scrapeWordCount: null,
      scrapeMethod: null,
      status: 'PENDING',
      error: null,
    };
    
    // PHASE 1: Search
    const searchStart = Date.now();
    const searchId = sendRequest('tools/call', {
      name: 'search_web',
      arguments: { query: keyword },
    });
    
    try {
      const searchResult = await waitForResponse(searchId);
      pageData.searchTime = Date.now() - searchStart;
      results.searchTimes.push(pageData.searchTime);
      
      const parsed = parseJSON(searchResult);
      
      // Handle both array results (direct) and { content: [...] } wrapper
      const items = Array.isArray(parsed) 
        ? parsed 
        : (parsed.content && Array.isArray(parsed.content)) 
          ? parsed.content 
          : (parsed.results && Array.isArray(parsed.results))
            ? parsed.results
            : [];
      
      if (items.length > 0) {
        const urls = items
          .filter(r => r.url || r.URL)
          .map(r => r.url || r.URL)
          .slice(0, 3);
        
        pageData.searchUrls = urls;
        pageData.searchResult = items.slice(0, 5);
      }
    } catch (err) {
      pageData.searchTime = Date.now() - searchStart;
      results.searchTimes.push(pageData.searchTime);
      pageData.error = `Search failed: ${err.message}`;
      results.failed++;
      results.searchFailures.push({ page, keyword, error: err.message });
    }
    
    if (pageData.searchUrls && pageData.searchUrls.length > 0) {
      results.succeeded++;
      pageData.status = 'SUCCESS';
    }
    
    // PHASE 2: Scrape first URL
    if (pageData.searchUrls && pageData.searchUrls.length > 0) {
      const url = pageData.searchUrls[0];
      
      const scrapeStart = Date.now();
      const scrapeId = sendRequest('tools/call', {
        name: 'scrape_page',
        arguments: { url },
      });
      
      try {
        const scrapeResult = await waitForResponse(scrapeId);
        pageData.scrapeTime = Date.now() - scrapeStart;
        results.scrapeTimes.push(pageData.scrapeTime);
        
        const parsed = parseJSON(scrapeResult);
        if (parsed && parsed.title) {
          pageData.scrapeResult = parsed;
          pageData.scrapeTitle = parsed.title;
          pageData.scrapeUrl = parsed.url || url;
          pageData.scrapeWordCount = parsed.metadata?.wordCount || null;
          pageData.scrapeMethod = parsed.metadata?.extractionMethod || null;
        }
      } catch (err) {
        pageData.scrapeTime = Date.now() - scrapeStart;
        results.scrapeTimes.push(pageData.scrapeTime);
        pageData.error += ` | Scrape failed: ${err.message}`;
      }
    }
    
    results.pages.push(pageData);
    
    // Progress every 10 pages
    if ((page + 1) % 10 === 0) {
      const elapsed = ((Date.now() - results.startTime) / 1000).toFixed(1);
      const rate = (page / elapsed).toFixed(2);
      const pct = ((page / TOTAL_PAGES) * 100).toFixed(0);
      const sAvg = (results.searchTimes.reduce((a,b) => a+b,0) / results.searchTimes.length).toFixed(0);
      const scAvg = results.scrapeTimes.length > 0
        ? (results.scrapeTimes.reduce((a,b) => a+b,0) / results.scrapeTimes.length).toFixed(0)
        : 'N/A';
      logLine(`\n  ── Progress: ${page}/${TOTAL_PAGES} (${pct}%) | ${elapsed}s | ${rate} p/s | S:${sAvg}ms Sc:${scAvg}ms`);
    }
    
    await sleep(COOLDOWN_MS);
  }
  
  results.endTime = Date.now();
  
  // Generate report
  const totalElapsed = ((results.endTime - results.startTime) / 1000).toFixed(1);
  const pagesPerSec = (TOTAL_PAGES / ((results.endTime - results.startTime) / 1000)).toFixed(2);
  
  const avg = arr => arr.length > 0 ? arr.reduce((a,b) => a+b,0) / arr.length : 0;
  const mn = arr => arr.length > 0 ? Math.min(...arr) : 0;
  const mx = arr => arr.length > 0 ? Math.max(...arr) : 0;
  
  const report = {
    benchmark: {
      name: 'LightSerp Search + Scrape Benchmark',
      totalPages: TOTAL_PAGES,
      date: new Date().toISOString(),
      totalTimeMs: results.endTime - results.startTime,
      totalTimeSec: parseFloat(totalElapsed),
      pagesPerSecond: parseFloat(pagesPerSec),
      successRate: `${((results.succeeded / TOTAL_PAGES) * 100).toFixed(1)}%`,
      searchAvgMs: Math.round(avg(results.searchTimes)),
      scrapeAvgMs: results.scrapeTimes.length > 0 ? Math.round(avg(results.scrapeTimes)) : 0,
    },
    search: {
      avgMs: Math.round(avg(results.searchTimes)),
      minMs: Math.round(mn(results.searchTimes)),
      maxMs: Math.round(mx(results.searchTimes)),
      calls: results.searchTimes.length,
      failures: results.searchFailures.length,
    },
    scrape: {
      avgMs: results.scrapeTimes.length > 0 ? Math.round(avg(results.scrapeTimes)) : 0,
      minMs: results.scrapeTimes.length > 0 ? Math.round(mn(results.scrapeTimes)) : 0,
      maxMs: results.scrapeTimes.length > 0 ? Math.round(mx(results.scrapeTimes)) : 0,
      calls: results.scrapeTimes.length,
      failures: results.scrapeFailures.length,
    },
    pages: results.pages.map(p => ({
      index: p.index,
      keyword: p.keyword,
      searchUrls: p.searchUrls,
      searchTimeMs: p.searchTime,
      scrapeTimeMs: p.scrapeTime,
      scrapeTitle: p.scrapeTitle,
      scrapeUrl: p.scrapeUrl,
      scrapeWordCount: p.scrapeWordCount,
      scrapeMethod: p.scrapeMethod,
      status: p.status,
      error: p.error,
    })),
  };
  
  const safeDate = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `benchmark-${TOTAL_PAGES}-pages-${safeDate}.json`;
  const filepath = path.join(OUTPUT_DIR, filename);
  const fs = await import('fs');
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  fs.writeFileSync(filepath, JSON.stringify(report, null, 2));
  
  logLine('\n\n============================================================');
  logLine('  BENCHMARK COMPLETE');
  logLine('============================================================');
  logLine(`  Total pages:    ${TOTAL_PAGES}`);
  logLine(`  Succeeded:      ${results.succeeded} (${((results.succeeded/TOTAL_PAGES)*100).toFixed(1)}%)`);
  logLine(`  Failed:         ${results.failed}`);
  logLine(`  Total time:     ${totalElapsed}s (${pagesPerSec} pages/sec)`);
  logLine(`  Search avg:     ${avg(results.searchTimes).toFixed(0)}ms | min: ${mn(results.searchTimes).toFixed(0)}ms | max: ${mx(results.searchTimes).toFixed(0)}ms`);
  if (results.scrapeTimes.length > 0) {
    logLine(`  Scrape avg:     ${avg(results.scrapeTimes).toFixed(0)}ms | min: ${mn(results.scrapeTimes).toFixed(0)}ms | max: ${mx(results.scrapeTimes).toFixed(0)}ms`);
  }
  logLine(`  Search failures: ${results.searchFailures.length}`);
  logLine(`  Scrape failures: ${results.scrapeFailures.length}`);
  logLine(`\n  Report: ${filepath}`);
  logLine('============================================================\n');
  
  // Kill server and exit
  server.kill('SIGTERM');
  setTimeout(() => server.kill('SIGKILL'), 3000);
  process.exit(0);
}

// ── Server Setup ───────────────────────────────────────────────────
server = spawn('node', [LIGHTSERP_PATH], {
  stdio: ['pipe', 'pipe', 'pipe'],
  env: localEnv,
});

server.stdout.on('data', (data) => {
  processStdout(data);
});

server.stderr.on('data', () => {
  // Ignore stderr (accessing resources, deprecation warnings)
});

server.on('error', (err) => {
  console.error('Failed to start MCP server:', err.message);
  process.exit(1);
});

// Wait for server to be ready, then initialize
server.on('spawn', () => {
  logLine('MCP server spawned, waiting for initialization...');
  
  // Initialize after server is up
  setTimeout(() => {
    const initId = sendRequest('initialize', {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: { name: 'lightserp-benchmark', version: '2.0' }
    });
    
    waitForResponse(initId, 15000)
      .then((result) => {
        logLine('MCP server initialized successfully');
        logLine(`Starting benchmark: ${TOTAL_PAGES} pages...\n`);
        runBenchmark().catch(err => {
          console.error('Benchmark error:', err);
          server.kill();
          process.exit(1);
        });
      })
      .catch(err => {
        console.error('Initialization failed:', err.message);
        server.kill();
        process.exit(1);
      });
  }, 8000);
});

server.on('close', (code) => {
  if (code !== 0) {
    console.error(`MCP server exited with code ${code}`);
  }
});

// Global timeout - 2 hours for 1000-page runs
const globalTimeout = setTimeout(() => {
  console.error('Benchmark exceeded 2-hour timeout');
  savePartialResults();
  server.kill();
  process.exit(1);
}, 7200000);

// Save partial results on SIGTERM (backup for killed processes)
function savePartialResults() {
  if (results.pages.length > 0) {
    const avg = arr => arr.length > 0 ? arr.reduce((a,b) => a+b,0) / arr.length : 0;
    const mn = arr => arr.length > 0 ? Math.min(...arr) : 0;
    const mx = arr => arr.length > 0 ? Math.max(...arr) : 0;
    
    const totalElapsed = Date.now() - (results.startTime || Date.now());
    const pagesPerSec = (results.pages.length / (totalElapsed / 1000)).toFixed(2);
    
    const report = {
      benchmark: {
        name: 'LightSerp Search + Scrape Benchmark (PARTIAL)',
        totalPages: TOTAL_PAGES,
        pagesCompleted: results.pages.length,
        date: new Date().toISOString(),
        totalTimeMs: totalElapsed,
        totalTimeSec: parseFloat((totalElapsed/1000).toFixed(1)),
        pagesPerSecond: parseFloat(pagesPerSec),
        successRate: `${((results.succeeded / results.pages.length) * 100).toFixed(1)}%`,
        searchAvgMs: Math.round(avg(results.searchTimes)),
        scrapeAvgMs: results.scrapeTimes.length > 0 ? Math.round(avg(results.scrapeTimes)) : 0,
        killed: true,
      },
      search: {
        avgMs: Math.round(avg(results.searchTimes)),
        minMs: Math.round(mn(results.searchTimes)),
        maxMs: Math.round(mx(results.searchTimes)),
        calls: results.searchTimes.length,
        failures: results.searchFailures.length,
      },
      scrape: {
        avgMs: results.scrapeTimes.length > 0 ? Math.round(avg(results.scrapeTimes)) : 0,
        minMs: results.scrapeTimes.length > 0 ? Math.round(mn(results.scrapeTimes)) : 0,
        maxMs: results.scrapeTimes.length > 0 ? Math.round(mx(results.scrapeTimes)) : 0,
        calls: results.scrapeTimes.length,
        failures: results.scrapeFailures.length,
      },
      pages: results.pages.map(p => ({
        index: p.index,
        keyword: p.keyword,
        searchUrls: p.searchUrls,
        searchTimeMs: p.searchTime,
        scrapeTimeMs: p.scrapeTime,
        scrapeTitle: p.scrapeTitle,
        scrapeUrl: p.scrapeUrl,
        scrapeWordCount: p.scrapeWordCount,
        scrapeMethod: p.scrapeMethod,
        status: p.status,
        error: p.error,
      })),
    };
    
    const safeDate = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `benchmark-1000-pages-${safeDate}-partial.json`;
    const filepath = path.join(OUTPUT_DIR, filename);
    fs.writeFileSync(filepath, JSON.stringify(report, null, 2));
    console.error(`Partial report saved: ${filepath}`);
  }
}

process.on('SIGTERM', () => {
  savePartialResults();
  server.kill();
  process.exit(1);
});
