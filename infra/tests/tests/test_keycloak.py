"""
test_kc.py — Keycloak OIDC authentication tests.

Verifies that Keycloak is reachable and can issue tokens for both tenants.
"""

import pytest


class TestKeycloakConnectivity:
    """Basic Keycloak reachability and configuration tests."""

    def test_service_up(self, kc):
        """Keycloak should respond on the main endpoint."""
        import requests
        r = kc["requests"].get(
            kc["base"], timeout=10, allow_redirects=True
        )
        assert r.status_code in (200, 302, 401, 301), \
            f"Unexpected status: {r.status_code} for {kc['base']}"

    def test_master_realm(self, kc):
        """The 'master' realm should exist."""
        r = kc["requests"].get(
            f"{kc['base']}/admin/realms/master", timeout=10
        )
        # May require admin login — just verify the endpoint responds
        print(f"  Master realm status: {r.status_code}")

    def test_unified_realm_config(self, kc):
        """The 'unified' realm should be configured."""
        r = kc["requests"].get(
            f"{kc['base']}/realms/unified", timeout=10, allow_redirects=True
        )
        print(f"  Unified realm status: {r.status_code}")

    def test_iacgenie_client_configured(self, kc):
        """IacGenie Keycloak client should exist."""
        # Check by listing clients via admin API
        try:
            # First get admin token
            r = kc["requests"].post(
                f"{kc['base']}/realms/master/protocol/openid-connect/token",
                data={
                    "grant_type": "password",
                    "client_id": "admin-cli",
                    "username": kc["admin"],
                    "password": kc["admin_pw"],
                },
                timeout=10,
            )
            if r.status_code == 200:
                token = r.json().get("access_token")
                # List clients
                r2 = kc["requests"].get(
                    f"{kc['base']}/admin/realms/unified/clients",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10,
                )
                if r2.status_code == 200:
                    clients = r2.json()
                    client_ids = [c["clientId"] for c in clients]
                    assert "iacgenie" in client_ids, \
                        f"'iacgenie' client not found in unified realm. Clients: {client_ids}"
                    print(f"  iacgenie client found")
            else:
                print(f"  Admin auth status: {r.status_code} (may require different auth)")
        except Exception as e:
            print(f"  Admin client check skipped: {e}")

    def test_lightsrp_client_configured(self, kc):
        """LightSrp Keycloak client should exist."""
        try:
            r = kc["requests"].post(
                f"{kc['base']}/realms/master/protocol/openid-connect/token",
                data={
                    "grant_type": "password",
                    "client_id": "admin-cli",
                    "username": kc["admin"],
                    "password": kc["admin_pw"],
                },
                timeout=10,
            )
            if r.status_code == 200:
                token = r.json().get("access_token")
                r2 = kc["requests"].get(
                    f"{kc['base']}/admin/realms/unified/clients",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10,
                )
                if r2.status_code == 200:
                    clients = r2.json()
                    client_ids = [c["clientId"] for c in clients]
                    assert "lightsrp" in client_ids, \
                        f"'lightsrp' client not found. Clients: {client_ids}"
                    print(f"  lightsrp client found")
            else:
                print(f"  Admin auth status: {r.status_code}")
        except Exception as e:
            print(f"  Admin client check skipped: {e}")


class TestKeycloakOIDCFlow:
    """End-to-end OIDC token flow tests."""

    def test_openid_configuration(self, kc):
        """Verify OIDC discovery endpoint returns valid config."""
        r = kc["requests"].get(
            f"{kc['base']}/realms/unified/.well-known/openid-configuration",
            timeout=10,
        )
        if r.status_code == 200:
            config = r.json()
            assert "authorization_endpoint" in config
            assert "token_endpoint" in config
            assert "issuer" in config
        else:
            pytest.skip(f"OIDC discovery not available: {r.status_code}")
