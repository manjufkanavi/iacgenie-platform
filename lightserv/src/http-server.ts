import http from 'http';
import { log, httpLogger, generateUuid } from './logger.js';
import { initializeCache } from './cache.js';
import { initializeQueue } from './queue.js';
import { handleApiRoutes } from './api-routes.js';
import { getHealthStatus } from './health.js';
import crypto from 'crypto';

const PORT = process.env.HTTP_PORT ? parseInt(process.env.HTTP_PORT) : 3001;
const BIND_HOST = process.env.HTTP_HOST || '0.0.0.0'; // Bind to all interfaces for external access

export async function startHttpServer() {
  try {
    await initializeCache();
    await initializeQueue();

    const server = http.createServer((req, res) => {
      httpLogger(req, res);

      const reqId = req.headers['x-request-id'] as string || generateUuid();
      (req as any).reqId = reqId;
      res.setHeader('X-Request-Id', reqId);

      // Handle API routes
      if (handleApiRoutes(req, res)) {
        return;
      }

      // Handle health check endpoints
      if (req.url === '/health' && req.method === 'GET') {
        handleHealthCheck(req, res);
      } else if (req.url === '/ready' && req.method === 'GET') {
        void handleReadinessCheck(req, res);
      } else {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Not Found', reqId }));
      }
    });

    server.on('error', (err) => {
      log.warn(`HTTP server error: ${err.message}`);
      server.emit('_bind_error', err);
    });

    const listenPromise = new Promise<void>((resolve, reject) => {
      server.once('_bind_error', reject);
      server.listen(PORT, BIND_HOST, () => {
        log.info(`HTTP server listening on ${BIND_HOST}:${PORT}`);
        resolve();
      });
    });

    await listenPromise;
    return server;
  } catch (error) {
    log.error('Failed to start HTTP server', error);
    throw error;
  }
}

/**
 * Start the MCP-over-SSE server on a separate port.
 * This allows MCP clients to connect via HTTP instead of stdio.
 *
 * @param requestHandler Custom request handler that returns true if it handled the request
 */
export async function startMcpsseServer(
  requestHandler: (req: http.IncomingMessage, res: http.ServerResponse) => Promise<boolean> | boolean
): Promise<http.Server | null> {
  const MCP_PORT = parseInt(process.env.MCP_SSE_PORT || '7805');

  try {
    const server = http.createServer(async (req, res) => {
      httpLogger(req, res);

      const reqId = req.headers['x-request-id'] as string || generateUuid();
      (req as any).reqId = reqId;
      res.setHeader('X-Request-Id', reqId);

      // Check for JWT auth on MCP endpoints
      const authHeader = req.headers.authorization;
      const mcpPath = req.url?.split('?')[0] || '';

      if (mcpPath.startsWith('/mcp') && authHeader) {
        const token = authHeader.replace('Bearer ', '');
        try {
          const { validateToken } = await import('./auth.js');
          await validateToken(token);
        } catch {
          res.writeHead(401, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Unauthorized', reqId }));
          return;
        }
      }

      // Pass to custom handler
      const handled = await requestHandler(req, res);
      if (handled) return;

      // Default 404
      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Not Found', reqId }));
    });

    server.on('error', (err) => {
      log.warn(`MCP SSE server error: ${err.message}`);
    });

    await new Promise<void>((resolve, reject) => {
      server.once('error', reject);
      server.listen(MCP_PORT, '0.0.0.0', () => {
        log.info(`MCP SSE server listening on 0.0.0.0:${MCP_PORT}`);
        log.info(`MCP endpoint: http://0.0.0.0:${MCP_PORT}/mcp`);
        resolve();
      });
    });

    return server;
  } catch (error) {
    log.error('Failed to start MCP SSE server', error);
    return null;
  }
}

function handleHealthCheck(_req: http.IncomingMessage, res: http.ServerResponse) {
  try {
    const healthStatus = getHealthStatus();
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(healthStatus, null, 2));
  } catch (error) {
    log.error('Health check failed', error);
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'unhealthy', error: 'Internal server error' }));
  }
}

async function handleReadinessCheck(_req: http.IncomingMessage, res: http.ServerResponse) {
  try {
    let cacheStatus = 'unknown';
    let queueStatus = 'unknown';

    try {
      const cacheTest = await initializeCache();
      cacheStatus = cacheTest ? 'connected' : 'fallback';
    } catch (cacheError) {
      cacheStatus = 'failed';
      log.warn('Cache connection test failed', cacheError);
    }

    try {
      await initializeQueue();
      queueStatus = 'connected';
    } catch (queueError) {
      queueStatus = 'failed';
      log.warn('Queue connection test failed', queueError);
    }

    const readinessStatus = {
      status: 'ready',
      timestamp: new Date().toISOString(),
      dependencies: {
        cache: cacheStatus,
        queue: queueStatus,
        searxng: process.env.SEARXNG_URL ? 'configured' : 'not_configured',
        proxy: process.env.PROXY_URLS ? 'configured' : 'not_configured',
        mcpSse: process.env.MCP_SSE_PORT ? `port ${process.env.MCP_SSE_PORT}` : 'disabled',
      }
    };

    const isReady = cacheStatus !== 'failed' && queueStatus !== 'failed';
    if (isReady) {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(readinessStatus, null, 2));
    } else {
      readinessStatus.status = 'not_ready';
      res.writeHead(503, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(readinessStatus, null, 2));
    }
  } catch (error) {
    log.error('Readiness check failed', error);
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'not_ready', error: 'Internal server error' }));
  }
}
