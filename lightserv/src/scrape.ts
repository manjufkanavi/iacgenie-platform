/**
 * Web scraping — LightPanda MCP extraction with caching and proxy support.
 */

import { processScrapeJobSync } from "./queue.js";
import { ScrapeResult } from "./types.js";
import { log } from "./logger.js";
import { getCachedScrape, setCachedScrape, scrapeCacheMetrics, CachedScrapeEntry } from "./cache.js";
import { shutdownProxyPool } from "./proxy.js";
import { smartScrape } from "./pagezen.js";

/**
 * Scrape a URL and extract readable content.
 * @param url - URL to scrape
 * @param useAsync - If true, process via NSQ job queue
 */
export async function scrapePage(url: string, useAsync: boolean = false): Promise<ScrapeResult> {
  log.info(`📄 Starting scrape for URL: ${url}`, { async: useAsync });

  if (useAsync) {
    try {
      log.debug(`📤 Processing async scrape job for: ${url}`);
      const jobId = `scrape_${Date.now()}`;
      const result = await processScrapeJobSync(jobId, url, (_jId: string, jUrl: string) =>
        scrapePageSync(jUrl)
      );
      return {
        ...result,
        metadata: {
          ...result.metadata,
          processingMethod: 'async'
        }
      };
    } catch (error) {
      log.warn(`⚠️ Async scrape failed, retrying synchronously: ${url}`, error);
      return await scrapePageSync(url);
    }
  }

  return await scrapePageSync(url);
}

async function scrapePageSync(url: string): Promise<ScrapeResult> {
  // Check Redis cache first (skip for async jobs to get fresh content)
  let cached: CachedScrapeEntry | null = null;
  try {
    cached = await getCachedScrape(url);
  } catch (error) {
    log.warn(`⚠️ Cache read error for: ${url}`, error);
    scrapeCacheMetrics.errors++;
  }

  if (cached) {
    log.info(`📦 Returning cached scrape result for: ${url}`);
    const meta = cached.result.metadata as Record<string, unknown>;
    return {
      title: cached.result.title,
      content: cached.result.content,
      excerpt: meta.excerpt as string | undefined || null,
      byline: meta.byline as string | undefined || null,
      siteName: meta.siteName as string | undefined || null,
      length: meta.length as number | undefined || null,
      publishedTime: meta.publishedTime as string | undefined || null,
      metadata: {
        extractionMethod: 'cached',
        scrapedAt: cached.scrapedAt,
        ...meta,
      }
    };
  }

  try {
    log.debug(`🔍 Starting synchronous scrape for: ${url}`);
    const result = await smartScrape(url);

    // Cache the result
    await setCachedScrape(url, {
      title: result.title,
      content: result.content || '',
      metadata: result.metadata,
    });

    return result;
  } catch (error) {
    log.error(`❌ Scrape error for: ${url}`, error);
    throw new Error("Scraping failed");
  }
}

// Export metrics for server.ts /metrics endpoint
export function getCacheMetrics() {
  return {
    ...scrapeCacheMetrics,
    cacheType: 'scrape',
  };
}

// Graceful shutdown
export function shutdown() {
  log.info("🛑 Shutting down scraper...");
  shutdownProxyPool();
}
