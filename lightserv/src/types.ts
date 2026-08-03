export interface SearchResult {
  title: string;
  url: string;
  snippet: string;
  engine: string;
}

export interface ScrapeResult {
  title: string | null;
  content: string | null;
  excerpt: string | null;
  byline: string | null;
  siteName: string | null;
  length: number | null;
  publishedTime: string | null;
  finalUrl?: string | null;
  metadata?: Record<string, unknown>;
}

export interface ScrapeRequest {
  jobId: string;
  url: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

export interface CacheEntry {
  key: string;
  value: any;
  expiresAt: number;
}

// ── Auth Types ───────────────────────────────────────────────────────

export interface AuthToken {
  userId: string;
  username: string;
  roles: string[];
  iat?: number;
  exp?: number;
}

export interface User {
  id: string;
  keycloakId: string | null;
  email: string | null;
  username: string;
  role: string;
  emailVerified: boolean;
  avatarUrl: string | null;
  displayName: string | null;
  passwordHash: string | null;
  createdAt: Date;
  lastLoginAt: Date | null;
}

export interface ApiKey {
  id: string;
  userId: string;
  name: string;
  keyPrefix: string;
  permissions: string[];
  isActive: boolean;
  createdAt: Date;
  lastUsedAt: Date | null;
  expiresAt: Date | null;
}

export interface UsageLog {
  id: number;
  userId: string;
  keyId: string | null;
  toolName: string;
  requestAt: Date;
  metadata: any | null;
}

export interface KeycloakToken {
  access_token: string;
  expires_in: number;
  refresh_token?: string;
  scope: string;
  token_type: string;
}

export interface KeycloakIntrospectionResponse {
  active: boolean;
  sub?: string;
  client_id?: string;
  username?: string;
  preferred_username?: string;
  email?: string;
  email_verified?: boolean;
  roles?: string[];
  scope?: string;
  exp?: number;
  iat?: number;
  [key: string]: unknown;
}

// ── Auth Errors ──────────────────────────────────────────────────────
// NOTE: AppError and subclasses are now in errors.ts.
// This file is kept for backwards compatibility.
export { AppError, ValidationError, AuthenticationError, AuthorizationError, NotFoundError, RateLimitError, ServiceUnavailableError, ConfigurationError } from './errors.js';
