#!/usr/bin/env python3
"""
OpenBao Secret Generator & Seeder

Generates random secure passwords/tokens for all services and seeds OpenBao.

Usage: python3 openbao-seed.py
"""
import os, sys, json, string, secrets
import urllib.request, urllib.error, ssl

OPENBAO_ADDR = os.getenv("OPENBAO_ADDR", "http://127.0.0.1:8200")
TOKEN = os.getenv("OPENBAO_TOKEN", os.getenv("OPENBAO_ROOT_TOKEN", ""))
ENV_FILE = os.getenv("ENV_FILE", "/home/mkanavi/docker/iacgenie/.env")

if not TOKEN:
    print("ERROR: OPENBAO_TOKEN or OPENBAO_ROOT_TOKEN not set")
    sys.exit(1)

ctx = ssl.create_default_context()

def rand_password(length=24):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(chars) for _ in range(length))

def openbao_enable_kv(mount):
    url = f"{OPENBAO_ADDR}/v1/sys/mounts/{mount}"
    payload = json.dumps({"type": "kv", "options": {"version": "2"}}).encode()
    req = urllib.request.Request(url, data=payload,
        headers={"X-Vault-Token": TOKEN, "Content-Type": "application/json"},
        method="PUT")
    try:
        r = urllib.request.urlopen(req, context=ctx, timeout=10)
        print(f"  Enabled: {mount}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if "already exists" in body:
            print(f"  Exists: {mount}")

def openbao_write(mount, path, data):
    url = f"{OPENBAO_ADDR}/v1/{mount}/data/{path}"
    payload = json.dumps({"data": data}).encode()
    req = urllib.request.Request(url, data=payload,
        headers={"X-Vault-Token": TOKEN, "Content-Type": "application/json"},
        method="POST")
    try:
        r = urllib.request.urlopen(req, context=ctx, timeout=10)
        return True
    except urllib.error.HTTPError:
        return False

def main():
    print("==> Generating secrets for all services\n")

    passwords = {
        "PG_ROOT_PASSWORD":      rand_password(32),
        "PG_APP_PASSWORD":       rand_password(32),
        "PG_KC_PASSWORD":        rand_password(32),
        "REDIS_PASSWORD":        rand_password(32),
        "MINIO_ROOT_PASSWORD":   rand_password(32),
        "GITEA_ADMIN_PASSWORD":  rand_password(32),
        "KEYCLOAK_ADMIN_PASSWORD": rand_password(32),
        "LIGHTSERP_API_SECRET":  rand_password(32),
        "LIGHTSERP_KEYCLOAK_CLIENT_SECRET": rand_password(32),
        "SEARXNG_SECRET_KEY":    rand_password(32),
        "JWT_SECRET":            rand_password(32),
        "NSQD_AUTH_TOKEN":       rand_password(32),
        "PAGEZEN_API_SECRET":    rand_password(32),
        "TERRAFORM_API_KEY":     rand_password(32),
    }

    print("Generated passwords (first 4 + last 4 chars):")
    for k, v in passwords.items():
        print(f"  {k}: {v[:4]}...{v[-4:]}")

    # Enable KV mounts
    print("\n==> Ensuring KV mounts")
    for mount in ["iacgenie/kv", "lightserp/kv", "terraform/kv"]:
        openbao_enable_kv(mount)

    # Write secrets
    print("\n==> Seeding OpenBao")
    secrets = {
        "iacgenie/kv": {
            "postgres": {"username": "lightsrp", "password": passwords["PG_APP_PASSWORD"], "database": "lightsrp"},
            "redis": {"password": passwords["REDIS_PASSWORD"]},
            "minio": {"access_key": "iacgenie", "secret_key": passwords["MINIO_ROOT_PASSWORD"]},
            "gitea": {"admin_password": passwords["GITEA_ADMIN_PASSWORD"]},
            "keycloak": {"admin_user": "admin", "admin_password": passwords["KEYCLOAK_ADMIN_PASSWORD"]},
            "keycloak_db": {"username": "keycloak", "password": passwords["PG_KC_PASSWORD"], "database": "keycloak"},
            "lightserp": {
                "api_secret": passwords["LIGHTSERP_API_SECRET"],
                "keycloak_client_secret": passwords["LIGHTSERP_KEYCLOAK_CLIENT_SECRET"],
                "keycloak_db_password": passwords["PG_KC_PASSWORD"],
            },
            "searxng": {"secret_key": passwords["SEARXNG_SECRET_KEY"]},
            "nginx": {"jwt_secret": passwords["JWT_SECRET"]},
            "nsqd": {"auth_token": passwords["NSQD_AUTH_TOKEN"]},
            "pagezen": {"api_secret": passwords["PAGEZEN_API_SECRET"]},
            "terraform": {"api_key": passwords["TERRAFORM_API_KEY"]},
        },
    }
    for mount, paths in secrets.items():
        for path, data in paths.items():
            if openbao_write(mount, path, data):
                print(f"  WRITTEN: {mount}/{path}")

    # Update .env
    print("\n==> Updating .env")
    env_vars = {
        "PG_ROOT_PASSWORD":     passwords["PG_ROOT_PASSWORD"],
        "PG_APP_PASSWORD":      passwords["PG_APP_PASSWORD"],
        "PG_KC_PASSWORD":       passwords["PG_KC_PASSWORD"],
        "REDIS_PASSWORD":       passwords["REDIS_PASSWORD"],
        "MINIO_ROOT_PASSWORD":  passwords["MINIO_ROOT_PASSWORD"],
        "GITEA_ADMIN_PASSWORD": passwords["GITEA_ADMIN_PASSWORD"],
        "KEYCLOAK_ADMIN_PASSWORD": passwords["KEYCLOAK_ADMIN_PASSWORD"],
        "LIGHTSERP_API_SECRET": passwords["LIGHTSERP_API_SECRET"],
        "LIGHTSERP_KEYCLOAK_CLIENT_SECRET": passwords["LIGHTSERP_KEYCLOAK_CLIENT_SECRET"],
        "SEARXNG_SECRET_KEY":   passwords["SEARXNG_SECRET_KEY"],
        "JWT_SECRET":           passwords["JWT_SECRET"],
        "NSQD_AUTH_TOKEN":      passwords["NSQD_AUTH_TOKEN"],
        "PAGEZEN_API_SECRET":   passwords["PAGEZEN_API_SECRET"],
        "TERRAFORM_API_KEY":    passwords["TERRAFORM_API_KEY"],
    }

    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            lines = f.readlines()
        new_lines = []
        for line in lines:
            updated = False
            for k, v in env_vars.items():
                if line.startswith(k + "="):
                    new_lines.append(k + "=" + v + "\n")
                    updated = True
                    break
            if not updated:
                new_lines.append(line)
        with open(ENV_FILE, "w") as f:
            f.writelines(new_lines)
    else:
        with open(ENV_FILE, "w") as f:
            f.write("# Generated by openbao-seed.py\n")
            for k, v in env_vars.items():
                f.write(k + "=" + v + "\n")

    print("  Updated " + str(len(env_vars)) + " keys in " + ENV_FILE)
    print("\n==> Seed complete")

if __name__ == "__main__":
    main()
