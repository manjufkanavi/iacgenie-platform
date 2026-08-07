/**
 * Secret enforcement — prevents startup with default/weak credentials.
 *
 * Reads the actual secrets from code defaults and environment.
 * If ANY secret is still a default value, throws at startup.
 */

import { log } from './logger.js';
import { secrets } from './lib/secrets-provider.js';

const DEFAULTS = {
  SEARXNG_SECRET_KEY: 'benchmark-key',
  A12N_SECRET: 'benchmark-secret',
  COMPOSE_JWT: 'benchmark-jwt-key',
};

/**
 * Called once at server startup. Throws if any secret equals a default.
 * JWT_SECRET is checked separately — it must be set, not just "not default".
 */
export async function enforceSecrets(): Promise<void> {
  // Initialize OpenBao secrets provider (falls back to env vars if not configured)
  await secrets.initialize();

  // JWT_SECRET must be present and non-empty (no default check needed)
  const jwtSecret = await secrets.getJwtSecret();
  if (!jwtSecret || jwtSecret.length < 32) {
    log.error('❌ JWT_SECRET is missing or too short (< 32 characters). Set a cryptographically random value.');
    throw new Error(
      'LightSerp startup aborted: JWT_SECRET must be set to a secure value (min 32 chars, generate with: node -e "console.log(require(\'crypto\').randomBytes(32).toString(\'hex\'))"\' )'
    );
  }

  const searxngConfig = await secrets.getSearxngConfig();

  const checks: { name: string; actual: string }[] = [
    { name: 'SEARXNG_SECRET_KEY', actual: searxngConfig.secret || DEFAULTS.SEARXNG_SECRET_KEY },
    { name: 'A12N_SECRET', actual: process.env.A12N_SECRET || DEFAULTS.A12N_SECRET },
    { name: 'DOCKER_JWT_SECRET', actual: jwtSecret || DEFAULTS.COMPOSE_JWT },
  ];

  const violations: string[] = [];
  for (const { name, actual } of checks) {
    if (Object.values(DEFAULTS).includes(actual)) {
      violations.push(`${name}: set to default value`);
    }
  }

  if (violations.length > 0) {
    log.error('❌ SECRET ENFORCEMENT FAILED:', violations);
    throw new Error(
      `LightSerp startup aborted: default secrets detected. Set the following env vars:\n${violations.map((v) => `  ${v}`).join('\n')}`
    );
  }

  log.info('All secrets validated — no defaults detected');
}
