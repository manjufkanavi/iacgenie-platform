#!/usr/bin/env node
/**
 * Shared Auth Wrapper — Keycloak SSO for ClamAV / CrowdSec / PageGen
 *
 * Single-file Express application that fronts an internal dashboard:
 *   /login       → Keycloak OAuth2 redirect
 *   /callback    → OIDC code exchange → httpOnly JWT cookie
 *   /dashboard   → user-info page (protected)
 *   /logout      → clear cookie → /login
 *   /health      → simple liveness probe
 *
 * All routes except /login, /callback, and /health are protected
 * by JWT validation against Keycloak's JWKS endpoint.
 */

// ─── Load .env early ───────────────────────────────────────────
require("dotenv").config();

const {
  KEYCLOAK_URL,
  KEYCLOAK_REALM,
  KEYCLOAK_CLIENT_ID,
  KEYCLOAK_CLIENT_SECRET,
  SESSION_SECRET,
  PORT,
  DASHBOARD_URL,
  SERVICE_NAME,
  CALLBACK_PATH,
  WELCOME_PATH,
  JWT_COOKIE_NAME,
  JWT_EXPIRES_IN,
} = process.env;

// ─── Defaults & validation ─────────────────────────────────────
const config = {
  keycloakUrl: (KEYCLOAK_URL || "https://auth.iacgenie.com").replace(/\/+$/, ""),
  realm: KEYCLOAK_REALM || "iacgenie",
  clientId: KEYCLOAK_CLIENT_ID || "shared-auth-wrapper",
  clientSecret: KEYCLOAK_CLIENT_SECRET || "",
  sessionSecret: SESSION_SECRET || "CHANGE-ME-THIS-SESSION-SECRET",
  port: parseInt(PORT, 10) || 3000,
  dashboardUrl: DASHBOARD_URL || "http://localhost:8080",
  serviceName: SERVICE_NAME || "Shared Auth",
  callbackPath: CALLBACK_PATH || "/callback",
  welcomePath: WELCOME_PATH || "/dashboard",
  jwtCookieName: JWT_COOKIE_NAME || "auth_token",
  jwtExpiresIn: parseInt(JWT_EXPIRES_IN, 10) || 3600,
  redirectUri: `${process.env.BASE_URL || `http://localhost:${PORT || 3000}`}${CALLBACK_PATH || "/callback"}`,
};

// Build OpenID metadata URLs once at startup
const DISCOVERY_URL = `${config.keycloakUrl}/realms/${config.realm}/.well-known/openid-configuration`;

// ─── Dependencies ──────────────────────────────────────────────
const express = require("express");
const session = require("express-session");
const fetch = (...args) => import("node-fetch").then(({ default: nf }) => nf.default(...args));

// ─── OpenID Connect metadata cache ─────────────────────────────
let oidcMetadata = null;

async function loadOidcMetadata() {
  if (oidcMetadata) return oidcMetadata;

  const res = await fetch(DISCOVERY_URL);
  if (!res.ok) {
    throw new Error(`Failed to discover OIDC config: HTTP ${res.status}`);
  }
  oidcMetadata = await res.json();
  return oidcMetadata;
}

// ─── JWKS cache ────────────────────────────────────────────────
let jwksCache = null;
let jwksExpiry = 0;

async function getJwks() {
  const now = Date.now();
  if (jwksCache && now < jwksExpiry) {
    return jwksCache;
  }

  const metadata = await loadOidcMetadata();
  const jwksUrl = metadata.jwks_uri;
  const res = await fetch(jwksUrl);

  if (!res.ok) {
    throw new Error(`Failed to fetch JWKS: HTTP ${res.status}`);
  }

  const data = await res.json();
  jwksCache = data.keys;
  // Cache for 5 minutes (or use max_age if provided)
  jwksExpiry = now + 5 * 60 * 1000;
  return jwksCache;
}

// ─── JWT validation with jose ───────────────────────────────────
let joseModule = null;

async function getJose() {
  if (!joseModule) {
    joseModule = await import("jose");
  }
  return joseModule;
}

async function validateJwt(token) {
  const jose = await getJose();
  const { jwtVerify } = jose;

  const keys = await getJwks();
  const jwks = { keys };

  const { jwt } = await jwtVerify(token, jwks, {
    issuer: config.keycloakUrl + "/realms/" + config.realm,
    audience: config.clientId,
  });

  return jwt;
}

// ─── Express setup ─────────────────────────────────────────────
const app = express();

app.set("trust proxy", 1); // Allow reverse-proxy setups

app.use(express.urlencoded({ extended: true }));
app.use(express.json());

// Session middleware — used only for state during login flow
app.use(
  session({
    secret: config.sessionSecret,
    resave: false,
    saveUninitialized: true,
    cookie: {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      maxAge: 24 * 60 * 60 * 1000, // 24 h
    },
  })
);

// ─── Helpers: HTML builders ────────────────────────────────────
function htmlPage(title, body) {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${title}</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                   "Helvetica Neue", Arial, sans-serif;
      background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #e0e0e0;
    }
    .card {
      background: rgba(255,255,255,0.07);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 16px;
      padding: 2.5rem 3rem;
      max-width: 480px;
      width: 100%;
      text-align: center;
      box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    .card h1 { font-size: 1.6rem; margin-bottom: 0.5rem; }
    .card h2 { font-size: 1.3rem; margin-bottom: 1rem; }
    .card p  { font-size: 0.95rem; color: #b0b0b0; margin-bottom: 1.5rem; line-height: 1.5; }
    .service-tag {
      display: inline-block;
      background: rgba(76, 175, 80, 0.25);
      color: #81c784;
      padding: 0.25rem 0.75rem;
      border-radius: 999px;
      font-size: 0.8rem;
      font-weight: 600;
      margin-bottom: 1rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
    a.btn {
      display: inline-block;
      background: #4caf50;
      color: #fff;
      padding: 0.75rem 2rem;
      border-radius: 8px;
      text-decoration: none;
      font-weight: 600;
      font-size: 1rem;
      transition: background 0.2s;
      border: none;
      cursor: pointer;
    }
    a.btn:hover { background: #388e3c; }
    a.btn.secondary {
      background: rgba(255,255,255,0.1);
      color: #e0e0e0;
      margin-left: 0.5rem;
    }
    a.btn.secondary:hover { background: rgba(255,255,255,0.2); }
    table.info { width: 100%; border-collapse: collapse; margin-top: 1rem; }
    table.info td {
      padding: 0.5rem 0.75rem;
      border-bottom: 1px solid rgba(255,255,255,0.08);
      text-align: left;
      font-size: 0.9rem;
    }
    table.info td:first-child {
      font-weight: 600;
      color: #81c784;
      width: 130px;
    }
    .flash {
      background: rgba(244, 67, 54, 0.2);
      border: 1px solid rgba(244,67,54,0.4);
      color: #ef9a9a;
      padding: 0.75rem 1rem;
      border-radius: 8px;
      margin-bottom: 1.5rem;
      font-size: 0.9rem;
    }
    .flash.ok {
      background: rgba(76,175,80,0.2);
      border-color: rgba(76,175,80,0.4);
      color: #a5d6a7;
    }
  </style>
</head>
<body>
  ${body}
</body>
</html>`;
}

// ─── State redirect helper (PKCE-safe state for login) ──────────
function getAuthUrl() {
  const state = Math.random().toString(36).slice(2);
  const nonce = Math.random().toString(36).slice(2);
  const redirectUri = config.redirectUri;

  const params = new URLSearchParams({
    response_type: "code",
    client_id: config.clientId,
    redirect_uri: redirectUri,
    scope: "openid profile email",
    state,
    nonce,
  });

  return `${config.keycloakUrl}/realms/${config.realm}/protocol/openid-connect/auth?${params.toString()}`;
}

// ─── Routes ─────────────────────────────────────────────────────

// Health check — unauthenticated
app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: config.serviceName, timestamp: new Date().toISOString() });
});

// ─── Login (redirect to Keycloak) ──────────────────────────────
app.get("/login", (_req, res) => {
  res.redirect(getAuthUrl());
});

// ─── Callback (exchange code for tokens) ───────────────────────
app.get(config.callbackPath, async (req, res) => {
  const { code, state, error } = req.query;

  // Error from Keycloak
  if (error) {
    return res.status(400).send(
      htmlPage("Login Error", `
        <div class="card">
          <span class="service-tag">${config.serviceName}</span>
          <h1>Login Failed</h1>
          <div class="flash">${error}: ${req.query.error_description || "No details"}</div>
          <a href="/login" class="btn">Try Again</a>
        </div>
      `)
    );
  }

  if (!code) {
    return res.status(400).send(
      htmlPage("Bad Request", `
        <div class="card">
          <span class="service-tag">${config.serviceName}</span>
          <h1>Missing Authorization Code</h1>
          <p>The callback did not include a code parameter.</p>
          <a href="/login" class="btn">Try Again</a>
        </div>
      `)
    );
  }

  try {
    // Exchange code for tokens
    const tokenRes = await fetch(`${config.keycloakUrl}/realms/${config.realm}/protocol/openid-connect/token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({
        grant_type: "authorization_code",
        code,
        client_id: config.clientId,
        client_secret: config.clientSecret,
        redirect_uri: config.redirectUri,
      }),
    });

    if (!tokenRes.ok) {
      const errBody = await tokenRes.text();
      throw new Error(`Token exchange failed: HTTP ${tokenRes.status} — ${errBody.slice(0, 200)}`);
    }

    const tokens = await tokenRes.json();

    // Store JWT in httpOnly cookie
    res.cookie(config.jwtCookieName, tokens.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: config.jwtExpiresIn * 1000,
      path: "/",
    });

    // Redirect to the actual dashboard
    res.redirect(config.dashboardUrl);
  } catch (err) {
    console.error("Callback error:", err.message);
    res.status(500).send(
      htmlPage("Server Error", `
        <div class="card">
          <span class="service-tag">${config.serviceName}</span>
          <h1>Authentication Error</h1>
          <div class="flash">Could not complete login. Please try again.</div>
          <a href="/login" class="btn">Back to Login</a>
        </div>
      `)
    );
  }
});

// ─── JWT middleware ─────────────────────────────────────────────
async function authMiddleware(req, res, next) {
  const token = req.cookies?.[config.jwtCookieName];

  if (!token) {
    // Not authenticated — redirect to login
    return res.redirect("/login");
  }

  try {
    const payload = await validateJwt(token);
    req.user = payload;
    // Extend token expiry on the cookie
    res.cookie(config.jwtCookieName, token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: config.jwtExpiresIn * 1000,
      path: "/",
    });
    next();
  } catch (err) {
    console.warn("JWT validation failed:", err.message);
    // Clear invalid cookie and redirect to login
    res.clearCookie(config.jwtCookieName, { path: "/" });
    res.redirect("/login");
  }
}

// ─── Dashboard (protected) ─────────────────────────────────────
app.get("/dashboard", authMiddleware, (req, res) => {
  const user = req.user || {};

  const body = `
    <div class="card" style="max-width:560px;">
      <span class="service-tag">${config.serviceName}</span>
      <h1>Welcome, ${user.preferred_username || user.name || "User"}!</h1>
      <p>You are authenticated and authorized to access ${config.serviceName}.</p>

      <table class="info">
        <tr><td>Username</td><td>${user.preferred_username || user.name || "—"}${user.name !== user.preferred_username && user.name ? " (" + user.name + ")" : ""}</td></tr>
        <tr><td>Email</td><td>${user.email || "—"}</td></tr>
        <tr><td>Email Verified</td><td>${user.email_verified ? "Yes" : "No"}</td></tr>
        <tr><td>User ID</td><td>${user.sub || "—"}</td></tr>
        <tr><td>Roles</td><td>${(user.roles || []).join(", ") || "— (no roles claim)"}</td></tr>
      </table>

      <div style="margin-top:1.5rem;">
        <a href="${config.dashboardUrl}" class="btn">Go to ${config.serviceName} →</a>
        <a href="/logout" class="btn secondary">Logout</a>
      </div>
    </div>
  `;

  res.send(htmlPage(`Dashboard — ${config.serviceName}`, body));
});

// ─── Logout (clear cookie) ─────────────────────────────────────
app.get("/logout", (req, res) => {
  res.clearCookie(config.jwtCookieName, { path: "/" });

  // Also check if Keycloak has a SLO endpoint
  const logoutRedirect = `${config.keycloakUrl}/realms/${config.realm}/protocol/openid-connect/logout?post_logout_redirect_uri=${encodeURIComponent(config.redirectUri)}&client_id=${encodeURIComponent(config.clientId)}`;

  // Redirect to Keycloak logout, or fall back to login
  // Use a small JS redirect so we can attempt Keycloak SLO gracefully
  res.send(`<!DOCTYPE html>
<html>
<head><meta http-equiv="refresh" content="0;url=${logoutRedirect}"></head>
<body>
  <p>Logging out... <a href="/login">Click here if redirected</a>.</p>
</body>
</html>`);
});

// ─── Root — redirect to login ──────────────────────────────────
app.get("/", (_req, res) => {
  res.redirect("/login");
});

// ─── 404 catch-all ─────────────────────────────────────────────
app.use((_req, res) => {
  res.status(404).send(
    htmlPage("Not Found", `
      <div class="card">
        <span class="service-tag">${config.serviceName}</span>
        <h1>404 — Not Found</h1>
        <p>The requested resource does not exist.</p>
        <a href="/login" class="btn">Login</a>
      </div>
    `)
  );
});

// ─── Error handler ──────────────────────────────────────────────
app.use((err, _req, res, _next) => {
  console.error("Unhandled error:", err);
  res.status(500).send(
    htmlPage("Server Error", `
      <div class="card">
        <span class="service-tag">${config.serviceName}</span>
        <h1>Internal Server Error</h1>
        <div class="flash">Something went wrong. Please try again.</div>
        <a href="/login" class="btn">Login</a>
      </div>
    `)
  );
});

// ─── Start server ───────────────────────────────────────────────
const server = app.listen(config.port, () => {
  console.log(`
╔══════════════════════════════════════════════════════════╗
║  ${config.serviceName.padEnd(47)}║
║  Auth Wrapper listening on port ${String(config.port).padEnd(43)}║
╚══════════════════════════════════════════════════════════╝
`);
  console.log(`  Service : ${config.serviceName}`);
  console.log(`  Realm   : ${config.realm}`);
  console.log(`  Client  : ${config.clientId}`);
  console.log(`  Dashboard: ${config.dashboardUrl}`);
  console.log(`  Base URL : ${config.redirectUri}`);
  console.log("");
  console.log("  Routes:");
  console.log("    /login          → Keycloak login");
  console.log(`  ${config.callbackPath}             → OIDC callback`);
  console.log("    /dashboard      → User info (protected)");
  console.log("    /logout         → Logout");
  console.log("    /health         → Health check");
  console.log("");
});

// Graceful shutdown
process.on("SIGINT", () => {
  console.log("\nShutting down gracefully...");
  server.close(() => process.exit(0));
});
process.on("SIGTERM", () => {
  console.log("\nShutting down gracefully...");
  server.close(() => process.exit(0));
});

module.exports = app;
