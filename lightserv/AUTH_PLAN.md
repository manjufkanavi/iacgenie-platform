# LightSerp Multi-Tenant Authentication Plan

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER BROWSER                                 │
│  lightserp.iacgenie.com                                             │
│  ┌───────────────┐  ┌───────────────┐  ┌─────────────────────────┐  │
│  │   Login Page  │  │ Dashboard Page│  │   Settings Page         │  │
│  │ (keycloak)    │  │ (token check) │  │ (API key mgmt)          │  │
│  └───────┬───────┘  └───────┬───────┘  └────────────┬────────────┘  │
└──────────┼──────────────────┼───────────────────────┼────────────────┘
           │                  │                       │
           ▼                  ▼                       │
┌─────────────────────────────────────────────────────────────────────┐
│                        NGINX (VM:80)                                │
│  lightserp.iacgenie.com → proxy to :3070 (WebUI)                   │
│  /oauth/*     → proxy to :8085 (Keycloak)                           │
│  /.well-known │ → proxy to :8085 (Keycloak OIDC discovery)          │
└──────────────────┬──────────────────────────────────────────────────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          │
   ┌─────────┐  ┌─────────┐  │
   │ WebUI   │  │  API    │  │
   │ :3070   │  │ :3071   │  │
   │ Next.js │  │ Express │  │
   │ (hosted │  │ (MCP)   │  │
   │  login) │  │ API     │  │
   └─────────┘  └─────────┘  │
        │                      │
        │                      ▼
        │              ┌───────────────┐
        │              │   Keycloak    │
        │              │   :8085       │
        │              │ (auth server) │
        │              └───────┬───────┘
        │                      │
        │                      ▼
        │              ┌───────────────┐
        │              │   PostgreSQL  │
        │              │   :5432       │
        │              │ (user store)  │
        │              └───────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────┐
│                Cloudflare Tunnel                       │
│  lightserp.iacgenie.com → http://127.0.0.1:80         │
└───────────────────────────────────────────────────────┘
```

## Critical Design Decisions

### 1. Auth Flow: SPA + Keycloak (Hosted)
- **NOT** a12n-server. Use **Keycloak 26** (already on VM, just needs restart)
- Keycloak handles: user registration, login, password reset, email verification
- WebUI is a **pure SPA** that receives JWTs from Keycloak
- API server validates JWTs via Keycloak token introspection endpoint

### 2. API Keys per User
- Each authenticated user can create multiple API keys (`lsk_xxx...`)
- API keys are validated server-side (SHA-256 hash stored in PostgreSQL)
- API keys grant scoped access: `search`, `scrape`, `deep_research`
- Each key has usage tracking (total, hourly, daily)

### 3. MCP Tool Routing
- WebUI serves as a **proxy layer** between users and the MCP server
- Users configure their agentic tools with: `https://lightserp.iacgenie.com/api/mcp`
- The API validates the user's API key or JWT, then forwards to the MCP server
- Each user's calls are tracked against their usage limits

### 4. Data Storage
- **PostgreSQL**: users, API keys, usage tracking, sessions
- **Redis**: JWT token cache, session cache, rate limiting
- Keycloak's built-in PostgreSQL stores Keycloak user data

---

## Task Breakdown

### PHASE 1: Keycloak Integration (Foundation)
**Goal:** Get Keycloak running, accessible at `keycloak.iacgenie.com`

#### 1.1 Start Keycloak on VM
- [ ] Enable Keycloak Docker container (`iacgenie-keycloak-1` exists but stopped)
- [ ] Configure environment: admin credentials, DB connection to existing PostgreSQL
- [ ] Start Keycloak and verify it's accessible
- [ ] Create realm: "lightserp"
- [ ] Create client: "lightserp-webui" (openid-connect, confidential, redirect URI: https://lightserp.iacgenie.com/*)
- [ ] Create client: "lightserp-api" (openid-connect, confidential)

#### 1.2 Update Nginx Configuration
- [ ] Add reverse proxy rules for Keycloak:
  - `/oauth/*` → `http://127.0.0.1:8085`
  - `/.well-known/openid-configuration` → Keycloak discovery
- [ ] Add separate server block or rewrite for OAuth paths
- [ ] Test Nginx config reload

#### 1.3 Add Keycloak to Cloudflare Tunnel
- [ ] Configure cloudflared ingress to include Keycloak
- [ ] Register `keycloak.iacgenie.com` → `http://127.0.0.1:8085`
- [ ] Update Nginx to not serve Keycloak (just pass through for OAuth flow)

#### 1.4 Verify Keycloak Endpoints
- [ ] `/.well-known/openid-configuration` accessible
- [ ] Admin login works
- [ ] User registration works
- [ ] Password reset works

---

### PHASE 2: API Server — PostgreSQL Backend + Token Management
**Goal:** Replace in-memory API keys with PostgreSQL + add Keycloak token validation

#### 2.1 Database Schema
Create migration file: `migrations/001_create_auth_tables.sql`
- [ ] `users` table: id, email (unique), username, password_hash, email_verified (bool), keycloak_id, created_at, updated_at
- [ ] `api_keys` table: id, user_id (FK), name, key_hash (unique, indexed), key_prefix, permissions (JSONB), created_at, last_used_at, is_active
- [ ] `usage_logs` table: id, user_id (FK), key_id (FK), tool_name, request_at, metadata (JSONB)
- [ ] `refresh_tokens` table: id, user_id (FK), token_hash, expires_at, created_at, revoked (bool)

#### 2.2 Update `src/auth.ts`
- [ ] Add `validateJwtFromKeycloak()` — validates JWT via Keycloak introspection
- [ ] Add `createUserFromKeycloakInfo()` — syncs Keycloak user to local DB
- [ ] Add `getUserApiKey(userId)` — retrieves user's API keys from DB
- [ ] Add `revokeApiKey(keyId, userId)`
- [ ] Keep existing `generateToken` as fallback for demo

#### 2.3 Update `src/types.ts`
- [ ] Add `ApiKey` interface
- [ ] Add `User` interface
- [ ] Add `UsageLog` interface

#### 2.4 Add PostgreSQL connection
- [ ] Create `src/db.ts` — PostgreSQL connection pool (use pg library)
- [ ] Connect to existing `iacgenie-postgres-1` container
- [ ] Run migrations on startup

#### 2.5 Update `docker-compose.lightserp-web.yml`
- [ ] Add `KEYCLOAK_URL` env var
- [ ] Add `KEYCLOAK_REALM` env var
- [ ] Add `KEYCLOAK_CLIENT_ID` env var
- [ ] Add `KEYCLOAK_CLIENT_SECRET` env var
- [ ] Add `DATABASE_URL` env var pointing to PostgreSQL
- [ ] Update API service to depend on postgres

---

### PHASE 3: REST API Routes — Auth, API Key Mgmt
**Goal:** Add proper auth API endpoints

#### 3.1 `/api/auth/keycloak/callback`
- [ ] POST — receives token from Keycloak OAuth flow
- [ ] Validates token with Keycloak introspection
- [ ] Creates/updates user in local PostgreSQL
- [ ] Returns JWT signed with local secret (session token for the SPA)
- [ ] Sets HTTP-only cookie for session

#### 3.2 `/api/auth/login`
- [ ] POST — email/password login (fallback, non-Keycloak)
- [ ] Validates against PostgreSQL password_hash
- [ ] Returns JWT + refresh token

#### 3.3 `/api/auth/register`
- [ ] POST — email/password registration
- [ ] Creates user, sends verification email
- [ ] Requires email verification before activation

#### 3.4 `/api/auth/logout`
- [ ] POST — invalidates session cookie
- [ ] Optionally revokes refresh token

#### 3.5 `/api/auth/password-reset`
- [ ] POST — sends password reset email with token
- [ ] POST `/api/auth/password-reset/:token` — sets new password

#### 3.6 `/api/keys` (GET + POST)
- [ ] GET — list user's API keys (requires JWT or API key auth)
- [ ] POST — create new API key with name + permissions
- [ ] Returns the raw key (only shown once)

#### 3.7 `/api/keys/:id` (DELETE)
- [ ] Delete/revoke an API key

#### 3.8 `/api/keys/:id/rotate` (POST)
- [ ] Rotate an API key (generate new one, invalidate old)

#### 3.9 `/api/usage` (GET)
- [ ] Return usage stats for current user/key

#### 3.10 Update `src/api-routes.ts`
- [ ] Migrate all handlers from in-memory to PostgreSQL
- [ ] Add JWT validation middleware
- [ ] Add API key validation middleware

---

### PHASE 4: MCP Proxy Layer
**Goal:** WebUI proxies MCP calls through the API server with auth

#### 4.1 `/api/mcp` endpoint
- [ ] POST endpoint that accepts MCP JSON-RPC requests
- [ ] Validates `Authorization: Bearer <JWT>` or `X-API-Key: lsk_xxx`
- [ ] Rate limits per user
- [ ] Proxies request to internal MCP server (localhost:3071 or stdio)
- [ ] Logs usage to `usage_logs` table
- [ ] Returns MCP response to client

#### 4.2 Rate limiting per user
- [ ] 30 req/min for general tools (search, scrape)
- [ ] 10 req/min for heavy tools (deep research, parallel scan)
- [ ] Sliding window counter in Redis

#### 4.3 Update MCP server (`src/server.ts`)
- [ ] Keep existing MCP tools as-is (they work via stdio)
- [ ] Add HTTP proxy that wraps MCP calls
- [ ] The proxy layer handles auth, rate limiting, logging

---

### PHASE 5: WebUI — Authentication Pages
**Goal:** Replace the current "logged in" dashboard with proper auth flow

#### 5.1 Login Page (`/auth/login`)
- [ ] "Login with Keycloak" button (OAuth2 redirect)
- [ ] Alternative: Email/Password login form
- [ ] "Forgot password" link
- [ ] "Sign up" link

#### 5.2 Register Page (`/auth/register`)
- [ ] Email, username, password fields
- [ ] Password strength indicator
- [ ] Terms of service checkbox
- [ ] Sends verification email

#### 5.3 Password Reset (`/auth/reset-password`, `/auth/reset/:token`)
- [ ] Forgot password form (enter email)
- [ ] Reset form (enter new password + token)

#### 5.4 Dashboard with auth state
- [ ] Check for valid JWT on page load
- [ ] If no token → redirect to `/auth/login`
- [ ] If token valid → show existing dashboard
- [ ] If token expired → refresh via refresh token or redirect to login

#### 5.5 Settings Page — API Key Management
- [ ] List all API keys with last-used dates
- [ ] "Create new key" dialog (name, permissions checkboxes)
- [ ] "Revoke key" confirmation
- [ ] "Rotate key" action
- [ ] Usage statistics chart

#### 5.6 Update `src/contexts/mcp-provider.tsx`
- [ ] Store JWT in localStorage + HTTP-only cookie
- [ ] Pass JWT in Authorization header for API calls
- [ ] Handle token expiry (auto-refresh or re-login)

---

### PHASE 6: Docker Compose & Deployment
**Goal:** Everything runs together on the VM

#### 6.1 Update `docker-compose.lightserp-web.yml`
```yaml
services:
  # WebUI (Next.js) - port 3070
  lightserp-webui:
    build: ./webui
    environment:
      - NEXT_PUBLIC_KEYCLOAK_URL=https://keycloak.iacgenie.com
      - NEXT_PUBLIC_KEYCLOAK_REALM=lightserp
      - NEXT_PUBLIC_KEYCLOAK_CLIENT_ID=lightserp-webui
      - NEXT_PUBLIC_API_URL=https://lightserp.iacgenie.com/api
  
  # API Server (MCP + REST) - port 3071
  lightserp-api:
    build: .
    environment:
      - KEYCLOAK_URL=http://keycloak:8080
      - KEYCLOAK_REALM=lightserp
      - KEYCLOAK_CLIENT_ID=lightserp-api
      - DATABASE_URL=postgresql://user:pass@iacgenie-postgres-1:5432/lightserp
      - REDIS_URL=redis://iacgenie-redis-1:6379
  
  # Keycloak (if not already on VM)
  keycloak:
    image: quay.io/keycloak/keycloak:26.0
    environment:
      - KEYCLOAK_ADMIN=admin
      - KEYCLOAK_ADMIN_PASSWORD=<secure>
      - KC_DB=postgres
      - KC_DB_URL=jdbc:postgresql://iacgenie-postgres-1:5432/keycloak
      - KC_DB_USERNAME=...
      - KC_DB_PASSWORD=...
      - KC_HOSTNAME=keycloak.iacgenie.com
      - KC_HTTP_RELATIVE_PATH=/
      - KC_PROXY=edge  # behind Nginx/Cloudflare
    command: start
    depends_on:
      - iacgenie-postgres-1
```

#### 6.2 Update Nginx config
```nginx
upstream keycloak {
    server 127.0.0.1:8085;
}

server {
    listen 80;
    server_name lightserp.iacgenie.com keycloak.iacgenie.com;
    
    # Keycloak — pass through for OAuth flow
    location /realms/ {
        proxy_pass http://keycloak;
    }
    location /.well-known/ {
        proxy_pass http://keycloak;
    }
    location /protocol/ {
        proxy_pass http://keycloak;
    }
    location /oauth/ {
        proxy_pass http://keycloak;
    }
    
    # WebUI — everything else
    location / {
        proxy_pass http://127.0.0.1:3070;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### 6.3 Update Cloudflare Tunnel
- [ ] `lightserp.iacgenie.com` → `http://127.0.0.1:80`
- [ ] `keycloak.iacgenie.com` → `http://127.0.0.1:8085`

#### 6.4 Initial Admin Setup
- [ ] Create admin user in Keycloak
- [ ] Create initial admin user in local PostgreSQL
- [ ] Seed initial API key for first admin

---

### PHASE 7: Security Hardening
**Goal:** Production-ready security

#### 7.1 HTTPS
- [ ] Obtain SSL certificate via Let's Encrypt or Cloudflare Origin CA
- [ ] Configure Nginx with HTTPS (port 443)
- [ ] Redirect HTTP → HTTPS

#### 7.2 Token Security
- [ ] JWTs: HS256 with strong secret, 15min expiry
- [ ] Refresh tokens: 7-day expiry, stored hashed in DB
- [ ] API keys: 32-byte random, SHA-256 hashed, prefixed `lsk_`
- [ ] HTTP-only, Secure cookies for sessions
- [ ] CSRF protection on state-changing endpoints

#### 7.3 Rate Limiting
- [ ] Per-user rate limits via Redis
- [ ] Sliding window algorithm
- [ ] Different limits per tool type
- [ ] 429 responses with Retry-After header

#### 7.4 Logging & Monitoring
- [ ] Log all auth events (login, logout, failed attempts)
- [ ] Log API key usage
- [ ] Monitor for brute-force attacks
- [ ] Grafana dashboard for auth metrics

---

### PHASE 8: Testing & Verification
#### 8.1 End-to-End Tests
- [ ] User registers → receives email → verifies → logs in → gets dashboard
- [ ] User creates API key → uses key in MCP tool → sees usage logged
- [ ] User revokes API key → key rejected → old usage shows
- [ ] JWT expires → refresh token works → seamless session
- [ ] Expired refresh token → redirect to login

#### 8.2 Security Tests
- [ ] SQL injection attempts on all endpoints
- [ ] XSS attempts on login/register forms
- [ ] API key enumeration (should fail)
- [ ] Rate limit triggering (429 after limit)
- [ ] Token tampering (rejected)

---

## File Change Summary

### New Files
1. `src/db.ts` — PostgreSQL connection pool
2. `src/auth-keycloak.ts` — Keycloak token handling
3. `src/auth-apikey.ts` — API key management
4. `src/mcp-proxy.ts` — MCP proxy with auth
5. `migrations/001_create_auth_tables.sql` — DB schema
6. `webui/src/app/auth/login/page.tsx` — Login page
7. `webui/src/app/auth/register/page.tsx` — Register page
8. `webui/src/app/auth/reset-password/page.tsx` — Password reset
9. `webui/src/app/auth/reset/[token]/page.tsx` — Reset token page
10. `webui/src/app/auth/callback/route.ts` — Keycloak OAuth callback
11. `webui/src/components/auth/login-form.tsx`
12. `webui/src/components/auth/register-form.tsx`
13. `webui/src/components/settings/api-keys.tsx` — API key management
14. `webui/src/lib/session.ts` — Session management

### Modified Files
1. `src/api-routes.ts` — Migrate from in-memory to PostgreSQL
2. `src/auth.ts` — Add Keycloak + API key validation
3. `src/types.ts` — Add User, ApiKey, UsageLog interfaces
4. `src/server.ts` — Update MCP server entry point
5. `src/http-server.ts` — Add new auth/mcp proxy routes
6. `docker-compose.lightserp-web.yml` — Add Keycloak, DB, env vars
7. `nginx.conf` — Add Keycloak proxy, HTTPS
8. `webui/src/app/layout.tsx` — Add auth state, redirect logic
9. `webui/src/app/page.tsx` — Check auth, redirect if not logged in
10. `webui/src/contexts/mcp-provider.tsx` — Pass JWT in API calls
11. `webui/src/middleware.ts` — Route protection (skip auth for login/register)

### Dependencies to Add
- `pg` — PostgreSQL client
- `redis` — Redis client (already used, verify)
- `@keycloak/keycloak-admin-client` — Keycloak admin SDK
- `passport` / `passport-jwt` — JWT middleware (optional, can roll custom)

---

## Implementation Order (Priority)

1. **Phase 1** — Keycloak up and running (foundation)
2. **Phase 2** — API server with PostgreSQL (data layer)
3. **Phase 5** — Auth pages in WebUI (user experience)
4. **Phase 3** — REST API routes (authentication endpoints)
5. **Phase 4** — MCP proxy layer (core functionality)
6. **Phase 6** — Docker Compose & deployment
7. **Phase 7** — Security hardening
8. **Phase 8** — Testing

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Keycloak doesn't start on existing PostgreSQL | Pre-create `keycloak` database in PostgreSQL |
| WebUI JWT validation conflicts with existing MCP auth | Separate auth paths: `/api/*` uses JWT/API keys, MCP stdio uses existing token system |
| Cloudflare tunnel adds latency to OAuth flow | Use `KC_PROXY=edge` for Keycloak, keep token introspection internal |
| Rate limiting with in-memory causes data loss on restart | Use Redis (already on VM) for rate limit counters |
| Existing users/data lost | Migrate existing in-memory API keys to PostgreSQL on startup |
