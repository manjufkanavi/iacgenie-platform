#!/usr/bin/env node
// MCP stdio client - calls LightSerp tools via JSON-RPC over stdin/stdout
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const LIGHTSERP_PATH = path.join('/Users/manjunathkanavi/workspace/git_workspace/LightSerp', 'dist', 'server.js');

const args = process.argv[2] || 'search'; // 'search' or 'scrape'
const query = process.argv.slice(3).join(' ') || '';

if (!query) {
  console.error('Usage: node mcp-client.js search|scrape <query/url>');
  process.exit(1);
}

// The local dist/server.js needs local-accessible URLs (not docker network names)
const localEnv = {
  ...process.env,
  NODE_ENV: 'production',
  // Use local ports (not docker-compose hostnames)
  HTTP_PORT: '3004',
  SEARXNG_URL: 'http://127.0.0.1:8070/search?format=json',
  REDIS_URL: 'redis://127.0.0.1:8071',
  NSQD_URL: '127.0.0.1:8073',  // NSQD TCP port (4150 → 8073)
  NSQ_LOOKUPD_URL: '127.0.0.1:8072',  // NSQ Lookupd HTTP port (4161 → 8072)
  PROXY_URLS: '',
  // LightPanda native scraping — no PageZen HTTP service needed
  LIGHTPANDA_BIN: '/usr/local/bin/lightpanda',
  JWT_SECRET: 'mcp-client-local-secret',
  // LightPanda native scraping config (no PageZen HTTP service)
  LIGHTPANDA_TIMEOUT_MS: '30000',
};

const server = spawn('node', [LIGHTSERP_PATH], {
  stdio: ['pipe', 'pipe', 'pipe'],
  env: localEnv
});

let buffer = '';
let initialized = false;

server.stdout.on('data', (data) => {
  buffer += data.toString();
  processContent(buffer);
});

server.stderr.on('data', (data) => {
  // Show stderr for debugging (don't suppress)
  const lines = data.toString().split('\n');
  for (const line of lines) {
    if (line && !line.includes('Accessing resource') && !line.includes('option is deprecated')) {
      // Log for debugging but don't clutter output
    }
  }
});

let requestId = 1;

function sendRequest(method, params) {
  const req = JSON.stringify({ jsonrpc: '2.0', id: requestId++, method, params }) + '\n';
  server.stdin.write(req);
}

function processContent(content) {
  const lines = content.split('\n').filter(l => l.trim());
  for (const line of lines) {
    try {
      const msg = JSON.parse(line);
      if (msg.result && msg.result !== null) {
        // Found our response
        if (typeof msg.result.content?.[0]?.text === 'string') {
          const text = msg.result.content[0].text;
          // Could be JSON (search results) or HTML (scrape results)
          try {
            const parsed = JSON.parse(text);
            console.log(JSON.stringify(parsed, null, 2));
          } catch {
            console.log(text);
          }
          server.kill();
          process.exit(0);
        }
      }
      if (msg.error) {
        console.error('MCP Error:', msg.error);
        server.kill();
        process.exit(1);
      }
    } catch {}
  }
}

// Initialize first
server.on('spawn', () => {
  setTimeout(() => {
    sendRequest('initialize', {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: { name: 'lightserp-client', version: '1.0.0' }
    });

    // After init, send tool call
    setTimeout(() => {
      if (args === 'search') {
        sendRequest('tools/call', {
          name: 'search_web',
          arguments: { query }
        });
      } else if (args === 'scrape') {
        sendRequest('tools/call', {
          name: 'scrape_page',
          arguments: { url: query }
        });
      }
    }, 3000);
  }, 5000);
});

server.on('error', (err) => {
  console.error('Failed to start MCP server:', err.message);
  process.exit(1);
});

// Also listen for process exit with non-zero code
server.on('close', (code) => {
  if (code !== 0 && !initialized) {
    console.error(`MCP server exited with code ${code}`);
    process.exit(1);
  }
});

// Timeout after 90 seconds
setTimeout(() => {
  console.error('Timeout waiting for MCP response');
  server.kill();
  process.exit(1);
}, 90000);
