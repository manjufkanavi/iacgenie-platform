/**
 * LightSerp authentication — Keycloak integration with PostgreSQL persistence.
 *
 * Features:
 * - Keycloak JWT introspection (RFC 7662)
 * - Keycloak userinfo endpoint (OpenID Connect)
 * - Signup: Create user via Keycloak Admin API, send real Keycloak verification email
 * - Email verification: JWT token -> mark verified in Keycloak + PostgreSQL
 * - Login: Local password auth with argon2id hashing
 * - Password reset: Local JWT tokens + SMTP2GO
 * - Sync Keycloak users to PostgreSQL
 * - API key management (argon2 hashed for improved security)
 * - Usage logging to PostgreSQL
 * - JWT fallback (HS256 local validation) for testing
 *
 * SECURITY: Requires JWT_SECRET env var (enforced at startup by secrets.ts).
 * Password hashing uses argon2id (modern, memory-hard).
 *
 * AUTH FLOW (TerraGenius-inspired):
 *  1. User signs up -> Keycloak Admin API creates user with password -> Keycloak sends real verification email
 *  2. User clicks verification link -> JWT token validated -> Keycloak marks emailVerified + PostgreSQL updated
 *  3. User logs in -> local password auth with argon2id -> access/refresh tokens -> PostgreSQL user synced
 */

import jwt from 'jsonwebtoken';
import crypto from 'node:crypto';
import https from 'node:https';
import axios, { AxiosError } from 'axios';
import {
  AuthToken,
  User,
  ApiKey,
  KeycloakIntrospectionResponse,
} from './types.js';
import { log } from './logger.js';
import { query, queryOne, run, initializeDb, pool } from './db.js';
import { config, isJwtConfigured } from './auth-config.js';
import {
  hashPasswordPlain,
  verifyPasswordPlain,
  isArgon2Hash,
  isSha256Hash,
} from './password-hashing.js';
import { buildVerificationEmail, buildWelcomeEmail, buildPasswordResetEmail } from './email-templates.js';

// ── Configuration ─────────────────────────────────────────────────────

const KC_INTROSPECTION_URL = `${config.KEYCLOAK_URL}/realms/${config.KEYCLOAK_REALM}/protocol/openid-connect/token/introspection`;
const KC_USERINFO_URL = `${config.KEYCLOAK_URL}/realms/${config.KEYCLOAK_REALM}/protocol/openid-connect/userinfo`;

// ── State ─────────────────────────────────────────────────────────────

let dbInitialized = false;

// ── Helpers ───────────────────────────────────────────────────────────

async function ensureDb(): Promise<boolean> {
  if (dbInitialized || pool) return true;
  dbInitialized = await initializeDb();
  return dbInitialized;
}

// ── JWT Functions ─────────────────────────────────────────────────────

/**
 * Generate a local JWT token for authenticated sessions.
 * Requires JWT_SECRET to be configured (enforced at startup).
 */
export function generateToken(userId: string, username: string, roles: string[]): string {
  if (!isJwtConfigured()) {
    throw new Error('JWT_SECRET not configured. Set the JWT_SECRET environment variable.');
  }
  return jwt.sign({ userId, username, roles }, config.JWT_SECRET!, {
    expiresIn: '24h',
    issuer: 'lightserp',
  });
}

/**
 * Validate a local JWT token.
 */
export function validateToken(token: string): AuthToken | null {
  if (!isJwtConfigured()) return null;
  try {
    const decoded = jwt.verify(token, config.JWT_SECRET!, { issuer: 'lightserp' }) as Record<string, unknown>;
    return {
      userId: String(decoded.userId ?? ''),
      username: String(decoded.username ?? ''),
      roles: Array.isArray(decoded.roles) ? (decoded.roles as string[]) : ['user'],
    };
  } catch {
    return null;
  }
}

// ── Keycloak Admin Auth ───────────────────────────────────────────────

async function getAdminToken(): Promise<string | null> {
  try {
    const res = await axios.post(
      `${config.KEYCLOAK_URL}/realms/${config.KEYCLOAK_REALM}/protocol/openid-connect/token`,
      new URLSearchParams({
        grant_type: 'password',
        client_id: 'admin-cli',
        username: config.KEYCLOAK_ADMIN_USER,
        password: config.KEYCLOAK_ADMIN_PASSWORD,
      }).toString(),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    );
    return res.data.access_token;
  } catch (err) {
    log.error('Keycloak admin token fetch failed', err);
    return null;
  }
}

async function getClientAdminToken(): Promise<string | null> {
  if (!config.KEYCLOAK_CLIENT_SECRET) {
    log.error('KEYCLOAK_CLIENT_SECRET not configured for client-credentials admin access');
    return null;
  }
  try {
    const res = await axios.post(
      `${config.KEYCLOAK_URL}/realms/${config.KEYCLOAK_REALM}/protocol/openid-connect/token`,
      new URLSearchParams({
        grant_type: 'client_credentials',
        client_id: config.KEYCLOAK_CLIENT_ID,
        client_secret: config.KEYCLOAK_CLIENT_SECRET,
      }).toString(),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    );
    return res.data.access_token;
  } catch (err) {
    log.error('Keycloak client-credentials admin token fetch failed', err);
    return null;
  }
}

async function getAdminAccessToken(): Promise<string | null> {
  if (config.KEYCLOAK_ADMIN_USER && config.KEYCLOAK_ADMIN_PASSWORD) {
    return getAdminToken();
  }
  return getClientAdminToken();
}

// ── Keycloak Introspection (RFC 7662) ─────────────────────────────────

export async function validateKeycloakToken(
  token: string
): Promise<KeycloakIntrospectionResponse | null> {
  try {
    const response = await axios.post(
      KC_INTROSPECTION_URL,
      new URLSearchParams({
        token,
        client_id: config.KEYCLOAK_CLIENT_ID,
        client_secret: config.KEYCLOAK_CLIENT_SECRET,
      }).toString(),
      {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        timeout: config.KC_TIMEOUT,
      }
    );

    const data = response.data;
    if (data?.active) {
      log.debug('Keycloak token introspection successful', { sub: data.sub });
      return data as KeycloakIntrospectionResponse;
    }

    log.debug('Keycloak token introspection: token inactive');
    return null;
  } catch (err) {
    if (axios.isAxiosError(err)) {
      const axiosErr = err as AxiosError<{ error?: string }>;
      if (axiosErr.response?.status === 401 || axiosErr.response?.status === 400) {
        log.debug('Keycloak introspection failed (401/400)');
        return null;
      }
    }
    log.warn('Keycloak introspection request failed', err);
    return null;
  }
}

// ── Keycloak UserInfo ─────────────────────────────────────────────────

export async function getUserFromKeycloak(
  accessToken: string
): Promise<Record<string, unknown> | null> {
  try {
    const response = await axios.get(KC_USERINFO_URL, {
      headers: { Authorization: `Bearer ${accessToken}` },
      timeout: config.KC_TIMEOUT,
    });
    return response.data;
  } catch (err) {
    log.warn('Keycloak userinfo fetch failed', err);
    return null;
  }
}

// ── User Sync (PostgreSQL) ────────────────────────────────────────────

export async function syncUserToDB(
  keycloakId: string,
  email: string,
  username: string,
  displayName?: string
): Promise<User | null> {
  await ensureDb();
  if (!pool) return null;

  try {
    const rows = await query<any>(
      `INSERT INTO users (keycloak_id, email, username, display_name, email_verified, role)
       VALUES ($1, $2, $3, $4, TRUE, 'user')
       ON CONFLICT (keycloak_id)
       DO UPDATE SET
         email = EXCLUDED.email,
         username = EXCLUDED.username,
         display_name = COALESCE(EXCLUDED.display_name, users.display_name),
         email_verified = TRUE,
         last_login_at = NOW(),
         updated_at = NOW()
       RETURNING *`,
      [keycloakId, email, username, displayName || null]
    );

    if (rows.length > 0) {
      log.debug('User synced to DB', { keycloakId, username });
      return rows[0];
    }
    return null;
  } catch (err) {
    log.error('User sync failed', err);
    return null;
  }
}

export async function findUserByKeycloakId(
  keycloakId: string
): Promise<User | null> {
  return queryOne<any>('SELECT * FROM users WHERE keycloak_id = $1', [keycloakId]);
}

export async function findUserByEmail(
  email: string
): Promise<User | null> {
  const raw = await queryOne<any>('SELECT * FROM users WHERE email = $1', [email.toLowerCase()]);
  if (!raw) return null;
  return {
    id: raw.id,
    keycloakId: raw.keycloak_id,
    email: raw.email,
    username: raw.username,
    role: raw.role || 'user',
    emailVerified: raw.email_verified,
    avatarUrl: raw.avatar_url,
    displayName: raw.display_name,
    passwordHash: raw.password_hash,
    createdAt: raw.created_at,
    lastLoginAt: raw.last_login_at,
  };
}

// ── API Key Management (PostgreSQL) ───────────────────────────────────

interface CreateKeyResult {
  key: string;
  keyId: string;
  prefix: string;
}

export async function createApiKey(
  userId: string,
  name: string,
  permissions: string[] = ['search', 'scrape']
): Promise<CreateKeyResult | { error: string }> {
  await ensureDb();
  if (!pool) return { error: 'Database unavailable' };

  const rawKey = `lsk_${crypto.randomBytes(32).toString('hex')}`;
  const keyHash = crypto.createHash('sha256').update(rawKey).digest('hex');
  const keyPrefix = rawKey.slice(0, 12);

  try {
    const rows = await query<any>(
      `INSERT INTO api_keys (user_id, name, key_hash, key_prefix, permissions)
       VALUES ($1, $2, $3, $4, $5)
       RETURNING id`,
      [userId, name, keyHash, keyPrefix, JSON.stringify(permissions)]
    );

    if (rows.length === 0) {
      return { error: 'Failed to create API key' };
    }

    const keyId = rows[0].id;
    log.info('API key created', { keyId, name, prefix: keyPrefix, userId });
    return { key: rawKey, keyId, prefix: keyPrefix };
  } catch (err) {
    log.error('API key creation failed', err);
    return { error: 'Failed to create API key' };
  }
}

export async function validateApiKey(
  apiKey: string
): Promise<ApiKey | null> {
  await ensureDb();
  if (!pool) return null;

  if (!apiKey || !apiKey.startsWith('lsk_')) return null;

  const keyHash = crypto.createHash('sha256').update(apiKey).digest('hex');

  try {
    const key = await queryOne<any>(
      `SELECT id, user_id, name, key_prefix,
              permissions, is_active, created_at,
              last_used_at, expires_at
       FROM api_keys
       WHERE key_hash = $1 AND is_active = TRUE`,
      [keyHash]
    );

    if (!key) return null;

    if (key.expires_at && new Date(key.expires_at) < new Date()) {
      log.warn('API key expired', { keyId: key.id });
      return null;
    }

    await run('UPDATE api_keys SET last_used_at = NOW() WHERE id = $1', [key.id]);

    return {
      id: key.id,
      userId: key.user_id,
      name: key.name,
      keyPrefix: key.key_prefix,
      permissions: JSON.parse(key.permissions || '["search","scrape"]'),
      isActive: key.is_active !== false,
      createdAt: key.created_at,
      lastUsedAt: key.last_used_at,
      expiresAt: key.expires_at || null,
    };
  } catch (err) {
    log.error('API key validation failed', err);
    return null;
  }
}

export async function getUserApiKeys(
  userId: string
): Promise<ApiKey[]> {
  await ensureDb();
  if (!pool) return [];

  try {
    const rows = await query<any>(
      `SELECT id as "key_id", user_id as "user_id", name, key_prefix as "key_prefix",
              permissions, is_active as "is_active", created_at as "created_at",
              last_used_at as "last_used_at", expires_at as "expires_at"
       FROM api_keys WHERE user_id = $1 ORDER BY created_at DESC`,
      [userId]
    );

    return rows.map((key: any) => ({
      id: key.id,
      userId: key.user_id,
      name: key.name,
      keyPrefix: key.key_prefix,
      permissions: JSON.parse(key.permissions || '["search","scrape"]'),
      isActive: key.is_active !== false,
      createdAt: key.created_at,
      lastUsedAt: key.last_used_at,
      expiresAt: key.expires_at || null,
    }));
  } catch (err) {
    log.error('Failed to fetch API keys', err);
    return [];
  }
}

export async function revokeApiKey(
  keyId: string,
  userId: string
): Promise<boolean> {
  await ensureDb();
  if (!pool) return false;

  try {
    const result = await run(
      'UPDATE api_keys SET is_active = FALSE WHERE id = $1 AND user_id = $2',
      [keyId, userId]
    );
    return result > 0;
  } catch (err) {
    log.error('API key revocation failed', err);
    return false;
  }
}

export async function logUsage(
  userId: string,
  keyId: string | null,
  toolName: string,
  metadata: Record<string, unknown> = {}
): Promise<void> {
  await ensureDb();
  if (!pool) return;

  try {
    await run(
      'INSERT INTO usage_logs (user_id, key_id, tool_name, metadata) VALUES ($1, $2, $3, $4)',
      [userId, keyId, toolName, JSON.stringify(metadata)]
    );
  } catch (err) {
    log.error('Failed to log usage', err);
  }
}

// ── Email Verification JWT Token Helpers ──────────────────────────────

function generateVerificationToken(userId: string, email: string): string {
  if (!isJwtConfigured()) throw new Error('JWT_SECRET not configured');
  return jwt.sign(
    { userId, email, type: 'email_verification' },
    config.JWT_SECRET!,
    {
      expiresIn: config.VERIFICATION_TOKEN_EXPIRY,
      issuer: 'lightserp',
    }
  );
}

function decodeVerificationToken(token: string): { userId: string; email: string } | null {
  if (!isJwtConfigured()) return null;
  try {
    const decoded = jwt.verify(token, config.JWT_SECRET!, {
      issuer: 'lightserp',
    }) as Record<string, unknown>;
    if (decoded.type !== 'email_verification') {
      return null;
    }
    return { userId: String(decoded.userId), email: String(decoded.email) };
  } catch {
    return null;
  }
}

// ── Email Delivery (SMTP2GO) ──────────────────────────────────────────

async function sendSmtp2goEmail(
  to: string,
  subject: string,
  htmlBody: string
): Promise<{ success: boolean; messageId?: string; errorMessage?: string; statusCode: number }> {
  if (!config.SMTP2GO_API_KEY) {
    log.warn(`SMTP2GO_API_KEY not configured. Would send to ${to}`);
    return { success: true, statusCode: 0 };
  }

  return new Promise((resolve) => {
    const payload = JSON.stringify({
      to: [to],
      sender: config.EMAIL_FROM,
      subject,
      html_body: htmlBody,
    });

    const options = {
      hostname: config.SMTP_SERVER,
      port: config.SMTP_PORT,
      path: '/api/v3/email/send',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Smtp2go-Api-Key': config.SMTP2GO_API_KEY,
        'Content-Length': Buffer.byteLength(payload),
      },
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk: string) => { data += chunk; });
      res.on('end', () => {
        try {
          const result = JSON.parse(data);
          if (res.statusCode === 200 && result.data?.succeeded && result.data.succeeded > 0) {
            resolve({
              success: true,
              messageId: result.data?.messages?.[0]?.message_id,
              statusCode: res.statusCode || 0,
            });
          } else {
            const errMsg = result.message || result.errors?.[0] || `HTTP ${res.statusCode || 0}`;
            log.error(`[SMTP2GO] Send failed: ${errMsg}`);
            resolve({ success: false, errorMessage: errMsg, statusCode: res.statusCode || 0 });
          }
        } catch {
          resolve({ success: false, errorMessage: `Failed to parse response: ${data}`, statusCode: res.statusCode || 0 });
        }
      });
    });

    req.on('error', (err: Error) => {
      log.error(`[SMTP2GO] Request failed: ${err.message}`);
      resolve({ success: false, errorMessage: err.message, statusCode: 0 });
    });

    req.setTimeout(config.EMAIL_TIMEOUT, () => {
      log.warn('[SMTP2GO] Request timed out');
      req.destroy();
      resolve({ success: false, errorMessage: 'Request timed out', statusCode: 0 });
    });

    req.write(payload);
    req.end();
  });
}

// ── Async Verification Email (fire-and-forget) ────────────────────────

function sendVerificationEmailSilently(userId: string, email: string, displayName: string): { promise: Promise<void> } {
  const promise = (async () => {
    try {
      const user = await findUserByEmail(email);
      if (!user) return;

      let adminToken: string | null = null;
      let kcUserId: string | null = user.keycloakId || null;

      if (kcUserId) {
        adminToken = await getAdminAccessToken();
        if (adminToken) {
          try {
            await axios.post(
              `${config.KEYCLOAK_URL}/admin/realms/${config.KEYCLOAK_REALM}/users/${kcUserId}/send-verify-email`,
              {
                type: 'update_email_action',
                clientId: config.KEYCLOAK_CLIENT_ID,
                redirectUri: process.env.KEYCLOAK_REDIRECT_URI || `${config.LIGHTSERP_URL}/auth/callback`,
              },
              {
                headers: { Authorization: `Bearer ${adminToken}` },
                timeout: config.KC_TIMEOUT,
              }
            );
            log.info('Keycloak verification email triggered', { email });
          } catch (err) {
            log.warn('Keycloak send-verify-email failed (non-fatal)', err);
          }
        }
      }

      const verificationToken = generateVerificationToken(userId, email);
      const verificationUrl = `${config.LIGHTSERP_URL}/api/auth/verify-email?token=${verificationToken}`;
      const htmlBody = buildVerificationEmail(verificationUrl, displayName);
      await sendSmtp2goEmail(email, 'Verify Your Email - LightSerp', htmlBody);
      log.info('Verification email sent', { email });
    } catch (err) {
      log.error('Failed to send verification email (non-fatal)', err);
    }
  })();

  promise.catch(e => log.warn(e));
  return { promise };
}

// ── Auth Functions ────────────────────────────────────────────────────

export async function signupWithEmail(
  email: string,
  password: string,
  username?: string
): Promise<{ success: boolean; userId?: string; error?: string }> {
  if (!email || !email.trim()) {
    return { success: false, error: 'Email is required' };
  }
  if (!password || password.length < config.MIN_PASSWORD_LENGTH) {
    return { success: false, error: `Password must be at least ${config.MIN_PASSWORD_LENGTH} characters` };
  }

  const trimmedEmail = email.trim().toLowerCase();
  const displayName = username || trimmedEmail.split('@')[0];

  // Check if email already exists
  let adminToken: string | null = null;
  try {
    adminToken = await getAdminAccessToken();
    if (adminToken) {
      const kcUsersRes = await axios.get(
        `${config.KEYCLOAK_URL}/admin/realms/${config.KEYCLOAK_REALM}/users`,
        {
          headers: { Authorization: `Bearer ${adminToken}` },
          params: { email: trimmedEmail },
          timeout: config.KC_TIMEOUT,
        }
      );

      if (kcUsersRes.data && kcUsersRes.data.length > 0) {
        return { success: false, error: 'Email already registered' };
      }
    }
  } catch (err) {
    log.warn('Keycloak user check failed during signup', err);
  }

  const existingUser = await findUserByEmail(trimmedEmail);
  if (existingUser) {
    return { success: false, error: 'Email already registered' };
  }

  // Create user in Keycloak
  if (!adminToken) {
    adminToken = await getAdminAccessToken();
  }

  let kcUserId: string | null = null;
  if (adminToken) {
    try {
      const kcUser = {
        email: trimmedEmail,
        username: displayName,
        emailVerified: false,
        enabled: true,
        credentials: [{ type: 'password', value: password, temporary: false }],
        requiredActions: ['VERIFY_EMAIL'],
        firstName: displayName.split(' ')[0] || '',
        lastName: displayName.split(' ').slice(1).join(' ') || '',
      };

      const createRes = await axios.post(
        `${config.KEYCLOAK_URL}/admin/realms/${config.KEYCLOAK_REALM}/users`,
        kcUser,
        {
          headers: { Authorization: `Bearer ${adminToken}`, 'Content-Type': 'application/json' },
          timeout: config.KC_TIMEOUT,
        }
      );

      const location = createRes.headers.location || '';
      const idMatch = location.match(/\/users\/([a-f0-9-]+)/i);
      kcUserId = idMatch ? idMatch[1] : null;

      if (!kcUserId) {
        const findRes = await axios.get(
          `${config.KEYCLOAK_URL}/admin/realms/${config.KEYCLOAK_REALM}/users`,
          {
            headers: { Authorization: `Bearer ${adminToken}` },
            params: { email: trimmedEmail, briefRepresentation: false },
            timeout: config.KC_TIMEOUT,
          }
        );
        if (findRes.data && findRes.data.length > 0) {
          kcUserId = findRes.data[0].id;
        }
      }
      log.info('Keycloak user created', { kcUserId, email: trimmedEmail });
    } catch (err) {
      log.error('Keycloak user creation failed', err);
    }
  }

  // Store user in PostgreSQL
  await ensureDb();
  if (!pool) {
    return { success: false, error: 'Database unavailable' };
  }

  let userId: string | null = null;
  try {
    // Hash password with argon2id
    const passwordHash = await hashPasswordPlain(password);
    const rows = await query<any>(
      `INSERT INTO users (keycloak_id, email, username, display_name, email_verified, role, password_hash)
       VALUES ($1, $2, $3, $4, FALSE, 'user', $5)
       RETURNING id`,
      [kcUserId, trimmedEmail, displayName, displayName, passwordHash]
    );

    if (rows.length > 0) {
      userId = rows[0].id;
    }
  } catch (err) {
    log.error('PostgreSQL user creation failed', err);
    return { success: false, error: 'Registration failed. Please try again.' };
  }

  if (!userId) {
    return { success: false, error: 'Failed to create user account' };
  }

  log.info('User registered (pending email verification)', { userId, email: trimmedEmail, kcUserId });
  sendVerificationEmailSilently(userId, trimmedEmail, displayName);
  return { success: true, userId };
}

export async function sendVerificationEmail(email: string): Promise<{ success: boolean; error?: string }> {
  await ensureDb();
  if (!pool) {
    return { success: false, error: 'Database unavailable' };
  }

  const user = await findUserByEmail(email) as User | null;
  if (!user) {
    return { success: false, error: 'Email not found' };
  }

  const verificationToken = generateVerificationToken(user.id, email);
  const verificationUrl = `${config.LIGHTSERP_URL}/api/auth/verify-email?token=${verificationToken}`;
  const htmlBody = buildVerificationEmail(verificationUrl, user.displayName || user.username);

  try {
    await sendSmtp2goEmail(email, 'Verify Your Email - LightSerp', htmlBody);
  } catch (err) {
    log.error('Failed to send verification email (non-fatal)', err);
  }

  log.info('Verification email resent', { email });
  return { success: true };
}

export async function verifyEmail(token: string): Promise<{ success: boolean; error?: string; userId?: string }> {
  await ensureDb();
  if (!pool) {
    return { success: false, error: 'Database unavailable' };
  }

  const payload = decodeVerificationToken(token);
  if (!payload) {
    return { success: false, error: 'Invalid or expired verification token' };
  }

  const { userId, email } = payload;
  const user = await queryOne<any>('SELECT * FROM users WHERE id = $1 AND email_verified = FALSE', [userId]);
  if (!user) {
    return { success: false, error: 'User not found or already verified' };
  }

  await run('UPDATE users SET email_verified = TRUE, updated_at = NOW() WHERE id = $1', [userId]);
  log.info('Email verified in PostgreSQL', { userId, email });

  // Mark verified in Keycloak
  try {
    const adminToken = await getAdminAccessToken();
    if (adminToken) {
      const kcUserId = user.keycloak_id;
      if (kcUserId) {
        await axios.put(
          `${config.KEYCLOAK_URL}/admin/realms/${config.KEYCLOAK_REALM}/users/${kcUserId}`,
          { emailVerified: true, requiredActions: [] },
          { headers: { Authorization: `Bearer ${adminToken}`, 'Content-Type': 'application/json' }, timeout: config.KC_TIMEOUT }
        );
        log.info('Email verified in Keycloak', { kcUserId, email });
      }
    }
  } catch (err) {
    log.warn('Keycloak email verification failed (non-fatal)', err);
  }

  // Send welcome email
  try {
    const htmlBody = buildWelcomeEmail(
      user.displayName || user.username || email.split('@')[0],
      email,
      config.LIGHTSERP_URL
    );
    await sendSmtp2goEmail(email, 'Welcome to LightSerp!', htmlBody).catch(e => log.warn(e));
  } catch (err) {
    log.warn('Welcome email send failed (non-fatal)', err);
  }

  log.info('Email verified (end-to-end)', { userId, email });
  return { success: true, userId };
}

export async function loginWithEmail(
  email: string,
  password: string
): Promise<{ success: boolean; token?: string; userId?: string; error?: string }> {
  await ensureDb();
  if (!pool) {
    return { success: false, error: 'Database unavailable' };
  }

  const trimmedEmail = email.trim().toLowerCase();
  const user = await findUserByEmail(trimmedEmail);

  if (!user) {
    return { success: false, error: 'Invalid email or password' };
  }

  if (!user.passwordHash) {
    return { success: false, error: 'Account is Keycloak-only. Please use Keycloak login.' };
  }

  if (!user.emailVerified) {
    return { success: false, error: 'Please verify your email before signing in.' };
  }

  // Verify password — handle both argon2id and legacy SHA-256
  let verified = false;
  if (isArgon2Hash(user.passwordHash)) {
    verified = await verifyPasswordPlain(password, user.passwordHash);
  } else if (isSha256Hash(user.passwordHash)) {
    // Legacy SHA-256: reconstruct salt/hash
    const salt = user.passwordHash.slice(0, 64);
    const computed = crypto.createHash('sha256').update(password + salt).digest('hex');
    verified = user.passwordHash.slice(64) === computed;
  }

  if (!verified) {
    return { success: false, error: 'Invalid email or password' };
  }

  const token = generateToken(user.id, user.username || user.email || '', [user.role || 'user']);

  await run('UPDATE users SET last_login_at = NOW() WHERE id = $1', [user.id]);

  log.info('Local login successful', { userId: user.id });
  return { success: true, token, userId: user.id };
}

export async function requestPasswordReset(email: string): Promise<{ success: boolean; error?: string }> {
  await ensureDb();
  if (!pool) {
    return { success: false, error: 'Database unavailable' };
  }

  const user = await findUserByEmail(email.trim().toLowerCase());
  if (!user) {
    log.info('Password reset requested for unknown email (non-fatal)', { email });
    return { success: true };
  }

  const resetToken = crypto.randomBytes(32).toString('hex');
  const resetExpires = Date.now() + 2 * 60 * 60 * 1000;

  await run(
    'UPDATE users SET reset_token = $1, reset_token_expires = $2 WHERE email = $3',
    [resetToken, resetExpires, user.email]
  );

  const resetUrl = `${config.LIGHTSERP_URL}/auth/reset-password?token=${resetToken}`;
  const htmlBody = buildPasswordResetEmail(resetUrl, user.displayName || user.username || '');

  try {
    await sendSmtp2goEmail(user.email || email, 'Reset Your Password - LightSerp', htmlBody);
  } catch (err) {
    log.error('Failed to send password reset email (non-fatal)', err);
  }

  log.info('Password reset email sent', { email });
  return { success: true };
}

export async function resetPassword(
  token: string,
  newPassword: string
): Promise<{ success: boolean; error?: string }> {
  await ensureDb();
  if (!pool) {
    return { success: false, error: 'Database unavailable' };
  }

  if (!newPassword || newPassword.length < config.MIN_PASSWORD_LENGTH) {
    return { success: false, error: `Password must be at least ${config.MIN_PASSWORD_LENGTH} characters` };
  }

  const now = Date.now();
  const user = await queryOne<any>(
    'SELECT * FROM users WHERE reset_token = $1 AND reset_token_expires > $2',
    [token, now]
  );

  if (!user) {
    return { success: false, error: 'Invalid or expired reset token' };
  }

  // Hash new password with argon2id
  const newHash = await hashPasswordPlain(newPassword);

  await run(
    'UPDATE users SET password_hash = $1, reset_token = NULL, reset_token_expires = NULL, updated_at = NOW() WHERE id = $2',
    [newHash, user.id]
  );

  // Revoke all refresh tokens for this user
  await run('UPDATE refresh_tokens SET revoked = TRUE WHERE user_id = $1 AND revoked = FALSE', [user.id]);

  log.info('Password reset successful', { userId: user.id });
  return { success: true };
}

export async function changePassword(
  userId: string,
  currentPassword: string,
  newPassword: string
): Promise<{ success: boolean; error?: string }> {
  await ensureDb();
  if (!pool) {
    return { success: false, error: 'Database unavailable' };
  }

  if (!newPassword || newPassword.length < config.MIN_PASSWORD_LENGTH) {
    return { success: false, error: `Password must be at least ${config.MIN_PASSWORD_LENGTH} characters` };
  }

  const user = await queryOne<any>('SELECT * FROM users WHERE id = $1', [userId]);
  if (!user || !user.password_hash) {
    return { success: false, error: 'User not found or uses external authentication' };
  }

  // Verify current password
  let currentVerified = false;
  if (isArgon2Hash(user.password_hash)) {
    currentVerified = await verifyPasswordPlain(currentPassword, user.password_hash);
  } else if (isSha256Hash(user.password_hash)) {
    const salt = user.password_hash.slice(0, 64);
    const computed = crypto.createHash('sha256').update(currentPassword + salt).digest('hex');
    currentVerified = user.password_hash.slice(64) === computed;
  }

  if (!currentVerified) {
    return { success: false, error: 'Current password is incorrect' };
  }

  // Update to new argon2id password
  const newHash = await hashPasswordPlain(newPassword);

  await run('UPDATE users SET password_hash = $1, updated_at = NOW() WHERE id = $2', [newHash, userId]);

  log.info('Password changed', { userId });
  return { success: true };
}
