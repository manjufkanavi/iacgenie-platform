/**
 * IaCGenie Unified Auth Wrapper v2
 * Handles OIDC auth + dashboard + proxy for multiple backend services
 *
 * Env: PORT, KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID,
 *       KEYCLOAK_CLIENT_SECRET, SESSION_SECRET, SERVICE_NAME,
 *       SERVICE_TITLE, SERVICE_DESCRIPTION
 *
 * SERVICE_BACKENDS env: comma-separated "name:port" pairs
 *   Example: "clamav:9092,pagegen:3032,crowdsec:3033,searxng:8084"
 */
const express = require('express');
const session = require('express-session');
const jwt = require('jsonwebtoken');
const crypto = require('crypto');
const fetch = require('node-fetch');
const http = require('http');

const app = express();
const PORT = parseInt(process.env.PORT) || 9090;
const KC_URL = process.env.KEYCLOAK_URL || 'https://auth.iacgenie.com';
const KC_REALM = process.env.KEYCLOAK_REALM || 'iacgenie';
const KC_CLIENT_ID = process.env.KEYCLOAK_CLIENT_ID || 'auth-wrapper';
const KC_CLIENT_SECRET = process.env.KEYCLOAK_CLIENT_SECRET || '';
const SESSION_SECRET = process.env.SESSION_SECRET || 'iacgenie-auth-wrapper-2024';
const SERVICE_NAME = process.env.SERVICE_NAME || 'Auth-Wrapper';
const SERVICE_TITLE = process.env.SERVICE_TITLE || SERVICE_NAME;
const SERVICE_DESCRIPTION = process.env.SERVICE_DESCRIPTION || '';

// Parse backend services: "clamav:9092,pagegen:3032,crowdsec:3033,searxng:8084"
const BACKENDS = {};
const svcBackendsRaw = process.env.SERVICE_BACKENDS || 'default:9090';
svcBackendsRaw.split(',').forEach(function (pair) {
  var parts = pair.split(':');
  if (parts.length === 2) BACKENDS[parts[0]] = parseInt(parts[1]);
});

// Domain-to-backend mapping via Host header
const DOMAIN_BACKEND_MAP = {
  'clamav.iacgenie.com': 'clamav',
  'pagegen.iacgenie.com': 'pagegen',
  'crowdsec.iacgenie.com': 'crowdsec',
  'search.iacgenie.com': 'searxng'
};

const SERVICE_DISPLAY_NAMES = {
  'clamav': 'ClamAV Dashboard',
  'pagegen': 'PageGen Dashboard',
  'crowdsec': 'CrowdSec Dashboard',
  'searxng': 'SearXNG Search'
};

const KC_AUTH_URL = KC_URL + '/realms/' + KC_REALM + '/protocol/openid-connect/auth';
const KC_TOKEN_URL = KC_URL + '/realms/' + KC_REALM + '/protocol/openid-connect/token';
const KC_LOGOUT_URL = KC_URL + '/realms/' + KC_REALM + '/protocol/openid-connect/logout';

/* -- Token verification -- */
function verifyToken(req, res, next) {
  var token = req.cookies && req.cookies.access_token;
  if (!token) return res.redirect('/login');
  try {
    var decoded = jwt.decode(token);
    if (!decoded || decoded.exp * 1000 < Date.now()) return res.redirect('/login');
    req.user = decoded;
    next();
  } catch (e) { res.redirect('/login'); }
}

/* -- Get backend port from Host header -- */
function getBackendPort(req) {
  var host = req.get('X-Forwarded-Host') || req.hostname;
  var svcName = DOMAIN_BACKEND_MAP[host] || 'default';
  return BACKENDS[svcName] || BACKENDS['default'] || 9090;
}

function getServiceName(req) {
  var host = req.get('X-Forwarded-Host') || req.hostname;
  var svcName = DOMAIN_BACKEND_MAP[host] || 'default';
  return SERVICE_DISPLAY_NAMES[svcName] || SERVICE_TITLE;
}

/* -- Middleware -- */
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(session({
  secret: SESSION_SECRET, resave: false, saveUninitialized: true,
  cookie: { httpOnly: true, secure: false, maxAge: 300000 }
}));

/* -- Login -- */
app.get('/login', function (req, res) {
  var fwdHost = req.get('X-Forwarded-Host') || req.hostname;
  var redirectBase = 'https://' + fwdHost;
  var state = crypto.randomBytes(16).toString('hex');
  var params = new URLSearchParams({
    response_type: 'code', client_id: KC_CLIENT_ID,
    redirect_uri: redirectBase + '/callback',
    scope: 'openid profile email', state: state
  });
  res.cookie('auth_state', state, { httpOnly: true, maxAge: 300000, sameSite: 'lax' });
  res.redirect(KC_AUTH_URL + '?' + params);
});

/* -- Callback -- */
app.get('/callback', async function (req, res) {
  var code = req.query.code, state = req.query.state;
  if (!code || state !== (req.cookies && req.cookies.auth_state))
    return res.status(400).send('Invalid auth state');
  var fwdHost = req.get('X-Forwarded-Host') || req.hostname;
  var redirectBase = 'https://' + fwdHost;
  try {
    var resp = await fetch(KC_TOKEN_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'authorization_code', code: code,
        redirect_uri: redirectBase + '/callback',
        client_id: KC_CLIENT_ID, client_secret: KC_CLIENT_SECRET
      })
    });
    var tokens = await resp.json();
    if (!tokens.access_token)
      return res.status(400).send('Auth failed: no access token');
    res.cookie('access_token', tokens.access_token, {
      httpOnly: true, secure: false, sameSite: 'lax',
      maxAge: (tokens.expires_in || 3600) * 1000
    });
    res.clearCookie('auth_state');
    res.redirect('/dashboard');
  } catch (e) { console.error('Token error:', e.message); res.status(500).send('Auth failed'); }
});

/* -- Dashboard -- */
app.get('/dashboard', verifyToken, function (req, res) {
  var u = req.user;
  var roles = (u.realm_access && u.realm_access.roles) ? u.realm_access.roles.join(', ') : 'N/A';
  var title = getServiceName(req);
  var html = '<!DOCTYPE html><html lang="en"><head>'
    + '<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    + '<title>' + title + ' - Dashboard</title>'
    + '<style>'
    + '*{margin:0;padding:0;box-sizing:border-box}'
    + 'body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);min-height:100vh}'
    + '.hdr{background:rgba(255,255,255,.95);padding:16px 40px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 2px 10px rgba(0,0,0,.1)}'
    + '.hdr h1{margin:0;color:#1a1a2e;font-size:24px}.hdr h1 span{color:#e94560}'
    + '.user-info{display:flex;align-items:center;gap:16px}.user-info .user{color:#555;font-size:14px}'
    + '.user-info a{color:#e94560;text-decoration:none;font-size:14px}'
    + '.ctr{max-width:960px;margin:40px auto;padding:0 20px}'
    + '.wlcm{text-align:center;margin-bottom:40px}.wlcm h2{color:rgba(255,255,255,.9);font-size:32px;margin-bottom:8px}'
    + '.wlcm p{color:rgba(255,255,255,.6);font-size:16px}'
    + '.card{background:rgba(255,255,255,.95);border-radius:16px;padding:32px;margin-bottom:24px;box-shadow:0 8px 32px rgba(0,0,0,.2)}'
    + '.card h2{color:#1a1a2e;margin-top:0;padding-bottom:12px;border-bottom:2px solid #e94560;font-size:20px}'
    + '.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px}'
    + '.item{padding:16px;background:#f8f9fa;border-radius:10px}'
    + '.item label{display:block;font-size:11px;color:#888;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}'
    + '.item .v{font-size:16px;font-weight:600;color:#1a1a2e;word-break:break-all}'
    + '.btn{display:inline-block;padding:12px 24px;border-radius:10px;text-decoration:none;font-weight:600;font-size:14px;margin-right:10px;margin-bottom:10px;border:none;cursor:pointer}'
    + '.btn-primary{background:linear-gradient(135deg,#e94560,#c23152);color:white}'
    + '.btn-outline{background:transparent;color:#e94560;border:2px solid #e94560}'
    + '.btn:hover{opacity:.9}.actions{display:flex;gap:10px;flex-wrap:wrap}'
    + '.sdot{display:inline-block;width:10px;height:10px;border-radius:50%;background:#4caf50;margin-right:6px}'
    + 'footer{text-align:center;color:rgba(255,255,255,.4);padding:30px;font-size:13px}'
    + '</style></head><body>'
    + '<div class="hdr"><h1>' + title + '</h1>'
    + '<div class="user-info"><span class="user">&#x1F464; ' + (u.preferred_username || u.name || 'User') + '</span>'
    + '<a href="/logout">Logout</a></div></div>'
    + '<div class="ctr">'
    + '<div class="wlcm"><h2>Welcome to ' + title + '</h2>'
    + '<p>You are authenticated and ready to use the service.</p></div>'
    + '<div class="card"><h2><span class="sdot"></span>Service Status</h2><div class="grid">'
    + '<div class="item"><label>Service</label><div class="v">' + title + '</div></div>'
    + '<div class="item"><label>Status</label><div class="v"><span style="color:#4caf50">&#x25CF; Active</span></div></div>'
    + '<div class="item"><label>User</label><div class="v">' + (u.preferred_username || 'N/A') + '</div></div>'
    + '<div class="item"><label>Email</label><div class="v">' + (u.email || 'N/A') + '</div></div>'
    + '<div class="item"><label>Roles</label><div class="v">' + roles + '</div></div>'
    + '<div class="item"><label>Client</label><div class="v">' + KC_CLIENT_ID + '</div></div>'
    + '</div></div>';
  if (SERVICE_DESCRIPTION)
    html += '<div class="card"><h2>About</h2><p>' + SERVICE_DESCRIPTION + '</p></div>';
  html += '<div class="card"><h2>Actions</h2><div class="actions">'
    + '<a href="/login" class="btn btn-outline">Refresh Token</a>'
    + '<a href="/logout" class="btn btn-primary">Logout</a></div></div></div>'
    + '<footer>IaCGenie Platform — Secure Authenticated Access</footer></body></html>';
  res.send(html);
});

/* -- Logout -- */
app.get('/logout', function (req, res) {
  var fwdHost = req.get('X-Forwarded-Host') || req.hostname;
  var redirectBase = 'https://' + fwdHost;
  res.clearCookie('access_token');
  res.clearCookie('auth_state');
  res.redirect(KC_LOGOUT_URL + '?post_logout_redirect_uri=' + encodeURIComponent(redirectBase + '/login'));
});

/* -- Health -- */
app.get('/health', function (req, res) {
  res.json({ status: 'ok', service: SERVICE_NAME, title: SERVICE_TITLE });
});

/* -- Root -- */
app.get('/', function (req, res) { res.redirect('/login'); });

/* -- Proxy authenticated requests to backend service -- */
app.use('/proxied', verifyToken, function (req, res) {
  var targetPort = getBackendPort(req);
  var options = {
    hostname: '127.0.0.1',
    port: targetPort,
    path: req.path,
    method: req.method,
    headers: Object.assign({}, req.headers)
  };
  delete options.host;
  options.host = '127.0.0.1:' + targetPort;
  if (req.user) {
    options.headers['X-User-Name'] = req.user.preferred_username || '';
    options.headers['X-User-Email'] = req.user.email || '';
    options.headers['X-User-Roles'] = JSON.stringify(
      req.user.realm_access && req.user.realm_access.roles || []
    );
    options.headers['X-Forwarded-Auth'] = 'Bearer ' + req.cookies.access_token;
  }
  options.headers['X-Service-Name'] = SERVICE_NAME;
  var proxyReq = http.request(options, function (proxyRes) {
    res.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(res);
  });
  proxyReq.on('error', function (err) {
    console.error('Proxy error:', err.message);
    if (!res.headersSent) res.status(502).send('Backend service unavailable');
  });
  req.pipe(proxyReq);
});

app.listen(PORT, '0.0.0.0', function () {
  console.log(SERVICE_NAME + ' v2 listening on port ' + PORT);
  console.log('  Backends: ' + JSON.stringify(BACKENDS));
  console.log('  Domain map: ' + JSON.stringify(DOMAIN_BACKEND_MAP));
});
