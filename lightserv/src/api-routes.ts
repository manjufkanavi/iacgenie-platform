/**
 * API routes — REST endpoints for auth, email verification, and API key management.
 *
 * Auth flows: local password-based (signup/login/password reset/email verification)
 *              + Keycloak OAuth callback
 * Keys: CRUD for per-user API keys backed by PostgreSQL
 *
 * Uses Zod for input validation on all endpoints.
 */

import type { IncomingMessage, ServerResponse } from 'node:http';
import { z } from 'zod';
import { log } from './logger.js';
import { generateUuid } from './logger.js';
import {
  createApiKey,
  getUserApiKeys,
  revokeApiKey,
  validateApiKey,
  logUsage,
  validateToken,
  generateToken,
  syncUserToDB,
  signupWithEmail,
  verifyEmail,
  sendVerificationEmail,
  requestPasswordReset,
  resetPassword,
  changePassword,
  findUserByEmail,
  loginWithEmail,
} from './auth.js';

// --- HTTP Helpers ---

function readBody(req: IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', (chunk) => (body += chunk));
    req.on('end', () => resolve(body));
    req.on('error', reject);
  });
}

function jsonResponse(res: ServerResponse, status: number, data: object, reqId?: string): void {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  // Use provided reqId, or extract from request stored on response.locals if available
  const resolvedReqId = reqId || '';
  if (resolvedReqId) {
    headers['X-Request-Id'] = resolvedReqId;
  }
  res.writeHead(status, headers);
  res.end(JSON.stringify(data));
}

// Attach X-Request-Id to response and log context
function attachReqId(req: IncomingMessage, res: ServerResponse): string {
  let reqId = (req.headers['x-request-id'] as string) || '';
  if (!reqId) {
    reqId = generateUuid();
  }
  // Store on the request for loggers to pick up
  (req as any).reqId = reqId;
  res.setHeader('X-Request-Id', reqId);
  return reqId;
}

// Wrapper: get reqId from request for automatic injection into responses
function getReqId(req: IncomingMessage): string {
  return (req as any).reqId || '';
}

// --- Zod Schemas ---

const RegisterSchema = z.object({
  email: z.string().email('Invalid email format').min(5).max(255),
  password: z.string().min(8).max(128),
  username: z.string().max(64).optional(),
});

const LoginSchema = z.object({
  email: z.string().min(5).max(255),
  password: z.string().min(1).max(128),
});

const EmailSchema = z.object({
  email: z.string().email('Invalid email format').min(5).max(255),
});

const ResetPasswordSchema = z.object({
  token: z.string().min(1),
  newPassword: z.string().min(8).max(128),
});

const ChangePasswordSchema = z.object({
  currentPassword: z.string().min(1).max(128),
  newPassword: z.string().min(8).max(128),
});

const CreateKeySchema = z.object({
  name: z.string().max(128).optional(),
  permissions: z.array(z.string()).max(10).optional(),
});

const TokenGenSchema = z.object({
  username: z.string().max(64).optional(),
  roles: z.array(z.string()).optional(),
  userId: z.string().max(64).optional(),
});

// --- Auth Helpers ---

async function getAuthenticatedUser(
  req: IncomingMessage
): Promise<{ userId: string; key?: { id: string; userId: string } } | null> {
  const apiKey = req.headers['x-api-key'] as string;
  if (apiKey) {
    const key = await validateApiKey(apiKey);
    if (key) {
      return { userId: key.userId, key: { id: key.id, userId: key.userId } };
    }
  }

  const authHeader = req.headers.authorization as string;
  if (authHeader?.startsWith('Bearer ')) {
    const token = authHeader.slice(7);
    try {
      const authToken = await validateToken(token);
      return { userId: authToken!.userId };
    } catch {
      return null;
    }
  }

  return null;
}

// ── Signup Route ──────────────────────────────────────────────────────

async function handleRegister(
  req: IncomingMessage,
  res: ServerResponse
): Promise<void> {
  const body = await readBody(req);
  let parsed: z.infer<typeof RegisterSchema>;
  try {
    parsed = RegisterSchema.parse(JSON.parse(body));
  } catch {
    jsonResponse(res, 400, { error: 'Invalid request body. Required: email, password', reqId: getReqId(req) }, getReqId(req));
    return;
  }

  const result = await signupWithEmail(parsed.email, parsed.password, parsed.username);

  if (!result.success) {
    jsonResponse(res, 400, { error: result.error, reqId: getReqId(req) }, getReqId(req));
    return;
  }

  log.info('New user registered (verification email sent automatically)', { email: parsed.email });
  jsonResponse(res, 201, {
    userId: result.userId,
    email: parsed.email,
    username: parsed.username || parsed.email.split('@')[0],
    message: 'Account created. Please check your email to verify your address.',
    requiresVerification: true,
    reqId: getReqId(req),
  }, getReqId(req));
}

// ── Login Route ───────────────────────────────────────────────────────

async function handleLogin(
  req: IncomingMessage,
  res: ServerResponse
): Promise<void> {
  const body = await readBody(req);
  let parsed: z.infer<typeof LoginSchema>;
  try {
    parsed = LoginSchema.parse(JSON.parse(body));
  } catch {
    jsonResponse(res, 400, { error: 'Invalid request body. Required: email, password', reqId: getReqId(req) }, getReqId(req));
    return;
  }

  const result = await loginWithEmail(parsed.email, parsed.password);

  if (!result.success) {
    jsonResponse(res, 401, { error: result.error, reqId: getReqId(req) }, getReqId(req));
    return;
  }

  jsonResponse(res, 200, {
    userId: result.userId,
    token: result.token,
    message: 'Logged in successfully',
    reqId: getReqId(req),
  }, getReqId(req));
}

// ── Email Verification Route ──────────────────────────────────────────

async function handleVerifyEmail(
  req: IncomingMessage,
  res: ServerResponse
): Promise<void> {
  const url = new URL(
    req.url || '/',
    `http://${req.headers.host || 'localhost'}`
  );
  const token = url.searchParams.get('token') || url.pathname.split('/').pop();

  if (!token) {
    jsonResponse(res, 400, { error: 'Verification token is required', reqId: getReqId(req) }, getReqId(req));
    return;
  }

  const result = await verifyEmail(token);

  if (!result.success) {
    jsonResponse(res, 400, { error: result.error, reqId: getReqId(req) }, getReqId(req));
    return;
  }

  jsonResponse(res, 200, {
    success: true,
    message: 'Email verified successfully. You can now log in.',
    reqId: getReqId(req),
  }, getReqId(req));
}

// ── Resend Verification Email ─────────────────────────────────────────

async function handleResendVerification(
  req: IncomingMessage,
  res: ServerResponse
): Promise<void> {
  const body = await readBody(req);
  let parsed: z.infer<typeof EmailSchema>;
  try {
    parsed = EmailSchema.parse(JSON.parse(body));
  } catch {
    jsonResponse(res, 400, { error: 'Invalid request body. Required: email', reqId: getReqId(req) }, getReqId(req));
    return;
  }

  const result = await sendVerificationEmail(parsed.email);
  if (!result.success) {
    jsonResponse(res, 400, { error: result.error, reqId: getReqId(req) }, getReqId(req));
    return;
  }

  jsonResponse(res, 200, {
    success: true,
    message: 'Verification email sent. Please check your inbox.',
    reqId: getReqId(req),
  }, getReqId(req));
}

// ── Password Reset Request ────────────────────────────────────────────

async function handlePasswordReset(
  req: IncomingMessage,
  res: ServerResponse
): Promise<void> {
  const body = await readBody(req);
  let parsed: z.infer<typeof EmailSchema>;
  try {
    parsed = EmailSchema.parse(JSON.parse(body));
  } catch {
    jsonResponse(res, 400, { error: 'Invalid request body. Required: email', reqId: getReqId(req) }, getReqId(req));
    return;
  }

  const result = await requestPasswordReset(parsed.email);
  if (!result.success) {
    jsonResponse(res, 400, { error: result.error, reqId: getReqId(req) }, getReqId(req));
    return;
  }

  // Always return success to avoid email enumeration
  jsonResponse(res, 200, {
    success: true,
    message: 'If an account exists with that email, you will receive a reset link.',
    reqId: getReqId(req),
  }, getReqId(req));
}

// ── Password Reset (with token) ───────────────────────────────────────

async function handleResetPassword(
  req: IncomingMessage,
  res: ServerResponse
): Promise<void> {
  const body = await readBody(req);
  let parsed: z.infer<typeof ResetPasswordSchema>;
  try {
    parsed = ResetPasswordSchema.parse(JSON.parse(body));
  } catch {
    jsonResponse(res, 400, { error: 'Invalid request body. Required: token, newPassword', reqId: getReqId(req) }, getReqId(req));
    return;
  }

  const result = await resetPassword(parsed.token, parsed.newPassword);
  if (!result.success) {
    jsonResponse(res, 400, { error: result.error, reqId: getReqId(req) }, getReqId(req));
    return;
  }

  jsonResponse(res, 200, {
    success: true,
    message: 'Password has been reset successfully. You can now log in.',
    reqId: getReqId(req),
  }, getReqId(req));
}

// ── Change Password (authenticated) ───────────────────────────────────

async function handleChangePassword(
  req: IncomingMessage,
  res: ServerResponse
): Promise<void> {
  const auth = await getAuthenticatedUser(req);
  if (!auth) {
    jsonResponse(res, 401, { error: 'Invalid API key or token', reqId: getReqId(req) }, getReqId(req));
    return;
  }

  const body = await readBody(req);
  let parsed: z.infer<typeof ChangePasswordSchema>;
  try {
    parsed = ChangePasswordSchema.parse(JSON.parse(body));
  } catch {
    jsonResponse(res, 400, { error: 'Invalid request body. Required: currentPassword, newPassword', reqId: getReqId(req) }, getReqId(req));
    return;
  }

  const result = await changePassword(auth.userId, parsed.currentPassword, parsed.newPassword);
  if (!result.success) {
    jsonResponse(res, 400, { error: result.error, reqId: getReqId(req) }, getReqId(req));
    return;
  }

  jsonResponse(res, 200, {
    success: true,
    message: 'Password changed successfully.',
    reqId: getReqId(req),
  }, getReqId(req));
}

// ── Token Generation ──────────────────────────────────────────────────

async function handleTokenGen(
  req: IncomingMessage,
  res: ServerResponse
): Promise<void> {
  const body = await readBody(req);
  let parsed: z.infer<typeof TokenGenSchema>;
  try {
    parsed = TokenGenSchema.parse(JSON.parse(body));
  } catch {
    jsonResponse(res, 400, { error: 'Invalid request body', reqId: getReqId(req) }, getReqId(req));
    return;
  }

  const token = generateToken(
    parsed.userId || `user_${Date.now()}`,
    parsed.username || 'testuser',
    parsed.roles || ['user']
  );
  jsonResponse(res, 200, { token, reqId: getReqId(req) }, getReqId(req));
}

// ── API Key Routes ────────────────────────────────────────────────────

async function handleListKeys(
  req: IncomingMessage,
  res: ServerResponse
): Promise<void> {
  const auth = await getAuthenticatedUser(req);
  if (!auth) {
    jsonResponse(res, 401, { error: 'Invalid API key or token', reqId: getReqId(req) }, getReqId(req));
    return;
  }

  const keys = await getUserApiKeys(auth.userId);
  jsonResponse(res, 200, { keys, reqId: getReqId(req) }, getReqId(req));
}

async function handleCreateKey(
  req: IncomingMessage,
  res: ServerResponse
): Promise<void> {
  const auth = await getAuthenticatedUser(req);
  if (!auth) {
    jsonResponse(res, 401, { error: 'Invalid API key or token', reqId: getReqId(req) }, getReqId(req));
    return;
  }

  const body = await readBody(req);
  let parsed: z.infer<typeof CreateKeySchema>;
  try {
    parsed = CreateKeySchema.parse(JSON.parse(body));
  } catch {
    jsonResponse(res, 400, { error: 'Invalid request body', reqId: getReqId(req) }, getReqId(req));
    return;
  }

  const result = await createApiKey(
    auth.userId,
    parsed.name || 'My Key',
    parsed.permissions || ['search', 'scrape']
  );

  if ('error' in result) {
    jsonResponse(res, 400, result, getReqId(req));
    return;
  }

  await logUsage(auth.userId, null, 'create_api_key', {
    keyId: result.keyId,
    name: result.prefix,
  });

  jsonResponse(res, 201, {
    id: result.keyId,
    key: result.key,
    prefix: result.prefix,
    message: 'API key created. Save this key — it will not be shown again.',
    reqId: getReqId(req),
  }, getReqId(req));
}

async function handleDeleteKey(
  req: IncomingMessage,
  res: ServerResponse,
  keyId: string
): Promise<void> {
  const auth = await getAuthenticatedUser(req);
  if (!auth) {
    jsonResponse(res, 401, { error: 'Invalid API key or token', reqId: getReqId(req) }, getReqId(req));
    return;
  }

  const success = await revokeApiKey(keyId, auth.userId);
  if (!success) {
    jsonResponse(res, 404, { error: 'Key not found or already revoked', reqId: getReqId(req) }, getReqId(req));
    return;
  }

  await logUsage(auth.userId, null, 'revoke_api_key', { keyId });
  jsonResponse(res, 200, { success: true, reqId: getReqId(req) }, getReqId(req));
}

async function handleUsage(
  req: IncomingMessage,
  res: ServerResponse
): Promise<void> {
  const auth = await getAuthenticatedUser(req);
  if (!auth) {
    jsonResponse(res, 401, { error: 'Invalid API key or token', reqId: getReqId(req) }, getReqId(req));
    return;
  }

  await logUsage(auth.userId, auth.key?.id || null, 'usage_check', {});

  jsonResponse(res, 200, {
    status: 'ok',
    userId: auth.userId,
    keyId: auth.key?.id || null,
    timestamp: new Date().toISOString(),
    reqId: getReqId(req),
  }, getReqId(req));
}

// ── MCP Proxy ─────────────────────────────────────────────────────────

async function handleMcpProxy(
  req: IncomingMessage,
  res: ServerResponse
): Promise<void> {
  const auth = await getAuthenticatedUser(req);
  if (!auth) {
    jsonResponse(res, 401, { error: 'Invalid API key or token', reqId: getReqId(req) }, getReqId(req));
    return;
  }

  try {
    const body = await readBody(req);
    const mcpServerPort = req.url ? new URL(req.url, `http://${req.headers.host || 'localhost'}`).searchParams.get('mcp_port') || '3001' : '3001';
    const targetUrl = `http://127.0.0.1:${mcpServerPort}/mcp`;

    const fetchRes = await fetch(targetUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
    });

    const data = await fetchRes.text();
    res.writeHead(fetchRes.status, { 'Content-Type': 'application/json' });
    res.end(data);
    await logUsage(auth.userId, null, 'mcp_proxy', {
      method: 'POST',
      statusCode: fetchRes.status,
    });
  } catch (err: unknown) {
    log.error('MCP proxy error:', err);
    jsonResponse(res, 502, { error: 'MCP proxy error', reqId: getReqId(req) }, getReqId(req));
  }
}

// ── Keycloak OAuth Callback ───────────────────────────────────────────

async function handleKeycloakCallback(
  req: IncomingMessage,
  res: ServerResponse
): Promise<void> {
  try {
    const body = await readBody(req);
    const { code } = JSON.parse(body) as { code?: string };

    if (!code) {
      jsonResponse(res, 400, { error: 'Authorization code is required', reqId: getReqId(req) }, getReqId(req));
      return;
    }

    const keycloakUrl = process.env.KEYCLOAK_URL || 'http://iacgenie-keycloak:8080';
    const realm = process.env.KEYCLOAK_REALM || 'lightserp';
    const clientId = process.env.KEYCLOAK_CLIENT_ID || 'lightserp-webui';
    const clientSecret = process.env.KEYCLOAK_CLIENT_SECRET || '';
    const redirectUri = process.env.KEYCLOAK_REDIRECT_URI || 'https://lightserp.iacgenie.com/auth/callback';

    const tokenRes = await fetch(`${keycloakUrl}/realms/${realm}/protocol/openid-connect/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        code,
        redirect_uri: redirectUri,
        client_id: clientId,
        client_secret: clientSecret,
      }).toString(),
    });

    if (!tokenRes.ok) {
      const errBody = await tokenRes.text();
      log.error('Keycloak token exchange failed', { status: tokenRes.status, body: errBody });
      jsonResponse(res, 400, { error: 'Failed to exchange code for token with Keycloak', reqId: getReqId(req) }, getReqId(req));
      return;
    }

    const tokenData = (await tokenRes.json()) as Record<string, unknown>;
    const accessToken = tokenData.access_token as string;

    if (!accessToken) {
      log.error('No access token returned from Keycloak', tokenData);
      jsonResponse(res, 500, { error: 'No access token from Keycloak', reqId: getReqId(req) }, getReqId(req));
      return;
    }

    const introspectRes = await fetch(
      `${keycloakUrl}/realms/${realm}/protocol/openid-connect/userinfo`,
      {
        headers: { Authorization: `Bearer ${accessToken}` },
      }
    );

    let userInfo: Record<string, unknown> = {};
    if (introspectRes.ok) {
      userInfo = (await introspectRes.json()) as Record<string, unknown>;
    }

    const userId = (userInfo.keycloak_id as string) || (userInfo.sub as string) || `kc_${Date.now()}`;
    const username = (userInfo.preferred_username as string) || (userInfo.username as string) || (userInfo.email as string) || 'user';
    const email = userInfo.email as string | undefined;

    const existingUser = await findUserByEmail(email || username);
    if (!existingUser) {
      await syncUserToDB(userId, email || username, username);
    }

    const jwtToken = generateToken(userId, username, ['user']);

    log.info('Keycloak OAuth callback succeeded', { userId, username });

    jsonResponse(res, 200, {
      token: jwtToken,
      user: {
        id: userId,
        username,
        email,
      },
      reqId: getReqId(req),
    }, getReqId(req));
  } catch (err: unknown) {
    log.error('Keycloak callback error:', err);
    jsonResponse(res, 500, { error: 'Internal server error during Keycloak callback', reqId: getReqId(req) }, getReqId(req));
  }
}

// ── Route Router ──────────────────────────────────────────────────────

export function handleApiRoutes(
  req: IncomingMessage,
  res: ServerResponse
): boolean {
  const url = new URL(
    req.url || '/',
    `http://${req.headers.host || 'localhost'}`
  );

  // Attach reqId for request tracing
  const reqId = attachReqId(req, res);

  // Legacy API redirect: /api/* → /api/v1/* (301)
  if (url.pathname.startsWith('/api/') && !url.pathname.startsWith('/api/v1/')) {
    const redirectPath = url.pathname.replace(/^\/api\//, '/api/v1/');
    res.writeHead(301, {
      'Location': redirectPath,
      'Content-Type': 'application/json',
    });
    res.end(JSON.stringify({
      status: 301,
      message: 'Moved Permanently. The /api/ endpoint has been deprecated in favor of /api/v1/.',
      oldPath: url.pathname,
      newPath: redirectPath,
    }));
    return true;
  }

  // Only handle /api/v1/ routes
  if (!url.pathname.startsWith('/api/v1/')) return false;

  // CORS
  const allowedOrigins = (process.env.CORS_ORIGIN || '').split(',').filter(Boolean);
  const origin = req.headers.origin;
  if (origin && (allowedOrigins.length === 0 || allowedOrigins.includes(origin))) {
    res.setHeader('Access-Control-Allow-Origin', origin);
  }
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-API-Key, Authorization, X-Request-Id');
  res.setHeader('Access-Control-Allow-Credentials', 'true');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return true;
  }

  // Log with reqId context
  log.info(`${req.method} ${url.pathname}`, { reqId });

  const path = url.pathname;
  const queryParams = url.searchParams;

  // Auth routes
  if (path === '/api/v1/auth/register' && req.method === 'POST') {
    handleRegister(req, res);
    return true;
  }

  if (path === '/api/v1/auth/login' && req.method === 'POST') {
    handleLogin(req, res);
    return true;
  }

  if (path === '/api/v1/auth/verify-email' || path.startsWith('/api/v1/auth/verify/')) {
    if (req.method === 'GET') {
      handleVerifyEmail(req, res);
      return true;
    }
    // POST variant
    (async () => {
      const body = await readBody(req);
      try {
        const { token } = JSON.parse(body);
        if (!token) {
          const tokenFromUrl = queryParams.get('token') || path.split('/').pop();
          if (!tokenFromUrl) {
            jsonResponse(res, 400, { error: 'Verification token is required', reqId }, reqId);
            return;
          }
          const result = await verifyEmail(tokenFromUrl);
          if (!result.success) {
            jsonResponse(res, 400, { error: result.error, reqId }, reqId);
            return;
          }
          jsonResponse(res, 200, { success: true, message: 'Email verified successfully.', reqId }, reqId);
        } else {
          const result = await verifyEmail(token);
          if (!result.success) {
            jsonResponse(res, 400, { error: result.error, reqId }, reqId);
            return;
          }
          jsonResponse(res, 200, { success: true, message: 'Email verified successfully.', reqId }, reqId);
        }
      } catch {
        jsonResponse(res, 400, { error: 'Invalid request body', reqId }, reqId);
      }
    })();
    return true;
  }

  if (path === '/api/v1/auth/resend-verification' && req.method === 'POST') {
    handleResendVerification(req, res);
    return true;
  }

  if ((path === '/api/v1/auth/forgot-password' || path === '/api/v1/auth/reset-request') && req.method === 'POST') {
    handlePasswordReset(req, res);
    return true;
  }

  if (path === '/api/v1/auth/reset-password' && req.method === 'POST') {
    handleResetPassword(req, res);
    return true;
  }

  if (path === '/api/v1/auth/change-password' && req.method === 'POST') {
    handleChangePassword(req, res);
    return true;
  }

  if (path === '/api/v1/auth/token' && req.method === 'POST') {
    handleTokenGen(req, res);
    return true;
  }

  if (path === '/api/v1/auth/keycloak/callback' && req.method === 'POST') {
    handleKeycloakCallback(req, res);
    return true;
  }

  // API key routes
  if (path === '/api/v1/keys' && req.method === 'GET') {
    handleListKeys(req, res);
    return true;
  }

  if (path === '/api/v1/keys' && req.method === 'POST') {
    handleCreateKey(req, res);
    return true;
  }

  if (path.startsWith('/api/v1/keys/') && req.method === 'DELETE') {
    const id = path.split('/api/v1/keys/')[1];
    handleDeleteKey(req, res, id);
    return true;
  }

  if (path === '/api/v1/usage' && req.method === 'GET') {
    handleUsage(req, res);
    return true;
  }

  // Health
  if (path === '/api/v1/health' && req.method === 'GET') {
    jsonResponse(res, 200, {
      status: 'ok',
      version: '2.0.0',
      timestamp: new Date().toISOString(),
      features: ['smtp2go-email', 'password-auth', 'email-verification', 'password-reset', 'keycloak-oauth', 'api-keys'],
    }, reqId);
    return true;
  }

  // MCP proxy
  if (path === '/api/v1/mcp' && req.method === 'POST') {
    handleMcpProxy(req, res);
    return true;
  }

  return false;
}
