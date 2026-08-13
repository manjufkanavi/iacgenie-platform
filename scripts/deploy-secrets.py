#!/usr/bin/env python3
"""Deploy OpenBao secrets → VM .env file"""
import subprocess, json, os
from datetime import datetime, timezone

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, shell=isinstance(cmd, str))
    return r.returncode, r.stdout, r.stderr

VM_SSH = ['ssh', '-i', os.path.expanduser('~/.ssh/newvm_key'), 'mkanavi@192.168.0.118', '-o', 'StrictHostKeyChecking=no']
TOKENS_DIR = "/home/mkanavi/docker/iacgenie/data/openbao_raft/service_tokens"

# 1. Get root token
_, root_token, _ = run(VM_SSH + ["python3 -c \"import json;print(json.load(open('/home/mkanavi/docker/iacgenie/data/openbao_raft/init_keys.json'))['root_token'])\""])
root_token = root_token.strip()

# 2. List all secrets
_, list_out, _ = run(VM_SSH + ["curl -sk -H 'X-Vault-Token: " + root_token + "' http://127.0.0.1:8200/v1/iacgenie/kv/metadata/?list=true"])
keys = json.loads(list_out).get('data', {}).get('keys', [])

# 3. Read all secrets
all_secrets = {}
for key in keys:
    _, out, _ = run(VM_SSH + ["curl -sk -H 'X-Vault-Token: " + root_token + "' http://127.0.0.1:8200/v1/iacgenie/kv/data/" + key])
    sdata = json.loads(out)
    vals = sdata.get('data', {}).get('data', {})
    service = key.upper()
    for k, v in vals.items():
        all_secrets[f"{service}_{k.upper()}"] = str(v)

print(f"Read {len(all_secrets)} secrets from OpenBao")

# 4. Generate .env
env_lines = [
    "# OpenBao-secrets-only environment",
    "# Deployed: " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    "",
    "OPENBAO_ADDR=http://127.0.0.1:8200",
    "OPENBAO_ROOT_TOKEN=" + all_secrets.get("IACGENIE_KV_OPENBAO_ROOT_TOKEN", ""),
    "",
    "# Service tokens",
    f"IACGENIE_SERVICE_TOKEN={all_secrets.get('IACGENIE_SERVICE_TOKEN', '')}",
    f"LIGHTSERP_TOKEN={all_secrets.get('LIGHTSERP_TOKEN', '')}",
    f"TERRAFORM_TOKEN={all_secrets.get('TERRAFORM_TOKEN', '')}",
    "",
    "# PostgreSQL",
    f"PG_ROOT_PASSWORD={all_secrets.get('POSTGRES_PASSWORD', '')}",
    f"POSTGRES_KC_PASSWORD={all_secrets.get('POSTGRES_KC_PASSWORD', '')}",
    f"POSTGRES_USERNAME={all_secrets.get('POSTGRES_USERNAME', '')}",
    f"POSTGRES_DATABASE={all_secrets.get('POSTGRES_DATABASE', '')}",
    "",
    "# Redis",
    f"REDIS_PASSWORD={all_secrets.get('REDIS_PASSWORD', '')}",
    "",
    "# MinIO",
    f"MINIO_ROOT_ACCESS_KEY={all_secrets.get('MINIO_ACCESS_KEY', '')}",
    f"MINIO_ROOT_PASSWORD={all_secrets.get('MINIO_SECRET_KEY', '')}",
    "",
    "# Keycloak",
    f"KEYCLOAK_ADMIN_PASSWORD={all_secrets.get('KEYCLOAK_ADMIN_PASSWORD', '')}",
    f"KEYCLOAK_ADMIN_USER={all_secrets.get('KEYCLOAK_ADMIN_USER', '')}",
    "",
    "# JWT",
    f"JWT_SECRET={all_secrets.get('JWT_SECRET', '')}",
    "",
    "# LightSerp",
    f"LIGHTSERP_API_SECRET={all_secrets.get('LIGHTSERP_API_SECRET', '')}",
    "",
    "# Cloudflare",
    f"CLOUDFLARE_TUNNEL_TOKEN={all_secrets.get('CLOUDFLARE_TUNNEL_TOKEN', '')}",
    "",
    "# SearXNG",
    f"SEARXNG_SECRET={all_secrets.get('SEARXNG_SECRET_KEY', '')}",
    "",
    "# Grafana",
    f"GRAFANA_ADMIN_PASSWORD={all_secrets.get('GRAFANA_ADMIN_PASSWORD', '')}",
    f"GRAFANA_ADMIN_USER={all_secrets.get('GRAFANA_ADMIN_USER', '')}",
    "",
    "# Jenkins",
    f"JENKINS_ADMIN_PASSWORD={all_secrets.get('JENKINS_ADMIN_PASSWORD', '')}",
    f"JENKINS_ADMIN_USER={all_secrets.get('JENKINS_ADMIN_USER', '')}",
    "",
    "# GitHub OAuth",
    f"GITHUB_CLIENT_ID={all_secrets.get('GH_OAUTH_CLIENT_ID', '')}",
    f"GITHUB_CLIENT_SECRET={all_secrets.get('GH_OAUTH_CLIENT_SECRET', '')}",
    "",
    "# Google OAuth",
    f"GOOGLE_CLIENT_SECRET={all_secrets.get('GOOGLE_OAUTH_CLIENT_SECRET', '')}",
    "",
    "# External API keys",
    f"GEMINI_API_KEY={all_secrets.get('GEMINI_API_KEY', '')}",
    f"OPENAI_API_KEY={all_secrets.get('OPENAI_API_KEY', '')}",
    "",
    "# SMTP",
    f"SMTP_ADDR={all_secrets.get('SMTP_HOST', '')}",
    f"SMTP_PORT={all_secrets.get('SMTP_PORT', '')}",
    f"SMTP_USER={all_secrets.get('SMTP_USERNAME', '')}",
    f"SMTP_PASS={all_secrets.get('SMTP_PASSWORD', '')}",
    f"SMTP_FROM={all_secrets.get('SMTP_FROM_ADDRESS', '')}",
    "",
    "# Vite",
    f"VITE_API_BASE_URL={all_secrets.get('VITE_API_BASE_URL', '')}",
    f"VITE_FRONTEND_URL={all_secrets.get('VITE_FRONTEND_URL', '')}",
]

env_content = '\n'.join(env_lines) + '\n'
tmp_env = "/tmp/github_secrets.env"
with open(tmp_env, 'w') as f:
    f.write(env_content)

# 5. Deploy to VM
print("\nDeploying .env to VM...")
subprocess.run(['scp', '-i', os.path.expanduser('~/.ssh/newvm_key'), '-o', 'StrictHostKeyChecking=no', tmp_env, 'mkanavi@192.168.0.118:/home/mkanavi/docker/iacgenie/.env'])
subprocess.run(VM_SSH + ['chmod 600 /home/mkanavi/docker/iacgenie/.env'])
print("  ✓ .env deployed")

# 6. Deploy service tokens
for svc_name, env_var in [("iacgenie-service", "IACGENIE_SERVICE_TOKEN"), ("lightserp", "LIGHTSERP_TOKEN"), ("terraform", "TERRAFORM_TOKEN")]:
    token = all_secrets.get(env_var, "")
    if token:
        subprocess.run(VM_SSH + [f"echo '{token}' > {TOKENS_DIR}/{svc_name}.token && chmod 600 {TOKENS_DIR}/{svc_name}.token"])
        print(f"  ✓ {svc_name} token")

print(f"\n✓ Done: {len(all_secrets)} secrets deployed to VM")
