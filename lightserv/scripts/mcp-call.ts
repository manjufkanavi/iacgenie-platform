import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, '..');

async function callMcpTool(toolName: string, args: Record<string, any>): Promise<string> {
  return new Promise((resolve, reject) => {
    const mcp = spawn('node', ['dist/server.js'], {
      cwd: rootDir,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, NODE_ENV: 'production' }
    });

    let responseData = '';
    let messageId = 1;

    // Initialize MCP
    const initMsg = {
      jsonrpc: '2.0',
      id: messageId++,
      method: 'initialize',
      params: {
        protocolVersion: '2024-11-05',
        capabilities: {},
        clientInfo: { name: 'mcp-test', version: '1.0.0' }
      }
    };

    mcp.stdin.write(JSON.stringify(initMsg) + '\n');

    // Tool call message
    const toolCallMsg = {
      jsonrpc: '2.0',
      id: messageId++,
      method: 'tools/call',
      params: {
        name: toolName,
        arguments: args
      }
    };

    let sentInit = false;
    let sentToolCall = false;

    mcp.stdout.on('data', (data: Buffer) => {
      const text = data.toString();
      responseData += text;
      
      const lines = text.split('\n').filter(l => l.trim());
      for (const line of lines) {
        try {
          const msg = JSON.parse(line);
          if (msg.result && !sentToolCall) {
            // Initialization successful, send tool call
            sentToolCall = true;
            mcp.stdin.write(JSON.stringify(toolCallMsg) + '\n');
          } else if (msg.result && sentToolCall) {
            // Tool call result
            mcp.stdin.end();
            mcp.kill();
            resolve(JSON.stringify(msg.result));
            return;
          } else if (msg.error) {
            mcp.stdin.end();
            mcp.kill();
            reject(new Error(`MCP Error: ${msg.error.message}`));
            return;
          }
        } catch (e) {
          // Not JSON, ignore
        }
      }
    });

    mcp.stderr.on('data', (data: Buffer) => {
      console.error(`MCP stderr: ${data.toString()}`);
    });

    mcp.on('exit', (code) => {
      if (code !== 0 && code !== null) {
        reject(new Error(`MCP process exited with code ${code}`));
      }
    });

    // Timeout after 30 seconds
    setTimeout(() => {
      mcp.stdin.end();
      mcp.kill();
      reject(new Error('MCP call timed out after 30 seconds'));
    }, 30000);
  });
}

async function main() {
  const toolName = process.argv[2];
  const argsStr = process.argv[3] || '{}';
  const args = JSON.parse(argsStr);

  try {
    const result = await callMcpTool(toolName, args);
    console.log(result);
  } catch (error) {
    console.error(JSON.stringify({ error: (error as Error).message }));
    process.exit(1);
  }
}

main();
