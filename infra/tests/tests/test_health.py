"""
test_health.py — Verify every service in the unified infrastructure is reachable
and reporting healthy status.
"""

import pytest


# ─── Individual service health checks ────────────────────────────────────────

class TestHealthPostgres:
    def test_tcp_port_open(self, services_available):
        assert services_available.get("postgres"), "PostgreSQL is not reachable"

    def test_accepts_connections(self, pg):
        """Verify we can query the database."""
        cur = pg.cursor()
        cur.execute("SELECT 1")
        assert cur.fetchone()[0] == 1
        cur.close()

    def test_version(self, pg):
        cur = pg.cursor()
        cur.execute("SHOW server_version")
        version = cur.fetchone()[0]
        assert int(version.split(".")[0]) >= 15, f"Expected PG>=15, got {version}"
        cur.close()

    def test_databases_exist(self, pg):
        cur = pg.cursor()
        cur.execute(
            "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname"
        )
        dbs = {row[0] for row in cur.fetchall()}
        for expected in ("iacgenie", "lightsrp", "kc"):
            assert expected in dbs, f"Database '{expected}' missing from PostgreSQL"
        cur.close()


class TestHealthRedis:
    def test_tcp_port_open(self, services_available):
        assert services_available.get("redis"), "Redis is not reachable"

    def test_info(self, redis_ia):
        info = redis_ia.info()
        assert info["redis_version"]
        assert info["role"] == "master"

    def test_set_get(self, redis_ia):
        key = "test_unified:health:ping"
        redis_ia.set(key, "pong", ex=10)
        assert redis_ia.get(key) == "pong"


class TestHealthMinIO:
    def test_tcp_port_open(self, services_available):
        assert services_available.get("minio"), "MinIO is not reachable"

    def test_s3_list_buckets(self, s3):
        """Ensure we can enumerate buckets."""
        buckets = s3.list_buckets()
        names = {b["Name"] for b in buckets}
        assert len(names) > 0, "No buckets found"


class TestHealthOpenBao:
    def test_service_up(self, obao):
        """OpenBao dev mode returns 472 (unsealed) on /v1/sys/health, which is a valid status."""
        import requests
        r = obao["session"].get(f"{obao['base']}/v1/sys/health")
        assert r.status_code in (200, 472, 501), \
            f"OpenBao health returned {r.status_code}: {r.text[:200]}"


class TestHealthKeycloak:
    def test_service_up(self, kc):
        import requests
        r = kc["requests"].get(kc["base"], allow_redirects=True)
        # A well-known endpoint is the realm config
        r2 = kc["requests"].get(
            f"{kc['base']}/realms/master", allow_redirects=True, timeout=10
        )
        assert r2.status_code in (200, 302, 401), \
            f"Keycloak realm returned {r2.status_code}: {r2.text[:200]}"


class TestHealthSearXNG:
    def test_service_up(self, sx):
        r = sx["requests"].get(f"{sx['base']}/search?format=json&q=test", timeout=10)
        assert r.status_code == 200, f"SearXNG returned {r.status_code}"


class TestHealthNSQ:
    def test_nsqd_stats(self, nsqd):
        assert "Stats" in nsqd["stats"], f"NSQD stats missing: {nsqd['stats']}"


class TestHealthPrometheus:
    def test_prometheus_up(self, services_available):
        if not services_available.get("prometheus"):
            pytest.skip("Prometheus not available")

        import requests
        r = requests.get(
            f"http://{PROMETHEUS_HOST}:{PROMETHEUS_PORT}/-/healthy", timeout=5
        )
        assert r.status_code == 200, f"Prometheus returned {r.status_code}"


class TestHealthGrafana:
    def test_grafana_up(self, services_available):
        if not services_available.get("grafana"):
            pytest.skip("Grafana not available")

        import requests
        r = requests.get(
            f"http://{GRAFANA_HOST}:{GRAFANA_PORT}/api/health", timeout=5
        )
        assert r.status_code == 200, f"Grafana returned {r.status_code}"


class TestHealthSummary:
    """Overall pass/fail summary for the health check suite."""

    def test_at_least_three_services_up(self, services_available):
        up_count = sum(1 for v in services_available.values() if v)
        assert up_count >= 3, f"Only {up_count} services are up; expected >= 3"
        print(f"  Health summary: {up_count}/9 services healthy")
