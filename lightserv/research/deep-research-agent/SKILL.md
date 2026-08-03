---
name: deep-research-agent
description: "Use when the user asks for deep research on any topic — generates diverse search queries via LightSerp MCP, crawls 20+ pages per query with deduplication, synthesizes findings, and produces a comprehensive Gemini-style research report (.md format)."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [research, deep-research, mcp, automation, content-synthesis]
    related_skills: [lightserp, wiki-compiler, blogwatcher]
---

# Deep Research Agent

An autonomous research agent that performs deep, multi-step research on any topic using LightSerp MCP (search + scrape), producing a structured Gemini-style research report in markdown format.

## When to Use

- User asks for deep research on any topic ("research X deeply", "write a deep report on Y", "comprehensive analysis of Z")
- Topic requires understanding across multiple sub-topics, angles, or disciplines
- User wants a detailed research document (not just a summary or quick answer)
- User says "make it like Gemini deep research" or "comprehensive research report"

## When NOT to Use

- Simple factual questions ("what is X") — use a normal search instead
- Real-time data ("current stock price", "today's news") — this is retrospective research
- Topics requiring access to paywalled/protected content — research is limited to publicly accessible pages
- Very narrow topics with < 10 search results — the pipeline needs sufficient search coverage

## Prerequisites

1. **Docker running:** `docker ps` → should show at least SearXNG container
2. **SearXNG accessible:** `curl -s http://127.0.0.1:8080/search?q=test&format=json` → should return results
3. **MCP server running:** `curl -s http://localhost:3001/health` → should return healthy
4. **mcp-client.js available:** `~/workspace/git_workspace/LightSerp/mcp-client.js`

**Start Docker:**
```bash
# If Docker Desktop is installed
open -a Docker
# Wait for it to initialize, then:
cd ~/workspace/git_workspace/LightSerp && docker compose up -d
```

**Verify all services:**
```bash
curl -s http://localhost:3001/health
curl -s http://127.0.0.1:8080/search?q=test&format=json
```

If any of these fail, the pipeline will detect it and abort with a clear message.

## How It Works (5-Phase Pipeline)

```
Topic → Query Generation → Batch Search → Multi-page Crawl → Deduplication → Synthesis → Research Report (.md)
```

### Phase 1: Query Generation

Given a research topic, generates 30 diverse search queries across 10 categories:

1. Definition & Overview ("what is X", "X explained")
2. Technical Deep Dive ("how X works", "X architecture")
3. Industry & Applications ("X use cases", "X real world")
4. Comparative Analysis ("X vs alternatives", "X comparison")
5. Trends & Future ("X future trends", "X outlook")
6. Challenges & Limitations ("X problems", "X drawbacks")
7. Statistics & Market ("X market size", "X data 2025")
8. Expert Opinion ("X research paper", "X academic")
9. Case Studies ("X implementation", "X case study")
10. Tools & Best Practices ("X tools", "X guide")

### Phase 2: Batch Search Execution

Each query is executed via LightSerp MCP:
```bash
node ~/workspace/git_workspace/LightSerp/mcp-client.js search "YOUR QUERY HERE"
```

- Batch size: 5 queries per batch
- Gap between batches: 3 seconds
- All results tracked and saved

### Phase 3: Multi-Page Crawl

From each query's search results:
- Select top 3 results + diverse source types (academic, news, blog, community, industry, developer)
- Minimum 8 pages per query, max 100 total
- Deduplicate across ALL queries
- Skip pages with < 100 words of readable content

### Phase 4: Synthesis

Extract from all crawled content:
- Key statistics and data points
- Expert quotes and perspectives
- Source classification and clustering
- Confidence assessment per finding

### Phase 5: Report Generation

Produces a structured markdown report with:
- Executive Summary (2-3 paragraphs)
- Introduction & Background
- Technical Understanding & Core Concepts
- Key Statistics & Data Points
- Expert Perspectives & Key Insights
- Sources & Further Reading (organized by type)
- Research Limitations
- Full source table with URLs

## Running the Pipeline

### Step 1: Check MCP Health

```bash
curl -s http://localhost:3001/health
```

### Step 2: Run the Pipeline

```bash
node ~/workspace/git_workspace/LightSerp/scripts/deep-research-pipeline.js "YOUR TOPIC HERE"
```

### Example

```bash
# Full deep research
node ~/workspace/git_workspace/LightSerp/scripts/deep-research-pipeline.js "transformer architecture in large language models"

# Shorter topic
node ~/workspace/git_workspace/LightSerp/scripts/deep-research-pipeline.js "quantum computing applications in 2025"

# Market research
node ~/workspace/git_workspace/LightSerp/scripts/deep-research-pipeline.js "electric vehicle battery technology market trends India"
```

### Typical Runtime

- **30 queries** × ~12s each = ~6 minutes (search)
- **60-80 pages** × ~5s each = ~5-7 minutes (scrape)
- **Total:** ~12-15 minutes for full research
- Progress is printed to stdout at each phase

## Output

### Final Report

Saved to: `~/.hermes/research/{topic_slug}_research.md`

Example: `~/.hermes/research/transformer-architecture-in-llms_research.md`

### Intermediate Data

Saved to: `~/.hermes/research/tmp/`

- `{topic_slug}_queries.json` — generated search queries
- `{topic_slug}_results.json` — search results + crawl summary

## Report Structure

The generated report follows this structure:

```
# DEEP RESEARCH REPORT: {TOPIC}

**Generated:** {date}
**Search Queries Executed:** 30
**Pages Crawled:** {count}
**Total Content Analyzed:** {words} words

---

## Executive Summary
2-3 paragraph overview of findings

## 1. Introduction & Background
Key definitions and historical context

## 2. Technical Understanding & Core Concepts
Deep dive into how things work

## 3. Key Statistics & Data Points
Table of extracted statistics

## 4. Expert Perspectives & Key Insights
Quotes and perspectives from sources

## 5. Sources & Further Reading
All sources organized by type

## Research Limitations
Transparent disclosure of constraints
```

## Skill Execution Workflow

1. **Receive topic** from user
2. **Check MCP health** — restart if unhealthy
3. **Run pipeline:** `node deep-research-pipeline.js "topic"`
4. **Monitor progress** — output shows phase-by-phase status
5. **Report completion** — deliver path to generated report
6. **Deliver report** — share key findings or full file via `MEDIA:` attachment

## Common Pitfalls

1. **MCP not running** — always check health before starting. If unhealthy, restart LightSerp.
2. **Topic too broad** — "AI" is too broad. Prefer "AI in healthcare diagnostics" or "LLM fine-tuning methods".
3. **Rate limiting** — if MCP starts returning errors, the pipeline will skip those queries and continue. No automatic retry.
4. **LinkedIn/Facebook pages** — these return login walls, not content. Pipeline automatically skips low-word-count pages.
5. **Very short topics** — if the topic is 1-2 words, consider expanding: "LLM" → "large language model training methods".
6. **Long runtime** — 12-15 minutes is normal for full research. Don't interrupt the process.

## Verification Checklist

- [ ] Docker is running (`docker ps`)
- [ ] SearXNG accessible (`curl http://127.0.0.1:8080/search?q=test`)
- [ ] MCP health check passed (`curl localhost:3001/health`)
- [ ] Pipeline script exists at `~/workspace/git_workspace/LightSerp/scripts/deep-research-pipeline.js`
- [ ] Output directory created (`~/.hermes/research/`)
- [ ] Pre-flight search test passed (pipeline auto-checks before proceeding)
- [ ] All search queries executed (or logged errors for failed ones)
- [ ] Minimum 20 pages crawled (check output for crawled count)
- [ ] Report saved to `~/.hermes/research/{topic_slug}_research.md`
- [ ] No fabricated data — all statistics traceable to source URLs
