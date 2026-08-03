#!/usr/bin/env python3
"""conftest.py - Shared fixtures for unified infra integration tests."""

import os, subprocess, time, socket
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
ENV_PATH = HERE / ".env"

def _parse_env(path):
    path = Path(path)
    env = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        val = val.strip().strip("'\"")
        env[key.strip()] = val
    return env

ENV = _parse_env(ENV_PATH)

POSTGRES_SUPER_PASSWORD = ENV.get("POSTGRES_SUPER_PASSWORD", "")
POSTGRES_APP_PASSWORD = ENV.get("POSTGRES_APP_PASSWORD", "")
POSTGRES_KC_PASSWORD = ENV.get("POSTGRES_KC_PASSWORD", "")
REDIS_PASSWORD = ENV.get("REDIS_PASSWORD", "")
MINIO_ROOT_USER = ENV.get("MINIO_ROOT_USER", "minioadmin")
MINIO_ROOT_PASSWORD = ENV.get("MINIO_ROOT_PASSWORD", "minioadmin")
OPENBAO_ROOT_TOKEN = ENV.get("OPENBAO_ROOT_TOKEN", "")
OPENBAO_TOKEN = ENV.get("OPENBAO_TOKEN", "")
KEYCLOAK_ADMIN = ENV.get("KEYCLOAK_ADMIN", "admin")
KEYCLOAK_ADMIN_PASSWORD = ENV.get("KEYCLOAK_ADMIN_PASSWORD", "admin")
SEARXNG_SECRET = ENV.get("SEARXNG_SECRET", "")

PG_HOST, REDIS_HOST, MINIO_HOST = "postgres", "redis", "minio"
OPENBAO_HOST, KEYCLOAK_HOST, SEARXNG_HOST = "openbao", "keycloak", "searxng"
NSQD_HOST, NSQ_LOOKUP_HOST = "nsqd", "nsqlookupd"
PROMETHEUS_HOST, GRAFANA_HOST = "prometheus", "grafana"

PG_PORT, REDIS_PORT = 5432, 6379
MINIO_API_PORT = 9000
OPENBAO_PORT, KEYCLOAK_PORT, SEARXNG_PORT = 8200, 8080, 8080
NSQD_PORT, NSQ_LOOKUP_PORT = 4150, 4160
PROMETHEUS_PORT, GRAFANA_PORT = 9090, 3001

PG_IACGENIE_DB, PG_LIGHTSRP_DB, PG_KEYCLOAK_DB = "iacgenie", "lightsrp", "keycloak"
REDIS_IACGENIE_DB, REDIS_LIGHTSRP_DB = 0, 1
MINIO_IACGENIE_BUCKETS = ["iacgenie-artifacts", "iacgenie-logs", "iacgenie-plans", "iacgenie-outputs"]
MINIO_LIGHTSRP_BUCKETS = ["lightsrp-searxng", "lightsrp-cache", "lightsrp-content"]
OPENBAO_IACGENIE_PATH = "secret/iacgenie"
OPENBAO_LIGHTSRP_PATH = "secret/lightsrp"

def _healthy(hostname, port, timeout=5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            socket.create_connection((hostname, port), timeout=2).close()
            return True
        except (ConnectionRefusedError, TimeoutError, OSError):
            time.sleep(0.5)
    return False

@pytest.fixture(scope="session")
def services_available():
    avail = {
        "postgres": _healthy(PG_HOST, PG_PORT),
        "redis": _healthy(REDIS_HOST, REDIS_PORT),
        "minio": _healthy(MINIO_HOST, MINIO_API_PORT),
        "openbao": _healthy(OPENBAO_HOST, OPENBAO_PORT),
        "keycloak": _healthy(KEYCLOAK_HOST, KEYCLOAK_PORT),
        "searxng": _healthy(SEARXNG_HOST, SEARXNG_PORT),
        "nsqd": _healthy(NSQD_HOST, NSQD_PORT),
        "prometheus": _healthy(PROMETHEUS_HOST, PROMETHEUS_PORT),
        "grafana": _healthy(GRAFANA_HOST, GRAFANA_PORT),
    }
    print("\n[SERVICES]")
    for svc, up in avail.items():
        print(f"  [{'UP' if up else 'DN'}] {svc}")
    return avail

# ---- fixtures ----

@pytest.fixture(scope="session")
def pg(services_available):
    if not services_available.get("postgres"):
        pytest.skip("PostgreSQL not available")
    import psycopg2
    conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, user="postgres",
                           password=POSTGRES_SUPER_PASSWORD, dbname="postgres",
                           connect_timeout=10)
    conn.autocommit = True
    yield conn
    conn.close()

@pytest.fixture(scope="session")
def pg_iacgenie(services_available):
    if not services_available.get("postgres"):
        pytest.skip("PostgreSQL not available")
    import psycopg2
    conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, user="postgres",
                           password=POSTGRES_SUPER_PASSWORD, dbname=PG_IACGENIE_DB,
                           connect_timeout=10)
    conn.autocommit = True
    yield conn
    conn.close()

@pytest.fixture(scope="session")
def pg_lightsrp(services_available):
    if not services_available.get("postgres"):
        pytest.skip("PostgreSQL not available")
    import psycopg2
    conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, user="postgres",
                           password=POSTGRES_SUPER_PASSWORD, dbname=PG_LIGHTSRP_DB,
                           connect_timeout=10)
    conn.autocommit = True
    yield conn
    conn.close()

@pytest.fixture(scope="session")
def redis_ia(services_available):
    if not services_available.get("redis"):
        pytest.skip("Redis not available")
    import redis
    c = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD,
                    db=REDIS_IACGENIE_DB, decode_responses=True,
                    protocol=2, socket_connect_timeout=10)
    yield c
    for k in c.scan_iter(match="test_unified:*"):
        c.delete(k)

@pytest.fixture(scope="session")
def redis_ls(services_available):
    if not services_available.get("redis"):
        pytest.skip("Redis not available")
    import redis
    c = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD,
                    db=REDIS_LIGHTSRP_DB, decode_responses=True,
                    protocol=2, socket_connect_timeout=10)
    yield c
    for k in c.scan_iter(match="test_unified:*"):
        c.delete(k)

@pytest.fixture(scope="session")
def s3(services_available):
    if not services_available.get("minio"):
        pytest.skip("MinIO not available")
    import boto3
    from botocore.config import Config
    yield boto3.client("s3", endpoint_url=f"http://{MINIO_HOST}:{MINIO_API_PORT}",
                       aws_access_key_id=MINIO_ROOT_USER,
                       aws_secret_access_key=MINIO_ROOT_PASSWORD,
                       config=Config(signature_version="s3v4"), region_name="us-east-1")

@pytest.fixture(scope="session")
def obao(services_available):
    if not services_available.get("openbao"):
        pytest.skip("OpenBao not available")
    import requests
    base = f"http://{OPENBAO_HOST}:{OPENBAO_PORT}"
    r = requests.get(f"{base}/v1/sys/health", timeout=10)
    if r.status_code not in (200, 472, 501):
        pytest.skip(f"OpenBao not ready: {r.status_code}")
    s = requests.Session()
    s.headers["X-Vault-Token"] = OPENBAO_ROOT_TOKEN
    s.headers["Content-Type"] = "application/json"
    yield {"base": base, "session": s, "token": OPENBAO_ROOT_TOKEN}

@pytest.fixture(scope="session")
def kc(services_available):
    if not services_available.get("keycloak"):
        pytest.skip("Keycloak not available")
    import requests
    base = f"http://{KEYCLOAK_HOST}:{KEYCLOAK_PORT}"
    r = requests.get(base, timeout=10, allow_redirects=True)
    if r.status_code == 404:
        pytest.skip("Keycloak not ready yet")
    yield {"base": base, "admin": KEYCLOAK_ADMIN, "pw": KEYCLOAK_ADMIN_PASSWORD, "requests": requests}

@pytest.fixture(scope="session")
def sx(services_available):
    if not services_available.get("searxng"):
        pytest.skip("SearXNG not available")
    import requests
    yield {"base": f"http://{SEARXNG_HOST}:{SEARXNG_PORT}", "requests": requests}
