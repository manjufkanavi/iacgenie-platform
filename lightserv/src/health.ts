/**
 * Server Health Check — verifies actual dependencies, not just port availability.
 *
 * Called by http-server.ts handleHealthCheck to provide a real picture
 * of service health: cache connectivity, queue availability, LightPanda status.
 */

import { getCacheMetrics } from './cache.js';
import { getQueueMetrics } from './queue.js';
import { getLightPandaHealth } from './pagezen.js';

export interface ServerHealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  version: string;
  nodeEnv: string;
  uptime: number;
  dependencies: {
    cache: 'connected' | 'unavailable' | 'error';
    queue: 'connected' | 'fallback' | 'error';
    lightPanda: 'healthy' | 'unavailable' | 'error';
  };
}

/**
 * Get a comprehensive health status by checking all dependencies.
 * This is the authoritative health check for monitoring and readiness probes.
 */
export function getHealthStatus(): ServerHealthStatus {
  // Check cache
  let cacheStatus: 'connected' | 'unavailable' | 'error' = 'connected';
  try {
    const cacheMetrics = getCacheMetrics();
    if (!cacheMetrics.redisConnected) {
      cacheStatus = 'unavailable';
    }
  } catch {
    cacheStatus = 'error';
  }

  // Check queue
  let queueStatus: 'connected' | 'fallback' | 'error' = 'connected';
  try {
    const queueMetrics = getQueueMetrics();
    if (!queueMetrics) {
      queueStatus = 'fallback';
    }
  } catch {
    queueStatus = 'error';
  }

  // Check LightPanda
  let lightPandaStatus: 'healthy' | 'unavailable' | 'error' = 'healthy';
  try {
    const lpHealth = getLightPandaHealth();
    if (!lpHealth.available) {
      lightPandaStatus = 'unavailable';
    }
  } catch {
    lightPandaStatus = 'error';
  }

  // Overall status
  let status: 'healthy' | 'degraded' | 'unhealthy' = 'healthy';
  if (cacheStatus === 'error' || queueStatus === 'error' || lightPandaStatus === 'error') {
    status = 'unhealthy';
  } else if (cacheStatus === 'unavailable' || queueStatus === 'fallback' || lightPandaStatus === 'unavailable') {
    status = 'degraded';
  }

  return {
    status,
    timestamp: new Date().toISOString(),
    version: '3.0.0',
    nodeEnv: process.env.NODE_ENV || 'development',
    uptime: process.uptime(),
    dependencies: {
      cache: cacheStatus,
      queue: queueStatus,
      lightPanda: lightPandaStatus,
    },
  };
}
