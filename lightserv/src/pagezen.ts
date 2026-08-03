import { scrape, isAvailable, getMetrics } from './lightpanda-scrape.js';
import { ScrapeResult } from './types.js';
import { log } from './logger.js';
import { validateUrl } from './ssrf.js';

// ── LightPanda availability ────────────────────────────────────────────

let lpAvailable = false;
let lpCheckPromise: Promise<boolean> | null = null;

export function startLightPandaService(): Promise<boolean> {
  if (lpCheckPromise) return lpCheckPromise;
  lpCheckPromise = isAvailable().then((v) => { lpAvailable = v; return v; });
  return lpCheckPromise;
}

export function stopLightPandaService(): void {
  lpCheckPromise = null;
  lpAvailable = false;
}

// ── LightPanda health ──────────────────────────────────────────────────

export interface LightPandaHealth {
  available: boolean;
  status: 'healthy' | 'degraded' | 'unhealthy';
  lastCheck: string;
  binary: string;
  timeoutMs: number;
  maxBytes: number;
  metrics: ReturnType<typeof getMetrics>;
}

let healthCheckTimer: ReturnType<typeof setInterval> | null = null;

export function startHealthCheck(): void {
  healthCheckTimer = setInterval(async () => {
    try {
      lpAvailable = await isAvailable();
    } catch { lpAvailable = false; }
  }, 60000);
}

export function stopHealthCheck(): void {
  if (healthCheckTimer) { clearInterval(healthCheckTimer); healthCheckTimer = null; }
  stopLightPandaService();
}

export function getLightPandaHealth(): LightPandaHealth {
  return {
    available: lpAvailable,
    status: lpAvailable ? 'healthy' : 'unhealthy',
    lastCheck: new Date().toISOString(),
    binary: process.env.LIGHTPANDA_BIN || `${process.env.HOME}/bin/lightpanda`,
    timeoutMs: parseInt(process.env.LIGHTPANDA_TIMEOUT_MS || '30000', 10),
    maxBytes: parseInt(process.env.LIGHTPANDA_MAX_BYTES || '65536', 10),
    metrics: getMetrics(),
  };
}

export function getLightPandaMetrics() {
  return getMetrics();
}

export function registerShutdownHandlers(): void { stopHealthCheck(); }

// ── Process tracking for graceful shutdown ──────────────────────────────

/** Track all spawned LightPanda child processes for graceful shutdown. */
const activeProcesses: Set<import('child_process').ChildProcess> = new Set();

/** Track a spawned LightPanda child process. */
export function trackProcess(proc: import('child_process').ChildProcess): void {
  activeProcesses.add(proc);
  proc.on('exit', () => { activeProcesses.delete(proc); });
}

/** Kill all tracked LightPanda child processes. */
export function killAllProcesses(): void {
  if (activeProcesses.size === 0) return;
  log.info(`🧹 Killing ${activeProcesses.size} pending LightPanda processes...`);

  // SIGTERM first
  for (const proc of activeProcesses) {
    try { proc.kill('SIGTERM'); } catch (e) { log.warn('Failed to SIGTERM process', e); }
  }

  // SIGKILL after 5s if still alive
  setTimeout(() => {
    let remaining = 0;
    for (const proc of activeProcesses) {
      try { proc.kill('SIGKILL'); remaining++; } catch (e) { log.warn('Failed to SIGKILL process', e); }
    }
    if (remaining > 0) {
      log.warn(`⚠️ ${remaining} LightPanda processes did not terminate, force-killed`);
    }
    activeProcesses.clear();
  }, 5000);
}

// ── Smart scrape — LightPanda only ─────────────────────────────────────

/**
 * Scrape a URL using LightPanda MCP.
 * If LightPanda is not available or returns no content, returns a
 * failed ScrapeResult with extractionMethod: 'failed'.
 */
export async function smartScrape(url: string, config?: { timeoutMs?: number }): Promise<ScrapeResult> {
  log.info(`📄 Scrape: ${url}`);

  // SSRF protection — validate URL before any processing
  try {
    await validateUrl(url);
  } catch (err) {
    log.warn(`⚠️ SSRF blocked: ${url}`, err instanceof Error ? err : new Error(String(err)));
    return {
      title: null, content: null, excerpt: null, byline: null, siteName: null,
      length: null, publishedTime: null,
      metadata: { extractionMethod: 'ssrf_blocked', scrapedAt: new Date().toISOString(), url },
    };
  }

  // Quick LP check on first call
  if (!lpCheckPromise) { startLightPandaService(); }

  if (lpAvailable) {
    try {
      const result = await scrape(url, config?.timeoutMs);
      if (result && result.content && result.content.length > 20) {
        log.info(`✅ LightPanda scraped: ${url}`, { contentLength: result.content.length, method: 'lightpanda' });
        return result;
      }
      log.info('⚠️ LightPanda returned empty content for: ' + url);
    } catch (err) {
      log.warn(`⚠️ LightPanda scrape failed for: ${url}`, err instanceof Error ? err : new Error(String(err)));
      lpAvailable = false;
    }
  } else {
    log.info('⚠️ LightPanda not available — scrape will fail for: ' + url);
  }

  return {
    title: null, content: null, excerpt: null, byline: null, siteName: null,
    length: null, publishedTime: null,
    metadata: { extractionMethod: 'failed', scrapedAt: new Date().toISOString(), url },
  };
}
