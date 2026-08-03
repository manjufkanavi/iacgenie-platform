/**
 * Standardized error hierarchy for LightSerp.
 *
 * Every error carries:
 * - code: machine-readable error identifier
 * - statusCode: HTTP status for external consumption
 * - userMessage: human-friendly error message
 * - isOperational: true for expected errors (config/validation), false for bugs
 */

export class AppError extends Error {
  constructor(
    public readonly userMessage: string,
    public readonly statusCode: number = 500,
    public readonly code: string = 'INTERNAL_ERROR',
    public readonly isOperational: boolean = true
  ) {
    super(userMessage);
    this.name = this.constructor.name;
  }

  toJson(): Record<string, unknown> {
    return {
      error: this.userMessage,
      code: this.code,
      statusCode: this.statusCode,
    };
  }
}

export class ValidationError extends AppError {
  constructor(message: string) {
    super(message, 400, 'VALIDATION_ERROR', true);
  }
}

export class AuthenticationError extends AppError {
  constructor(message: string = 'Authentication required') {
    super(message, 401, 'AUTH_REQUIRED', true);
  }
}

export class AuthorizationError extends AppError {
  constructor(message: string = 'Insufficient permissions') {
    super(message, 403, 'FORBIDDEN', true);
  }
}

export class NotFoundError extends AppError {
  constructor(resource: string = 'Resource') {
    super(`${resource} not found`, 404, 'NOT_FOUND', true);
  }
}

export class RateLimitError extends AppError {
  constructor(message: string = 'Rate limit exceeded') {
    super(message, 429, 'RATE_LIMITED', true);
  }
}

export class ServiceUnavailableError extends AppError {
  constructor(message: string = 'Service unavailable') {
    super(message, 503, 'SERVICE_UNAVAILABLE', true);
  }
}

export class ConfigurationError extends AppError {
  constructor(message: string) {
    super(message, 500, 'CONFIGURATION_ERROR', false);
  }
}

/**
 * Format an error into a safe string for MCP tool responses.
 * Extracts the first line of the error message and truncates to 200 chars.
 */
export function formatMcpError(err: unknown): { text: string } {
  if (err instanceof AppError) {
    return { text: err.userMessage };
  }
  if (err instanceof Error) {
    return { text: err.message.split('\n')[0].substring(0, 200) };
  }
  return { text: String(err).split('\n')[0].substring(0, 200) };
}
