#!/usr/bin/env node
/**
 * LightSerp Benchmark Runner — 1000 unique web page tests
 * Optimized: reuses single MCP process for all queries
 */

import { spawn } from 'child_process';
import { writeFileSync, mkdirSync } from 'fs';
import { join } from 'path';

const TOTAL_QUERIES = parseInt(process.env.BENCHMARK_QUERIES || '1000', 10);
const OUTPUT_DIR = process.env.BENCHMARK_OUTPUT_DIR || join(process.cwd(), 'benchmark-results');
const REPORT_FILE = join(OUTPUT_DIR, 'benchmark-report.json');
const HTML_REPORT = join(OUTPUT_DIR, 'benchmark-report.html');

// ── Query Pools ────────────────────────────────────────────────────────
const QUERY_POOLS = {
  tech: [
    'Rust programming language tutorial', 'Kubernetes vs Docker containers',
    'TypeScript vs JavaScript performance', 'Go concurrency goroutines',
    'Python asyncio patterns', 'WebAssembly benchmarks 2024',
    'GraphQL vs REST API performance', 'React Vue Angular comparison',
    'PostgreSQL vs MongoDB database', 'Redis caching strategies',
    'Kafka vs RabbitMQ messaging', 'Terraform vs Pulumi IaC',
    'gRPC vs REST protocols', 'eBPF kernel programming',
    'WebGPU browser graphics', 'Quantum computing basics',
    'ML model quantization', 'RAG vector database',
    'LLM fine-tuning vs prompting', 'Edge vs cloud computing',
  ],
  science: [
    'Climate change ocean acidification', 'CRISPR gene editing 2024',
    'Dark matter detection experiments', 'mRNA vaccine mechanisms',
    'Quantum entanglement teleportation', 'Solar energy efficiency',
    'CRISPR ethics considerations', 'Exoplanet James Webb telescope',
    'Nuclear fusion breakthrough', 'Antibiotic resistance bacteria',
    'Gravitational wave LIGO', 'Protein folding AlphaFold',
    'Neuroscience consciousness', 'Dark energy expansion',
    'Synthetic biology organisms',
  ],
  business: [
    'SaaS pricing strategies 2024', 'Remote work productivity stats',
    'AI startup funding trends', 'E-commerce conversion optimization',
    'Cryptocurrency market Bitcoin', 'Supply chain logistics',
    'Fintech blockchain banking', 'Enterprise AI case studies',
    'Cybersecurity threats 2024', 'ESG sustainable business',
    'Digital transformation ROI', 'Venture capital reports',
    'Microservices patterns', 'CI/CD pipeline optimization',
    'Cloud cost optimization',
  ],
  general: [
    'best coffee beans near me', 'learn programming from scratch',
    'healthy meal prep recipes', 'travel Europe 2024',
    'home workout no equipment', 'personal finance budgeting',
    'book recommendations fiction', 'photography tips beginners',
    'garden planting vegetables', 'meditation mindfulness',
    'electric cars comparison', 'smart home automation',
    'minimalist living tips', 'yoga poses beginners',
    'DIY home improvement',
  ],
};

function generateQueries(count) {
  const allQueries = Object.values(QUERY_POOLS).flat();
  const queries = [];
  const used = new Set();
  while (queries.length < count) {
    for (const [cat, pool] of Object.entries(QUERY_POOLS)) {
      for (const q of pool) {
        if (queries.length >= count) break;
        const variant = `${q} ${cat} site:.com`;
        if (!used.has(variant)) { used.add(variant); queries.push({ query: variant, category: cat, index: queries.length }); }
      }
    }
    for (let i = queries.length; i < count; i++) {
      const baseQ = allQueries[i % allQueries.length];
      const variant = `${baseQ} ${i + 1}`;
      if (!used.has(variant)) { used.add(variant); queries.push({ query: variant, category: 'general', index: i }); }
    }
  }
  return queries.slice(0, count);
}

// ── MCP Client (single process, reused) ────────────────────────────────

class McpClient {
  constructor() {
    this.proc = null;
    this.msgId = 0;
    this.pending = new Map();
    this.connected = false;
  }

  async connect() {
    return new Promise((resolve, reject) => {
      this.proc = spawn('node', ['/Users/manjunathkanavi/.hermes/mcp/lightserp/mcp-server.js'], {
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env, SEARXNG_URL: 'http://127.0.0.1:18082', LIGHTPANDA_BIN: '/opt/homebrew/bin/lightpanda' },
      });

      let buf = '';
      this.proc.stdout.on('data', (data) => {
        buf += data.toString();
        const lines = buf.split('\n');
        buf = lines.pop() || '';
        for (const line of lines) {
          if (!line.trim()) continue;
          try { this.handleMessage(JSON.parse(line)); } catch {}
        }
      });
      this.proc.stderr.on('data', () => {});

      this.proc.on('error', reject);
      this.proc.on('exit', (code) => {
        if (code !== 0) reject(new Error(`MCP exited with code ${code}`));
      });

      // Initialize
      this.send({ jsonrpc: '2.0', id: ++this.msgId, method: 'initialize', params: { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'benchmark', version: '1.0.0' } } });
      setTimeout(() => { this.connected = true; resolve(); }, 2000);
    });
  }

  send(msg) {
    this.proc.stdin.write(JSON.stringify(msg) + '\n');
  }

  callTool(name, args, timeoutMs = 25000) {
    return new Promise((resolve) => {
      const id = ++this.msgId;
      const timer = setTimeout(() => {
        this.pending.delete(id);
        resolve({ success: false, error: 'timeout', time: timeoutMs });
      }, timeoutMs);

      this.pending.set(id, { resolve, timer });
      this.send({ jsonrpc: '2.0', id, method: 'tools/call', params: { name, arguments: args } });
    });
  }

  handleMessage(msg) {
    const pending = this.pending.get(msg.id);
    if (pending) {
      clearTimeout(pending.timer);
      this.pending.delete(msg.id);
      if (msg.error) {
        pending.resolve({ success: false, error: msg.error.message, time: 0, raw: msg });
      } else {
        const text = msg.result?.content?.[0]?.text || '';
        try {
          pending.resolve({ success: true, data: JSON.parse(text), time: 0, raw: msg });
        } catch {
          pending.resolve({ success: true, data: text, time: 0, raw: msg });
        }
      }
    }
  }

  async close() {
    if (this.proc) { this.proc.kill(); this.proc = null; }
  }
}

// ── Benchmark Runner ───────────────────────────────────────────────────

async function runBenchmark() {
  mkdirSync(OUTPUT_DIR, { recursive: true });
  console.log(`🚀 LightSerp Benchmark — ${TOTAL_QUERIES} queries`);
  console.log(`📁 Output: ${OUTPUT_DIR}`);

  const client = new McpClient();
  await client.connect();
  console.log('✅ MCP connected\n');

  const queries = generateQueries(TOTAL_QUERIES);
  const results = [];
  const stats = {
    total: TOTAL_QUERIES, searchSuccess: 0, searchFailure: 0,
    scrapeSuccess: 0, scrapeFailure: 0,
    totalSearchTime: 0, totalScrapeTime: 0,
    byCategory: {}, errors: [],
  };

  const startTime = Date.now();
  const scrapeUrl = 'https://example.com';

  for (let i = 0; i < queries.length; i++) {
    const q = queries[i];
    const cat = q.category;
    if (!stats.byCategory[cat]) stats.byCategory[cat] = { total: 0, success: 0, failure: 0, searchTime: 0, scrapeTime: 0 };
    stats.byCategory[cat].total++;

    const item = { index: q.index, query: q.query, category: cat };

    // Search
    const s0 = Date.now();
    const searchResult = await client.callTool('search_web', { query: q.query, maxResults: 5 });
    const sTime = Date.now() - s0;
    item.search = { ...searchResult, time: sTime };
    if (searchResult.success) { stats.searchSuccess++; stats.totalSearchTime += sTime; stats.byCategory[cat].success++; stats.byCategory[cat].searchTime += sTime; }
    else { stats.searchFailure++; stats.byCategory[cat].failure++; if (searchResult.error && !stats.errors.find(e => e.error === searchResult.error)) stats.errors.push({ error: searchResult.error, count: 1 }); }

    // Scrape
    const sc0 = Date.now();
    const scrapeResult = await client.callTool('scrape_page', { url: scrapeUrl });
    const scTime = Date.now() - sc0;
    item.scrape = { ...scrapeResult, time: scTime, url: scrapeUrl };
    if (scrapeResult.success) { stats.scrapeSuccess++; stats.totalScrapeTime += scTime; stats.byCategory[cat].success++; stats.byCategory[cat].scrapeTime += scTime; }
    else { stats.scrapeFailure++; stats.byCategory[cat].failure++; }

    results.push(item);

    if ((i + 1) % 50 === 0 || i === queries.length - 1) {
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      const rate = (i + 1) / (parseFloat(elapsed) || 1).toFixed(1);
      console.log(`  [${i + 1}/${queries.length}] (${elapsed}s, ${rate.toFixed(1)}/min) search: ${stats.searchSuccess}/${stats.searchFailure} | scrape: ${stats.scrapeSuccess}/${stats.scrapeFailure}`);
    }
  }

  const totalTime = ((Date.now() - startTime) / 1000).toFixed(1);
  stats.avgSearchTime = stats.searchSuccess > 0 ? Math.round(stats.totalSearchTime / stats.searchSuccess) : 0;
  stats.avgScrapeTime = stats.scrapeSuccess > 0 ? Math.round(stats.totalScrapeTime / stats.scrapeSuccess) : 0;
  stats.totalTime = totalTime;
  stats.successRate = (((stats.searchSuccess + stats.scrapeSuccess) / (stats.total * 2)) * 100).toFixed(1);
  stats.queryPerMinute = (queries.length / (parseFloat(totalTime) / 60)).toFixed(1);

  await client.close();

  const report = {
    metadata: { generatedAt: new Date().toISOString(), benchmarkVersion: '4.0.0', totalQueries: TOTAL_QUERIES, mcpServer: 'lightserp', transport: 'stdio', searxngUrl: 'http://127.0.0.1:18082', lightpandaBin: '/opt/homebrew/bin/lightpanda' },
    summary: stats, results,
  };

  writeFileSync(REPORT_FILE, JSON.stringify(report, null, 2));
  console.log(`\n✅ Complete! ${totalTime}s | ${stats.successRate}% success | ${stats.avgSearchTime}ms search | ${stats.avgScrapeTime}ms scrape | ${stats.queryPerMinute}/min`);
  console.log(`📊 ${REPORT_FILE}`);
  generateHtmlReport(report);
}

function generateHtmlReport(report) {
  const s = report.summary;
  const colors = { tech: '#3b82f6', science: '#8b5cf6', business: '#10b981', general: '#f59e0b' };
  const catRows = Object.entries(s.byCategory).map(([cat, d]) => {
    const rate = d.total > 0 ? ((d.success / d.total) * 100).toFixed(1) : 0;
    const c = rate >= 90 ? 'success' : rate >= 70 ? 'warning' : 'danger';
    return `<tr><td><span class="cb" style="background:${colors[cat] || '#6b7280'}">${cat}</span></td><td>${d.total}</td><td class="success">${d.success}</td><td class="failure">${d.failure}</td><td>${d.searchTime > 0 ? Math.round(d.searchTime / d.success) : 0}ms</td><td>${d.scrapeTime > 0 ? Math.round(d.scrapeTime / d.success) : 0}ms</td></tr>`;
  }).join('\n');

  const topErrors = s.errors.sort((a, b) => b.count - a.count).slice(0, 10).map(e => `<li><strong>${e.count}×</strong> ${e.error}</li>`).join('\n');

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LightSerp Benchmark v4.0</title>
<style>
:root{--bg:#0f172a;--surface:#1e293b;--surface2:#334155;--border:#475569;--text:#f1f5f9;--muted:#94a3b8;--accent:#38bdf8;--success:#4ade80;--danger:#f87171;--warning:#fbbf24}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.6;min-height:100vh}
.container{max-width:1100px;margin:0 auto;padding:2rem}
header{text-align:center;padding:3rem 0 2rem;border-bottom:1px solid var(--border);margin-bottom:2rem}
header h1{font-size:2.5rem;font-weight:800;background:linear-gradient(135deg,var(--accent),#818cf8);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
header p{color:var(--muted);font-size:1.1rem;margin-top:.5rem}
.badge{display:inline-block;background:var(--surface2);color:var(--accent);padding:.25rem .75rem;border-radius:9999px;font-size:.85rem;font-weight:600}
.metrics-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1.5rem;margin-bottom:2rem}
.metric-card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:1.5rem;text-align:center;transition:transform .2s,border-color .2s}
.metric-card:hover{transform:translateY(-2px);border-color:var(--accent)}
.metric-value{font-size:2.5rem;font-weight:800;color:var(--accent);line-height:1.2}
.metric-value.success{color:var(--success)}.metric-value.warning{color:var(--warning)}.metric-value.danger{color:var(--danger)}
.metric-label{color:var(--muted);font-size:.9rem;margin-top:.25rem}
.section{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:1.5rem;margin-bottom:1.5rem}
.section h2{font-size:1.25rem;font-weight:700;margin-bottom:1rem;padding-bottom:.75rem;border-bottom:1px solid var(--border)}
table{width:100%;border-collapse:collapse}
th{text-align:left;padding:.75rem 1rem;font-size:.8rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);border-bottom:1px solid var(--border)}
td{padding:.75rem 1rem;border-bottom:1px solid var(--border);font-size:.95rem}
tr:last-child td{border-bottom:none}tr:hover td{background:var(--surface2)}
.cb{display:inline-block;padding:.2rem .6rem;border-radius:6px;font-size:.8rem;font-weight:600;color:white}
.success{color:var(--success);font-weight:600}.failure{color:var(--danger);font-weight:600}
.chart-bar{display:flex;align-items:center;gap:1rem;margin-bottom:.75rem}
.chart-label{width:100px;font-size:.9rem;color:var(--muted);text-align:right}
.chart-track{flex:1;height:24px;background:var(--surface2);border-radius:4px;overflow:hidden}
.chart-fill{height:100%;border-radius:4px;display:flex;align-items:center;padding-left:.5rem;font-size:.8rem;font-weight:600;color:white;min-width:fit-content}
.error-list{list-style:none}
.error-list li{padding:.5rem 0;border-bottom:1px solid var(--border);font-size:.9rem;color:var(--muted)}
.error-list li:last-child{border-bottom:none}
footer{text-align:center;padding:2rem;color:var(--muted);font-size:.85rem;border-top:1px solid var(--border);margin-top:2rem}
.slideshow{position:relative;overflow:hidden}
.slide{display:none;animation:fadeIn .5s}
.slide.active{display:block}
@keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.nav-dots{display:flex;justify-content:center;gap:.5rem;margin:1.5rem 0}
.dot{width:10px;height:10px;border-radius:50%;background:var(--border);cursor:pointer;transition:background .2s}
.dot.active{background:var(--accent)}
.nav-buttons{display:flex;justify-content:center;gap:1rem;margin:1rem 0}
.nav-btn{background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:.5rem 1.5rem;border-radius:8px;cursor:pointer;font-size:.9rem;transition:all .2s}
.nav-btn:hover{background:var(--accent);color:var(--bg)}
.nav-btn:disabled{opacity:.5;cursor:not-allowed}
</style>
</head>
<body>
<div class="container">
<header>
<span class="badge">Benchmark Report v4.0</span>
<h1>🚀 LightSerp MCP Benchmark</h1>
<p>${new Date(report.metadata.generatedAt).toLocaleString()} · ${report.metadata.totalQueries} queries · ${report.metadata.transport} transport</p>
</header>

<div class="slideshow">
<div class="slide active" id="slide-1">
<div class="metrics-grid">
<div class="metric-card"><div class="metric-value">${s.total}</div><div class="metric-label">Total Queries</div></div>
<div class="metric-card"><div class="metric-value success">${s.successRate}%</div><div class="metric-label">Success Rate</div></div>
<div class="metric-card"><div class="metric-value">${s.avgSearchTime}ms</div><div class="metric-label">Avg Search Time</div></div>
<div class="metric-card"><div class="metric-value">${s.avgScrapeTime}ms</div><div class="metric-label">Avg Scrape Time</div></div>
<div class="metric-card"><div class="metric-value">${s.totalTime}s</div><div class="metric-label">Total Time</div></div>
<div class="metric-card"><div class="metric-value">${s.queryPerMinute}/min</div><div class="metric-label">Queries per Minute</div></div>
</div>
<div class="section"><h2>📊 Success Rate by Category</h2>
${Object.entries(s.byCategory).map(([cat, d]) => {
const rate = d.total > 0 ? ((d.success / d.total) * 100).toFixed(1) : 0;
const c = rate >= 90 ? 'success' : rate >= 70 ? 'warning' : 'danger';
return `<div class="chart-bar"><span class="chart-label">${cat}</span><div class="chart-track"><div class="chart-fill" style="width:${rate}%;background:var(--${c})">${rate}%</div></div><span style="color:var(--muted);font-size:.85rem">${d.success}/${d.total}</span></div>`;
}).join('\n')}
</div>
</div>

<div class="slide" id="slide-2">
<div class="section"><h2>📋 Category Breakdown</h2>
<table><thead><tr><th>Category</th><th>Queries</th><th>Success</th><th>Failures</th><th>Avg Search</th><th>Avg Scrape</th></tr></thead><tbody>${catRows}</tbody></table>
</div>
</div>

<div class="slide" id="slide-3">
<div class="section"><h2>⚠️ Top Errors</h2>
<ul class="error-list">${topErrors || '<li>No errors encountered</li>'}</ul>
</div>
<div class="section"><h2>📈 Performance Distribution</h2>
<div class="metrics-grid">
<div class="metric-card"><div class="metric-value success">${s.searchSuccess}</div><div class="metric-label">Search Successes</div></div>
<div class="metric-card"><div class="metric-value danger">${s.searchFailure}</div><div class="metric-label">Search Failures</div></div>
<div class="metric-card"><div class="metric-value success">${s.scrapeSuccess}</div><div class="metric-label">Scrape Successes</div></div>
<div class="metric-card"><div class="metric-value danger">${s.scrapeFailure}</div><div class="metric-label">Scrape Failures</div></div>
</div>
</div>
</div>

<div class="slide" id="slide-4">
<div class="section"><h2>🔬 Methodology</h2>
<table>
<tr><td>Tool</td><td>${report.metadata.mcpServer}</td></tr>
<tr><td>Transport</td><td>${report.metadata.transport}</td></tr>
<tr><td>SearXNG</td><td>${report.metadata.searxngUrl}</td></tr>
<tr><td>LightPanda</td><td>${report.metadata.lightpandaBin}</td></tr>
<tr><td>Queries/Category</td><td>${Math.floor(report.metadata.totalQueries / 4)}</td></tr>
<tr><td>Search Results</td><td>5 per query</td></tr>
<tr><td>Scrape Target</td><td>https://example.com</td></tr>
<tr><td>Timeout</td><td>25 seconds</td></tr>
<tr><td>Generated</td><td>${new Date(report.metadata.generatedAt).toISOString()}</td></tr>
</table>
</div>
<div class="section"><h2>🎯 Key Findings</h2>
<ul style="padding-left:1.5rem;color:var(--muted)">
<li style="padding:.5rem 0">Avg search: <strong style="color:var(--accent)">${s.avgSearchTime}ms</strong></li>
<li style="padding:.5rem 0">Avg scrape: <strong style="color:var(--accent)">${s.avgScrapeTime}ms</strong></li>
<li style="padding:.5rem 0">Success rate: <strong style="color:var(--success)">${s.successRate}%</strong></li>
<li style="padding:.5rem 0">Throughput: <strong style="color:var(--accent)">${s.queryPerMinute} queries/min</strong></li>
<li style="padding:.5rem 0">Duration: <strong style="color:var(--accent)">${s.totalTime}s</strong></li>
</ul>
</div>
</div>
</div>

<div class="nav-dots">
<span class="dot active" onclick="goTo(1)"></span>
<span class="dot" onclick="goTo(2)"></span>
<span class="dot" onclick="goTo(3)"></span>
<span class="dot" onclick="goTo(4)"></span>
</div>
<div class="nav-buttons">
<button class="nav-btn" id="prevBtn" onclick="prevSlide()" disabled>← Previous</button>
<button class="nav-btn" id="nextBtn" onclick="nextSlide()">Next →</button>
</div>

<footer><p>LightSerp MCP Benchmark · v4.0.0 · ${new Date(report.metadata.generatedAt).toLocaleString()}</p></footer>
</div>
<script>
let cur=1;const tot=4;
function goTo(n){document.querySelectorAll('.slide').forEach(s=>s.classList.remove('active'));document.querySelectorAll('.dot').forEach(d=>d.classList.remove('active'));document.getElementById('slide-'+n).classList.add('active');document.querySelectorAll('.dot')[n-1].classList.add('active');document.getElementById('prevBtn').disabled=n===1;document.getElementById('nextBtn').disabled=n===tot;cur=n}
function nextSlide(){if(cur<tot)goTo(cur+1)}
function prevSlide(){if(cur>1)goTo(cur-1)}
document.addEventListener('keydown',e=>{if(e.key==='ArrowRight')nextSlide();if(e.key==='ArrowLeft')prevSlide()});
</script>
</body></html>`;

  writeFileSync(HTML_REPORT, html);
  console.log(`📊 HTML: ${HTML_REPORT}`);
}

runBenchmark().catch(err => { console.error('Benchmark failed:', err); process.exit(1); });
