#!/usr/bin/env node
/**
 * PhD Research: Fine-tuning Qwen Coder 2.5 7B for AWS Architecture
 *
 * Uses LightSerp MCP tools for searching and scraping
 */

import { spawn } from "child_process";
import { writeFileSync, mkdirSync } from "fs";

const OUTPUT_DIR = "/tmp/phd-research-data";
mkdirSync(OUTPUT_DIR, { recursive: true });

// Generate 20 targeted search queries
const searchQueries = [
  // Core AWS Architecture
  "AWS architecture best practices",
  "AWS Well-Architected Framework implementation",
  "AWS architecture decision patterns",
  "AWS cloud architecture design patterns",
  "AWS architecture guide examples",
  "AWS architecture whitepaper case study",
  "AWS architecture reference implementation",
  "AWS architecture service selection guide",
  "AWS architecture scalability patterns",
  "AWS architecture reliability patterns",
  
  // Security & Cost
  "AWS architecture security best practices",
  "AWS architecture cost optimization patterns",
  "AWS architecture performance efficiency patterns",
  "AWS architecture operational excellence patterns",
  "AWS architecture sustainability patterns",
  
  // Advanced Patterns
  "AWS microservices architecture patterns",
  "AWS serverless architecture patterns",
  "AWS event driven architecture patterns",
  "AWS data architecture patterns",
  "AWS networking architecture patterns",
  "AWS DevOps CI/CD architecture patterns",
  "AWS machine learning architecture patterns",
];

console.log("Generated", searchQueries.length, "search queries:");
searchQueries.forEach((q, i) => console.log(`  ${i + 1}. ${q}`));

// Save to file
writeFileSync('/tmp/research-queries.json', JSON.stringify({
  totalQueries: searchQueries.length,
  queries: searchQueries,
  generatedAt: new Date().toISOString(),
}, null, 2));

console.log(`\nSaved to /tmp/research-queries.json`);
