#!/usr/bin/env node
// Scrape specific URLs with MCP
import { spawn } from 'child_process';
import fs from 'fs';

const LIGHTSERP_PATH = '/Users/manjunathkanavi/workspace/git_workspace/LightSerp/dist/server.js';
const urls = [
  'https://www.instagram.com/jumi_techi/',
  'https://www.instagram.com/jumi_techi_kra/',
  'https://www.instagram.com/crochetwith_jumi/',
  'https://www.instagram.com/jumitechi/',
  'https://www.facebook.com/nabum.nuna/',
  'https://www.bcci.tv/domestic/womens-under-15-one-day-trophy-2022-23/match/28',
  'https://dngc.ac.in/uploads/web_document/main_document_1696064768_1.pdf',
  'https://www.facebook.com/p/Aniis-Restaurant-100075792867663/',
  'https://nregastrep.nic.in/netnrega/delayed_pay_detail.aspx?typ=1&lflag=eng&state_name=ARUNACHAL+PRADESH&state_code=03&district_name=PAKKE+KESSANG&district_code=0323&block_code=0303004&block_name=PAKKE-KESSANG&panchayat_code=0303004006&panchayat_name=RILLOH-01&fin_year=2024-2025',
  'https://ecourtsindia.com/Search?query=State+Of+Ap&page=1&pageSize=10&cc=ARPP01&st=DISPOSED&pg=2',
  'https://www.facebook.com/roohihaflongbar/photos/roohi-rigu-rikhaosa-in-red-with-a-handmade-potli-bag-dm-to-orderroohi-handwoven-/494694092675904/',
  'https://www.facebook.com/kabitaskitchen/videos/%E0%A4%AE%E0%A4%BF%E0%A4%9F%E0%A5%8D%E0%A4%9F%E0%A5%80-%E0%A4%95%E0%A5%87-%E0%A4%AC%E0%A4%B0%E0%A5%8D%E0%A4%A4%E0%A4%A8-%E0%A4%AE%E0%A5%87%E0%A4%82-%E0%A4%B9%E0%A4%BE%E0%A4%82%E0%A4%A1%E0%A5%80-%E0%A4%AA%E0%A4%A8%E0%A5%80%E0%A4%B0-%E0%A4%95%E0%A5%80-%E0%A4%AB%E0%A5%87%E0%A4%AE%E0%A4%B8-%E0%A4%B0%E0%A5%87%E0%A4%B8%E0%A4%BF%E0%A4%AA%E0%A5%80-handi-paneer-recipe-by-kabitaskitc/261739089720081/',
  'https://www.facebook.com/waittilligetfamous/photos/i-know-its-going-to-be-a-shock-but-hey-iam-a-mom-now-please-welcome-mini-me-alth/796531978755931/',
  'https://www.facebook.com/roohihaflongbar/posts/guess-what-are-we-cooking-today/628281702650475/',
];

async function scrapeUrl(url) {
  return new Promise((resolve, reject) => {
    let stdoutBuf = '';
    const server = spawn('node', [LIGHTSERP_PATH], { stdio: ['pipe', 'pipe', 'pipe'], env: { ...process.env } });
    
    server.stdout.on('data', (data) => { stdoutBuf += data.toString(); });
    server.stderr.on('data', () => {});
    
    server.stdout.on('data', (data) => {
      const text = data.toString();
      const lines = text.split('\n').filter(l => l.trim());
      for (const line of lines) {
        try {
          const msg = JSON.parse(line);
          if (msg.id && (msg.result || msg.error)) {
            if (msg.error) { server.kill(); reject(new Error(msg.error.message || JSON.stringify(msg.error))); }
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
        server.stdin.write(JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'scrape-client', version: '1.0.0' } } }) + '\n');
        setTimeout(() => {
          server.stdin.write(JSON.stringify({ jsonrpc: '2.0', id: 2, method: 'tools/call', params: { name: 'scrape_page', arguments: { url } } }) + '\n');
        }, 1000);
      }, 2500);
    });
    server.on('error', reject);
    setTimeout(() => { server.kill(); reject(new Error('Timeout')); }, 45000);
  });
}

async function main() {
  for (let i = 0; i < urls.length; i++) {
    const url = urls[i];
    process.stdout.write(`Scrape ${i+1}/${urls.length}: ${url.substring(0, 80)}\n`);
    try {
      const result = await scrapeUrl(url);
      console.log(`RESULT (${result.length} chars):\n${result.substring(0, 2000)}\n`);
    } catch (err) {
      console.log(`ERROR: ${err.message}\n`);
    }
    // Rate limit delay
    await new Promise(r => setTimeout(r, 2200));
  }
}

main().catch(console.error);
