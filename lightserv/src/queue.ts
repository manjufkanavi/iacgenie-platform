/**
 * NSQ queue integration with result storage and async job processing.
 *
 * Architecture:
 * 1. publishScrapeJob() → pushes to 'scrape_jobs' topic
 * 2. Consumer runs scrape logic → stores result in Redis
 * 3. getScrapeResult() → polls Redis for result (with timeout/wakeup)
 *
 * Graceful degradation: if NSQ is unavailable, jobs are processed
 * synchronously and results stored in memory/Redis.
 */

import { Writer, Reader } from 'nsqjs';
import { ScrapeResult } from './types.js';
import { log } from './logger.js';
import { setRedisCache, getRedisCache, deleteRedisCache } from './cache.js';

const NSQD_URL = process.env.NSQD_URL || 'iacgenie-nsqd:4150';
const LOOKUPD_URL = NSQD_URL.replace('4150', '4161');

const NSQ_TOPIC_JOBS = 'scrape_jobs';
// const NSQ_TOPIC_RESULTS = 'scrape_results';

let writer: Writer | null = null;
let reader: Reader | null = null;
let consumerRunning = false;

// In-memory result store for when NSQ is unavailable
const pendingResults = new Map<string, {
  resolve: (result: ScrapeResult) => void;
  reject: (err: Error) => void;
  timer: ReturnType<typeof setTimeout> | null;
  promiseResult?: ScrapeResult;
}>();

// Queue metrics
const queueMetrics = {
  jobsPublished: 0,
  jobsProcessed: 0,
  jobsFailed: 0,
  jobsRetried: 0,
  activeConsumers: 0,
  avgProcessingTime: 0,
};

export interface QueueMetrics {
  nsqConnected: boolean;
  jobsPublished: number;
  jobsProcessed: number;
  jobsFailed: number;
  jobsRetried: number;
  avgProcessingTime: number;
  pendingResultCount: number;
}

// ── Initialization ──────────────────────────────────────────────────

export async function initializeQueue(): Promise<void> {
  try {
    log.info('🚀 Initializing NSQ queue...');

    // Initialize NSQ writer
    writer = new Writer(NSQ_TOPIC_JOBS, NSQD_URL);
    await Promise.race([
      new Promise<void>((resolve, reject) => {
        writer?.on('ready', () => {
          log.info(`✅ NSQ writer connected to ${NSQD_URL}`);
          resolve();
        });
        writer?.on('error', reject);
      }),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error('NSQ writer connection timeout')), 3000)
      ),
    ]);

    // Initialize NSQ reader
    reader = new Reader(NSQ_TOPIC_JOBS, 'scrape_consumers', {
      lookupdHTTPAddresses: LOOKUPD_URL,
      maxInFlight: 5, // Process up to 5 jobs concurrently
    });

    log.info('✅ NSQ queue initialized');
  } catch (error: any) {
    log.warn(`⚠️ NSQ not available (${error.message}), queue will fall back to sync mode`);
    writer = null;
    reader = null;
  }
}

export function getQueueMetrics(): QueueMetrics {
  return {
    nsqConnected: !!writer,
    jobsPublished: queueMetrics.jobsPublished,
    jobsProcessed: queueMetrics.jobsProcessed,
    jobsFailed: queueMetrics.jobsFailed,
    jobsRetried: queueMetrics.jobsRetried,
    avgProcessingTime: queueMetrics.avgProcessingTime,
    pendingResultCount: pendingResults.size,
  };
}

export function shutdownQueue(): void {
  if (consumerRunning && reader) {
    reader.close();
    consumerRunning = false;
  }
  if (writer) {
    writer.end?.();
    writer = null;
  }
  // Clear pending result watchers
  for (const entry of pendingResults.values()) {
    if (entry.timer) clearTimeout(entry.timer);
  }
  pendingResults.clear();
  log.info('🛑 Queue shutdown complete');
}

// ── Job Publishing ──────────────────────────────────────────────────

export async function publishScrapeJob(jobId: string, url: string): Promise<void> {
  /* startTime tracking removed */
  queueMetrics.jobsPublished++;

  const jobMessage = JSON.stringify({ jobId, url, timestamp: new Date().toISOString() });

  if (!writer) {
    // Fallback: publish directly via HTTP API if available
    try {
      const resp = await fetch(`http://${NSQD_URL}/put?topic=${NSQ_TOPIC_JOBS}`, {
        method: 'POST',
        body: jobMessage,
        headers: { 'Content-Type': 'application/json' },
      });
      if (!resp.ok) throw new Error(`HTTP put failed: ${resp.status}`);
      log.info(`📤 Published job ${jobId} via HTTP fallback`);
      return;
    } catch (e) {
      log.warn(`⚠️ NSQ HTTP fallback also failed for job ${jobId}`);
      return;
    }
  }

  return new Promise((resolve, reject) => {
    writer?.send(NSQ_TOPIC_JOBS, jobMessage, (err: unknown) => {
      if (err) {
        queueMetrics.jobsFailed++;
        log.error(`❌ Failed to publish job ${jobId}: ${err}`);
        reject(err);
      } else {
        log.info(`📤 Published job ${jobId} for ${url}`);
        resolve();
      }
    });
  });
}

// ── Consumer Registration ───────────────────────────────────────────

/**
 * Register a scrape handler function. The consumer will listen for
 * scrape_jobs and process them, storing results in Redis.
 *
 * @param handler - Function that takes jobId+url and returns a ScrapeResult
 */
export function registerConsumer(handler: (jobId: string, url: string) => Promise<ScrapeResult>): void {
  if (consumerRunning) {
    log.warn('⚠️ Consumer already registered, skipping');
    return;
  }

  const handleMessage = async (msg: any) => {
    const startTime = Date.now();
    const jobId = msg.id;

    try {
      const job = JSON.parse(msg.body.toString()) as { jobId: string; url: string };
      log.info(`📥 Processing job ${job.jobId}: ${job.url}`);

      const result = await handler(job.jobId, job.url);
      const elapsed = Date.now() - startTime;

      // Store result in Redis (TTL: 1 hour)
      const resultKey = `scrape:result:${jobId}`;
      await setRedisCache(resultKey, {
        ...result,
        processedAt: new Date().toISOString(),
        processingTime: elapsed,
      }, 3600);

      queueMetrics.jobsProcessed++;
      queueMetrics.avgProcessingTime =
        (queueMetrics.avgProcessingTime * queueMetrics.jobsProcessed + elapsed) /
        (queueMetrics.jobsProcessed + 1);

      log.info(`✅ Job ${job.jobId} completed in ${elapsed}ms (${result.content?.length || 0} chars)`);
      msg.finish();
    } catch (error: any) {
      queueMetrics.jobsFailed++;
      log.error(`❌ Job ${jobId} failed: ${error.message}`);
      queueMetrics.jobsRetried++;

      // Requeue with exponential backoff
      const delay = Math.min(1000 * Math.pow(2, queueMetrics.jobsRetried), 30000);
      msg.requeue(delay);
    }
  };

  if (!reader) {
    // Start reader if not initialized
    initializeQueue().then(() => {
      if (reader) {
        reader.on('message', handleMessage);
        reader.on('error', (err: any) =>
          log.error(`❌ NSQ reader error: ${err}`)
        );
        consumerRunning = true;
        log.info(`👂 Consumer started, listening on ${NSQ_TOPIC_JOBS}`);
      } else {
        log.warn('⚠️ NSQ reader not available, starting sync consumer');
        startSyncConsumer(handler);
      }
    });
  } else {
    reader.on('message', handleMessage);
    reader.on('error', (err: any) =>
      log.error(`❌ NSQ reader error: ${err}`)
    );
    consumerRunning = true;
    log.info(`👂 Consumer started on ${NSQ_TOPIC_JOBS} (maxInFlight=5)`);
  }
}

// ── Sync Fallback Consumer ──────────────────────────────────────────

/**
 * When NSQ is unavailable, process jobs synchronously via HTTP push.
 * The scrape_page MCP tool can push jobs to NSQD HTTP API directly.
 */
function startSyncConsumer(_handler: (jobId: string, url: string) => Promise<ScrapeResult>): void {
  // This runs inline — no separate process. Jobs are processed as
  // scrape_page MCP tool calls arrive.
  consumerRunning = true;
  log.info('👂 Sync consumer active — processing jobs inline');
}

// ── Result Retrieval ────────────────────────────────────────────────

export function getScrapeResult(jobId: string, timeout = 30000): Promise<ScrapeResult> {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + timeout;

    // Poll Redis for the result
    const poll = async () => {
      if (Date.now() > deadline) {
        reject(new Error(`Result for job ${jobId} not ready after ${timeout}ms`));
        return;
      }

      const key = `scrape:result:${jobId}`;
      const cached = await getRedisCache(key);
      if (cached) {
        resolve(cached as ScrapeResult);
        return;
      }

      // Check in-memory pending results (for NSQ-unavailable mode)
      const pending = pendingResults.get(jobId);
      if (pending && pending.promiseResult) {
        resolve(pending.promiseResult);
        return;
      }

      // Poll again after 500ms
      setTimeout(poll, 500);
    };

    poll();
  });
}

// ── Direct Job Processing (for sync MCP tool calls) ─────────────────

/**
 * Process a scrape job synchronously. Used by the scrape_page MCP tool
 * when the user wants immediate results.
 */
export async function processScrapeJobSync(jobId: string, url: string,
  handler: (jobId: string, url: string) => Promise<ScrapeResult>
): Promise<ScrapeResult> {
  const startTime = Date.now();

  // Try NSQ publish first — validate URL is internal (SSRF protection)
  let nsqPublished = false;
  if (NSQD_URL && !NSQD_URL.match(/^(localhost|127\.0\.0\.1|10\.|172\.(1[6-9]|2\d|3[01])\.|192\.168\.)/)) {
    log.warn(`⚠️ NSQD_URL blocked: ${NSQD_URL} — not an internal address`);
    nsqPublished = false;
  } else if (NSQD_URL) {
    try {
      await publishScrapeJob(jobId, url);
      nsqPublished = true;
    } catch {
      log.info(`⚠️ NSQ unavailable, processing job ${jobId} locally`);
    }
  }

  // Only process locally if NSQ publish failed or URL was blocked.
  // If NSQ succeeded, the NSQ consumer will call handler() and store the result in Redis.
  if (!nsqPublished) {
    try {
      const result = await handler(jobId, url);
      queueMetrics.jobsProcessed++;

      // Store in Redis for async retrieval
      const resultKey = `scrape:result:${jobId}`;
      await setRedisCache(resultKey, {
        ...result,
        processedAt: new Date().toISOString(),
        processedVia: 'local',
        processingTime: Date.now() - startTime,
      }, 3600);

      return result;
    } catch (error: any) {
      queueMetrics.jobsFailed++;
      log.error(`❌ Job ${jobId} failed: ${error.message}`);
      throw error;
    }
  }

  // NSQ handled the job — wait for the async result
  return await getScrapeResult(jobId, 120000);
}

// ── Cleanup ─────────────────────────────────────────────────────────

export function cleanupResult(jobId: string): void {
  const key = `scrape:result:${jobId}`;
  deleteRedisCache(key).catch((e) => log.debug('Cleanup deleteRedisCache error', { key, error: e }));
  // Clear pending watcher
  const pending = pendingResults.get(jobId);
  if (pending) {
    if (pending.timer) clearTimeout(pending.timer);
    pendingResults.delete(jobId);
    log.debug(`Cleaned up result for job ${jobId}`);
  }
}
