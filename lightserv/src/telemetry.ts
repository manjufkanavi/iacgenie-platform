import { NodeSDK } from '@opentelemetry/sdk-node';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { Resource } from '@opentelemetry/resources';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-node';
import { diag, DiagConsoleLogger, DiagLogLevel } from '@opentelemetry/api';

// Configure OpenTelemetry diagnostics
diag.setLogger(new DiagConsoleLogger(), DiagLogLevel.INFO);

const LOGTIDE_URL = process.env.LOGTIDE_URL || 'http://logtide:4318/v1/traces';

export function initializeTelemetry() {
  try {
    console.error('🔍 Initializing OpenTelemetry...');

    const traceExporter = new OTLPTraceExporter({
      url: LOGTIDE_URL,
    });

    const spanProcessor = new BatchSpanProcessor(traceExporter);

    const sdk = new NodeSDK({
      resource: new Resource({
        [SemanticResourceAttributes.SERVICE_NAME]: 'lightserp-mcp',
        [SemanticResourceAttributes.SERVICE_VERSION]: '3.0.0',
        [SemanticResourceAttributes.DEPLOYMENT_ENVIRONMENT]: process.env.NODE_ENV || 'development'
      }),
      spanProcessor: spanProcessor as any,
      instrumentations: [getNodeAutoInstrumentations({
        '@opentelemetry/instrumentation-http': {
          enabled: true,
          ignoreIncomingRequestHook: (request: any) => {
            // Don't trace health check endpoints
            return !!request.url?.includes('/health') || !!request.url?.includes('/ready');
          }
        },
        '@opentelemetry/instrumentation-fs': {
          enabled: false // Disable filesystem instrumentation for performance
        }
      })]
    });

    sdk.start();

    // Handle graceful shutdown
    process.on('SIGTERM', () => {
      sdk.shutdown()
        .then(() => console.error('✅ OpenTelemetry SDK shut down successfully'))
        .finally(() => process.exit(0));
    });

    console.error('✅ OpenTelemetry initialized successfully');
    return sdk;
  } catch (error) {
    console.error('❌ Failed to initialize OpenTelemetry:', error);
    // Continue without telemetry if initialization fails
    return null;
  }
}