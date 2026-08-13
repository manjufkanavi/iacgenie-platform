#!/usr/bin/env python3
"""
Fetch all secrets from OpenBao KV and write unified .env file.
Designed to run on the VM (192.168.0.118) where OpenBao is running.
"""
import json
import os
import subprocess
import sys

VAULT_ADDR = "http://127.0.0.1:8200"
ROOT_TOKEN_PATH = "/home/mkanavi/docker/iacgenie/data/openbao_raft/init_keys.json"
ENV_DEST = "/home/mkanavi/docker/iacgenie/.env"

def slurp(path):
    with open(path) as f:
        return json.load(f)

def openbao_get(path, token):
    r = subprocess.run(
        ['curl', '-sk', '-w', '\n%{http_code}',
         '-H', f'X-Vault-Token: {token}',
         f'{VAULT_ADDR}/v1/{path}'],
        capture_output=True, text=True
    )
    lines = r.stdout.strip().split('\n')
    code = int(lines[-1])
    body = '\n'.join(lines[:-1])
    return code, json.loads(body) if body else {}

def main():
    # 1. Read root token
    keys = slurp(ROOT_TOKEN_PATH)
    root = keys['root_token']
    print(f"Got root token (len={len(root)})", file=sys.stderr)

    # 2. List secrets
    code, data = openbao_get('iacgenie/kv/metadata/?list=true', root)
    if code != 200:
        print(f"ERROR: Could not list OpenBao KV secrets (HTTP {code})", file=sys.stderr)
        sys.exit(1)

    kv_keys = data.get('data', {}).get('keys', [])
    print(f"Found {len(kv_keys)} secret keys in OpenBao", file=sys.stderr)

    # 3. Read all secrets
    all_secrets = {}
    for k in kv_keys:
        code, data = openbao_get(f'iacgenie/kv/data/{k}', root)
        if code == 200:
            vals = data.get('data', {}).get('data', {})
            for vk, vv in vals.items():
                all_secrets[f"{k}_{vk}".upper()] = str(vv)

    print(f"Read {len(all_secrets)} individual values from OpenBao", file=sys.stderr)

    # 4. Map to unified .env var names
    # Use the stored key names directly if they match, otherwise map
    env = {
        'OPENBAO_ADDR': VAULT_ADDR,
    }

    for k, v in all_secrets.items():
        env[k] = v

    # Ensure required env vars exist (some may be duplicates from KV, some computed)
    # PostgreSQL defaults
    if 'POSTGRES_USER' not in env:
        env['POSTGRES_USER'] = 'iacgenie_pg'
    if 'POSTGRES_DB' not in env:
        env['POSTGRES_DB'] = 'iacgenie'

    # LightSerp database URL
    pg_user = env.get('POSTGRES_USER', 'iacgenie_pg')
    pg_db = env.get('POSTGRES_DB', 'iacgenie')
    if 'LIGHTSERP_DATABASE_URL' not in env:
        env['LIGHTSERP_DATABASE_URL'] = f'postgresql://{pg_user}:***@postgres:5432/{pg_db}'

    # 5. Write .env
    output = f"""# OpenBao-secrets-only environment
# Deployed by Ansible fetch-openbao-env.py
# NO hardcoded passwords — all values from OpenBao KV
# Source: {VAULT_ADDR}
# Secrets count: {len(env)}
"""
    for k in sorted(env.keys()):
        output += f'{k}={env[k]}\n'

    with open(ENV_DEST, 'w') as f:
        f.write(output)
    os.chmod(ENV_DEST, 0o600)

    print(f"Written {len(env)} vars to {ENV_DEST}")

if __name__ == '__main__':
    main()
