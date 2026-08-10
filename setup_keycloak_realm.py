#!/usr/bin/env python3
"""Setup Keycloak iacgenie realm and OIDC clients using host-side curl."""
import json, hashlib, subprocess, sys

# Read the token from the kcadm config
with open('/tmp/kc_config_host.json') as f:
    config = json.load(f)

# Get the first valid token
endpoints = config.get('endpoints', {})
token = None
for endpoint_key, endpoint_data in endpoints.items():
    for realm_key, realm_data in endpoint_data.items():
        t = realm_data.get('token')
        if t and t != 'eyJhbG...' and len(t) > 100:
            token = t
            break
    if token:
        break

if not token:
    print("ERROR: Could not find a valid admin token in kcadm.config")
    sys.exit(1)

print(f"Token: {token[:40]}... ({len(token)} chars)")

KC_ADMIN = "http://127.0.0.1:8083"
REALM_NAME = "iacgenie"

def api(method, path, data=None):
    """Make API call to Keycloak Admin REST API"""
    cmd = ['curl', '-s', '-X', method, f'{KC_ADMIN}{path}']
    cmd.extend(['-H', f'Authorization: Bearer {token}'])
    cmd.append('-H', 'Content-Type: application/json')
    if data:
        cmd.extend(['-d', json.dumps(data)])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print(f"  [ERR] HTTP error: {result.stderr[:200]}")
            return None
        if not result.stdout.strip():
            return None
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        print("  [ERR] Timeout")
        return None
    except json.JSONDecodeError as e:
        print(f"  [ERR] JSON parse error: {e}")
        return None

def api_post(method, path, data):
    """Post with JSON body"""
    cmd = ['curl', '-s', '-X', method, f'{KC_ADMIN}{path}',
           '-H', f'Authorization: Bearer ***           '-H', 'Content-Type: application/json']
    if data:
        cmd.extend(['-d', json.dumps(data)])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print(f"  [ERR] HTTP {result.returncode}: {result.stderr[:200]}")
            return None
        if not result.stdout.strip():
            return None
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        print("  [ERR] Timeout")
        return None
    except json.JSONDecodeError as e:
        print(f"  [ERR] JSON parse error: {e}")
        return None

def log(m): print(f"  [OK] {m}")
def warn(m): print(f"  [WARN] {m}")

# === Step 1: Create Realm ===
print("\n=== Step 1: Create Realm ===")

# Check if realm exists
realms = api('GET', '/admin/realms')
if realms:
    for r in realms:
        if r.get('realm') == REALM_NAME:
            realm_id = r['id']
            log(f"Realm '{REALM_NAME}' exists (id: {realm_id})")
            break
    else:
        # Create realm
        realm_data = {
            "name": REALM_NAME, "enabled": True,
            "displayName": "IacGenie Platform",
            "accessTokenLifespan": 3600,
            "ssoSessionIdleTimeout": 43200,
            "ssoSessionMaxLifespan": 43200,
            "sslRequired": "external",
            "registrationAllowed": False,
            "registrationEmailAsUsername": True,
            "passwordPolicy": "length=12 and notUsername and specialCharacters=2",
            "loginWithEmailAllowed": True,
            "resetPasswordAllowed": True,
            "eventsEnabled": True, "adminEventsEnabled": True
        }
        result = api_post('POST', '/admin/realms', realm_data)
        if result:
            realm_id = result.get('id')
            log(f"Created realm '{REALM_NAME}' (id: {realm_id})")
        else:
            print("Failed to create realm. Trying alternate endpoint...")
            # Try /realms endpoint directly
            result2 = api_post('POST', '/realms', realm_data)
            if result2:
                realm_id = result2.get('id')
                log(f"Created realm '{REALM_NAME}' via /realms (id: {realm_id})")
            else:
                print("FAILED: Could not create realm")
                sys.exit(1)
else:
    print("ERROR: Could not list realms")
    sys.exit(1)

# === Step 2: Create Admin User ===
print("\n=== Step 2: Create Admin User ===")

users = api('GET', f'/admin/realms/{REALM_NAME}/users?username=admin')
if users and len(users) > 0:
    user_id = users[0]['id']
    log(f"Admin user exists (id: {user_id})")
else:
    user_data = {
        "username": "admin", "email": "admin@iacgenie.com",
        "firstName": "Platform", "lastName": "Admin",
        "emailVerified": True, "enabled": True,
        "credentials": [{"type": "password", "value": "IacGenie@2026!Admin", "temporary": False}]
    }
    # Create user - curl returns location header with user ID
    cmd = ['curl', '-s', '-X', 'POST', f'{KC_ADMIN}/admin/realms/{REALM_NAME}/users',
           '-H', f'Authorization: Bearer {token}',
           '-H', 'Content-Type: application/json',
           '-w', '\n%{http_code}',
           '-d', json.dumps(user_data)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    http_code = result.stdout.strip().split('\n')[-1]
    if http_code == '201':
        location = result.stderr.split('\n')[-2] if 'Location' in result.stderr else ''
        user_id = location.rstrip('/').split('/')[-1] if location else 'unknown'
        log(f"Created admin user (id: {user_id})")
    else:
        print(f"  HTTP {http_code}: {result.stdout[:200]}")
        # Try the alternate API
        cmd = ['curl', '-s', '-X', 'POST', f'{KC_ADMIN}/admin/realms/{REALM_NAME}/users',
               '-H', f'Authorization: Bearer {token}',
               '-H', 'Content-Type: application/json',
               '-d', json.dumps(user_data)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        print(f"  Response: {result.stdout[:200]}")
        user_id = "unknown"

# Reset password
cmd = ['curl', '-s', '-X', 'PUT', f'{KC_ADMIN}/admin/realms/{REALM_NAME}/users/{user_id}/reset-password',
       '-H', f'Authorization: Bearer {token}',
       '-H', 'Content-Type: application/json',
       '-d', json.dumps({"type":"password","value":"IacGenie@2026!Admin","temporary":False})]
result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
if result.returncode == 0:
    log("Admin password set: IacGenie@2026!Admin")

# === Step 3: Create OIDC Clients ===
print("\n=== Step 3: Create OIDC Clients ===")

CLIENTS = [
    ("admin-service", "IacGenie Admin Service", "Admin gateway",
     ["https://auth.iacgenie.com/*","https://gitea.iacgenie.com/*","https://vault.iacgenie.com/*"],
     "admin-svc-secret-" + hashlib.sha256(b"admin-service").hexdigest()[:16]),
    ("auth-wrapper", "Shared Auth Wrapper", "Centralized auth wrapper",
     ["https://clamav.iacgenie.com/*","https://crowdsec.iacgenie.com/*","https://pagegen.iacgenie.com/*"],
     "auth-wr-secret-" + hashlib.sha256(b"auth-wrapper").hexdigest()[:16]),
    ("clamav-wrapper", "ClamAV Dashboard", "ClamAV antivirus dashboard",
     ["https://clamav.iacgenie.com/*","https://auth.iacgenie.com/*"],
     "clamav-secret-" + hashlib.sha256(b"clamav-wrapper").hexdigest()[:16]),
    ("crowdsec-wrapper", "CrowdSec Dashboard", "CrowdSec security dashboard",
     ["https://crowdsec.iacgenie.com/*","https://auth.iacgenie.com/*"],
     "crowdsec-secret-" + hashlib.sha256(b"crowdsec-wrapper").hexdigest()[:16]),
    ("pagegen-wrapper", "PageGen Dashboard", "PageGen documentation dashboard",
     ["https://pagegen.iacgenie.com/*","https://auth.iacgenie.com/*"],
     "pagegen-secret-" + hashlib.sha256(b"pagegen-wrapper").hexdigest()[:16]),
    ("gitea", "Gitea Git Service", "Gitea Git service OIDC",
     ["https://gitea.iacgenie.com/user/oauth2/gitea"],
     "gitea-secret-" + hashlib.sha256(b"gitea").hexdigest()[:16]),
]

client_map = {}
for cid, name, desc, redirs, secret in CLIENTS:
    print(f"\n  Client: {cid}")
    # Check existing
    existing = api('GET', f'/admin/realms/{REALM_NAME}/clients?clientId={cid}')
    if existing and len(existing) > 0:
        log(f"Client '{cid}' exists (id: {existing[0]['id']})")
        client_map[cid] = existing[0]['id']
        continue
    
    cdata = {
        "clientId": cid, "name": name, "description": desc,
        "enabled": True, "clientAuthenticatorType": "client-secret",
        "redirectUris": redirs, "webOrigins": ["+"],
        "protocol": "openid-connect", "standardFlowEnabled": True,
        "implicitFlowEnabled": False, "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": False, "publicClient": False,
        "frontchannelLogout": True, "consentRequired": False,
        "clientSecret": secret,
        "attributes": {"oauth2.device.authorization.grant.enabled": "false",
                       "pkce.code.challenge.method.s256": "true"},
        "access": {"view":True,"configure":True,"manage":True,"roleMapping":True}
    }
    
    result = api_post('POST', f'/admin/realms/{REALM_NAME}/clients', cdata)
    if result:
        uid = result.get('id', cid)
        log(f"Created '{cid}' (id: {uid})")
        client_map[cid] = uid
    else:
        # Fallback: try with redirectUris as string array
        cdata2 = dict(cdata)
        cdata2["redirectUris"] = ','.join(redirs)
        result2 = api_post('POST', f'/admin/realms/{REALM_NAME}/clients', cdata2)
        if result2:
            uid = result2.get('id', cid)
            log(f"Created '{cid}' with string redirectUris (id: {uid})")
            client_map[cid] = uid

# === Summary ===
print("\n" + "="*60)
print("KEYCLOAK SETUP COMPLETE")
print("="*60)
print(f"URL:     http://127.0.0.1:8083")
print(f"Realm:   {REALM_NAME}")
print(f"Admin:   admin / IacGenie@2026!Admin")
print("\nClients & Secrets:")
for cid, _, _, _, secret in CLIENTS:
    if cid in client_map:
        print(f"  {cid}: {secret}")
print("="*60)
