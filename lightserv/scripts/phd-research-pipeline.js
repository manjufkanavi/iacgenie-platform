#!/usr/bin/env node
/**
 * PhD Research: Fine-tuning Qwen Coder 2.5 7B for AWS Architecture
 *
 * Direct integration with LightSerp modules (search, scrape)
 *
 * Phase 1: Generate search queries
 * Phase 2: For each query, search → scrape → store JSON
 * Phase 3: Analyze → generate research report
 */

import { writeFileSync, mkdirSync, readFileSync } from "fs";
import { join } from "path";
import { search } from "../src/search.js";
import { scrapePage } from "../src/scrape.js";
import { log } from "../src/logger.js";

const OUTPUT_DIR = "/tmp/phd-research-data";
mkdirSync(OUTPUT_DIR, { recursive: true });

// Read the search queries we generated
const queriesFile = join(OUTPUT_DIR, "research-queries.json");
const queriesData = JSON.parse(readFileSync(queriesFile, "utf8"));
const queries = queriesData.queries;

console.log(`\n🎯 PHASE 2: Scraping ${queries.length} queries...`);
console.log(`   Target: 100 unique URLs per query\n`);

async function searchForURLs(query) {
  try {
    const results = await search(query);
    console.log(`   Found ${results.length} results`);
    return results;
  } catch (error) {
    console.log(`   ❌ Search failed: ${error.message}`);
    return [];
  }
}

async function scrapeURL(url) {
  try {
    const result = await scrapePage(url);
    return {
      url: url,
      title: result.title || "",
      content: result.content || "",
      contentLength: result.content?.length || 0,
      scrapedAt: new Date().toISOString(),
    };
  } catch (error) {
    console.log(`   ❌ Scrape failed: ${url}`);
    return {
      url: url,
      title: "",
      content: "",
      contentLength: 0,
      scrapedAt: new Date().toISOString(),
      error: error.message,
    };
  }
}

async function runResearch() {
  // Track all scraped URLs
  const allURLs = new Set();
  const scrapeResults = [];
  let processedCount = 0;

  // Process each query
  for (let i = 0; i < queries.length; i++) {
    const query = queries[i];
    console.log(`\n📋 Processing query ${i + 1}/${queries.length}: ${query}`);

    // Search for URLs
    const searchResults = await searchForURLs(query);

    // Debug: Log first 3 results
    if (searchResults.length > 0) {
      console.log(`   First result keys: ${Object.keys(searchResults[0]).join(', ')}`);
      console.log(`   First result URL type: ${typeof searchResults[0].url}, value: ${String(searchResults[0].url).substring(0, 80)}`);
    }

    // Extract URLs from search results (search returns {url, title, snippet} objects)
    const newURLs = searchResults
      .filter((r) => r.url && typeof r.url === 'string')
      .map((r) => r.url);
    newURLs.forEach((u) => allURLs.add(u));

    console.log(`   ${newURLs.length} new unique URLs found\n`);

    // Scrape up to 100 URLs per query
    const urlsToScrape = newURLs.slice(0, 100);

    for (let j = 0; j < urlsToScrape.length; j++) {
      const url = urlsToScrape[j];
      console.log(`   📄 Scraping: ${url}`);
      const result = await scrapeURL(url);
      scrapeResults.push(result);
      processedCount++;

      // Save each result immediately
      const resultFile = join(
        OUTPUT_DIR,
        `scrape_${processedCount}.json`
      );
      writeFileSync(resultFile, JSON.stringify(result, null, 2));

      if ((j + 1) % 10 === 0) {
        console.log(`   Progress: ${processedCount}/${urlsToScrape.length} URLs scraped`);
      }
    }

    // Add delay between queries to avoid rate limiting
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }

  // Generate summary
  const successful = scrapeResults.filter((r) => r.contentLength > 100);
  const failed = scrapeResults.filter((r) => r.contentLength <= 100);

  const summary = {
    totalQueries: queries.length,
    queries: queries,
    totalURLsFound: allURLs.size,
    totalScraped: scrapeResults.length,
    successful: successful.length,
    failed: failed.length,
    successRate: ((successful.length / scrapeResults.length) * 100).toFixed(2),
    averageContentLength:
      successful.reduce((sum, r) => sum + r.contentLength, 0) /
      successful.length,
    minContentLength: Math.min(
      ...successful.map((r) => r.contentLength)
    ),
    maxContentLength: Math.max(
      ...successful.map((r) => r.contentLength)
    ),
    scrapedAt: new Date().toISOString(),
    outputDir: OUTPUT_DIR,
  };

  const summaryFile = join(OUTPUT_DIR, "summary.json");
  writeFileSync(summaryFile, JSON.stringify(summary, null, 2));

  console.log("\n\n🏁 RESEARCH PHASE 2 COMPLETE!");
  console.log(`   Total URLs found: ${summary.totalURLsFound}`);
  console.log(`   Total scraped: ${summary.totalScraped}`);
  console.log(`   Successful: ${summary.successful}`);
  console.log(`   Failed: ${summary.failed}`);
  console.log(`   Success rate: ${summary.successRate}%`);
  console.log(`   Summary saved to: ${summaryFile}`);
}

// Run the research pipeline
runResearch().catch((error) => {
  console.error("❌ Research pipeline failed:", error);
  process.exit(1);
});
