/**
 * Deep Research Engine
 * 
 * Autonomous multi-step research using LightSerp MCP search + scrape.
 * Generates diverse queries, crawls pages, deduplicates, and produces
 * a structured deep research report.
 * 
 * Phase 3 feature — LightSerp modular development.
 */

import crypto from 'crypto';
import { log } from './logger.js';
import type { SearchResult as BaseSearchResult, ScrapeResult as BaseScrapeResult } from './types.js';

// ─── Configuration ────────────────────────────────────────────────────────────

const DEFAULT_CONFIG = {
  MAX_QUERIES_PER_TOPIC: 30,
  MIN_PAGES_PER_QUERY: 20,
  MAX_PAGES_PER_QUERY: 50,
  BATCH_SIZE: 5,
  SEARCH_DELAY_MS: 3000,
  SCRAPE_DELAY_MS: 2000,
  MAX_TOTAL_PAGES: 100,
  MIN_WORD_COUNT: 50,
  QUERY_CATEGORIES: [
    'definition_overview',
    'technical_deep_dive',
    'industry_applications',
    'comparative_analysis',
    'trends_future',
    'challenges_limitations',
    'data_statistics',
    'case_studies',
    'resources_tools',
    'expert_perspectives',
  ],
};

// Use environment variables, never hardcoded local paths
const RESEARCH_HTTP_PORT = process.env.HTTP_PORT || '3000';

// ─── Query Generation ────────────────────────────────────────────────────────

/**
 * Generate diverse search queries for a given topic.
 * Returns an array of query strings covering multiple dimensions.
 */
export function generateSearchQueries(topic: string, count: number = 20): string[] {
  const queries: string[] = [];
  
  // Category 1: Definition & Overview
  queries.push(`What is ${topic} and how does it work`);
  queries.push(`${topic} explained simply`);
  queries.push(`Introduction to ${topic}`);
  queries.push(`${topic} fundamentals basics overview`);
  queries.push(`How ${topic} works step by step`);
  
  // Category 2: Technical Deep Dive
  queries.push(`Technical architecture of ${topic}`);
  queries.push(`How ${topic} works under the hood`);
  queries.push(`${topic} technical specifications details`);
  queries.push(`${topic} implementation methodology`);
  
  // Category 3: Industry & Applications
  queries.push(`${topic} industry applications 2025 2026`);
  queries.push(`Real world examples of ${topic}`);
  queries.push(`${topic} use cases by industry`);
  queries.push(`Companies using ${topic} case studies`);
  
  // Category 4: Comparative Analysis
  queries.push(`${topic} vs alternatives comparison`);
  queries.push(`Best ${topic} tools frameworks 2025`);
  queries.push(`${topic} comparison benchmark`);
  
  // Category 5: Trends & Future
  queries.push(`${topic} future trends outlook`);
  queries.push(`Emerging ${topic} technologies`);
  queries.push(`${topic} market forecast growth`);
  queries.push(`${topic} what's next evolution`);
  
  // Category 6: Challenges & Limitations
  queries.push(`${topic} challenges and limitations`);
  queries.push(`Problems with ${topic}`);
  queries.push(`${topic} criticism drawbacks`);
  
  // Category 7: Data & Statistics
  queries.push(`${topic} market size statistics data`);
  queries.push(`${topic} adoption rates growth rate`);
  
  // Category 8: Resources & Best Practices
  queries.push(`${topic} best practices guide`);
  queries.push(`${topic} learning resources tutorials`);
  
  // Category 9: Expert Perspectives
  queries.push(`Expert analysis on ${topic}`);
  queries.push(`${topic} research papers academic perspective`);
  
  // Category 10: Specific sub-queries (for broad topics, add specificity)
  if (topic.split(' ').length <= 3) {
    // Add a few more targeted queries for shorter topic names
    queries.push(`Comprehensive guide to ${topic}`);
    queries.push(`${topic} complete overview 2025`);
  }
  
  // Deduplicate and trim to requested count
  const unique = [...new Set(queries)];
  return unique.slice(0, count);
}

/**
 * Execute a search query via LightSerp MCP.
 * Returns an array of search results.
 */
export async function searchWithMCP(query: string): Promise<BaseSearchResult[]> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000);

  try {
    const url = `http://localhost:${RESEARCH_HTTP_PORT}/api/search?q=${encodeURIComponent(query)}`;
    const response = await fetch(url, { signal: controller.signal });

    if (!response.ok) {
      log.warn(`Search API returned ${response.status}`, { url, query });
      return [];
    }

    const data = await response.json();
    return Array.isArray(data) ? data : [];
  } catch (err) {
    log.warn(`Search API request failed`, { query, error: err instanceof Error ? err.message : String(err) });
    return [];
  } finally {
    clearTimeout(timeoutId);
  }
}

/**
 * Scrape a URL using LightSerp MCP.
 * Returns a ScrapeResult object.
 */
export async function scrapeWithMCP(url: string): Promise<BaseScrapeResult> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000);

  try {
    const apiUrl = `http://localhost:${RESEARCH_HTTP_PORT}/api/scrape?url=${encodeURIComponent(url)}`;
    const response = await fetch(apiUrl, { signal: controller.signal });

    if (!response.ok) {
      log.warn(`Scrape API returned ${response.status}`, { url });
      return {
        title: url,
        content: '',
        excerpt: null, byline: null, siteName: null, length: 0, publishedTime: null,
        metadata: { extractionMethod: 'error', extractionTime: '', responseTime: 30000, url, wordCount: 0, language: 'unknown' },
      };
    }

    const data = await response.json();
    if (data && typeof data === 'object' && 'content' in data) {
      return data as BaseScrapeResult;
    }

    return {
      title: url,
      content: '',
      excerpt: null, byline: null, siteName: null, length: 0, publishedTime: null,
      metadata: { extractionMethod: 'invalid_response', extractionTime: '', responseTime: 0, url, wordCount: 0, language: 'unknown' },
    };
  } catch (err) {
    log.warn(`Scrape API request failed`, { url, error: err instanceof Error ? err.message : String(err) });
    return {
      title: url,
      content: '',
      excerpt: null, byline: null, siteName: null, length: 0, publishedTime: null,
      metadata: { extractionMethod: 'error', extractionTime: '', responseTime: 30000, url, wordCount: 0, language: 'unknown' },
    };
  } finally {
    clearTimeout(timeoutId);
  }
}

// ─── URL Utility Functions ───────────────────────────────────────────────────

/**
 * Normalize a URL for deduplication.
 */
export function normalizeUrl(url: string): string {
  try {
    const u = new URL(url);
    u.search = ''; // Strip query parameters
    u.hash = ''; // Strip hash
    return u.href.toLowerCase().replace(/\/$/, '');
  } catch {
    return url.toLowerCase().replace(/\/$/, '');
  }
}

/**
 * Generate a hash for a URL (for file naming).
 */
export function urlHash(url: string): string {
  return crypto.createHash('md5').update(url).digest('hex').substring(0, 12);
}

// ─── Report Generation ───────────────────────────────────────────────────────

interface ResearchSource {
  url: string;
  title: string;
  type: string; // 'academic', 'industry', 'news', 'community', 'official'
  relevance: number; // 1-5
  quality: string; // 'high', 'medium', 'low'
  keyFinding: string;
  content: string;
}

interface ResearchReport {
  topic: string;
  slug: string;
  date: string;
  searchQueries: string[];
  sourcesCrawled: number;
  sources: ResearchSource[];
  executiveSummary: string;
  sections: { title: string; content: string }[];
  confidence: { finding: string; level: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNCERTAIN' }[];
  limitations: string[];
}

/**
 * Classify the type of a URL.
 */
export function classifySource(url: string, _title: string): string {
  const u = url.toLowerCase();
  if (u.includes('arxiv') || u.includes('doi') || u.includes('.edu') || u.includes('scholar')) {
    return 'academic';
  }
  if (u.includes('medium') || u.includes('techcrunch') || u.includes('blog')) {
    return 'industry';
  }
  if (u.includes('reddit') || u.includes('stackoverflow') || u.includes('hacker')) {
    return 'community';
  }
  if (u.includes('.gov') || u.includes('.in') || u.includes('government')) {
    return 'official';
  }
  if (u.includes('reuters') || u.includes('bloomberg') || u.includes('bbc') || u.includes('wire')) {
    return 'news';
  }
  if (u.includes('wikipedia')) {
    return 'encyclopedia';
  }
  return 'general';
}

/**
 * Extract the domain from a URL.
 */
export function extractDomain(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

// ─── Main Research Orchestrator ──────────────────────────────────────────────

export interface ResearchProgress {
  phase: string;
  message: string;
  progress: number; // 0-100
  current: number;
  total: number;
}

/**
 * Execute the full deep research pipeline.
 * This is the main entry point for the deep research engine.
 */
export async function executeDeepResearch(
  topic: string,
  config: Partial<typeof DEFAULT_CONFIG> = {}
): Promise<ResearchReport> {
  const merged = { ...DEFAULT_CONFIG, ...config };
  const slug = topic.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  
  console.error(`🔍 Deep Research: ${topic}`);
  console.error(`📝 Generating search queries...`);

  // Phase 1: Generate queries
  const queries = generateSearchQueries(topic, merged.MAX_QUERIES_PER_TOPIC);
  console.error(`📋 Generated ${queries.length} search queries`);

  // Phase 2: Execute searches
  const searchResults: { query: string; results: BaseSearchResult[] }[] = [];
  const allUrls = new Map<string, BaseSearchResult>(); // Dedup by URL
  
  for (let i = 0; i < queries.length; i += merged.BATCH_SIZE) {
    const batch = queries.slice(i, i + merged.BATCH_SIZE);
    console.error(`🔎 Searching batch ${Math.floor(i / merged.BATCH_SIZE) + 1}/${Math.ceil(queries.length / merged.BATCH_SIZE)}...`);
    
    for (const query of batch) {
      try {
        const results = await searchWithMCP(query);
        searchResults.push({ query, results });
        
        // Collect unique URLs
        for (const r of results) {
          const normalized = normalizeUrl(r.url);
          if (!allUrls.has(normalized)) {
            allUrls.set(normalized, r);
          }
        }
      } catch (err) {
        console.error(`  ⚠️  Search failed for: ${query}`);
      }
    }
    
    // Delay between batches
    if (i + merged.BATCH_SIZE < queries.length) {
      await new Promise(r => setTimeout(r, merged.SEARCH_DELAY_MS));
    }
  }
  
  console.error(`📊 Collected ${allUrls.size} unique URLs from ${queries.length} queries`);

  // Phase 3: Select and crawl URLs
  const selectedUrls: BaseSearchResult[] = [];
  const crawledSources: ResearchSource[] = [];
  
  // Strategy: Pick top results from each query, prioritizing diversity
  for (const sr of searchResults) {
    if (selectedUrls.length >= merged.MAX_TOTAL_PAGES) break;
    
    // Get top 5 from this query's results
    const topResults = sr.results.slice(0, 5);
    for (const r of topResults) {
      const normalized = normalizeUrl(r.url);
      if (!selectedUrls.find(s => normalizeUrl(s.url) === normalized)) {
        selectedUrls.push(r);
      }
      if (selectedUrls.length >= merged.MAX_TOTAL_PAGES) break;
    }
  }
  
  // Scrape selected URLs
  console.error(`📄 Crawling ${Math.min(selectedUrls.length, merged.MAX_TOTAL_PAGES)} pages...`);
  
  for (let i = 0; i < selectedUrls.length; i++) {
    if (crawledSources.length >= merged.MAX_TOTAL_PAGES) break;
    const urlInfo = selectedUrls[i];
    
    try {
      console.error(`  [${i + 1}/${selectedUrls.length}] Crawling: ${extractDomain(urlInfo.url)}`);
      const scraped = await scrapeWithMCP(urlInfo.url);
      
      // Skip low-quality content
      const content = scraped.content ?? '';
      const wordCount = Number(scraped.metadata?.wordCount) || content.split(/\s+/).length;
      if (wordCount < merged.MIN_WORD_COUNT) {
        console.error(`    ⚠️  Low quality (${wordCount} words), skipping`);
        continue;
      }
      
      // Classify and store
      const sourceType = classifySource(urlInfo.url, urlInfo.title);
      crawledSources.push({
        url: urlInfo.url,
        title: urlInfo.title,
        type: sourceType,
        relevance: 4, // Default high; refine during synthesis
        quality: ['academic', 'official', 'news'].includes(sourceType) ? 'high' : 'medium',
        keyFinding: scraped.excerpt ?? scraped.content?.substring(0, 200) ?? '',
        content: scraped.content ?? '',
      });
      
      console.error(`    ✓ ${sourceType} (${wordCount} words, ${scraped.metadata?.extractionMethod || 'unknown'} method)`);
    } catch (err) {
      console.error(`    ⚠️  Scrape failed: ${urlInfo.url}`);
    }
    
    // Delay between scrapes
    if (i + 1 < selectedUrls.length) {
      await new Promise(r => setTimeout(r, merged.SCRAPE_DELAY_MS));
    }
  }
  
  console.error(`✅ Crawled ${crawledSources.length} quality pages`);
  
  // Phase 4: Build the research report
  const report = buildResearchReport(topic, slug, queries, crawledSources);
  
  console.error(`📝 Report generated: ${report.sections.length} sections, ${report.sourcesCrawled} sources`);
  return report;
}

/**
 * Build a structured research report from collected sources.
 */
function buildResearchReport(
  topic: string,
  slug: string,
  searchQueries: string[],
  sources: ResearchSource[]
): ResearchReport {
  const date = new Date().toISOString().split('T')[0];
  
  // Group sources by category
  const byType: Record<string, ResearchSource[]> = {};
  for (const s of sources) {
    if (!byType[s.type]) byType[s.type] = [];
    byType[s.type].push(s);
  }
  
  // Build the report structure
  const report: ResearchReport = {
    topic,
    slug,
    date,
    searchQueries,
    sourcesCrawled: sources.length,
    sources,
    executiveSummary: `[Executive summary will be generated by AI after review of ${sources.length} sources.]`,
    sections: [],
    confidence: [],
    limitations: [`Research based on ${sources.length} crawled sources across multiple search engines.`],
  };

  // Define standard report sections
  const sectionTemplates = [
    { title: 'Executive Summary', weight: 0 },
    { title: 'Introduction & Background', weight: 1 },
    { title: 'Core Concepts & Fundamentals', weight: 2 },
    { title: 'Current State & Landscape', weight: 3 },
    { title: 'Applications & Use Cases', weight: 4 },
    { title: 'Technical Deep Dive', weight: 5 },
    { title: 'Comparative Analysis & Alternatives', weight: 6 },
    { title: 'Key Players & Stakeholders', weight: 7 },
    { title: 'Challenges, Risks & Limitations', weight: 8 },
    { title: 'Future Outlook & Trends', weight: 9 },
    { title: 'Expert Perspectives & Consensus', weight: 10 },
    { title: 'Data & Statistics', weight: 11 },
    { title: 'Resources & Further Reading', weight: 12 },
  ];
  
  report.sections = sectionTemplates.map(s => ({
    title: s.title,
    content: `[Section content will be populated by AI synthesizing ${sources.length} sources across ${Object.keys(byType).length} source types.]`,
  }));

  return report;
}

/**
 * Generate the final markdown report string.
 */
export function generateReportMarkdown(report: ResearchReport): string {
  const { topic, date, searchQueries, sourcesCrawled, sources, sections } = report;
  
  let md = `# DEEP RESEARCH REPORT: ${topic.toUpperCase()}\n\n`;
  md += `**Generated:** ${date}\n`;
  md += `**Topic:** ${topic}\n`;
  md += `**Research Depth:** Comprehensive\n`;
  md += `**Sources Crawled:** ${sourcesCrawled}\n`;
  md += `**Search Queries:** ${searchQueries.length}\n\n`;
  md += `---\n\n`;
  
  // Sources table
  md += `## Sources & Methodology\n\n`;
  md += `### Search Queries Executed (${searchQueries.length})\n\n`;
  for (const q of searchQueries) {
    md += `- \`${q}\`\n`;
  }
  md += `\n`;
  
  md += `### Sources Crawled (${sourcesCrawled})\n\n`;
  md += `| # | URL | Type | Quality | Key Finding |\n`;
  md += `|---|-----|------|---------|-------------|\n`;
  for (let i = 0; i < Math.min(sources.length, 50); i++) {
    const s = sources[i];
    md += `| ${i + 1} | [${s.url.substring(0, 60)}...](${s.url}) | ${s.type} | ${s.quality} | ${s.keyFinding.substring(0, 80)}... |\n`;
  }
  md += `\n`;
  
  md += `---\n\n`;
  
  // Sections
  for (const section of sections) {
    md += `## ${section.title}\n\n`;
    md += `${section.content}\n\n`;
  }
  
  md += `---\n\n`;
  md += `*Report generated by Deep Research Agent using LightSerp MCP*\n`;
  md += `*Search engines: Google, Bing, Brave, DuckDuckGo, Startpage, Mojeek*\n`;
  md += `*Crawl date: ${date}*\n`;
  
  return md;
}
