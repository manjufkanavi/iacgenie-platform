#!/usr/bin/env python3
# =============================================================================
# OpenBao Secret Consistency Checker
# =============================================================================
# Validates that:
#   1. All service .env files have the same values as OpenBao KV
#   2. Detects credential drift between infrastructure code and OpenBao
#   3. Reports mismatches and optional auto-fix
#
# Usage: python3 openbao-consistency-check.py [--fix]
# =============================================================================

import os, sys, subprocess, json, argparse, urllib.request, urllib.error, ssl

OPENBAO_ADDR = os.getenv("OPENBAO_ADDR", "http://127.0.0.1:8200")
TOKEN = os.getenv("OPENBAO_TOKEN", os.getenv("OPENBAO_ROOT_TOKEN", ""))
ENV_FILE = os.getenv("ENV_FILE", "/home/mkanavi/docker/iacgenie/.env")
VAULT_MOUNT = "iacgenie/kv"

if not TOKEN:
    print("ERROR: OPENBAO_TOKEN or OPENBAO_ROOT_TOKEN not set")
    sys.exit(1)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# ── OpenBao helpers ──────────────────────────────────────────────────────────

def openbao_get(mount, path):
    url = f"{OPENBAO_ADDR}/v1/{mount}/data/{path}"
    req = urllib.request.Request(url, headers={"X-Vault-Token": TOKEN})
    try:
        r = urllib.request.urlopen(req, context=ctx, timeout=10)
        data = json.loads(r.read())
        return data.get("data", {}).get("data", {})
    except urllib.error.HTTPError as e:
        print(f"  OPENBAO ERR {e.code}: {e.read().decode()[:100]}")
        return {}

# ── .env loader ──────────────────────────────────────────────────────────────

def load_env(path):
    env = {}
    if not os.path.exists(path):
        print(f"  WARNING: {path} not found")
        return env
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

# ── Mapping: service .env key → OpenBao mount/path/key ───────────────────────

SECRETS_MAP = {
    # Service → (env_key, openbao_mount, openbao_path, openbao_key)
    "POSTGRES_APP_PASSWORD": ("iacgenie/kv", "postgres", "password"),
    "PG_ROOT_PASSWORD":      ("iacgenie/kv", "postgres", "password"),
    "REDIS_PASSWORD":        ("iacgenie/kv", "redis", "password"),
    "MINIO_ROOT_PASSWORD":   ("iacgenie/kv", "minio", "secret_key"),
    "GITEA_ADMIN_PASSWORD":  ("iacgenie/kv", "gitea", "admin_password"),
    "KEYCLOAK_ADMIN_PASSWORD": ("iacgenie/kv", "keycloak", "admin_password"),
    "KC_DB_PASSWORD":        ("iacgenie/kv", "keycloak_db", "password"),
    "LIGHTSERP_API_SECRET":  ("iacgenie/kv", "lightserp", "api_secret"),
    "LIGHTSERP_KEYCLOAK_CLIENT_SECRET": ("iacgenie/kv", "lightserp", "keycloak_client_secret"),
    "SEARXNG_SECRET_KEY":    ("iacgenie/kv", "searxng", "secret_key"),
    "JWT_SECRET":            ("iacgenie/kv", "nginx", "jwt_secret"),
    "NSQD_AUTH_TOKEN":       ("iacgenie/kv", "nsqd", "auth_token"),
    "PAGEZEN_API_SECRET":    ("iacgenie/kv", "pagezen", "api_secret"),
    "TERRAFORM_API_KEY":     ("iacgenie/kv", "terraform", "api_key"),
}

# ── Consistency check ───────────────────────────────────────────────────────

def check_consistency(fix=False):
    env = load_env(ENV_FILE)
    if not env:
        print("ERROR: Could not load .env file")
        sys.exit(1)

    results = {"match": 0, "mismatch": 0, "missing_in_env": 0, "missing_in_vault": 0}

    print(f"\n{'ENV Key':<40} {'Status':<10} {'Source'}")
    print("-" * 90)

    for env_key, (vault_mount, vault_path, vault_key) in SECRETS_MAP.items():
        env_val = env.get(env_key, "")
        if not env_val:
            print(f"  {env_key:<40} {'MISSING':<10} .env")
            results["missing_in_env"] += 1
            continue

        vault_data = openbao_get(vault_mount, vault_path)
        if not vault_data:
            print(f"  {env_key:<40} {'MISSING':<10} OpenBao")
            results["missing_in_vault"] += 1
            continue

        vault_val = vault_data.get(vault_key, "")
        if env_val == vault_val:
            results["match"] += 1
            short_env = env_val[:8] + "…" + env_val[-4:] if len(env_val) > 12 else env_val
            print(f"  {env_key:<40} {'MATCH':<10} {short_env}")
        else:
            results["mismatch"] += 1
            short_env = env_val[:8] + "…" + env_val[-4:] if len(env_val) > 12 else env_val
            short_vault = vault_val[:8] + "…" + vault_val[-4:] if len(vault_val) > 12 else vault_val
            if fix:
                print(f"  {env_key:<40} {'MISMATCH':<10} .env={short_env} → OpenBao={short_vault} [FIXED]")
                # Update OpenBao with .env value
                url = f"{OPENBAO_ADDR}/v1/{vault_mount}/data/{vault_path}"
                payload = json.dumps({"data": {vault_key: env_val}}).encode()
                req = urllib.request.Request(url, data=payload,
                    headers={"X-Vault-Token": TOKEN, "Content-Type": "application/json"},
                    method="POST")
                urllib.request.urlopen(req, context=ctx, timeout=10)
            else:
                print(f"  {env_key:<40} {'MISMATCH':<10} .env={short_env} ≠ OpenBao={short_vault}")

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print(f"  Summary: {results['match']} match, {results['mismatch']} mismatch, "
          f"{results['missing_in_env']} missing in .env, "
          f"{results['missing_in_vault']} missing in OpenBao")
    print("=" * 90)

    return results["mismatch"] == 0 and results["missing_in_env"] == 0 and results["missing_in_vault"] == 0

# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check consistency between .env and OpenBao secrets")
    parser.add_argument("--fix", action="store_true", help="Auto-fix mismatches by updating OpenBao with .env values")
    args = parser.parse_args()

    ok = check_consistency(fix=args.fix)
    sys.exit(0 if ok else 1)
