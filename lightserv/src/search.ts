import axios from "axios";
import { getCachedSearch, setCachedSearch } from "./cache.js";
import { SearchResult } from "./types.js";
import { log } from "./logger.js";

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

    const res = await axios.get(`${SEARXNG_URL}/search`, {
      params: { q: query, format: 'json', categories: 'general' },
      headers: { 'Accept': 'application/json' },
      timeout: 15000,
    });

    let results = res.data.results.map((r: any) => ({
      title: r.title,
      url: r.url,
      snippet: r.content,
      engine: r.engine || "unknown"
    }));

    // Apply limit
    if (limit && results.length > limit) {
      results = results.slice(0, limit);
    }

    if (results.length === 0) {
      log.warn(`⚠️ No search results for "${query}" — SearXNG may need configuration check`);
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
