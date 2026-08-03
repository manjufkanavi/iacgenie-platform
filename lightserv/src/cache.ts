import { Redis } from 'ioredis';
import { SearchResult } from './types.js';
import { log } from './logger.js';

/** Simple LRU cache with max size and TTL. */
class LRUCache<K, V> extends Map<K, V> {
  private _maxSize: number;
  private _expiryMap: Map<K, number>; // key -> expiry timestamp

  constructor(maxSize: number) {
    super();
    this._maxSize = maxSize;
    this._expiryMap = new Map();
  }

  /** Set with TTL and eviction. */
  store(key: K, value: V, ttl: number = 300): void {
    // If key already exists, move it to end (most recently used)
    if (this.has(key)) {
      super.delete(key);
    }
    // Evict oldest entries if at capacity
    while (this.size >= this._maxSize) {
      const oldestKey = this.keys().next().value;
      if (oldestKey !== undefined) this.delete(oldestKey);
    }
    // Set the entry
    super.set(key, value);
    this._expiryMap.set(key, Date.now() + ttl * 1000);
  }

  get(key: K): V | undefined {
    const expiry = this._expiryMap.get(key);
    if (expiry && Date.now() > expiry) {
      // Expired — remove and return undefined
      this.delete(key);
      return undefined;
    }
    return super.get(key);
  }

  override delete(key: K): boolean {
    this._expiryMap.delete(key);
    return super.delete(key);
  }

  /** Remove all expired entries. */
  pruneExpired(): number {
    const now = Date.now();
    let pruned = 0;
    for (const [key, expiry] of this._expiryMap) {
      if (now > expiry) {
        super.delete(key);
        pruned++;
      }
    }
    return pruned;
  }

  /** Get metrics about cache usage. */
  metrics(): { size: number; maxSize: number; hitRate: number } {
    return {
      size: this.size,
      maxSize: this._maxSize,
      hitRate: 0, // caller should track hits/misses externally
    };
  }
}

const REDIS_URL = process.env.REDIS_URL || 'redis://localhost:6379';
const CACHE_TTL = 300; // 5 minutes in seconds

let redisClient: Redis | null = null;

export async function initializeCache() {
  try {
    redisClient = new Redis(REDIS_URL, {
      connectTimeout: 1000,
      maxRetriesPerRequest: 2,
      retryStrategy(times) {
        if (times > 2) {
          log.warn('🛑 Redis max retry attempts reached, disabling retries');
          return null;
        }
        return Math.min(times * 100, 500);
      },
      lazyConnect: true,
    });

    // Suppress ioredis unhandled error events
    redisClient.on('error', (err) => log.error('Redis connection error', err));

    // Test connection with timeout
    await Promise.race([
      redisClient.ping(),
      new Promise((_, reject) => setTimeout(() => reject(new Error('Redis ping timeout')), 2000))
    ]);
    log.info('✅ Redis cache initialized');

    return redisClient;
  } catch (error) {
    log.error('❌ Failed to initialize Redis cache', error);
    // Fallback to in-memory cache if Redis fails
    log.warn('🔄 Falling back to in-memory cache');
    return null;
  }
}

export async function getCachedSearch(query: string): Promise<SearchResult[] | null> {
  // If Redis is unavailable or closed, use memory cache immediately
  if (!redisClient || redisClient.status !== 'ready') {
    const data = getMemoryCache(`search:${query}`);
    if (data) {
      log.debug(`📦 Memory cache hit for query: ${query}`);
      return data as SearchResult[];
    }
    return null;
  }

  try {
    const cacheKey = `search:${query}`;
    const cachedData = await redisClient.get(cacheKey);

    if (cachedData) {
      log.debug(`📦 Cache hit for query: ${query}`);
      return JSON.parse(cachedData);
    }

    return null;
  } catch (error) {
    log.error('❌ Cache read error', error);
    // Fallback to memory cache
    const data = getMemoryCache(`search:${query}`);
    return data as SearchResult[] | null;
  }
}

export async function setCachedSearch(query: string, results: SearchResult[]): Promise<void> {
  if (redisClient && (redisClient.status === 'ready' || redisClient.status === 'connecting')) {
    try {
      const cacheKey = `search:${query}`;
      await redisClient.setex(cacheKey, CACHE_TTL, JSON.stringify(results));
      log.debug(`💾 Cached search results for: ${query}`, { resultCount: results.length });
      return;
    } catch (error) {
      log.error('❌ Redis cache write error, falling back to memory', error);
    }
  }

  // Fallback to memory cache
  setMemoryCache(`search:${query}`, results);
  log.debug(`💾 Cached in memory for: ${query}`, { resultCount: results.length });
}

export async function invalidateCache(query: string): Promise<void> {
  // If Redis is unavailable or closed, just clear memory cache
  if (!redisClient || redisClient.status !== 'ready') {
    memoryCache.delete(`search:${query}`);
    log.debug(`🗑️  Cleared memory cache for: ${query}`);
    return;
  }

  try {
    const cacheKey = `search:${query}`;
    await redisClient.del(cacheKey);
    log.info(`🗑️  Invalidated cache for: ${query}`);
  } catch (error) {
    // Fallback: clear memory cache
    memoryCache.delete(`search:${query}`);
    log.error('❌ Redis cache invalidation error, cleared memory', error);
  }
}

// In-memory fallback cache with LRU eviction
const memoryCache: LRUCache<string, { data: any; expiresAt: number }> = new LRUCache(1000);

export function getMemoryCache(key: string): any {
  const entry = memoryCache.get(key);
  if (entry && entry.expiresAt > Date.now()) {
    log.trace(`📦 Memory cache hit for: ${key}`);
    return entry.data;
  }
  return null;
}

export function setMemoryCache(key: string, data: any, ttl: number = 300): void {
  memoryCache.store(key, { data, expiresAt: Date.now() + ttl * 1000 }, ttl);
}

// ── Generic Redis Key-Value Ops ─────────────────────────────────────

export async function setRedisCache(key: string, value: unknown, ttl: number = 3600): Promise<void> {
  try {
    if (redisClient && redisClient.status === 'ready') {
      await redisClient.set(key, JSON.stringify(value), 'EX', ttl);
      log.trace(`💾 Redis SET ${key}`);
      return;
    }
  } catch (e) {
    log.warn(`⚠️ Redis SET failed for ${key}`, e);
  }
  // Fallback to memory cache
  setMemoryCache(key, value, ttl);
}

export async function getRedisCache(key: string): Promise<unknown> {
  // Check memory first
  const mem = getMemoryCache(key);
  if (mem) return mem;

  try {
    if (redisClient && redisClient.status === 'ready') {
      const raw = await redisClient.get(key);
      if (raw) {
        const parsed = JSON.parse(raw);
        log.trace(`📦 Redis GET ${key}`);
        return parsed;
      }
    }
  } catch (e) {
    log.warn(`⚠️ Redis GET failed for ${key}`, e);
  }
  return null;
}

export async function deleteRedisCache(key: string): Promise<void> {
  try {
    if (redisClient && redisClient.status === 'ready') {
      await redisClient.del(key);
      log.trace(`🗑️ Redis DEL ${key}`);
    }
  } catch (e) {
    log.warn(`⚠️ Redis DEL failed for ${key}`, e);
  }
  memoryCache.delete(key);
}

// Scrape result cache settings
const SCRAPE_CACHE_TTL = parseInt(process.env.SCRAPING_CACHE_TTL || '3600', 10); // 1 hour default

export interface CachedScrapeEntry {
  url: string;
  result: {
    title: string | null;
    content: string;
    metadata: Record<string, unknown>;
  };
  scrapedAt: string;
}

// Scrape cache metrics
export const scrapeCacheMetrics = {
  hits: 0,
  misses: 0,
  errors: 0,
  bytesServed: 0,
};

export async function getCachedScrape(url: string): Promise<CachedScrapeEntry | null> {
  const cacheKey = `scrape:cache:${url}`;
  const cached = await getRedisCache(cacheKey);
  if (cached) {
    scrapeCacheMetrics.hits++;
    const entry = cached as CachedScrapeEntry;
    scrapeCacheMetrics.bytesServed += entry.result.content.length;
    log.info(`📦 Scrape cache hit for: ${url}`);
    return entry;
  }
  scrapeCacheMetrics.misses++;
  return null;
}

export async function setCachedScrape(url: string, result: {
  title: string | null;
  content: string;
  metadata?: Record<string, unknown>;
}): Promise<void> {
  const cacheKey = `scrape:cache:${url}`;
  const entry: CachedScrapeEntry = {
    url,
    result: { ...result, metadata: result.metadata ?? {} },
    scrapedAt: new Date().toISOString(),
  };
  await setRedisCache(cacheKey, entry, SCRAPE_CACHE_TTL);
  log.info(`💾 Cached scrape result for: ${url}`);
}

export async function invalidateScrapeCache(url: string): Promise<void> {
  scrapeCacheMetrics.misses++;
  await deleteRedisCache(`scrape:cache:${url}`);
  log.info(`🗑️ Invalidated scrape cache for: ${url}`);
}

// ── Cache Metrics ────────────────────────────────────────────────────

interface CacheMetrics {
  redisConnected: boolean;
  memoryCacheSize: number;
}

export function getCacheMetrics(): CacheMetrics {
  return {
    redisConnected: !!redisClient && redisClient.status === 'ready',
    memoryCacheSize: memoryCache.size,
  };
}

export interface ScrapeCacheMetrics {
  hits: number;
  misses: number;
  errors: number;
  bytesServed: number;
  hitRate: number;
  totalRequests: number;
}

export function getScrapeCacheMetrics(): ScrapeCacheMetrics {
  const total = scrapeCacheMetrics.hits + scrapeCacheMetrics.misses;
  return {
    hits: scrapeCacheMetrics.hits,
    misses: scrapeCacheMetrics.misses,
    errors: scrapeCacheMetrics.errors,
    bytesServed: scrapeCacheMetrics.bytesServed,
    hitRate: total > 0 ? (scrapeCacheMetrics.hits / total) : 0,
    totalRequests: total,
  };
}
