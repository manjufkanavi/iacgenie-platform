import axios from "axios";
import { getCachedSearch, setCachedSearch } from "./cache.js";
import { SearchResult } from "./types.js";
import { log } from "./logger.js";
import { getProxyUrl, recordSuccess, recordFailure } from "./proxy.js";

export type { SearchResult };

const SEARXNG_URL = process.env.SEARXNG_URL || "http://iacgenie-searxng:8080";

export async function search(query: string, limit?: number): Promise<SearchResult[]> {
  try {
    log.debug(`🔍 Starting search for query: "${query}"`);

    // Check cache first
    const cachedResults = await getCachedSearch(query);
    if (cachedResults) {
      log.info(`📦 Cache hit for query: "${query}"`);
      return cachedResults.slice(0, limit);
    }

    log.info(`🌐 Querying SearXNG for: "${query}"`);

    // Try with proxy rotation
    const proxyUrl = getProxyUrl();
    let results: SearchResult[] = [];
    let lastError: Error | null = null;

    if (proxyUrl) {
      // Try with proxy first
      try {
        const proxyAxios = axios.create({
          proxy: {
            protocol: new URL(proxyUrl).protocol.replace(':', ''),
            host: new URL(proxyUrl).hostname,
            port: parseInt(new URL(proxyUrl).port || '8080'),
            auth: new URL(proxyUrl).username ? {
              username: new URL(proxyUrl).username,
              password: new URL(proxyUrl).password,
            } : undefined,
          },
          timeout: 15000,
        });

        const res = await proxyAxios.get(`${SEARXNG_URL}/search`, {
          params: { q: query, format: 'json', categories: 'general' },
          headers: { 'Accept': 'application/json' },
          timeout: 15000,
        });

        results = res.data.results.map((r: any) => ({
          title: r.title,
          url: r.url,
          snippet: r.content,
          engine: r.engine || "unknown"
        }));

        recordSuccess(proxyUrl);
        log.info(`✅ Search succeeded via proxy: ${proxyUrl}`);
      } catch (proxyErr) {
        lastError = proxyErr as Error;
        recordFailure(proxyUrl);
        log.warn(`⚠️ Proxy search failed: ${(proxyErr as Error).message}, trying direct`);
      }
    }

    // Fallback to direct request if proxy failed or no proxy configured
    if (results.length === 0) {
      try {
        const res = await axios.get(`${SEARXNG_URL}/search`, {
          params: { q: query, format: 'json', categories: 'general' },
          headers: { 'Accept': 'application/json' },
          timeout: 15000,
        });

        results = res.data.results.map((r: any) => ({
          title: r.title,
          url: r.url,
          snippet: r.content,
          engine: r.engine || "unknown"
        }));

        log.info(`✅ Search succeeded via direct connection`);
      } catch (directErr) {
        lastError = directErr as Error;
        log.error(`❌ Direct search also failed: ${(directErr as Error).message}`);
      }
    }

    // Apply limit
    if (limit && results.length > limit) {
      results = results.slice(0, limit);
    }

    if (results.length === 0) {
      log.warn(`⚠️ No search results for "${query}" — SearXNG may need configuration check`);
      if (lastError) {
        throw new Error(`Search failed: ${lastError.message}`);
      }
    }

    log.info(`📊 Received ${results.length} search results for "${query}"`);

    // Cache the results
    await setCachedSearch(query, results);

    return results;
  } catch (error) {
    log.error("❌ Search error", error);
    throw new Error("Search failed");
  }
}
