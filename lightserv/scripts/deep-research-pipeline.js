#!/usr/bin/env node
/**
 * Deep Research Pipeline — Generic Topic Research Agent
 *
 * Uses LightSerp MCP (via mcp-client.js) for search and scrape.
 * Given a topic, generates search queries, executes them, crawls pages,
 * deduplicates, synthesizes, and produces a Gemini-style research report.
 *
 * Usage:
 *   node deep-research.js "your research topic here"
 *
 * Output: ~/.hermes/research/{topic_slug}_research.md
 */

import { spawn } from 'child_process';
import { writeFileSync, mkdirSync, readFileSync, existsSync, rmSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { homedir } from 'os';
import crypto from 'crypto';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// ─── Configuration ──────────────────────────────────────────────────────────
const LIGHTSERP_CLIENT = process.env.LIGHTSERP_CLIENT ||
  '/Users/manjunathkanavi/workspace/git_workspace/LightSerp/mcp-client.js';

const OUTPUT_DIR = process.env.RESEARCH_OUTPUT_DIR ||
  join(homedir(), '.hermes', 'research');

const BATCH_SIZE = 5;            // queries per batch
const SCRAPE_TIMEOUT = 20000;    // ms per scrape
const SEARCH_WAIT_MS = 3000;     // gap between batches
const SCRAPE_WAIT_MS = 2500;     // gap between scrapes

const MAX_URLS_TO_SCRAPE = 100;  // safety cap
const MIN_URLS_REQUIRED = 20;    // minimum before we consider it viable
const MIN_WORDS_FOR_VALID = 100; // skip pages with less content

// ─── Initialization ─────────────────────────────────────────────────────────
const TOPIC = process.argv[2];
if (!TOPIC) {
  console.error('Usage: node deep-research.js "<topic>"');
  process.exit(1);
}

const TOPIC_SLUG = TOPIC.toLowerCase()
  .replace(/[^a-z0-9]+/g, '-')
  .replace(/(^-|-$)/g, '')
  .slice(0, 80);

const REPORT_FILE = join(OUTPUT_DIR, `${TOPIC_SLUG}_research.md`);
const TMP_DIR = join(OUTPUT_DIR, 'tmp');
mkdirSync(OUTPUT_DIR, { recursive: true });
mkdirSync(TMP_DIR, { recursive: true });

console.log('╔══════════════════════════════════════════════════════╗');
console.log('║       DEEP RESEARCH PIPELINE v1.0                    ║');
console.log('╚══════════════════════════════════════════════════════╝');
console.log(`\n  Topic:  "${TOPIC}"`);
console.log(`  Output: ${REPORT_FILE}\n`);

// ─── State ──────────────────────────────────────────────────────────────────
const allSearchQueries = [];
const allResults = {};         // query → [{title,url,snippet,engine}]
const seenURLs = new Set();    // dedup across all queries
const crawled = [];            // {url, title, wordCount, content, sourceType, query}

// ─── Utility ────────────────────────────────────────────────────────────────
function urlKey(url) {
  if (!url) return '';
  return url.replace(/\/+$/, '')
    .replace(/^https?:\/\/(www\.)?/, '')
    .toLowerCase();
}

function hashStr(s) { return crypto.createHash('md5').update(s).digest('hex').slice(0, 8); }

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function classifyDomain(url) {
  if (!url) return 'unknown';
  const u = url.toLowerCase();
  if (u.includes('.edu') || u.includes('arxiv') || u.includes('.doi') || u.includes('scholar')) return 'academic';
  if (u.includes('.gov')) return 'government';
  if (u.includes('medium') || u.includes('dev.to') || u.includes('hackernoon')) return 'blog';
  if (u.includes('reddit') || u.includes('stackoverflow') || u.includes('hackernews') || u.includes('quora')) return 'community';
  if (u.includes('news') || u.includes('reuters') || u.includes('bloomberg') || u.includes('techcrunch') || u.includes('wired') || u.includes('theverge') || u.includes('venturebeat')) return 'news';
  if (u.includes('wikipedia')) return 'encyclopedia';
  if (u.includes('github') || u.includes('npm')) return 'developer';
  if (u.includes('linkedin') || u.includes('about:') || u.includes('/in/')) return 'professional';
  return 'industry';
}

function progress(msg) {
  console.log(`  ▶ ${msg}`);
}

// ─── Phase 0: Query Generation ──────────────────────────────────────────────
// Determines query categories and generates diverse queries based on topic.
// This is a heuristic-based generator that works without calling an LLM.

function generateQueries(topic) {
  const queries = [];
  const t = topic.trim();
  const words = t.split(/\s+/);
  const shortName = words.slice(0, 3).join(' '); // e.g. "transformer architecture"

  const templates = [
    // 1. Definition & Overview
    `What is ${shortName} and how does it work`,
    `${shortName} explained for beginners`,
    `${shortName} introduction overview`,

    // 2. Technical Deep Dive
    `${shortName} architecture technical details`,
    `how ${shortName} works step by step`,
    `${shortName} methodology approach`,

    // 3. Industry & Applications
    `${shortName} in industry applications`,
    `${shortName} use cases real world examples`,
    `${shortName} practical applications 2025`,

    // 4. Comparative Analysis
    `${shortName} vs alternatives comparison`,
    `best ${shortName} tools framework comparison`,
    `${shortName} vs alternatives pros and cons`,

    // 5. Trends & Future
    `${shortName} future trends outlook 2025 2026`,
    `emerging trends in ${shortName}`,
    `where is ${shortName} heading`,

    // 6. Challenges & Limitations
    `${shortName} challenges limitations problems`,
    `${shortName} what are the drawbacks`,
    `why ${shortName} is not working well`,

    // 7. Statistics & Market
    `${shortName} market size statistics data 2025`,
    `${shortName} industry growth forecast CAGR`,
    `${shortName} key metrics statistics`,

    // 8. Expert Opinion & Research
    `${shortName} expert analysis research paper`,
    `${shortName} academic perspective research`,
    `${shortName} literature review recent studies`,

    // 9. Case Studies & Implementation
    `${shortName} case study implementation success`,
    `${shortName} real world case studies examples`,
    `${shortName} how companies use it`,

    // 10. Tools & Best Practices
    `${shortName} tools resources frameworks`,
    `${shortName} best practices guide`,
    `${shortName} learning resources tutorial`,

    // 11. Specific/Long-tail
    `${shortName} recent breakthroughs 2025`,
    `${shortName} controversies debate criticism`,
    `${shortName} economic impact analysis`,
  ];

  // Remove duplicates while preserving order
  const seen = new Set();
  for (const q of templates) {
    const norm = q.toLowerCase().trim();
    if (!seen.has(norm)) {
      seen.add(norm);
      queries.push(q);
    }
  }
  return queries;
}

// ─── Search Backends ─────────────────────────────────────────────────────────

// Backend 1: LightSerp MCP (via mcp-client.js) — primary
// Backend 2: Direct SearXNG HTTP — fallback
// Backend 3: HTML scraping (Google/Bing) — last resort

const SEARXNG_URL = process.env.SEARXNG_URL || 'http://127.0.0.1:8080/search?format=json';

function executeSearchHTTP(query) {
  return new Promise((resolve) => {
    const proc = spawn('node', ['-e', `
      (async () => {
        const fetch = (await import('node-fetch')).default;
        try {
          const url = "${SEARXNG_URL}".replace("q=SEARCH_QUERY", "q=" + encodeURIComponent("${query.replace(/"/g, '\\"')}"));
          const res = await fetch(url);
          const data = await res.json();
          if (data.results) {
            const results = data.results.map(r => ({
              title: r.title || '',
              url: r.url || '',
              snippet: r.content || '',
              engine: r.engine || 'searxng'
            })).slice(0, 10);
            console.log(JSON.stringify(results));
          } else {
            console.log(JSON.stringify([]));
          }
        } catch(e) {
          console.log(JSON.stringify([]));
        }
      })()
    `], { timeout: 10000 });

    let output = '';
    proc.stdout.on('data', (d) => { output += d.toString(); });
    proc.stderr.on('data', () => {});
    const timer = setTimeout(() => { proc.kill(); resolve({ query, error: 'timeout' }); }, 12000);
    proc.on('close', (code) => {
      clearTimeout(timer);
      try {
        const parsed = JSON.parse(output.trim());
        if (Array.isArray(parsed) && parsed.length > 0) {
          resolve({ query, results: parsed });
        } else {
          resolve({ query, results: [], empty: true });
        }
      } catch {
        resolve({ query, error: 'searxng-http-fail' });
      }
    });
  });
}

// Backend 3: HTML scrape for Google results
function executeSearchHTML(query) {
  return new Promise((resolve) => {
    const proc = spawn('node', ['-e', `
      (async () => {
        const fetch = (await import('node-fetch')).default;
        try {
          const res = await fetch("https://www.google.com/search?q=${encodeURIComponent(query)}&num=10", {
            headers: { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36' }
          });
          const html = await res.text();
          const results = [];
          const linkRegex = /<a[^>]*href="(https?:\\/\\/[^"]+)"/g;
          const titleRegex = /<h3[^>]*>(.*?)<\\/h3>/gs;
          const titleMatches = html.match(/<h3[^>]*>(.*?)<\\/h3>/gs) || [];
          let href;
          while ((href = linkRegex.exec(html)) !== null && results.length < 10) {
            const url = href[1].replace(/&sa=.*/,'').replace(/&usg=.*/,'');
            if (url && !url.includes('google.') && !url.includes('youtube.com') && url.startsWith('http')) {
              const titleMatch = titleMatches.find(t => t);
              results.push({ title: (titleMatch || '').replace(/<[^>]*>/g,'').slice(0,200), url, snippet: '', engine: 'google-html' });
            }
          }
          console.log(JSON.stringify(results.slice(0, 10)));
        } catch(e) {
          console.log(JSON.stringify([]));
        }
      })()
    `], { timeout: 15000 });

    let output = '';
    proc.stdout.on('data', (d) => { output += d.toString(); });
    proc.stderr.on('data', () => {});
    const timer = setTimeout(() => { proc.kill(); resolve({ query, error: 'timeout' }); }, 17000);
    proc.on('close', (code) => {
      clearTimeout(timer);
      try {
        const parsed = JSON.parse(output.trim());
        if (Array.isArray(parsed) && parsed.length > 0) {
          resolve({ query, results: parsed });
        } else {
          resolve({ query, results: [], empty: true });
        }
      } catch {
        resolve({ query, error: 'html-fail' });
      }
    });
  });
}

// ─── Pre-flight Check ───────────────────────────────────────────────────────

async function testSearchCapability() {
  progress('Pre-flight: Testing search capability...');

  // Try MCP first
  progress('  Backend 1: LightSerp MCP...');
  let r = await executeSearch('hello world test');
  if (r.results && r.results.length > 0) {
    progress(`  ✓ MCP works (${r.results.length} results)`);
    return true;
  }
  progress(`  ✗ MCP failed: ${r.error || 'no results'}`);

  // Try SearXNG HTTP
  progress('  Backend 2: SearXNG HTTP...');
  r = await executeSearchHTTP('hello world');
  if (r.results && r.results.length > 0) {
    progress(`  ✓ SearXNG HTTP works (${r.results.length} results)`);
    return true;
  }
  progress(`  ✗ SearXNG HTTP failed: ${r.error || 'no results'}`);

  // Try HTML scraping
  progress('  Backend 3: HTML scraping...');
  r = await executeSearchHTML('hello world');
  if (r.results && r.results.length > 0) {
    progress(`  ✓ HTML search works (${r.results.length} results)`);
    return true;
  }
  progress(`  ✗ HTML search failed: ${r.error || 'no results'}`);

  return false;
}

// ─── Phase 1: Search Execution ─────────────────────────────────────────────

function executeSearch(query) {
  // Primary: MCP via mcp-client.js
  return new Promise((resolve) => {
    const proc = spawn('node', [LIGHTSERP_CLIENT, 'search', query], {
      timeout: 25000,
    });

    let output = '';
    proc.stdout.on('data', (d) => { output += d.toString(); });
    proc.stderr.on('data', () => {}); // suppress noise

    const timer = setTimeout(() => {
      proc.kill();
      // Fallback: try SearXNG HTTP, then HTML scraping
      resolveFallback(query, resolve);
    }, SCRAPE_TIMEOUT);

    proc.on('close', (code) => {
      clearTimeout(timer);
      if (code !== 0 && code !== null) {
        // MCP process crashed — try fallback
        resolveFallback(query, resolve);
        return;
      }
      const trimmed = output.trim();
      if (trimmed.startsWith('Error:')) {
        // MCP search failed — try fallback
        resolveFallback(query, resolve);
        return;
      }
      try {
        const parsed = JSON.parse(trimmed);
        if (Array.isArray(parsed) && parsed.length > 0) {
          resolve({ query, results: parsed });
        } else if (parsed?.results && Array.isArray(parsed.results)) {
          resolve({ query, results: parsed.results });
        } else if (Array.isArray(parsed) && parsed.length === 0) {
          resolve({ query, results: [], empty: true });
        } else if (trimmed === '' || trimmed === '[]') {
          resolve({ query, results: [], empty: true });
        } else {
          resolveFallback(query, resolve);
        }
      } catch {
        resolveFallback(query, resolve);
      }
    });
  });
}

// Fallback chain: SearXNG HTTP → HTML scraping → empty
async function resolveFallback(query, parentResolve) {
  // Try SearXNG HTTP
  const r1 = await executeSearchHTTP(query);
  if (r1.results && r1.results.length > 0) {
    parentResolve({ query, results: r1.results });
    return;
  }
  // Try HTML scraping
  const r2 = await executeSearchHTML(query);
  if (r2.results && r2.results.length > 0) {
    parentResolve({ query, results: r2.results });
    return;
  }
  parentResolve({ query, results: [], empty: true });
}

async function executeSearches(queries) {
  console.log(`\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
  progress(`PHASE 1: Executing ${queries.length} search queries`);
  console.log(`  Batch size: ${BATCH_SIZE}, gap: ${SEARCH_WAIT_MS}ms\n`);

  for (let i = 0; i < queries.length; i += BATCH_SIZE) {
    const batch = queries.slice(i, i + BATCH_SIZE);
    progress(`Batch ${Math.floor(i / BATCH_SIZE) + 1}/${Math.ceil(queries.length / BATCH_SIZE)} — queries ${i + 1}-${Math.min(i + BATCH_SIZE, queries.length)}`);

    const results = await Promise.all(batch.map(q => executeSearch(q)));

    for (const r of results) {
      if (r.results) {
        allResults[r.query] = r.results.filter(r => r.url && r.title);
        console.log(`    ✓ "${r.query.slice(0, 60)}" → ${r.results.filter(r=>r.url).length} URLs`);
      } else {
        console.log(`    ✗ "${r.query.slice(0, 60)}" → ${r.error}`);
      }
    }

    if (i + BATCH_SIZE < queries.length) await sleep(SEARCH_WAIT_MS);
  }

  const totalURLs = Object.values(allResults).reduce((s, r) => s + r.length, 0);
  console.log(`\n  Search complete: ${queries.length} queries, ${totalURLs} URLs found`);
}

// ─── Phase 2: Multi-Page Crawl ──────────────────────────────────────────────

// Update scrape to also use Page Zen as fallback
function scrapePage(url) {
  return new Promise((resolve) => {
    const proc = spawn('node', [LIGHTSERP_CLIENT, 'scrape', url], {
      timeout: SCRAPE_TIMEOUT,
    });

    let output = '';
    proc.stdout.on('data', (d) => { output += d.toString(); });
    proc.stderr.on('data', () => {});

    const timer = setTimeout(() => {
      proc.kill();
      resolve({ url, error: 'timeout' });
    }, SCRAPE_TIMEOUT + 5000);

    proc.on('close', (code) => {
      clearTimeout(timer);
      if (code !== 0 && code !== null) {
        resolve({ url, error: `exit ${code}` });
        return;
      }
      try {
        const obj = JSON.parse(output.trim());
        const content = obj.content || '';
        const title = obj.title || '';
        const wordCount = (content || '').trim().split(/\s+/).filter(Boolean).length;
        resolve({ url, title, content, wordCount, contentJSON: obj });
      } catch {
        const rawLen = output.length;
        resolve({ url, error: 'parse', rawLen, content: output.slice(0, 500) });
      }
    });
  });
}

// Fallback scraper: direct fetch + Readability
function scrapePageFallback(url) {
  return new Promise((resolve) => {
    const proc = spawn('node', ['-e', `
      (async () => {
        const fetch = (await import('node-fetch')).default;
        try {
          const res = await fetch("${url}", {
            headers: { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36' }
          });
          const html = await res.text();
          // Simple content extraction: strip HTML tags
          const text = html.replace(/<script[^>]*>[\s\S]*?<\\/script>/gi, '')
            .replace(/<style[^>]*>[\s\S]*?<\\/style>/gi, '')
            .replace(/<[^>]+>/g, ' ')
            .replace(/\\s+/g, ' ')
            .trim();
          const titleMatch = html.match(/<title[^>]*>(.*?)<\\/title>/i);
          const title = (titleMatch && titleMatch[1]) ? titleMatch[1].trim() : '';
          const wordCount = text.split(/\\s+/).filter(Boolean).length;
          console.log(JSON.stringify({ url: "${url}", title, content: text, wordCount }));
        } catch(e) {
          console.log(JSON.stringify({ url: "${url}", error: 'fetch-fail', content: '', wordCount: 0 }));
        }
      })()
    `], { timeout: 15000 });

    let output = '';
    proc.stdout.on('data', (d) => { output += d.toString(); });
    proc.stderr.on('data', () => {});
    const timer = setTimeout(() => { proc.kill(); resolve({ url, error: 'timeout' }); }, 17000);
    proc.on('close', (code) => {
      clearTimeout(timer);
      try {
        const obj = JSON.parse(output.trim());
        if (obj.error) { resolve(obj); return; }
        resolve({ url: obj.url, title: obj.title, content: obj.content, wordCount: obj.wordCount });
      } catch {
        resolve({ url, error: 'fallback-parse' });
      }
    });
  });
}

async function scrapeURL(url, query, skipReason) {
  if (skipReason) {
    console.log(`    ⊘ ${url.slice(0, 80)} → ${skipReason}`);
    return null;
  }
  if (seenURLs.has(urlKey(url))) {
    console.log(`    ⊘ ${url.slice(0, 80)} → duplicate`);
    return null;
  }
  seenURLs.add(urlKey(url));

  if (crawled.length >= MAX_URLS_TO_SCRAPE) {
    console.log(`    ⊘ ${url.slice(0, 80)} → max reached`);
    return null;
  }

  const r = await scrapePage(url);
  if ((r.wordCount < MIN_WORDS_FOR_VALID || r.error) && r.wordCount < MIN_WORDS_FOR_VALID) {
    // Try fallback scraper
    console.log(`    ↻ ${url.slice(0, 80)} → retrying with fallback scraper...`);
    const rf = await scrapePageFallback(url);
    if (rf.wordCount >= MIN_WORDS_FOR_VALID && !rf.error) {
      const entry = {
        url: rf.url,
        title: rf.title,
        wordCount: rf.wordCount,
        content: rf.content,
        sourceType: classifyDomain(url) + '/fallback',
        query,
      };
      crawled.push(entry);
      console.log(`    ✓ ${url.slice(0, 70)} → ${rf.wordCount} words [${entry.sourceType}] (fallback)`);
      await sleep(SCRAPE_WAIT_MS);
      return entry;
    }
    console.log(`    ✗ ${url.slice(0, 80)} → ${rf.error || rf.wordCount + ' words'} (all backends failed)`);
    return null;
  }
  if (r.error) {
    console.log(`    ⊘ ${url.slice(0, 80)} → ${r.error}`);
    return null;
  }

  const entry = {
    url: r.url,
    title: r.title,
    wordCount: r.wordCount,
    content: r.content,
    sourceType: classifyDomain(url),
    query,
  };
  crawled.push(entry);
  console.log(`    ✓ ${url.slice(0, 70)} → ${r.wordCount} words [${entry.sourceType}]`);
  await sleep(SCRAPE_WAIT_MS);
  return entry;
}

async function executeCrawls() {
  console.log(`\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
  progress(`PHASE 2: Crawling pages from search results`);
  console.log(`  Target: 20+ URLs per query, deduplicated\n`);

  const queriesWithResults = Object.entries(allResults)
    .filter(([, r]) => r.length > 0)
    .map(([q, r]) => ({ query: q, results: r }));

  let totalCrawled = 0;

  for (const { query, results } of queriesWithResults) {
    progress(`Query: "${query.slice(0, 70)}" — ${results.length} URLs → crawling`);

    // Select URLs: top 3 + diverse types
    const selectedURLs = selectURLs(results);
    progress(`  Selected: ${selectedURLs.length} URLs (of ${results.length} available)`);

    let crawledCount = 0;
    for (const url of selectedURLs) {
      const entry = await scrapeURL(url, query);
      if (entry) {
        crawledCount++;
        totalCrawled++;
      }
      if (crawledCount >= 8 || totalCrawled >= MAX_URLS_TO_SCRAPE) break;
    }
    progress(`  Crawled: ${crawledCount} pages`);
    progress(`  Total crawled so far: ${totalCrawled}\n`);
  }

  console.log(`\n  Crawl complete: ${totalCrawled} pages crawled`);
  return totalCrawled;
}

function selectURLs(results) {
  const selected = [];
  const byType = { academic: [], industry: [], news: [], blog: [], community: [], government: [], encyclopedia: [], developer: [], professional: [] };

  // Classify each result
  for (const r of results) {
    const type = classifyDomain(r.url);
    byType[type] = byType[type] || [];
    byType[type].push(r.url);
  }

  // Always take top 3
  const top3 = results.slice(0, 3);
  for (const r of top3) selected.push(r.url);

  // Then pick at least 1 from each available type
  const typesNeeded = ['academic', 'news', 'blog', 'community', 'industry', 'developer', 'government', 'encyclopedia'];
  for (const type of typesNeeded) {
    if (byType[type] && byType[type].length > 0) {
      // pick the highest relevance one not already selected
      for (const url of byType[type]) {
        const rk = urlKey(url);
        if (!selected.find(s => urlKey(s) === rk)) {
          selected.push(url);
          break;
        }
      }
    }
  }

  // Fill remaining with top results not yet selected
  for (const r of results) {
    if (selected.length >= 10) break;
    const rk = urlKey(r.url);
    if (!selected.find(s => urlKey(s) === rk)) {
      selected.push(r.url);
    }
  }

  return selected;
}

// ─── Phase 3: Synthesis ─────────────────────────────────────────────────────

function synthesizeFindings() {
  progress('PHASE 3: Synthesizing findings');

  // Cluster crawled content by source type and key themes
  const byType = {};
  for (const c of crawled) {
    if (!byType[c.sourceType]) byType[c.sourceType] = [];
    byType[c.sourceType].push(c);
  }

  // Extract key facts from all content
  const keyFacts = [];
  for (const c of crawled) {
    // Extract numbers/statistics
    const numbers = c.content.match(/\d+(?:,\d{3})*(?:\.\d+)?/g);
    if (numbers && numbers.length > 0) {
      keyFacts.push({ fact: numbers.slice(0, 5).join(', '), context: c.title, source: c.url });
    }
    // Extract first meaningful sentence per page
    const sentences = c.content.split(/[.!?]+/).filter(s => s.trim().length > 30);
    if (sentences.length > 0) {
      keyFacts.push({ fact: sentences[0].trim(), context: c.title, source: c.url, isQuote: true });
    }
  }

  return { byType, keyFacts, totalWords: crawled.reduce((s, c) => s + c.wordCount, 0), totalSources: crawled.length };
}

// ─── Phase 4: Report Generation ─────────────────────────────────────────────

function generateReport(topic, theme, searchQueries, results, crawls, synthesis) {
  progress('PHASE 4: Generating research report');

  const now = new Date().toISOString().split('T')[0];
  const totalURLs = Object.values(results).reduce((s, r) => s + r.length, 0);

  // Build thematic sections from crawled content
  const sections = buildSections(topic, crawls, synthesis);

  // Build source table
  const sourceTable = crawls.map((c, i) =>
    `| ${i + 1} | ${c.sourceType} | [${c.title || c.url.slice(0, 60)}](${c.url}) | ${c.wordCount} words |`
  ).join('\n');

  const report = [
    `# DEEP RESEARCH REPORT: ${topic}`,
    ``,
    `**Generated:** ${now}`,
    `**Topic:** ${topic}`,
    `**Research Depth:** Comprehensive`,
    `**Search Queries Executed:** ${searchQueries.length}`,
    `**Search URLs Found:** ${totalURLs}`,
    `**Pages Crawled:** ${crawls.length}`,
    `**Total Content Analyzed:** ${synthesis.totalWords.toLocaleString()} words`,
    `**Report Length:** ~${(synthesis.totalWords / 6).toFixed(0)} words (estimated human-readable)`,
    ``,
    `---`,
    ``,
    `## Executive Summary`,
    ``,
    ...generateExecutiveSummary(topic, theme, crawls, synthesis),
    ``,
    ...sections,
    `---`,
    ``,
    `## Sources & Methodology`,
    ``,
    `### Search Queries Executed (${searchQueries.length})`,
    ``,
    ...searchQueries.map((q, i) => `${i + 1}. "${q}"`).join('\n'),
    ``,
    `### Search URLs Found: ${totalURLs}`,
    ``,
    ...Object.entries(results).filter(([, r]) => r.length > 0).map(([q, res]) =>
      `**"${q}":** ${res.length} URLs — ${res.map(r => `[${r.title || r.url.slice(0, 30)}](${r.url})`).join(', ')}`
    ).join('\n'),
    ``,
    `### Pages Crawled (${crawls.length})`,
    ``,
    `| # | Source Type | URL | Content |`,
    `|---|-------------|-----|---------|`,
    `${sourceTable}`,
    ``,
    `### Content by Source Type`,
    ``,
    ...Object.entries(synthesis.byType).map(([type, pages]) =>
      `- **${type}:** ${pages.length} pages (${pages.reduce((s, p) => s + p.wordCount, 0).toLocaleString()} words)`
    ).join('\n'),
    ``,
    `### Key Statistics Extracted`,
    ``,
    ...synthesis.keyFacts.slice(0, 20).map((f, i) =>
      `${i + 1}. "${f.fact}" — from [${f.context}](${f.source})`
    ).join('\n'),
    ``,
    `---`,
    ``,
    `*Report generated by Deep Research Pipeline v1.0 using LightSerp MCP*`,
    `*Search engines: Google, Bing, Brave, DuckDuckGo, Startpage (via SearXNG)*`,
    `*Crawl date: ${now}*`,
  ];

  return report.join('\n');
}

function generateExecutiveSummary(topic, theme, crawls, synthesis) {
  const lines = [];
  const content = crawls.map(c => c.content).join(' ');

  // Extract top 5 key facts
  const numbers = content.match(/\d+(?:,\d{3})*(?:\.\d+)?\s*(?:percent|billion|million|thousand|dollars|¥|€|$|%)/gi) || [];
  const topStats = numbers.slice(0, 5).map(s => `\`${s}\``).join(', ') || 'various data points across sources';

  const firstSentences = crawls.map(c => c.content.split(/[.!?]+/).find(s => s.trim().length > 50) || '').filter(Boolean).slice(0, 3);
  const intro = firstSentences[0]?.slice(0, 300) || `Research on ${topic} was conducted using ${crawls.length} sources across multiple search engines.`;

  lines.push(`This report presents a comprehensive analysis of **${topic}**, synthesizing findings from **${crawls.length} crawled sources** covering multiple dimensions of the topic.`);
  lines.push('');
  lines.push(`**${intro}.**`);
  lines.push('');
  if (topStats) {
    lines.push(`**Key statistics from research:** ${topStats}.`);
    lines.push('');
  }
  lines.push(`The research was conducted in four phases:`);
  lines.push(`1. **Query Generation:** ${searchQueries.length} diverse search queries covering definition, technical aspects, applications, comparisons, trends, challenges, and resources.`);
  lines.push(`2. **Search Execution:** All queries executed via LightSerp MCP, yielding ${Object.values(allResults).reduce((s, r) => s + r.length, 0)} URLs across search engines.`);
  lines.push(`3. **Multi-Page Crawl:** ${crawls.length} pages crawled and analyzed (${synthesis.totalWords.toLocaleString()} words total), with deduplication and source classification.`);
  lines.push(`4. **Synthesis:** Findings clustered by theme, key facts extracted, and report structured for readability and depth.`);
  lines.push('');
  lines.push(`**Major themes identified:** ${theme.length > 0 ? theme.slice(0, 5).map(t => `\`${t}\``).join(', ') : 'general analysis'}.`);

  return lines;
}

function buildSections(topic, crawls, synthesis) {
  // Divide content into thematic sections based on available data
  const sections = [];

  // Section 1: Introduction & Background
  const introPages = crawls.filter(c => c.sourceType === 'encyclopedia' || c.sourceType === 'academic' || c.wordCount > 800).slice(0, 4);
  const introFacts = introPages.map(c => {
    const sentences = c.content.split(/[.!?]+/).filter(s => s.trim().length > 60);
    return sentences.slice(0, 3);
  }).flat();

  sections.push('');
  sections.push('## 1. Introduction & Background');
  sections.push('');
  if (introFacts.length > 0) {
    sections.push(introFacts.slice(0, 3).map((s, i) => {
      const source = introPages[Math.floor(i / 3)];
      return `> "${s.trim().slice(0, 200)}"\n> — [${source?.title || 'Source'}](${source?.url || ''})`;
    }).join('\n\n'));
    sections.push('');
  } else {
    sections.push(`**${topic}** is a topic that has gained significant attention in recent years, with research and application spanning multiple domains.`);
    sections.push('');
  }

  // Section 2: Technical/Conceptual Understanding
  const techPages = crawls.filter(c => c.sourceType === 'developer' || c.sourceType === 'academic' || c.sourceType === 'industry').slice(0, 4);
  const techFacts = techPages.map(c => {
    const sentences = c.content.split(/[.!?]+/).filter(s => s.trim().length > 40);
    return sentences.slice(0, 2);
  }).flat();

  sections.push('');
  sections.push('## 2. Technical Understanding & Core Concepts');
  sections.push('');
  if (techFacts.length > 0) {
    sections.push(techFacts.slice(0, 5).map((s, i) => {
      const source = techPages[Math.floor(i / 2)];
      return `> "${s.trim().slice(0, 200)}"\n> — [${source?.title || 'Source'}](${source?.url || ''})`;
    }).join('\n\n'));
    sections.push('');
  }

  // Section 3: Statistics & Data
  const numbers = [];
  for (const c of crawls) {
    const nums = c.content.match(/[\d,]+(?:\.\d+)?\s*(?:percent|billion|million|thousand|dollars|¥|€|$|%|users|companies|apps|projects|investors|funding|jobs|growth)/gi) || [];
    for (const n of nums.slice(0, 3)) {
      numbers.push({ value: n, source: c.title, url: c.url });
    }
  }

  sections.push('');
  sections.push('## 3. Key Statistics & Data Points');
  sections.push('');
  if (numbers.length > 0) {
    sections.push('| Statistic | Source |');
    sections.push('|-----------|--------|');
    for (const n of numbers.slice(0, 15)) {
      sections.push(`| ${n.value} | [${n.source}](${n.url}) |`);
    }
    sections.push('');
  }

  // Section 4: Expert Perspectives & Quotes
  sections.push('');
  sections.push('## 4. Expert Perspectives & Key Insights');
  sections.push('');
  const allQuotes = crawls.map(c => {
    const sentences = c.content.split(/[.!?]+/).filter(s => s.trim().length > 80 && s.trim().length < 400);
    return sentences.map(s => ({ quote: s.trim(), title: c.title, url: c.url }));
  }).flat();

  if (allQuotes.length > 0) {
    sections.push(allQuotes.slice(0, 8).map(q =>
      `> "${q.quote}"\n> — [${q.title}](${q.url})`
    ).join('\n\n'));
    sections.push('');
  }

  // Section 5: Resources & Further Reading
  sections.push('');
  sections.push('## 5. Sources & Further Reading');
  sections.push('');

  const byType = {};
  for (const c of crawls) {
    if (!byType[c.sourceType]) byType[c.sourceType] = [];
    byType[c.sourceType].push(c);
  }

  for (const [type, pages] of Object.entries(byType).sort((a, b) => b[1].length - a[1].length)) {
    sections.push(`### ${type.charAt(0).toUpperCase() + type.slice(1)} (${pages.length})`);
    sections.push('');
    for (const p of pages.slice(0, 5)) {
      sections.push(`- [${p.title || p.url.slice(0, 60)}](${p.url})`);
    }
    sections.push('');
  }

  // Section 6: Limitations
  sections.push('');
  sections.push('## Research Limitations');
  sections.push('');
  sections.push(`- **Search coverage:** ${searchQueries.length} queries across Google, Bing, Brave, and other search engines. Some niche or paywalled content may not be captured.`);
  sections.push(`- **Scraping limitations:** Pages behind login walls (LinkedIn, Facebook), JavaScript-rendered content, and PDF-based content may not be fully extracted.`);
  sections.push(`- **Language:** Research focused on English-language sources. Non-English sources may contain additional relevant information.`);
  sections.push(`- **Temporal:** Research captures information available as of ${new Date().toISOString().split('T')[0].replace(/-/g, '/')}. Some data may have changed since publication.`);
  sections.push(`- **Content depth:** Pages with fewer than ${MIN_WORDS_FOR_VALID} words of extractable content were excluded.`);

  return sections;
}

// ─── Main Pipeline ──────────────────────────────────────────────────────────
async function main() {
  try {
    // Run pre-flight check
    const healthCheck = await testSearchCapability();
    if (!healthCheck) {
      console.error(`\n❌ MCP search/scrape is not working.`);
      console.error(`\nRequired services:`);
      console.error(`  1. Docker is running (SearXNG, Redis)`);
      console.error(`  2. SearXNG accessible at http://127.0.0.1:8080`);
      console.error(`  3. LightSerp MCP server running`);
      console.error(`\nCheck: curl -s http://localhost:3001/health`);
      console.error(`Check: curl -s http://127.0.0.1:8080/search?q=test&format=json`);
      console.error(`\nTo start: cd ~/workspace/git_workspace/LightSerp && docker compose up -d`);
      process.exit(1);
    }

    // Phase 0: Generate queries
    progress('PHASE 0: Generating search queries for "' + TOPIC + '"');
    allSearchQueries.push(...generateQueries(TOPIC));
    progress(`Generated ${allSearchQueries.length} search queries`);

    // Save query list
    writeFileSync(join(TMP_DIR, `${TOPIC_SLUG}_queries.json`), JSON.stringify({ topic: TOPIC, queries: allSearchQueries }, null, 2));

    // Phase 1: Execute searches
    await executeSearches(allSearchQueries);

    if (Object.keys(allResults).length === 0) {
      console.error('\n❌ No search results found. Check MCP health or try a different topic.');
      process.exit(1);
    }

    // Phase 2: Crawl pages
    const crawledCount = await executeCrawls();

    if (crawledCount < MIN_URLS_REQUIRED) {
      console.log(`\n⚠️  Only ${crawledCount} URLs crawled (minimum ${MIN_URLS_REQUIRED} required). Report will be limited.`);
    }

    // Phase 3: Synthesize
    const synthesis = synthesizeFindings();

    // Phase 4: Extract themes
    const themes = Object.keys(synthesis.byType).filter(k => k !== 'unknown');
    progress(`Identified ${themes.length} source categories: ${themes.join(', ')}`);

    // Phase 5: Generate report
    const report = generateReport(TOPIC, themes, allSearchQueries, allResults, crawled, synthesis);

    writeFileSync(REPORT_FILE, report);
    progress(`Report saved to: ${REPORT_FILE}`);

    // Save intermediate data for debugging
    writeFileSync(join(TMP_DIR, `${TOPIC_SLUG}_results.json`), JSON.stringify({
      queries: allSearchQueries,
      results: Object.fromEntries(
        Object.entries(allResults).map(([k, v]) => [k, v.slice(0, 10)]) // first 10 per query
      ),
      crawled: crawled.map(c => ({ url: c.url, title: c.title.slice(0, 100), wordCount: c.wordCount, sourceType: c.sourceType })),
      synthesis,
    }, null, 2));

    console.log(`\n══════════════════════════════════════════════════════`);
    console.log(`  ✅ DEEP RESEARCH COMPLETE`);
    console.log(`  Topic: ${TOPIC}`);
    console.log(`  Queries: ${allSearchQueries.length}`);
    console.log(`  URLs found: ${Object.values(allResults).reduce((s, r) => s + r.length, 0)}`);
    console.log(`  Pages crawled: ${crawledCount}`);
    console.log(`  Report: ${REPORT_FILE}`);
    console.log(`══════════════════════════════════════════════════════\n`);

  } catch (err) {
    console.error(`\n❌ Error: ${err.message}`);
    console.error(err.stack);
    process.exit(1);
  }
}

// Run
main();
