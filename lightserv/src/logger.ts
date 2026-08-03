import pino, { destination } from 'pino';
import _pinoHttp from 'pino-http';

// Create main logger — logs to stderr to avoid polluting MCP stdout protocol channel
const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  serializers: {
    err: pino.stdSerializers.err
  },
  formatters: {
    log: (obj) => {
      // Inject reqId from the async local storage context if available
      // pino-http attaches reqId as a property on the request
      return obj;
    }
  }
}, destination({ dest: 2, sync: false }));

// Generate a UUID v4
export function generateUuid(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// Create HTTP request logger middleware — also logs to stderr
const pinoHttp = (_pinoHttp as any) as (opts?: Record<string, unknown>) => (req: unknown, res: unknown) => void;

export const httpLogger = pinoHttp({
  autoLogging: {
    ignore: (req: any) => {
      // Don't log health check endpoints
      return req.url?.includes('/health') || req.url?.includes('/ready');
    }
  },
  serializers: {
    req: (req: any) => ({
      method: req.method,
      url: req.url,
      remoteAddress: req.remoteAddress,
      remotePort: req.remotePort,
      reqId: req.reqId
    }),
    res: (res: any) => ({
      statusCode: res.statusCode,
      headers: res.headers
    })
  },
  stream: { write: (msg: string) => process.stderr.write(msg) },
  customProps: (req: any, _res: any) => ({ reqId: req.reqId })
});

// Logger methods
export const log = {
  info: (message: string, data?: any) => logger.info(data || {}, message),
  warn: (message: string, data?: any) => logger.warn(data || {}, message),
  error: (message: string, error?: Error | any) => {
    if (error instanceof Error) {
      logger.error({ err: error }, message);
    } else {
      logger.error(error || {}, message);
    }
  },
  debug: (message: string, data?: any) => logger.debug(data || {}, message),
  trace: (message: string, data?: any) => logger.trace(data || {}, message),
  fatal: (message: string, error?: Error | any) => {
    if (error instanceof Error) {
      logger.fatal({ err: error }, message);
    } else {
      logger.fatal(error || {}, message);
    }
  }
};

// Health check logger — also logs to stderr
export const healthLogger = pino({
  level: 'info'
}, destination({ dest: 2, sync: false }));

export default logger;
