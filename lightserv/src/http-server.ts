import http from 'http';
import { log, httpLogger } from './logger.js';
import { generateUuid } from './logger.js';
import { initializeCache } from './cache.js';
import { initializeQueue } from './queue.js';
import { handleApiRoutes } from './api-routes.js';
import { getHealthStatus } from './health.js';

const PORT = process.env.HTTP_PORT ? parseInt(process.env.HTTP_PORT) : 3000;

export async function startHttpServer() {
  try {
    await initializeCache();
    await initializeQueue();

    const server = http.createServer((req, res) => {
      httpLogger(req, res);

      // Attach reqId for non-API routes
      const reqId = req.headers['x-request-id'] as string || generateUuid();
      (req as any).reqId = reqId;
      res.setHeader('X-Request-Id', reqId);

      // Handle API routes
      if (handleApiRoutes(req, res)) {
        return; // API routes send their own response
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
      server.listen(PORT, () => {
        log.info(`HTTP server listening on port ${PORT}`);
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
        searxng: process.env.SEARXNG_URL ? 'configured' : 'not_configured'
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
