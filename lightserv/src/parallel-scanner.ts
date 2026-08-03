/**
 * Parallel Scanner — concurrent search + scrape with configurable concurrency.
 *
 * Usage:
 *   parallelSearchScrape({ query: 'AI agents', scrapeCount: 5, scrapeConcurrency: 3 })
 *     → runs all SearXNG queries in parallel, then scrapes top N results
 *       with concurrency control (each URL gets its own LightPanda MCP process).
 *
 *   parallelDeepScan({ queries: [...], scrapeCount: 10, scrapeConcurrency: 4 })
 *     → same but with predefined query list.
 *
 * Config via env:
 * - SCRAPE_CONCURRENCY: max parallel LightPanda scrapes (default: 4)
 * - SEARCH_CONCURRENCY: max parallel search queries (default: 10)
 *
 * All scraping uses LightPanda MCP exclusively — no fallback extractors.
 */

import { search, type SearchResult } from './search.js';
import { scrape as scrapeLightPanda } from './lightpanda-scrape.js';
import { log } from './logger.js';

export interface ScrapeConfig {
  url: string;
  timeoutMs?: number;
}

export interface SearchScrapeQuery {
  query: string;
  results: SearchResult[];
}

export interface ParallelSearchScrapeInput {
  query: string;
  scrapeCount?: number;       // how many search results to scrape (default: 5)
  scrapeConcurrency?: number; // max concurrent scrapes (default: 4)
  maxResults?: number;        // max SearXNG results per query (default: 20)
  scrapeTimeoutMs?: number;   // per-page scrape timeout (default: 30000)
}

export interface ParallelDeepScanInput {
  queries: string[];
  scrapeCount?: number;
  scrapeConcurrency?: number;
  maxResults?: number;
  scrapeTimeoutMs?: number;
}

export interface ScrapeEntry {
  url: string;
  title: string | null;
  content: string | null;
  contentLength: number;
  responseTime: number;
  query: string;
  queryIndex: number;
}

export interface ParallelSearchScrapeResult {
  input: {
    queries: string[];
    scrapeCount: number;
    scrapeConcurrency: number;
  };
  searchResults: SearchScrapeQuery[];
  scraped: ScrapeEntry[];
  stats: {
    totalUrls: number;
    scrapedCount: number;
    failedCount: number;
    avgResponseTime: number;
    totalTimeMs: number;
    searchQueries: number;
    pagesCrawled: number;
    pagesSucceeded: number;
    pagesFailed: number;
  };
}

// ── Concurrency runner ─────────────────────────────────────────────────

async function pMap<T, R>(items: T[], fn: (item: T, index: number) => Promise<R>, concurrency: number): Promise<ReadonlyArray<R | undefined>> {
  const results: R[] = new Array(items.length);
  let index = 0;

  const workers = Array.from({ length: Math.min(concurrency, items.length) }, async () => {
    while (index < items.length) {
      const i = index++;
      try {
        results[i] = await fn(items[i], i);
      } catch (err) {
        log.warn(`pMap error at index ${i}`, err instanceof Error ? err : new Error(String(err)));
        results[i] = undefined as R;
      }
    }
  });

  await Promise.all(workers);
  return results;
}

// ── Single URL scrape ──────────────────────────────────────────────────

async function scrapeUrl(url: string, timeoutMs: number, query: string, queryIndex: number): Promise<ScrapeEntry> {
  const start = Date.now();

  try {
    const result = await scrapeLightPanda(url, timeoutMs);
    if (result && result.content && result.content.length > 20) {
      return {
        url,
        title: result.title,
        content: result.content,
        contentLength: result.content.length,
        responseTime: Date.now() - start,
        query,
        queryIndex,
      };
    }
  } catch (err) {
    log.warn(`⚠️ LightPanda scrape failed: ${url}`, err instanceof Error ? err : new Error(String(err)));
  }

  return {
    url,
    title: null,
    content: null,
    contentLength: 0,
    responseTime: Date.now() - start,
    query,
    queryIndex,
  };
}

// ── Parallel search + scrape ───────────────────────────────────────────

export async function parallelSearchScrape(input: ParallelSearchScrapeInput): Promise<ParallelSearchScrapeResult> {
  const start = Date.now();
  const scrapeCount = input.scrapeCount || 5;
  const scrapeConcurrency = input.scrapeConcurrency || parseInt(process.env.SCORER_CONCURRENCY || '4', 10);
  const maxResults = input.maxResults || 20;
  const timeoutMs = input.scrapeTimeoutMs || 30000;

  log.info(`🚀 Parallel scan: query="${input.query}", scrapeCount=${scrapeCount}, concurrency=${scrapeConcurrency}`);

  // 1. Search in parallel
  log.info('🔎 Searching...');
  const searchResult = await search(input.query, maxResults);

  const searchScrapeQuery: SearchScrapeQuery = {
    query: input.query,
    results: searchResult,
  };

  // 2. Pick top URLs to scrape
  const urlsToScrape = searchResult
    .slice(0, scrapeCount)
    .map((r: any) => ({ url: r.url, query: input.query, queryIndex: 0 }));

  log.info(`📄 Scraping ${urlsToScrape.length} URLs with concurrency ${scrapeConcurrency}`);

  // 3. Scrape in parallel with concurrency control (LightPanda only)
  const scrapeResults = await pMap(
    urlsToScrape,
    async (item: { url: string; query: string; queryIndex: number }, i: number) => scrapeUrl(item.url, timeoutMs, input.query, i),
    scrapeConcurrency,
  );

  const filteredResults = scrapeResults.filter((r): r is ScrapeEntry => r !== undefined);
  const totalTime = Date.now() - start;

  const stats = {
    totalUrls: urlsToScrape.length,
    scrapedCount: filteredResults.length,
    failedCount: filteredResults.filter((r) => r.content === null).length,
    avgResponseTime: Math.round(filteredResults.reduce((s, r) => s + r.responseTime, 0) / Math.max(filteredResults.length, 1)),
    totalTimeMs: totalTime,
    searchQueries: 1,
    pagesCrawled: filteredResults.length,
    pagesSucceeded: filteredResults.filter((r) => r.content !== null).length,
    pagesFailed: filteredResults.filter((r) => r.content === null).length,
  };

  log.info(`✅ Parallel scan complete: ${stats.pagesSucceeded}/${stats.pagesCrawled} succeeded in ${totalTime}ms`);

  return {
    input: { queries: [input.query], scrapeCount, scrapeConcurrency },
    searchResults: [searchScrapeQuery],
    scraped: filteredResults,
    stats,
  };
}

// ── Deep scan (multiple queries) ───────────────────────────────────────

export async function parallelDeepScan(input: ParallelDeepScanInput): Promise<ParallelSearchScrapeResult> {
  const start = Date.now();
  const scrapeCount = input.scrapeCount || 5;
  const scrapeConcurrency = input.scrapeConcurrency || parseInt(process.env.SCORER_CONCURRENCY || '4', 10);
  const maxResults = input.maxResults || 10;
  const timeoutMs = input.scrapeTimeoutMs || 30000;

  log.info(`🚀 Deep scan: ${input.queries.length} queries, scrapeCount=${scrapeCount}, concurrency=${scrapeConcurrency}`);

  const allSearchResults: SearchScrapeQuery[] = [];
  const allScraped: ScrapeEntry[] = [];
  let queryIndex = 0;

  for (const query of input.queries) {
    const searchResult = await search(query, maxResults);
    allSearchResults.push({ query, results: searchResult });

    const urlsToScrape = searchResult.slice(0, scrapeCount).map((r) => ({ url: r.url, query, queryIndex }));
    const scrapeResults = await pMap(
      urlsToScrape,
      (item) => scrapeUrl(item.url, timeoutMs, query, item.queryIndex),
      scrapeConcurrency,
    );
    allScraped.push(...scrapeResults.filter((r): r is ScrapeEntry => r !== undefined));
    queryIndex++;
  }

  const totalTime = Date.now() - start;
  const pagesSucceeded = allScraped.filter((r) => r.content !== null).length;
  const pagesFailed = allScraped.filter((r) => r.content === null).length;

  log.info(`✅ Deep scan complete: ${pagesSucceeded} succeeded, ${pagesFailed} failed in ${totalTime}ms`);

  return {
    input: { queries: input.queries, scrapeCount, scrapeConcurrency },
    searchResults: allSearchResults,
    scraped: allScraped,
    stats: {
      totalUrls: allScraped.length,
      scrapedCount: allScraped.length,
      failedCount: pagesFailed,
      avgResponseTime: Math.round(allScraped.reduce((s, r) => s + r.responseTime, 0) / Math.max(allScraped.length, 1)),
      totalTimeMs: totalTime,
      searchQueries: input.queries.length,
      pagesCrawled: allScraped.length,
      pagesSucceeded,
      pagesFailed,
    },
  };
}
