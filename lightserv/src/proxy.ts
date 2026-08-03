/**
 * Proxy rotation with health tracking and auto-failover.
 *
 * Strategy:
 * - Config-driven pool of proxy URLs (datacenter, residential, mobile)
 * - Per-proxy health: track success/failure counts, last failure time
 * - Round-robin with fallback: skip unhealthy proxies, cycle back to healthy ones
 * - Configurable health thresholds (success streak required, failure cooldown)
 * - Graceful degradation when all proxies are down
 */
import { log } from './logger.js';

const PROXY_HEALTH_CHECK_INTERVAL = 60_000; // 1 minute
const PROXY_HEALTH_SUCCESS_STREAK = 3;       // consecutive successes to mark "healthy"
const PROXY_HEALTH_FAILURE_COOLDOWN = 120_000; // ms to wait before retrying a failed proxy
const PROXY_HEALTH_MAX_FAILURES = 5;          // consecutive failures before marking unhealthy

const HEALTHY = 'healthy' as const;
const UNHEALTHY = 'unhealthy' as const;
const COOLDOWN = 'cooldown' as const;

export interface ProxyEntry {
  url: string;
  status: typeof HEALTHY | typeof UNHEALTHY | typeof COOLDOWN;
  successStreak: number;
  consecutiveFailures: number;
  lastSuccess: number;
  lastFailure: number;
  totalRequests: number;
  totalFailures: number;
}

export interface ProxyMetrics {
  healthyCount: number;
  unhealthyCount: number;
  cooldownCount: number;
  total: number;
  proxies: { url: string; status: string; successStreak: number; consecutiveFailures: number }[];
}

let proxyPool: ProxyEntry[] = [];
let currentProxyIndex = 0;
let healthCheckTimer: ReturnType<typeof setInterval> | null = null;

export function initializeProxyPool(proxyUrls?: string[]): void {
  // Parse urls dynamically — accepts explicit arg, env var, or empty pool
  const raw = proxyUrls ?? process.env.PROXY_URLS;
  let urls: string[];
  if (Array.isArray(raw)) {
    urls = raw;
  } else if (typeof raw === 'string') {
    urls = raw.split(',')
      .map((u: string) => u.trim())
      .filter(Boolean);
  } else {
    urls = [];
  }

  proxyPool = urls.map((url: string) => ({
    url,
    status: HEALTHY,
    successStreak: 0,
    consecutiveFailures: 0,
    lastSuccess: 0,
    lastFailure: 0,
    totalRequests: 0,
    totalFailures: 0,
  }));

  currentProxyIndex = 0;

  // Periodic health re-evaluation
  if (healthCheckTimer) {
    clearInterval(healthCheckTimer);
  }
  if (proxyPool.length > 0) {
    healthCheckTimer = setInterval(runHealthCheck, PROXY_HEALTH_CHECK_INTERVAL);
  }

  log.debug(`[proxy] Initialized pool with ${proxyPool.length} proxy(s)`);
}

function runHealthCheck(): void {
  const now = Date.now();

  for (const proxy of proxyPool) {
    if (proxy.status === UNHEALTHY) {
      // Check if cooldown has elapsed
      if (now - proxy.lastFailure >= PROXY_HEALTH_FAILURE_COOLDOWN) {
        proxy.status = COOLDOWN;
        log.debug(`[proxy] ${maskUrl(proxy.url)}: cooldown ended, will retry`);
      }
    }
    // COOLDOWN proxies transition to HEALTHY via recordSuccess()
  }
}

function getNextHealthyProxy(): ProxyEntry | null {
  if (proxyPool.length === 0) return null;

  // Try to find a healthy/cooldown proxy starting from current index
  for (let i = 0; i < proxyPool.length; i++) {
    const idx = (currentProxyIndex + i) % proxyPool.length;
    const proxy = proxyPool[idx];

    if (proxy.status === HEALTHY || proxy.status === COOLDOWN) {
      currentProxyIndex = (idx + 1) % proxyPool.length;
      return proxy;
    }
  }

  // All proxies are unhealthy — return the one with fewest failures (best-effort)
  let best = proxyPool[0];
  for (const proxy of proxyPool) {
    if (proxy.consecutiveFailures < best.consecutiveFailures) {
      best = proxy;
    }
  }
  currentProxyIndex = proxyPool.indexOf(best) + 1;
  return best;
}

export function recordSuccess(proxyUrl: string): void {
  const proxy = proxyPool.find(p => p.url === proxyUrl);
  if (!proxy) return;

  proxy.successStreak++;
  proxy.consecutiveFailures = 0;
  proxy.lastSuccess = Date.now();
  proxy.totalRequests++;

  if (proxy.successStreak >= PROXY_HEALTH_SUCCESS_STREAK) {
    if (proxy.status !== HEALTHY) {
      log.debug(`[proxy] ${maskUrl(proxy.url)}: marked healthy (${proxy.successStreak} streak)`);
    }
    proxy.status = HEALTHY;
  }
}

export function recordFailure(proxyUrl: string): void {
  const proxy = proxyPool.find(p => p.url === proxyUrl);
  if (!proxy) return;

  proxy.consecutiveFailures++;
  proxy.lastFailure = Date.now();
  proxy.totalRequests++;
  proxy.totalFailures++;
  proxy.successStreak = 0;

  if (proxy.consecutiveFailures >= PROXY_HEALTH_MAX_FAILURES) {
    proxy.status = UNHEALTHY;
    log.debug(`[proxy] ${maskUrl(proxy.url)}: marked unhealthy (${proxy.consecutiveFailures} failures)`);
  } else if (proxy.status === HEALTHY) {
    proxy.status = COOLDOWN;
  }
}

export function getProxyUrl(): string | null {
  const proxy = getNextHealthyProxy();
  return proxy ? proxy.url : null;
}

export function getMetrics(): ProxyMetrics {
  const metrics: ProxyMetrics = {
    healthyCount: 0,
    unhealthyCount: 0,
    cooldownCount: 0,
    total: proxyPool.length,
    proxies: [],
  };

  for (const p of proxyPool) {
    switch (p.status) {
      case HEALTHY: metrics.healthyCount++; break;
      case UNHEALTHY: metrics.unhealthyCount++; break;
      case COOLDOWN: metrics.cooldownCount++; break;
    }
    metrics.proxies.push({
      url: p.url,
      status: p.status,
      successStreak: p.successStreak,
      consecutiveFailures: p.consecutiveFailures,
    });
  }

  return metrics;
}

export function getProxyPoolSize(): number {
  return proxyPool.length;
}

export function isProxyConfigured(): boolean {
  return proxyPool.length > 0;
}

export function shutdownProxyPool(): void {
  if (healthCheckTimer) {
    clearInterval(healthCheckTimer);
    healthCheckTimer = null;
  }
}

function maskUrl(url: string): string {
  try {
    const parsed = new URL(url);
    return `${parsed.protocol}//${parsed.hostname}:****`;
  } catch {
    return url.substring(0, 20) + '...';
  }
}
