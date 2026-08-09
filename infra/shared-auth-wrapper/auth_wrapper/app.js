const express = require('express');
const session = require('express-session');
const jwt = require('jsonwebtoken');
const crypto = require('crypto');
const fetch = require('node-fetch');

const app = express();
const PORT = process.env.PORT || 9090;
const KC_URL = process.env.KEYCLOAK_URL || 'http://127.0.0.1:8083';
const KC_REALM = process.env.KEYCLOAK_REALM || 'iacgenie';
const KC_CLIENT_ID = process.env.KEYCLOAK_CLIENT_ID || 'auth-wrapper';
const KC_CLIENT_SECRET = process.env.KEYCLOAK_CLIENT_SECRET || '';
const SESSION_SECRET = process.env.SESSION_SECRET || 'iacgen...t';
const DASHBOARD_URL_BASE = process.env.DASHBOARD_URL_BASE || 'https://auth.iacgenie.com';
const SERVICE_NAME = process.env.SERVICE_NAME || 'Auth-Wrapper';
const KC_AUTH_URL = KC_URL + '/realms/' + KC_REALM + '/protocol/openid-connect/auth';
const KC_TOKEN_URL = KC_URL + '/realms/' + KC_REALM + '/protocol/openid-connect/token';

function verifyToken(req, res, next) {
  const token = req.cookies && req.cookies.access_token;
  if (!token) return res.redirect('/login');
  try {
    const d = jwt.decode(token);
    if (!d || d.exp * 1000 < Date.now()) return res.redirect('/login');
    req.user = d;
    next();
  } catch (e) { res.redirect('/login'); }
}

app.use(session({
  secret: SESSION_SECRET,
  resave: false,
  saveUninitialized: true,
  cookie: { httpOnly: true, secure: false, maxAge: 300000 }
}));

app.get('/login', (req, res) => {
  const state = crypto.randomBytes(16).toString('hex');
  const params = new URLSearchParams({
    response_type: 'code',
    client_id: KC_CLIENT_ID,
    redirect_uri: DASHBOARD_URL_BASE + '/callback',
    scope: 'openid profile email',
    state: state
  });
  res.cookie('auth_state', state, { httpOnly: true, maxAge: 300000 });
  res.redirect(KC_AUTH_URL + '?' + params);
});

app.get('/callback', async (req, res) => {
  const code = req.query.code;
  const state = req.query.state;
  if (!code || state !== (req.cookies && req.cookies.auth_state)) {
    return res.status(400).send('Invalid state');
  }
  try {
    const resp = await fetch(KC_TOKEN_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        code: code,
        redirect_uri: DASHBOARD_URL_BASE + '/callback',
        client_id: KC_CLIENT_ID,
        client_secret: KC_CLIENT_SECRET
      })
    });
    const tokens = await resp.json();
    if (!tokens.access_token) return res.status(400).send('Auth failed');
    res.cookie('access_token', tokens.access_token, {
      httpOnly: true, secure: true, sameSite: 'lax',
      maxAge: (tokens.expires_in || 3600) * 1000
    });
    res.redirect('/dashboard');
  } catch (e) {
    console.error('Token error:', e.message);
    res.status(500).send('Auth failed');
  }
});

app.get('/dashboard', verifyToken, (req, res) => {
  const u = req.user;
  const roles = (u.realm_access && u.realm_access.roles) ? u.realm_access.roles.join(', ') : 'N/A';
  res.send('<!DOCTYPE html><html><head><title>' + SERVICE_NAME + ' - Dashboard</title>' +
    '<style>body{font-family:sans-serif;margin:40px;background:#f5f5f5}' +
    '.card{background:#fff;border-radius:8px;padding:30px;max-width:600px;margin:0 auto;box-shadow:0 2px 10px rgba(0,0,0,.1)}' +
    'h1{color:#333}.field{padding:8px 0;border-bottom:1px solid #eee}' +
    'label{font-weight:bold;color:#666;display:inline-block;width:120px}' +
    'a{color:#007bff;margin-right:15px}</style></head><body>' +
    '<div class="card"><h1>' + SERVICE_NAME + ' Dashboard</h1>' +
    '<div class="field"><label>User:</label>' + (u.preferred_username || 'N/A') + '</div>' +
    '<div class="field"><label>Email:</label>' + (u.email || 'N/A') + '</div>' +
    '<div class="field"><label>Roles:</label>' + roles + '</div>' +
    '<div style="margin-top:20px"><a href="/login">Refresh</a> | <a href="/logout">Logout</a></div></div></body></html>');
});

app.get('/logout', (req, res) => {
  res.clearCookie('access_token');
  res.clearCookie('auth_state');
  res.redirect(KC_URL + '/realms/' + KC_REALM + '/protocol/openid-connect/logout?post_logout_redirect_uri=' + DASHBOARD_URL_BASE + '/login');
});

app.get('/health', (req, res) => res.json({ status: 'ok', service: SERVICE_NAME }));
app.get('/', (req, res) => res.redirect('/login'));

app.listen(PORT, '0.0.0.0', () => {
  console.log(SERVICE_NAME + ' listening on port ' + PORT);
});
