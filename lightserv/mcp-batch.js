#!/usr/bin/env node
// MCP client that runs multiple queries sequentially
import { spawn } from 'child_process';

const LIGHTSERP_PATH = '/Users/manjunathkanavi/workspace/git_workspace/LightSerp/dist/server.js';
const queries = process.argv.slice(2);

if (queries.length === 0) {
  console.error('Usage: node mcp-batch.js "query1" "query2" ...');
  process.exit(1);
}

async function runSearch(query) {
  return new Promise((resolve, reject) => {
    let stdoutBuf = '';
    let stderrBuf = '';
    
    const server = spawn('node', [LIGHTSERP_PATH], {
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env }
    });

    server.stdout.on('data', (data) => { stdoutBuf += data.toString(); });
    server.stderr.on('data', (data) => { stderrBuf += data.toString(); });
    
    let messageCount = 0;
    
    server.stdout.on('data', (data) => {
      const text = data.toString();
      const lines = text.split('\n').filter(l => l.trim());
      for (const line of lines) {
        try {
          const msg = JSON.parse(line);
          if (msg.id && (msg.result || msg.error)) {
            messageCount++;
            if (msg.error) {
              server.kill();
              reject(new Error(msg.error.message || JSON.stringify(msg.error)));
            }
            if (msg.result && typeof msg.result.content?.[0]?.text === 'string') {
              server.kill();
              resolve(msg.result.content[0].text);
              return;
            }
          }
        } catch {}
      }
    });

    server.on('spawn', () => {
      setTimeout(() => {
        server.stdin.write(JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'batch-client', version: '1.0.0' } } }) + '\n');
        
        setTimeout(() => {
          server.stdin.write(JSON.stringify({ jsonrpc: '2.0', id: 2, method: 'tools/call', params: { name: 'search_web', arguments: { query } } }) + '\n');
        }, 1000);
      }, 2500);
    });

    server.on('error', reject);
    
    setTimeout(() => {
      server.kill();
      reject(new Error('Timeout'));
    }, 25000);
  });
}

async function main() {
  const results = [];
  for (let i = 0; i < queries.length; i++) {
    process.stdout.write(`Query ${i+1}/${queries.length}: ${queries[i]}\n`);
    try {
      const result = await runSearch(queries[i]);
      results.push({ query: queries[i], result });
    } catch (err) {
      results.push({ query: queries[i], error: err.message });
    }
  }
  console.log('\n\n=== RESULTS ===');
  for (const r of results) {
    console.log(`\n--- ${r.query} ---`);
    console.log(r.result || r.error);
  }
}

main().catch(console.error);
