#!/usr/bin/env node
// ── LightPanda MCP scraper ─────────────────────────────────────────────
// Runs `lightpanda mcp` as a child process over stdio JSON-RPC.
// The single most efficient call is `markdown {url}` — navigate + extract
// in one round-trip, returning clean JSON.

import { spawn } from 'child_process';
import { log } from './logger.js';
import type { ScrapeResult } from './types.js';

const BIN = process.env.LIGHTPANDA_BIN || '/usr/local/bin/lightpanda';
const MAX_CONCURRENT_SCRAPE = parseInt(process.env.MAX_CONCURRENT_SCRAPES || '10', 10);
const CONCURRENCY_COUNTER: { current: number } = { current: 0 };
const TO = parseInt(process.env.LIGHTPANDA_TIMEOUT_MS || '30000', 10);
const MB = parseInt(process.env.LIGHTPANDA_MAX_BYTES || '65536', 10);

/**
 * Scrape a single URL via `lightpanda mcp` stdio JSON-RPC.
 *
 * Spawns a fresh MCP process, sends `initialize` + `markdown {url}` in
 * quick succession, reads the markdown response, then calls
 * `evaluate {script: "document.title", url}` to get the page title.
 * All three JSON-RPC messages go over one stdio connection.
 */
export async function scrape(url: string, timeoutMs = TO): Promise<ScrapeResult | null> {
  // Enforce concurrency cap
  if (CONCURRENCY_COUNTER.current >= MAX_CONCURRENT_SCRAPE) {
    log.warn(`⚠️ Concurrency cap reached (${MAX_CONCURRENT_SCRAPE}), skipping scrape of ${url}`);
    return null;
  }
  CONCURRENCY_COUNTER.current++;

  const start = Date.now();

  return new Promise((resolve) => {
    const proxyUrl = process.env.LIGHTSERP_PROXY || null;
    const args = ['mcp'];
    if (proxyUrl) args.push('--proxy', proxyUrl);
    const proc = spawn(BIN, args, {
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, LP_LOG_LEVEL: 'warn' },
    });

    let buf = '';
    let resolved = false;
    const done = (err: Error | null, result: ScrapeResult | null) => {
      if (resolved) return;
      resolved = true;
      CONCURRENCY_COUNTER.current--;
      proc.kill();
      err ? resolve(null) : resolve(result);
    };

    const t = setTimeout(() => {
      CONCURRENCY_COUNTER.current--;
      done(new Error(`timeout for ${url}`), null);
    }, timeoutMs);

    // ── helper: accumulate stdout → parse line-by-line → fire callbacks ──

    const firstCb: { msg2?: boolean; msg3?: boolean } = {};

    const handleData = (data: Buffer) => {
      buf += data.toString();
      const lines = buf.split('\n');
      buf = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const p = JSON.parse(line);
          if (p.id === 1) continue; // init response

          if (p.id === 2 && !firstCb.msg2) {
            firstCb.msg2 = true;
            if (p.error) { done(new Error(p.error.message), null); return; }
            const block = p.result?.content?.[0];
            if (!block || block.type !== 'text') { done(new Error('no content'), null); return; }

            let text = block.text.trim();

            // Extract title from # heading
            let title: string | null = null;
            const m = text.match(/^# (.+)/m);
            if (m) { title = m[1].trim(); text = text.replace(/^#\s.*\n\n?/, '').trim(); }

            // Ask for document.title too (may differ from # heading)
            proc.stdin.write(JSON.stringify({
              jsonrpc: '2.0', id: 3, method: 'tools/call',
              params: { name: 'evaluate', arguments: { script: 'document.title', url } },
            }) + '\n');

            // ── Wait for evaluate (id:3) ─────────────────────────────
            let buf3 = '';
            const wait3 = (d3: Buffer) => {
              buf3 += d3.toString();
              const l3 = buf3.split('\n');
              buf3 = l3.pop() || '';
              for (const ll of l3) {
                try {
                  const pp = JSON.parse(ll);
                  if (pp.id === 3) {
                    if (pp.error) {
                      const elapsed = Date.now() - start;
                      CONCURRENCY_COUNTER.current--;
                      log.info(`✅ LightPanda scraped: ${url}`, { title, contentLength: text.length, responseTime: elapsed });
                      done(null, { title, content: text, excerpt: text.substring(0, 500).replace(/\n/g, ' '), byline: null, siteName: null, length: text.length, publishedTime: null, finalUrl: url, metadata: { extractionMethod: 'lightpanda', scrapedAt: new Date().toISOString(), responseTime: elapsed, extractionTime: new Date().toISOString(), wordCount: text.split(/\s+/).filter(Boolean).length, language: 'en' } });
                      return;
                    }
                    const val = pp.result;
                    const t2 = typeof val === 'string' ? val.trim() : (val?.text || title);
                    const elapsed = Date.now() - start;
                    CONCURRENCY_COUNTER.current--;
                    log.info(`✅ LightPanda scraped: ${url}`, { title: t2, contentLength: text.length, responseTime: elapsed });
                    done(null, { title: t2, content: text, excerpt: text.substring(0, 500).replace(/\n/g, ' '), byline: null, siteName: null, length: text.length, publishedTime: null, finalUrl: url, metadata: { extractionMethod: 'lightpanda', scrapedAt: new Date().toISOString(), responseTime: elapsed, extractionTime: new Date().toISOString(), wordCount: text.split(/\s+/).filter(Boolean).length, language: 'en' } });
                    return;
                  }
                } catch { /* skip */ }
              }
            };
            proc.stdout?.on('data', wait3);

            // If evaluate doesn't arrive in 3s, resolve with heading title
            setTimeout(() => {
              proc.stdout?.off('data', wait3);
              const elapsed = Date.now() - start;
              CONCURRENCY_COUNTER.current--;
              log.info(`✅ LightPanda scraped: ${url}`, { title, contentLength: text.length, responseTime: elapsed });
              done(null, { title, content: text, excerpt: text.substring(0, 500).replace(/\n/g, ' '), byline: null, siteName: null, length: text.length, publishedTime: null, finalUrl: url, metadata: { extractionMethod: 'lightpanda', scrapedAt: new Date().toISOString(), responseTime: elapsed, extractionTime: new Date().toISOString(), wordCount: text.split(/\s+/).filter(Boolean).length, language: 'en' } });
            }, 3000);

            return;
          }
        } catch { /* skip non-JSON */ }
      }
    };

    proc.stdout?.on('data', handleData);
    proc.stderr?.on('data', (data: Buffer) => { log.debug(`LightPanda stderr: ${data.toString().trim()}`); });
    proc.on('error', () => { clearTimeout(t); CONCURRENCY_COUNTER.current--; done(new Error('spawn error'), null); });
    proc.on('exit', (code) => { if (code !== null && code !== 0 && !resolved) { clearTimeout(t); CONCURRENCY_COUNTER.current--; done(new Error(`LightPanda exited with code ${code}`), null); } });

    // Send both JSON-RPC requests (initialize + markdown {url})
    proc.stdin.write(JSON.stringify({
      jsonrpc: '2.0', id: 1, method: 'initialize',
      params: { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'lightserp', version: '4.0.0' } },
    }) + '\n');
    proc.stdin.write(JSON.stringify({
      jsonrpc: '2.0', id: 2, method: 'tools/call',
      params: { name: 'markdown', arguments: { url, maxBytes: MB } },
    }) + '\n');
  });
}

export async function isAvailable(): Promise<boolean> {
  return new Promise((resolve) => {
    const proxyUrl = process.env.LIGHTSERP_PROXY || null;
    const args = ['mcp'];
    if (proxyUrl) args.push('--proxy', proxyUrl);
    const proc = spawn(BIN, args, { stdio: ['pipe', 'pipe', 'pipe'], env: { ...process.env, LP_LOG_LEVEL: 'warn' } });
    const t = setTimeout(() => { proc.kill(); resolve(false); }, 3000);
    let buf = '';
    proc.stdout?.on('data', (data: Buffer) => {
      buf += data.toString();
      for (const line of buf.split('\n')) {
        try {
          const p = JSON.parse(line);
          if (p.id === 1 && p.result?.protocolVersion) { proc.kill(); resolve(true); return; }
        } catch { /* skip */ }
      }
    });
    proc.on('error', () => { clearTimeout(t); resolve(false); });
    proc.on('exit', (code) => { clearTimeout(t); resolve(code === 0); });
    proc.stdin.write(JSON.stringify({
      jsonrpc: '2.0', id: 1, method: 'initialize',
      params: { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'health', version: '1.0' } },
    }) + '\n');
  });
}

export function getMetrics() {
  return { binary: BIN, timeoutMs: TO, maxBytes: MB, activeScrapes: CONCURRENCY_COUNTER.current, maxConcurrent: MAX_CONCURRENT_SCRAPE };
}
