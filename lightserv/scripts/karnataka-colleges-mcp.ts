import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const rootDir = resolve(__dirname, '..');

class LightSerpClient {
  private mcp: ReturnType<typeof spawn> | null = null;
  private messageId = 1;
  private messagePromises: Map<number, { resolve: (v: any) => void, reject: (e: any) => void }> = new Map();
  private responseData = '';
  private initialized = false;

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.mcp = spawn('node', ['dist/server.js'], {
        cwd: rootDir,
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env, NODE_ENV: 'production' }
      });

      this.mcp.on('error', (err) => reject(err));
      this.mcp.on('exit', (code) => {
        if (code !== 0 && code !== null) reject(new Error(`MCP server exited with code ${code}`));
      });

      this.mcp.stdout.on('data', (data: Buffer) => {
        this.responseData += data.toString();
        const lines = this.responseData.split('\n');
        this.responseData = lines.pop() || ''; // keep incomplete line

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const msg = JSON.parse(line);
            if (msg.method === 'initialize' && msg.result?.tools) {
              // MCP response to initialize
              this.initialized = true;
              resolve();
            } else if (msg.id && this.messagePromises.has(msg.id)) {
              const { resolve: r } = this.messagePromises.get(msg.id)!;
              this.messagePromises.delete(msg.id);
              r(msg.result);
            }
          } catch (e) {
            // skip parse errors
          }
        }
      });

      this.mcp.stderr.on('data', (data: Buffer) => {
        console.error('MCP stderr:', data.toString());
      });

      // Send initialize
      this.mcp.stdin.write(JSON.stringify({
        jsonrpc: '2.0', id: this.messageId++, method: 'initialize',
        params: { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'karnataka-colleges', version: '1.0' } }
      }) + '\n');
    });
  }

  private sendRequest(method: string, params: any): Promise<any> {
    return new Promise((resolve, reject) => {
      const id = this.messageId++;
      this.messagePromises.set(id, { resolve, reject });
      this.mcp!.stdin.write(JSON.stringify({
        jsonrpc: '2.0', id, method, params
      }) + '\n');
    });
  }

  async searchWeb(query: string, maxResults = 50): Promise<any[]> {
    const result = await this.sendRequest('tools/call', {
      name: 'search_web',
      arguments: { query }
    });
    if (result?.content?.[0]?.text) {
      try {
        return JSON.parse(result.content[0].text);
      } catch {
        return [];
      }
    }
    return [];
  }

  async scrapePage(url: string): Promise<string> {
    const result = await this.sendRequest('tools/call', {
      name: 'scrape_page',
      arguments: { url }
    });
    if (result?.content?.[0]?.text) {
      return result.content[0].text;
    }
    return '';
  }

  async close(): Promise<void> {
    if (this.mcp) {
      this.mcp.stdin.write(JSON.stringify({
        jsonrpc: '2.0', id: this.messageId++, method: 'shutdown'
      }) + '\n');
      setTimeout(() => this.mcp!.kill(), 500);
    }
  }
}

// --- Main: Build comprehensive Karnataka college list ---
async function main() {
  const client = new LightSerpClient();
  await client.connect();
  console.log('Connected to LightSerp MCP');

  // Step 1: Search for comprehensive list of engineering colleges in Karnataka
  console.log('\n=== Step 1: Searching for college lists ===');

  const searchQueries = [
    "list of all engineering colleges in Karnataka 2025 AICTE approved complete list",
    "Karnataka engineering colleges full list with name address district type government private",
    "engineering colleges in Karnataka Bangalore Mysore Hubli Dharwad Belgaum Mangalore Gulbarga Dharwad Raichur all districts list"
  ];

  const allCollegeUrls = new Set<string>();
  const allColleges = new Map<string, { name: string, district: string, type: string, website: string }>();

  for (const query of searchQueries) {
    console.log(`\nSearching: "${query.substring(0, 80)}..."`);
    const results = await client.searchWeb(query, 50);
    console.log(`Found ${results.length} results`);

    for (const r of results) {
      const url = r.url;
      const title = r.title || '';
      // Only keep pages that might contain college lists
      if (url.includes('college') && !url.includes('courses') && !url.includes('fee') && !url.includes('admission') && !url.includes('compare')) {
        allCollegeUrls.add(url);
      }
    }
  }

  console.log(`\nFound ${allCollegeUrls.size} potential college listing pages`);

  // Step 2: Scrape the listing pages to extract college names
  console.log('\n=== Step 2: Scraping listing pages ===');
  
  const listingPages = Array.from(allCollegeUrls).slice(0, 15); // First 15 pages
  let scrapedColleges = 0;

  for (const url of listingPages) {
    try {
      console.log(`Scraping: ${url}`);
      const content = await client.scrapePage(url);
      scrapedColleges += content.length;
      // Save to file for analysis
      fs.appendFileSync('scraped_colleges_raw.txt', `${url}\n${content}\n\n${'='.repeat(80)}\n\n`);
    } catch (e) {
      console.log(`  Error: ${e}`);
    }
  }

  await client.close();
  console.log(`\nTotal scraped: ${scrapedColleges} chars`);
  console.log('Saved to scraped_colleges_raw.txt');
}

import * as fs from 'fs';
main().catch(console.error);
