#!/usr/bin/env python3
"""
seed_openbao_kv.py — Store secrets in OpenBao KV v2.
Runs on the VM host (not inside Docker), uses curl to talk to OpenBao API.
Reads .env file and writes secrets to two path sets:
1. iacgenie/data/config/...  (for openbao_injector.py)
2. iacgenie/kv/data/...       (for fetch-openbao-env.py)
3. lightserp/data/config/...  (for lightserp injector)

Usage: python3 seed_openbao_kv.py
"""
import json
import os
import sys
import ssl
import urllib.request
import urllib.error


# =====================
# Configuration
# =====================
OPENBAO_ADDR = os.getenv("OPENBAO_ADDR", "https://127.0.0.1:8200")
ENV_PATH = os.getenv("ENV_PATH", "/home/mkanavi/docker/iacgenie/.env")
TOKEN_PATH = os.getenv("TOKEN_PATH", "/home/mkanavi/docker/iacgenie/openbao_raft/init_keys.json")


def get_token():
    """Get OpenBao root token."""
    token = os.getenv("OPENBAO_TOKEN")
    if token:
        return token
    try:
        with open(TOKEN_PATH) as f:
            return json.load(f)["root_token"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        print("[ERROR] Cannot read root token")
        sys.exit(1)


def parse_env(path):
    """Parse .env file into dict."""
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            v = v.strip()
            if len(v) >= 2 and ((v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")):
                v = v[1:-1]
            env[k.strip()] = v
    return env


def kv_put(engine, path, data, token):
    """Write KV v2 secret via REST API."""
    url = f"{OPENBAO_ADDR}/v1/{engine}/data/{path}"
    payload = json.dumps({"data": data}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "X-Vault-Token": token,
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        resp = urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=10)
        return True, resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return False, f"HTTP {e.code}: {body[:100]}"
    except Exception as e:
        return False, str(e)


def main():
    token = get_token()
    env = parse_env(ENV_PATH)

    print(f"Loaded {len(env)} env vars from {ENV_PATH}")
    print(f"OpenBao at {OPENBAO_ADDR}")
    print()

    results = []

    # ============ KV-GEN PATHS (for fetch-openbao-env.py) ============

    # PostgreSQL
    data = {
        "POSTGRES_USER": env.get("POSTGRES_USER", "iacgenie_pg"),
        "POSTGRES_PASSWORD": env.get("POSTGRES_PASSWORD", ""),
        "POSTGRES_DB": env.get("POSTGRES_DB", "iacgenie"),
    }
    ok, info = kv_put("iacgenie", "kv/data/postgres", data, token)
    results.append(("iacgenie/kv/data/postgres", ok, info))

    # Redis
    data = {"REDIS_PASSWORD": env.get("REDIS_PASSWORD", "")}
    ok, info = kv_put("iacgenie", "kv/data/redis", data, token)
    results.append(("iacgenie/kv/data/redis", ok, info))

    # MinIO
    data = {
        "MINIO_ROOT_USER": env.get("MINIO_ROOT_USER", ""),
        "MINIO_ROOT_PASSWORD": env.get("MINIO_ROOT_PASSWORD", ""),
    }
    ok, info = kv_put("iacgenie", "kv/data/minio", data, token)
    results.append(("iacgenie/kv/data/minio", ok, info))

    # Keycloak admin
    data = {
        "KEYCLOAK_ADMIN_USER": env.get("KEYCLOAK_ADMIN_USER", "admin"),
        "KEYCLOAK_ADMIN_PASSWORD": env.get("KEYCLOAK_ADMIN_PASSWORD", ""),
    }
    ok, info = kv_put("iacgenie", "kv/data/keycloak_admin", data, token)
    results.append(("iacgenie/kv/data/keycloak_admin", ok, info))

    # Keycloak DB
    data = {
        "KC_DB_PASSWORD": env.get("POSTGRES_KC_PASSWORD", ""),
        "KC_DB_NAME": env.get("POSTGRES_KC_DATABASE", "keycloak"),
    }
    ok, info = kv_put("iacgenie", "kv/data/keycloak_db", data, token)
    results.append(("iacgenie/kv/data/keycloak_db", ok, info))

    # JWT
    data = {"JWT_SECRET": env.get("JWT_SECRET", "")}
    ok, info = kv_put("iacgenie", "kv/data/jwt", data, token)
    results.append(("iacgenie/kv/data/jwt", ok, info))

    # Gitea DB
    data = {"GITEA_DB_PASSWORD": env.get("GITEA_DB_PASSWORD", "")}
    ok, info = kv_put("iacgenie", "kv/data/gitea_db", data, token)
    results.append(("iacgenie/kv/data/gitea_db", ok, info))

    # Gitea Admin
    data = {
        "GITEA_ADMIN_USERNAME": env.get("GITEA_ADMIN_USERNAME", "admin"),
        "GITEA_ADMIN_PASSWORD": env.get("GITEA_ADMIN_PASSWORD", ""),
    }
    ok, info = kv_put("iacgenie", "kv/data/gitea_admin", data, token)
    results.append(("iacgenie/kv/data/gitea_admin", ok, info))

    # Cloudflare
    data = {"CLOUDFLARE_TUNNEL_TOKEN": env.get("CLOUDFLARE_TUNNEL_TOKEN", "")}
    ok, info = kv_put("iacgenie", "kv/data/cloudflare", data, token)
    results.append(("iacgenie/kv/data/cloudflare", ok, info))

    # Grafana
    data = {
        "GRAFANA_ADMIN_USER": env.get("GRAFANA_ADMIN_USER", "admin"),
        "GRAFANA_ADMIN_PASSWORD": env.get("GRAFANA_ADMIN_PASSWORD", ""),
    }
    ok, info = kv_put("iacgenie", "kv/data/grafana", data, token)
    results.append(("iacgenie/kv/data/grafana", ok, info))

    # SearXNG
    data = {"SEARXNG_SECRET": env.get("SEARXNG_SECRET", "")}
    ok, info = kv_put("iacgenie", "kv/data/searxng", data, token)
    results.append(("iacgenie/kv/data/searxng", ok, info))

    # NSQD
    data = {"NSQD_NSQD_AUTH_REQUIRED": env.get("NSQD_NSQD_AUTH_REQUIRED", ""), "NSQD_NSQD_ADMIN_PASSWORD": env.get("NSQD_NSQD_ADMIN_PASSWORD", "")}
    ok, info = kv_put("iacgenie", "kv/data/nsqd", data, token)
    results.append(("iacgenie/kv/data/nsqd", ok, info))

    # SMTP
    data = {
        "SMTP_ADDR": env.get("SMTP_ADDR", ""),
        "SMTP_PORT": env.get("SMTP_PORT", "587"),
        "SMTP_USER": env.get("SMTP_USER", ""),
        "SMTP_PASS": env.get("SMTP_PASS", ""),
    }
    ok, info = kv_put("iacgenie", "kv/data/smtp", data, token)
    results.append(("iacgenie/kv/data/smtp", ok, info))

    # ============ INJECTOR PATHS (for openbao_injector.py) ============

    # iacgenie backend
    for key, path in [
        ("DATABASE_URL", "config/platform/database_url"),
        ("REDIS_URL", "config/platform/redis_url"),
        ("JWT_SECRET", "config/platform/jwt_secret"),
        ("OPENBAO_ADDR", "config/platform/openbao_addr"),
    ]:
        ok, info = kv_put("iacgenie", path, {"value": env.get(key, "")}, token)
        results.append((f"iacgenie/data/{path}", ok, info))

    # iacgenie Keycloak
    for key, path in [
        ("KEYCLOAK_ADMIN_USER", "config/keycloak/kc_admin_user"),
        ("KEYCLOAK_ADMIN_PASSWORD", "config/keycloak/kc_admin_password"),
    ]:
        ok, info = kv_put("iacgenie", path, {"value": env.get(key, "")}, token)
        results.append((f"iacgenie/data/{path}", ok, info))

    # iacgenie MinIO
    for key, path in [
        ("MINIO_ROOT_USER", "config/minio/minio_root_user"),
        ("MINIO_ROOT_PASSWORD", "config/minio/minio_root_password"),
    ]:
        ok, info = kv_put("iacgenie", path, {"value": env.get(key, "")}, token)
        results.append((f"iacgenie/data/{path}", ok, info))

    # ============ LIGHTSERP ============

    # Injector paths
    for key, path in [
        ("LIGHTSERP_DATABASE_URL", "data/config/lightserp_database_url"),
        ("LIGHTSERP_API_SECRET", "data/config/lightserp_api_secret"),
        ("LIGHTSERP_KEYCLOAK_CLIENT_SECRET", "data/config/lightserp_keycloak_client_secret"),
        ("REDIS_URL", "data/config/redis_url"),
        ("MINIO_ROOT_USER", "data/config/minio_access_key"),
        ("MINIO_ROOT_PASSWORD", "data/config/minio_secret_key"),
    ]:
        ok, info = kv_put("lightserp", path, {"value": env.get(key, "")}, token)
        results.append((f"lightserp/{path}", ok, info))

    # KV-gen path
    data = {
        "LIGHTSERP_DATABASE_URL": env.get("LIGHTSERP_DATABASE_URL", ""),
        "LIGHTSERP_API_SECRET": env.get("LIGHTSERP_API_SECRET", ""),
        "REDIS_URL": env.get("REDIS_URL", ""),
        "MINIO_ACCESS_KEY": env.get("MINIO_ROOT_USER", ""),
        "MINIO_SECRET_KEY": env.get("MINIO_ROOT_PASSWORD", ""),
    }
    ok, info = kv_put("iacgenie", "kv/data/lightserp", data, token)
    results.append(("iacgenie/kv/data/lightserp", ok, info))

    # ============ Summary ============
    print("\n=== Results ===")
    ok_count = sum(1 for _, ok, _ in results if ok)
    for path, ok, info in results:
        status = "OK" if ok else "FAIL"
        if isinstance(info, int):
            info = str(info)
        print(f"  [{status}] {path} - {info[:60]}")
    print(f"\nTotal: {ok_count}/{len(results)} succeeded")


if __name__ == "__main__":
    main()
