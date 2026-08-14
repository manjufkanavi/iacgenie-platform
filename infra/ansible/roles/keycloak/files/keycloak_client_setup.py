#!/usr/bin/env python3
"""
Ensure Keycloak client exists for a given configuration.
Gets admin token via admin UI login, then creates/updates client.
Usage: keycloak_client_setup.py --kc-url <url> --realm <realm> --admin-user <user> --admin-pass <pass> --client-id <id> --secret <secret> --redirect <uri>
"""
import argparse, json, sys
import httpx


def ensure_client(kc_url, realm, admin_user, admin_pass, client_id, client_secret, redirect_uris):
    """Ensure a Keycloak client exists with the given config."""
    # Step 1: Get admin token
    with httpx.Client(timeout=10) as c:
        resp = c.post(
            f"{kc_url}/protocol/openid-connect/token",
            data={
                "grant_type":    "password",
                "client_id":     "admin-cli",
                "username":      admin_user,
                "password":      admin_pass,
            },
        )
        if resp.status_code != 200:
            print(f"Failed to get admin token: {resp.status_code} {resp.text}")
            return 1
        admin_token = resp.json()["access_token"]
        print(f"Got admin token for {admin_user}")

    # Step 2: Ensure client exists
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {admin_token}"}

    with httpx.Client(timeout=10) as c:
        resp = c.get(f"{kc_url}/admin/realms/{realm}/clients?search={client_id}", headers=headers)
        clients = resp.json()
        existing = None
        for cl in clients:
            if cl["clientId"] == client_id:
                existing = cl
                break

        if existing:
            payload = {
                "clientId": client_id,
                "enabled": True,
                "clientAuthenticatorType": "client-secret",
                "redirectUris": redirect_uris,
                "secret": client_secret,
            }
            resp = c.put(f"{kc_url}/admin/realms/{realm}/clients/{existing['id']}", headers=headers, json=payload)
        else:
            payload = {
                "clientId": client_id,
                "enabled": True,
                "clientAuthenticatorType": "client-secret",
                "redirectUris": redirect_uris,
                "protocol": "openid-connect",
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": True,
                "publicClient": False,
                "secret": client_secret,
            }
            resp = c.post(f"{kc_url}/admin/realms/{realm}/clients", headers=headers, json=payload)

    action = "Updated" if existing else "Created"
    print(f"{action} client '{client_id}' -> status {resp.status_code}")
    return resp.status_code


def main():
    parser = argparse.ArgumentParser(description="Ensure Keycloak client")
    parser.add_argument("--kc-url", required=True, help="Keycloak admin URL")
    parser.add_argument("--realm", default="iacgenie")
    parser.add_argument("--admin-user", required=True)
    parser.add_argument("--admin-password", required=True)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--secret", required=True)
    parser.add_argument("--redirect-uris", nargs="+", required=True)
    args = parser.parse_args()

    code = ensure_client(
        kc_url=args.kc_url,
        realm=args.realm,
        admin_user=args.admin_user,
        admin_pass=args.admin_password,
        client_id=args.client_id,
        client_secret=args.secret,
        redirect_uris=args.redirect_uris,
    )
    sys.exit(0 if code in (200, 201) else 1)


if __name__ == "__main__":
    main()
