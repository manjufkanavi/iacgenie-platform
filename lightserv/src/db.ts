/**
 * PostgreSQL connection pool for LightSerp multi-tenant auth.
 *
 * Environment variables:
 *   DATABASE_URL  — e.g. postgresql://lightsrp:***@iacgenie-postgres:5432/lightsrp
 *   DB_NAME       — fallback DB name if DATABASE_URL has no db path
 *
 * Graceful degradation: if DB is unavailable, all functions log a warning
 * and return null/empty — the server continues to operate with JWT fallback.
 */

import { Pool, PoolClient, Client } from 'pg';
import { readFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
import { log } from './logger.js';

// ── Configuration ─────────────────────────────────────────────────────

const DB_URL = process.env.DATABASE_URL || process.env.POSTGRES_URL || null;

// If no DATABASE_URL, try to construct from environment
let connectionString: string | null = null;
if (DB_URL) {
  connectionString = DB_URL;
} else {
  const host = process.env.PGHOST || process.env.POSTGRES_HOST || 'iacgenie-postgres';
  const port = process.env.PGPORT || process.env.POSTGRES_PORT || '5432';
  const user = process.env.PGUSER || process.env.POSTGRES_USER || 'lightsrp';
  const password = process.env.PGPASSWORD || process.env.POSTGRES_PASSWORD || '';
  const db = process.env.DATABASE_NAME || process.env.POSTGRES_DB || 'lightsrp';
  if (host && user && password) {
    connectionString = `postgresql://${user}:***@${host}:${port}/${db}`;
  }
}

// ── Connection Pool ───────────────────────────────────────────────────

export let pool: Pool | null = null;

const poolConfig = {
  connectionString: connectionString || undefined,
  max: 10,
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: 5_000,
};

/**
 * Initialize the PostgreSQL connection pool and run migrations.
 * Returns true if successfully connected and migrated, false otherwise.
 * Does NOT throw — callers should check the return value.
 */
export async function initializeDb(): Promise<boolean> {
  if (!connectionString) {
    log.warn('⚠️ No DATABASE_URL or postgres env vars configured — skipping DB');
    return false;
  }

  try {
    pool = new Pool(poolConfig);

    // Test connection
    const client = await pool.connect();
    await client.query('SELECT NOW()');

    log.info('✅ PostgreSQL connected');

    // Run migrations
    await runMigrations(client);
    client.release();

    return true;
  } catch (err) {
    log.error('❌ PostgreSQL initialization failed — continuing without DB', err);
    pool = null;
    return false;
  }
}

// ── Migration Runner ──────────────────────────────────────────────────

/**
 * Read and execute the migration SQL file.
 */
async function runMigrations(client: PoolClient): Promise<void> {
  const __dirname = dirname(fileURLToPath(import.meta.url));
  const migrationPath = join(__dirname, '..', 'migrations', '001_create_auth_tables.sql');

  let migrationSql: string;
  try {
    migrationSql = readFileSync(migrationPath, 'utf-8');
  } catch {
    log.warn('⚠️ Migration file not found — skipping migrations');
    return;
  }

  // Split on semicolons and execute each statement
  const statements = migrationSql
    .split(';')
    .map((s: string) => s.trim())
    .filter((s: string) => s.length > 0 && !s.startsWith('--'));

  // Use a transaction so any failure rolls back
  await client.query('BEGIN');
  try {
    for (const stmt of statements) {
      await client.query(stmt);
    }
    await client.query('COMMIT');
    log.info('✅ Migrations applied successfully');
  } catch (err) {
    await client.query('ROLLBACK');
    log.error('❌ Migration failed (rolled back)', err);
    throw err;
  }
}

// ── Query Helpers ─────────────────────────────────────────────────────

interface QueryRow {
  [key: string]: unknown;
}

// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface DbRow {}

async function execQuery<T extends DbRow = DbRow>(
  text: string,
  params: unknown[] = []
): Promise<T[]> {
  if (!pool) {
    log.warn('⚠️ DB not initialized — query ignored', { text: text.substring(0, 80) });
    return [];
  }

  try {
    const result = await pool.query(text, params);
    return result.rows as T[];
  } catch (err) {
    log.error('❌ DB query failed', err);
    return [];
  }
}

async function execQueryOne<T extends DbRow = DbRow>(
  text: string,
  params: unknown[] = []
): Promise<T | null> {
  if (!pool) {
    log.warn('⚠️ DB not initialized — query ignored', { text: text.substring(0, 80) });
    return null;
  }

  try {
    const result = await pool.query(text, params);
    return (result.rows.length > 0 ? result.rows[0] : null) as T | null;
  } catch (err) {
    log.error('❌ DB query failed', err);
    return null;
  }
}

async function execRun(
  text: string,
  params: unknown[] = []
): Promise<number> {
  if (!pool) {
    log.warn('⚠️ DB not initialized — run ignored', { text: text.substring(0, 80) });
    return 0;
  }

  try {
    const result = await pool.query(text, params);
    return result.rowCount ?? 0;
  } catch (err) {
    log.error('❌ DB run failed', err);
    return 0;
  }
}

async function execWithTransaction<T>(
  fn: (client: PoolClient) => Promise<T>
): Promise<T | null> {
  if (!pool) return null;

  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const result = await fn(client);
    await client.query('COMMIT');
    return result;
  } catch (err) {
    await client.query('ROLLBACK');
    log.error('❌ Transaction failed (rolled back)', err);
    return null;
  } finally {
    client.release();
  }
}

// ── Shutdown ──────────────────────────────────────────────────────────

/**
 * End all pooled connections gracefully.
 */
export async function shutdownDb(): Promise<void> {
  if (pool) {
    await pool.end();
    pool = null;
    log.info('🔌 PostgreSQL pool closed');
  }
}

// ── Public API ────────────────────────────────────────────────────────

/**
 * Run a parameterized query and return rows.
 */
export async function query<T extends QueryRow = QueryRow>(
  text: string,
  params: unknown[] = []
): Promise<T[]> {
  return execQuery<T>(text, params);
}

/**
 * Run a query that returns a single row or null.
 */
export async function queryOne<T extends QueryRow = QueryRow>(
  text: string,
  params: unknown[] = []
): Promise<T | null> {
  return execQueryOne<T>(text, params);
}

/**
 * Run an INSERT/UPDATE/DELETE that returns the number of affected rows.
 */
export async function run(
  text: string,
  params: unknown[] = []
): Promise<number> {
  return execRun(text, params);
}

/**
 * Use a dedicated client for transaction-like operations.
 */
export async function withTransaction<T>(
  fn: (client: PoolClient) => Promise<T>
): Promise<T | null> {
  return execWithTransaction(fn);
}

// Re-export Pool and Client types for callers
export type { Pool, PoolClient, Client };
