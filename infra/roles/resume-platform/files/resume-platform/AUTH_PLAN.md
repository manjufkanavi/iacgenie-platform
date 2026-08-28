# Resume Platform — Full Auth Integration Plan

## Executive Summary

Migrate the resume platform from a **demo-only auth flow** to production-grade authentication matching IacGenie's patterns:
- Keycloak OIDC with PKCE for SSO login
- Email/password registration + login via auth-wrapper (shared Keycloak client)
- JWT access tokens with short expiry + refresh token rotation
- Protected routes, role-based access (user/admin)
- Password reset via email OTP
- Welcome emails on signup

---

## Current State Analysis

### What exists today (broken/incomplete)

| Component | Status | Issues |
|-----------|--------|--------|
| Frontend login page | Demo-only | `login-demo()` bypasses all auth, no Keycloak flow |
| Auth callback (`/auth/callback`) | Demo-only | Ignores the auth code, just calls `loginDemo()` |
| Auth context (`auth-context.tsx`) | Partial Keycloak redirect | `loginWithKeycloak()` builds a URL but never exchanges the code for tokens |
| Backend auth routes (`routes/auth.py`) | Token verify only | No login/signup endpoints — backend is purely a token validator |
| Backend auth service (`services/auth.py`) | Token validation only | Validates via Keycloak introspection but no user lifecycle endpoints |
| Nginx config | Routes auth to backend port 3006 | Auth endpoints need the full stack (login, signup, refresh) not just verify |

### What IacGenie does right (patterns to replicate)
- **Unified auth backend** with login/signup/refresh/password-reset/verify-email endpoints
- **Keycloak OIDC + PKCE** for browser-based SSO flow (redirect → code exchange → tokens)
- **Local JWT generation** after Keycloak auth — backend issues its own HS256 tokens
- **Refresh token rotation** with database storage and JTI revocation
- **ProtectedRoute component** with auto-refresh on stale tokens
- **Zustand auth store** persisted to localStorage
- **Email OTP flow** for verification and password reset

---

## Phase 1: Backend Auth Endpoints (Week 1)

### 1.1 Add Authentication Routes to Resume API

**File:** `api/routes/auth.py` (create new file, currently only has verify + n8n callback)

Add these endpoints following IacGenie's pattern:

```
POST /api/v1/auth/login          — Email/password login via auth-wrapper
POST /api/v1/auth/signup         — User registration (creates user in Keycloak + local DB)
POST /api/v1/auth/refresh        — Refresh access token (rotation)
POST /api/v1/auth/logout         — Revoke refresh token + clear session
GET  /api/v1/auth/config         — Returns auth capabilities for UI (like IacGenie)
GET  /api/v1/auth/keycloak/login — Redirect to Keycloak for SSO (PKCE flow)
GET  /api/v1/auth/keycloak/callback — Exchange auth code for tokens (PKCE)
POST /api/v1/auth/forgot-password — Send password reset OTP via email
POST /api/v1/auth/reset-otp       — Reset password with verified OTP
```

### 1.2 Auth Service (`services/auth.py`) — Extend

Current: only `validate_token()` and `get_user_from_token()`. Add:

```python
async def login_with_credentials(email, password) -> AuthResult
    # POST to auth-wrapper /api/auth/login (same as IacGenie)
    # Returns: {token, refresh_token, user}

async def register_user(email, password, display_name) -> AuthResult
    # POST to auth-wrapper /api/auth/signup
    # Creates user in Keycloak, stores local DB record

async def exchange_auth_code(code) -> dict
    # Exchange PKCE auth code for Keycloak tokens
    # POST to /realms/iacgenie/protocol/openid-connect/token
    # Returns: access_token, refresh_token

async def refresh_access_token(refresh_token) -> dict
    # Validate refresh token against DB
    # Generate new access + refresh tokens (rotation)

async def verify_email(otp_token, otp_code) -> bool
    # Verify OTP from email

async def send_password_reset_email(email) -> dict
    # Generate 6-digit OTP, store hashed in DB, send via SMTP

async def reset_password(otp_token, new_password) -> bool
    # Verify OTP token + set new password via auth-wrapper

async def logout(refresh_token) -> bool
    # Revoke refresh token from DB
```

### 1.3 Database Schema Additions (`database.py`)

Add these tables if not present:

```sql
-- Refresh tokens for rotation tracking (like IacGenie)
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    client_id VARCHAR(255),          -- 'web-app' or mobile app id
    token_hash CHAR(64) NOT NULL,     -- SHA-256 of plain refresh token
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    rotated_from_id UUID REFERENCES refresh_tokens(id),  -- rotation chain
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_token_hash ON refresh_tokens(token_hash);

-- OTP tokens for email verification and password reset
CREATE TABLE IF NOT EXISTS otp_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    purpose VARCHAR(50),              -- 'email_verify' or 'password_reset'
    email_hash CHAR(64) NOT NULL,     -- SHA-256 of user's email
    otp_code_hash CHAR(64) NOT NULL,  -- SHA-256 of the 6-digit code
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    used BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_otp_tokens_user ON otp_tokens(user_id, purpose);
```

### 1.4 Auth Wrapper Integration (`services/auth.py`)

The resume platform already has `AUTH_WRAPPER_URL` configured. Use it:

```python
# Auth wrapper endpoints (shared across all IacGenie platforms)
AUTH_WRAPPER_LOGIN = f"{AUTH_WRAPPER_URL}/api/auth/login"       # email/password login
AUTH_WRAPPER_SIGNUP = f"{AUTH_WRAPPER_URL}/api/auth/signup"      # user registration  
AUTH_WRAPPER_VERIFY_EMAIL = f"{AUTH_WRAPPER_URL}/api/auth/verify-email/{{token}}"
```

This means: **No need to manage passwords or bcrypt** — auth-wrapper handles all credential ops via Keycloak ROPC. The resume platform just proxies calls to it and adds its own JWT layer on top.

---

## Phase 2: Keycloak Client Setup (Week 1)

### 2.1 Register `resume-platform` OIDC client in Keycloak realm "iacgenie"

The setup script (`setup_keycloak_realm.py`) already references `resume-platform` client. Verify:

- **Client ID**: `resume-platform`
- **Access Type**: `confidential` (for backend) or `public` (for frontend SPA)
- **Standard Flow Enabled**: ✅ (Authorization Code + PKCE for SPAs)
- **Direct Access Grants**: ❌ (disable — use auth-wrapper instead of ROPC)
- **Valid Redirect URIs**: `https://resume.iacgenie.com/auth/callback` + dev variants
- **Valid Post Logout Redirect URIs**: `https://resume.iacgenie.com/login`
- **PKCE Code Challenge Method**: S256

### 2.2 Configure auth-wrapper for resume-platform

The shared `auth-wrapper` service needs:
- A client entry for `resume-platform` in its config (reads from Keycloak)
- The auth-wrapper already supports multiple clients — just ensure it has the `resume-platform` client secret

---

## Phase 3: Frontend Auth UI (Week 2)

### 3.1 Replace Login Page with Full IacGenie-Style Auth Pages

**Current:** `login/page.tsx` → just renders `<LoginInner />` with demo buttons
**Target:** Full auth flow matching IacGenie's `SignInPage.tsx`

#### New pages to create in `webui/src/app/`:

| Page | Purpose | IacGenie Reference |
|------|---------|-------------------|
| `/login` | Email/password login form + SSO redirect button | `SignInPage.tsx` (adapted) |
| `/signup` | Registration form with password strength meter | `SignUpPage.tsx` (adapted) |
| `/verify-email/[token]` | Email verification after signup with OTP entry | `VerifyOtpPage.tsx` (adapted) |
| `/forgot-password` | Enter email to receive password reset OTP | `ForgotPasswordPage.tsx` (adapted) |
| `/reset-password/[token]` | Enter new password after OTP verification | `ResetPasswordPage.tsx` (adapted) |
| `/auth/callback` | Keycloak PKCE code exchange result page | Current (but fix to actually exchange tokens) |

### 3.2 Auth Context (`contexts/auth-context.tsx`) — Major Rewrite

Current: basic localStorage + demo mode. Replace with IacGenie pattern using Zustand-like state management:

```typescript
// AuthContextValue interface (new)
interface AuthUser {
  keycloak_id: string;
  email: string;
  name?: string;
  roles?: string[];        // from Keycloak user attributes
}

interface AuthContextValue {
  // State
  user: AuthUser | null;
  token: string | null;     // access token (JWT from backend)  
  refreshToken: string | null;
  isLoading: boolean;

  // Actions — matching IacGenie login service exactly
  login: (email, password) => Promise<AuthUser>        // email/password via backend
  signup: (email, password, displayName) => Promise<SignupResult>
  loginWithKeycloak: () => void                        // redirect to Keycloak PKCE flow
  logout: () => Promise<void>                          // backend + client cleanup
  
  // Token management (like IacGenie's refreshIfExpired)
  setCredentials: (token, refreshToken, user) => void
  
  // Check on mount whether token is valid/refreshable
}

// Key changes from current implementation:
// 1. loginWithKeycloak() now redirects to proper PKCE flow (not demo)
// 2. login() calls backend POST /api/v1/auth/login (same as IacGenie's localAuthService.login)
// 3. signup() calls backend POST /api/v1/auth/signup  
// 4. logout() calls backend POST /api/v1/auth/logout to revoke refresh token
// 5. Token stored in localStorage under 'resume_token' / 'resume_refresh_token' (not resume-auth)
// 6. On mount: check if token exists, verify it via POST /api/v1/auth/verify
// 7. If expired: attempt refresh via POST /api/v1/auth/refresh (rotation)
```

### 3.3 Auth Callback Page Fix (`auth/callback/page.tsx`)

**Current:** Ignores the `code` parameter, just calls demo.
**Fix:** Actually exchange code for tokens:

```typescript
// In useEffect of CallbackInner:
useEffect(() => {
  const code = search.get('code');
  if (code) {
    // POST to backend: /api/v1/auth/keycloak/callback?code=XXX&state=YYY
    fetch('/api/v1/auth/keycloak/callback', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},  
      body: JSON.stringify({ code, state })
    }).then(res => res.json()).then(({ token, refresh_token, user }) => {
      persist(token, refresh_token, user);
      router.push('/dashboard');
    });
  } else {
    // No code — show error or demo fallback
    router.push('/login');
  }
}, [code, state]);
```

### 3.4 Protected Route Component (`components/protected-route.tsx`)

Create a Next.js route guard (using middleware or HOC pattern):

```typescript
// Pattern: wrap dashboard/resume/[id]/pages with ProtectedRoute HOC
export function ProtectedRoute({ children, requiredRole }) {
  const { isAuthenticated, isLoading, refreshIfExpired } = useAuth();

  useEffect(() => {
    if (isLoading) return; // still initializing
    
    const check = async () => {
      if (!isAuthenticated) {
        // Try to refresh stale token first (like IacGenie's ProtectedRoute)
        const refreshed = await refreshIfExpired();
        if (refreshed) return; // token was valid, continue rendering
      }
      
      // Not authenticated — redirect to login with return URL
      router.push(`/login?redirect=${encodeURIComponent(window.location.pathname)}`);
    };
    
    check();
  }, [isAuthenticated, isLoading]);

  if (isLoading) return <LoadingSpinner />;
  
  // If we get here, user is authenticated (or redirect already triggered)
  return <>{children}</>;
}

// Usage: 
// export default function DashboardPage() { return <ProtectedRoute><DashboardContent/></ProtectedRoute> }
// Or better: use Next.js middleware for route-level protection (see 3.5)
```

### 3.5 Next.js Middleware for Route Protection (Recommended over HOCs)

Create `middleware.ts` in webui root:

```typescript
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Public routes that don't require auth
const publicRoutes = ['/login', '/signup', '/', '/templates'];

export function middleware(request: NextRequest) {
  const token = request.cookies.get('resume_token')?.value;
  // Or read from localStorage via a different approach — cookies are better for SSR
  
  const isPublic = publicRoutes.some(route => 
    request.nextUrl.pathname === route || request.nextUrl.pathname.startsWith('/auth/')
  );

  if (!isPublic && !token) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  // If token exists, verify it with backend (lightweight check)  
  if (token && !isPublic) {
    // Optional: validate token header before proxying to backend API routes
  }

  return NextResponse.next(); // Continue to page/API route handler
}

export const config = {
  matcher: ['/dashboard/:path*', '/resume/:path*'], // Only protect authenticated routes
};
```

### 3.6 UI Components (Adapt from IacGenie)

Create these components following IacGenie's patterns:

| Component | Source | Resume Adaptation |
|-----------|--------|-------------------|
| `SecurePasswordInput` | IacGenie's `ui/SecurePasswordInput.tsx` | Already exists in resume, keep it |
| `OTP Input` | IacGenie's `ui/OTPInput.tsx` (6-digit boxes) | Add for email verify + password reset flows |
| `Password Strength Meter` | IacGenie's `ui/PasswordStrengthMeter.tsx` | Add for signup page |
| `Social Login Buttons` | IacGenie's `ui/SocialLogin.tsx` | Simplified — just Keycloak SSO button for resume platform |
| `SSO Modal` (optional) | IacGenie's `ui/SSOModal.tsx` | Skip — resume platform only has Keycloak SSO, no enterprise SAML |

---

## Phase 4: API Client Updates (Week 2)

### 4.1 Update `lib/api.ts`

Current: only has verify, list, get, upload, score, improve methods. Add auth endpoints:

```typescript
// Auth API calls (parallel IacGenie's localAuthService)

export const authApi = {
  // Login — same call pattern as IacGenie's localAuthService.login()  
  login: async (email: string, password: string) => {
    const res = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) throw new Error(await res.json().then(r => r.detail || 'Login failed'));
    const data = await res.json();
    return { token: data.access_token, refresh_token: data.refresh_token, user: data.user };
  },

  // Signup — with password strength validation  
  signup: async (email, password, displayName) => {
    const res = await fetch('/api/v1/auth/signup', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ email, password, displayName }),
    });
    if (!res.ok) throw new Error(await res.json().then(r => r.detail || 'Signup failed'));
    return await res.json();  // {message, user?, otp_token?}
  },

  // Refresh — with rotation  
  refresh: async (refreshToken) => {
    const res = await fetch('/api/v1/auth/refresh', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) throw new Error('Token refresh failed');
    return await res.json(); // {access_token, refresh_token}  (rotation)
  },

  // Logout — revoke on server  
  logout: async () => {
    await fetch('/api/v1/auth/logout', { method: 'POST' });
  },

  // Verify — check token validity (already exists, keep it)  
  verify: async () => {
    const token = localStorage.getItem('resume_token');
    return request('/auth/verify', token);  
  },

  // Forgot password — send OTP
  forgotPassword: async (email) => {
    const res = await fetch('/api/v1/auth/forgot-password', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ email }),
    });
    if (!res.ok) throw new Error('Failed to send reset email');
  },

  // Reset password — verify OTP + new password
  resetPassword: async (token, newPassword) => {
    const res = await fetch('/api/v1/auth/reset-otp', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, 
      body: JSON.stringify({ token, new_password: newPassword }),
    });
    if (!res.ok) throw new Error('Password reset failed');
  },

  // Verify email — OTP verification after signup  
  verifyEmail: async (token, otpCode) => {
    const res = await fetch('/api/v1/auth/verify-otp', {
      method: 'POST', headers: {'Content-Type': 'application/json'},  
      body: JSON.stringify({ token, otp_code: otpCode }),
    });
    if (!res.ok) throw new Error('Email verification failed');
  },

  // Auth config — discover available providers (like IacGenie)  
  getConfig: async () => {
    const res = await fetch('/api/v1/auth/config');
    return await res.json();  // {providers: [...], ssoEnabled, localAuthEnabled}
  },
};

// Also update the request() helper to auto-attach token + handle 401 → redirect
async function protectedRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('resume_token');
  
  // Auto-refresh if access token might be expired but refresh exists
  const refreshToken = localStorage.getItem('resume_refresh_token');  
  if (token && isTokenExpired(token) && refreshToken) {
    try { await refreshAuth(); } catch {} // silent fail, will get 401 below
  }

  const res = await fetch(`/api/v1${path}`, { 
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    ...init, 
  });

  if (res.status === 401) {
    // Token invalid — clear auth and redirect to login
    localStorage.removeItem('resume_token');  
    localStorage.removeItem('resume_refresh_token');
    window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`;
  }

  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return await (res.json() as T);  
}
```

### 4.2 Cookie-Based Auth Storage (Better than localStorage for Next.js)

**Recommendation:** Switch from `localStorage` to HTTP-only cookies for token storage. This prevents XSS theft of JWTs and works seamlessly with Next.js middleware.

```typescript
// In auth-context.tsx, when persisting:
const setCredentials = useCallback((newToken, newRefresh, newUser) => {  
  if (typeof window === 'undefined') return;
  
  // Set HTTP-only cookies via API call (backend sets the cookie)
  if (newToken && newRefresh) {
    fetch('/api/v1/auth/cookie', {  // New endpoint that sets HTTP-only cookies
      method: 'POST',
      headers: {'Content-Type': 'application/json'},  
      body: JSON.stringify({ token: newToken, refresh_token: newRefresh }),
    });
  } else {
    fetch('/api/v1/auth/cookie/clear', { method: 'DELETE' });  // New endpoint
  }

  setUserState(newUser);  
}, []);
```

**Alternative (simpler):** Keep localStorage for now but add `__Secure-` prefix and use SameSite cookies from the Next.js server.

---

## Phase 5: Nginx Configuration (Week 2)

### Current nginx config issues for auth integration:

1. **Auth endpoints routed to port 3006 (backend)** — correct, but need auth-wrapper path
2. **`/api/v1/auth/*` goes to backend** — need auth-wrapper for SSO redirect flow
3. **Frontend served from port 3006** — Next.js handles its own SPA routing

### Updated nginx vHost (`resume-platform.conf`):

```nginx
# Auth endpoints → backend (handles login/signup/refresh/password-reset)  
location /api/v1/auth/ {
    limit_req zone=auth burst=3 nodelay;
    proxy_pass http://127.0.0.1:3006;
    # ... headers (same as current)
}

# SSO redirect → auth-wrapper for Keycloak PKCE flow  
location /auth/ {
    proxy_pass http://127.0.0.9:9096;  # auth-wrapper on its own port
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;  
    # auth-wrapper handles redirect to Keycloak
}

# Main API (through auth-wrapper for token validation) — unchanged  
location /api/v1/resume/ {
    proxy_pass http://127.0.0.9:9096;
    # ... headers  
}

# Frontend SPA — unchanged
location / {
    proxy_pass http://127.0.0.1:3006;  # Next.js dev/prod server
}
```

---

## Phase 6: Email / SMTP Integration (Week 3)

### 6.1 SMTP Configuration via auth-wrapper

The resume platform should reuse the shared email infrastructure:
- **SMTP host**: `mail.iacgenie.com` (or whatever is configured in auth-wrapper)
- **Sender**: `noreply@iacgenie.com`
- **Templates stored in auth-wrapper** (reuse IacGenie templates with resume-specific branding)

### 6.2 Email Templates Needed (resume-platform specific):

| Template | Trigger | Content |
|----------|---------|---------|
| `welcome` | After signup | Welcome + verification link/OTP |  
| `password_reset_otp` | User requests password reset | 6-digit OTP + instructions |
| `password_changed` | After successful reset | Confirmation of password change |

### 6.3 SMTP2Go / Email Service Integration

Add to `services/auth.py`:
```python
import smtplib  # or use sendgrid / SMTP2Go SDK

async def send_otp_email(to_email: str, otp_code: str) -> bool:
    """Send 6-digit OTP via SMTP"""
    # Reuse auth-wrapper's email service or configure directly
    subject = "Reset your Resume Platform password"  
    body = f"""Your verification code is: {otp_code}
    
    This code expires in 10 minutes. If you didn't request this, ignore this email."""
    
    # Send via SMTP (same pattern as IacGenie's smtp2go_email_service)
    ...

async def send_welcome_email(to_email: str, verification_link: str, username: str) -> bool:
    """Send welcome + email verification link after signup"""  
    subject = "Welcome to Resume Platform"
    body = f"""Hi {username},\n\nPlease verify your email by clicking:  
    {verification_link}\n\nThis link expires in 24 hours."""
```

---

## Phase 7: Role-Based Access Control (Week 3)

### 7.1 User Roles in Keycloak

Configure user roles as **Keycloak client scopes** or **realm roles**:
- `user` — default role for all registered users  
- `admin` — platform administrators (can manage templates, view analytics)

### 7.2 Role Enforcement in Resume API

Add role checks to protected endpoints:
```python
# In routes/resumes.py, add admin-only endpoints

def require_admin(user: dict = Depends(require_auth)) -> dict:
    """Check user has admin role"""  
    roles = user.get('roles', []) or []
    if 'admin' not in roles:
        raise HTTPException(status_code=403, detail="Admin access required")  
    return user

# Admin-only routes
@router.get("/admin/users", dependencies=[Depends(require_admin)])  
async def list_all_users():
    """List all users (admin only)"""

@router.post("/templates", dependencies=[Depends(require_admin)])
async def create_template(template_data: TemplateCreate):  
    """Create a new resume template (admin only)"""
```

### 7.3 UI Role Display

Add role badge to Navbar:
- **Regular user**: Shows name + "Log out"  
- **Admin**: Shows name, role badge ("Admin"), and admin menu items

---

## File Change Summary

### New files to create:
1. `api/routes/auth.py` — Auth endpoints (login, signup, refresh, logout, forgot-password)
2. `webui/src/app/login/login-inner.tsx` — Full login form (replace demo)
3. `webui/src/app/signup/page.tsx` — Registration page  
4. `webui/src/app/verify-email/[token]/page.tsx` — Email verification with OTP
5. `webui/src/app/forgot-password/page.tsx` — Password reset request  
6. `webui/src/app/reset-password/[token]/page.tsx` — Password reset with new password
7. `webui/src/components/protected-route.tsx` — Route guard HOC

### Files to modify:
1. `api/services/auth.py` — Add login, signup, refresh, password-reset methods (extend current)
2. `api/database.py` — Add refresh_tokens and otp_tokens tables to schema
3. `contexts/auth-context.tsx` — Major rewrite: real Keycloak PKCE + backend auth
4. `auth/callback/page.tsx` — Actually exchange code for tokens  
5. `lib/api.ts` — Add authApi module, update request() with auto-refresh
6. `components/navbar.tsx` — Update logout flow (call backend), show user roles

### Infrastructure changes:
1. Ansible role `resume-platform` — add auth-related env vars, DB migration tasks  
2. Nginx vHost template (`resume-platform.conf.j2`) — update proxy rules
3. Docker Compose → add auth-wrapper as dependency, ensure network connectivity

---

## Environment Variables to Add (`resume-platform.env`)

```bash
# Auth (already partially present)  
NEXT_PUBLIC_KEYCLOAK_URL=https://keycloak.iacgenie.com
KEYCLOAK_REALM=iacgenie  
NEXT_PUBLIC_KEYCLOAK_CLIENT_ID=resume-platform
KEYCLOAK_CLIENT_SECRET=<from Keycloak admin console>

# New: Auth wrapper API
AUTH_WRAPPER_URL=http://auth-wrapper:9096  # or http://127.0.0.9:9096 for nginx proxy

# New: JWT signing (backend issues its own short-lived tokens)
JWT_SECRET=<32-char random string>
JWT_EXPIRATION=900        # 15 minutes for access tokens  
JWT_REFRESH_EXPIRATION=604800  # 7 days for refresh tokens

# New: SMTP (for welcome/verification/password reset emails)
SMTP_HOST=mail.iacgenie.com  
SMTP_PORT=587
SMTP_USER=noreply@iacgenie.com
SMTP_PASSWORD=<from secrets>  
FROM_EMAIL=noreply@iacgenie.com

# New: Database (for refresh_tokens and otp_tokens tables)
DATABASE_URL=postgresql+asyncpg://resume_platform:<password>@postgres:5432/iacgenie
```

---

## Migration Strategy (Zero Downtime)

### Step 1: Backend first
- Deploy new auth routes to backend (backward compatible — existing verify endpoint unchanged)  
- Run DB migrations for refresh_tokens and otp_tokens tables
- Configure Keycloak client secrets

### Step 2: Frontend  
- Deploy new auth pages alongside existing ones
- Auth callback page updated to exchange real tokens
- Old demo login still works for non-authenticated users (graceful transition)

### Step 3: Cutover
- Update nginx config for auth-wrapper routing  
- Restart Next.js frontend → new pages are live
- Users see full login/signup flow instead of demo

### Step 4: Cleanup  
- Remove `loginDemo()` from auth context (after verifying all flows work)
- Deprecate demo mode entirely

---

## Testing Checklist

- [ ] Login with email/password → gets access token + refresh token
- [ ] Signup creates user in Keycloak, returns OTP for email verification  
- [ ] Email verification with correct OTP → marks user as verified
- [ ] Forgot password sends 6-digit OTP via email  
- [ ] Reset password with valid OTP → new password works
- [ ] Token refresh (after 15 min expiry) returns new token pair without re-login
- [ ] Logout revokes refresh token — subsequent API calls return 401  
- [ ] Keycloak SSO redirect → code exchange → dashboard
- [ ] Protected routes redirect to login when unauthenticated  
- [ ] Stale token auto-refresh on API call failure (401)
- [ ] Demo mode still works for guests on landing page  
- [ ] Email templates render correctly with resume branding

---

## Key Differences from IacGenie (Resume-specific)

| Feature | IacGenie Platform | Resume Platform |
|---------|-------------------|-----------------|  
| Frontend framework | Vite + React Router (SPA) | Next.js 14+ App Router (SSR/ISR) |
| Route protection | React Router `<ProtectedRoute>` component | Next.js middleware + HOC  
| Token storage | localStorage (iacgenie_token) | Cookies recommended, or resume_token in localStorage
| SSO providers | Google + GitHub via Keycloak IDPs | Just Keycloak (simpler)  
| Email service | smtp2go via auth-wrapper | Same — reuse shared SMTP infrastructure
| Role system | Complex nested roles (global + per-project) | Simple: `user` / `admin`
| Demo mode | No demo — full auth required | Keep demo for testing/preview (optional)
| Password policy | Complex (length, upper, lower, number, special) | Standard bcrypt via auth-wrapper

---

## Timeline Summary

| Phase | Duration | Dependencies |
|-------|----------|-------------|  
| 1. Backend auth endpoints | Week 1 (3-4 days) | None — pure backend work |
| 2. Keycloak client setup | Week 1 (1 day) | Phase 1 auth service complete  
| 3. Frontend auth UI + context rewrite | Week 2 (5 days) | Phase 1-2 complete
| 4. API client updates + middleware | Week 2 (3 days) | Phase 3 auth context complete
| 5. Nginx config updates | Week 2 (1 day) | Phase 4 complete
| 6. Email/SMTP integration | Week 3 (2-3 days) | Phase 1 auth service complete
| 7. RBAC + role enforcement | Week 3 (2 days) | Phase 1-6 complete
| **Total** | **~3 weeks** | Sequential phases, some parallelizable
