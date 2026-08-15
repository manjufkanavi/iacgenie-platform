#!/usr/bin/env python3
"""
OpenBao Secret Injector — Docker entrypoint wrapper.

Authenticates to OpenBao via AppRole, fetches secrets from KV v2,
injects them as environment variables, then exec's the main process.

Usage:
    openbao-injector.sh <service-name> -- <command> [args...]

The service config is loaded from /etc/openbao-config/<service_name>.json.

Config file format:
    {
        "secret_paths": {
            "env_var_name": "vault_path/to/secret"
        },
        "openbao_addr": "http://openbao:8200",
        "approle_role_id_path": "/var/run/approle/role_id",
        "approle_secret_id_path": "/var/run/approle/secret_id",
        "timeout": 30
    }

Environment variables can override OpenBao settings:
    OPENBAO_ADDR - OpenBao address (default: from config)
    OPENBAO_ROLE_ID - AppRole role ID
    OPENBAO_SECRET_ID - AppRole secret ID
"""

import json, os, sys, subprocess, ssl, urllib.request, urllib.error, time, signal

def log(msg):
    print(f"[openbao-injector] {msg}", flush=True)

def load_config(service_name):
    """Load service config from /etc/openbao-config/<name>.json"""
    config_path = f"/etc/openbao-config/{service_name}.json"
    if not os.path.exists(config_path):
        log(f"ERROR: Config not found at {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        config = json.load(f)

    # Defaults
    config.setdefault("openbao_addr", "https://127.0.0.1:8200")
    config.setdefault("approle_role_id_path", "/var/run/approle/role_id")
    config.setdefault("approle_secret_id_path", "/var/run/approle/secret_id")
    config.setdefault("timeout", 30)
    config.setdefault("retry_attempts", 3)
    config.setdefault("retry_delay", 2)

    return config

def read_file(path):
    """Read a file, return stripped content."""
    with open(path) as f:
        return f.read().strip()

def get_role_id_and_secret_id(config):
    """Get AppRole credentials from config paths or env vars."""
    role_id = os.environ.get("OPENBAO_ROLE_ID")
    secret_id = os.environ.get("OPENBAO_SECRET_ID")

    # Try individual path files if configured
    rid_path = config.get("approle_role_id_path")
    sid_path = config.get("approle_secret_id_path")
    if rid_path and not role_id and os.path.exists(rid_path):
        role_id = read_file(rid_path)
    if sid_path and not secret_id and os.path.exists(sid_path):
        secret_id = read_file(sid_path)

    # Fallback: read from shared credential file
    if not role_id or not secret_id:
        cred_file = config.get("approle_cred_file", "/var/run/approle/default-creds.txt")
        if os.path.exists(cred_file):
            lines = read_file(cred_file).splitlines()
            if len(lines) >= 2:
                if not role_id:
                    role_id = lines[0].strip()
                if not secret_id:
                    secret_id = lines[1].strip()

    if not role_id or not secret_id:
        log("ERROR: AppRole role_id or secret_id not available")
        log(f"  role_id_path: {config['approle_role_id_path']} (exists: {os.path.exists(config['approle_role_id_path'])})")
        log(f"  secret_id_path: {config['approle_secret_id_path']} (exists: {os.path.exists(config['approle_secret_id_path'])})")
        cred_file = f"/var/run/approle/{service_name}-creds.txt"
        log(f"  shared creds: {cred_file} (exists: {os.path.exists(cred_file)})")
        sys.exit(1)

    return role_id, secret_id

def api_request(base_url, path, data=None, token=None, ssl_ctx=None):
    """Make an API request to OpenBao."""
    url = f"{base_url}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Vault-Token"] = token

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method="POST" if data else "GET")

    # Use default SSL context (validates against system CA bundle)
    ctx = ssl_ctx if ssl_ctx else ssl.create_default_context()
    resp = urllib.request.urlopen(req, timeout=config["timeout"], context=ctx)
    raw = resp.read()
    if raw:
        return json.loads(raw)
    return {"success": True}

def auth_approle(role_id, secret_id, addr, ssl_ctx=None):
    """Authenticate using AppRole, return client token."""
    result = api_request(addr, "/v1/auth/approle/login", {
        "role_id": role_id,
        "secret_id": secret_id
    }, ssl_ctx=ssl_ctx)
    token = result.get("auth", {}).get("client_token")
    if not token:
        log(f"ERROR: Failed to get token from AppRole login: {json.dumps(result)[:200]}")
        sys.exit(1)
    return token

def fetch_secret(addr, token, path, ssl_ctx=None):
    """Fetch a secret from KV v2."""
    result = api_request(addr, f"/v1/{path}", token=token, ssl_ctx=ssl_ctx)
    if not isinstance(result, dict):
        raise ValueError(f"Unexpected response type: {type(result)}")
    data = result.get("data", {}).get("data", {})
    return data

def inject_secrets(token, secret_paths, addr, ssl_ctx=None):
    """Fetch and inject secrets as environment variables."""
    for env_var, vault_path in secret_paths.items():
        if env_var in os.environ:
            # Already set (fallback), but let's overwrite with OpenBao value
            pass

        try:
            secrets = fetch_secret(addr, token, vault_path, ssl_ctx)
            if env_var in secrets:
                os.environ[env_var] = secrets[env_var]
                log(f"  ✓ {env_var} injected from {vault_path}")
            else:
                available_keys = list(secrets.keys())
                log(f"  ⚠ {env_var} not found in {vault_path} (available: {available_keys[:5]})")
        except Exception as e:
            log(f"  ✗ Failed to fetch {vault_path}: {e}")
            # Use existing env var as fallback
            if env_var in os.environ:
                log(f"    Using fallback from existing env var")

def main():
    global config

    if len(sys.argv) < 2:
        print("Usage: openbao-injector <service-name> -- <command> [args...]", file=sys.stderr)
        sys.exit(1)

    service_name = sys.argv[1]
    # Find -- separator
    cmd_start = None
    for i, arg in enumerate(sys.argv):
        if arg == "--" and i > 1:
            cmd_start = i + 1
            break

    if cmd_start is None:
        print("ERROR: Missing '--' separator. Usage: openbao-injector <service-name> -- <command>", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[cmd_start:]
    if not cmd:
        print("ERROR: No command specified after '--'", file=sys.stderr)
        sys.exit(1)

    # Load config
    config = load_config(service_name)
    # Use default SSL context (validates against system CA bundle)
    ssl_ctx = ssl.create_default_context()

    # Force HTTPS for all connections (OpenBao runs with TLS)
    addr = config["openbao_addr"]
    if addr.startswith("http://"):
        addr = addr.replace("http://", "https://", 1)
        log(f"Upgraded to HTTPS: {addr}")
    log(f"Service: {service_name}")
    log(f"OpenBao: {addr}")
    log(f"Secrets to inject: {len(config['secret_paths'])}")

    # Authenticate with retries
    token = None
    for attempt in range(config["retry_attempts"]):
        try:
            role_id, secret_id = get_role_id_and_secret_id(config)
            token = auth_approle(role_id, secret_id, addr, ssl_ctx)
            log("AppRole authentication: SUCCESS")
            break
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            log(f"Auth attempt {attempt + 1}/{config['retry_attempts']} failed: HTTP {e.code}")
            if attempt < config["retry_attempts"] - 1:
                time.sleep(config["retry_delay"])
        except Exception as e:
            log(f"Auth attempt {attempt + 1}/{config['retry_attempts']} failed: {e}")
            if attempt < config["retry_attempts"] - 1:
                time.sleep(config["retry_delay"])

    if not token:
        log("ERROR: All authentication attempts failed. No AppRole credentials available.")
        log("Service will use existing environment variables (no OpenBao injection).")

    # Inject secrets
    if token:
        inject_secrets(token, config["secret_paths"], addr, ssl_ctx)
    else:
        log("Skipping secret injection (no token available, using existing env vars)")

    log(f"Injecting {len(config['secret_paths'])} secrets from OpenBao...")
    log("Running: " + " ".join(cmd))
    log("---")

    # Exec the main command (replaces the injector process)
    env = {**os.environ}
    result = subprocess.run(cmd, env=env)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
