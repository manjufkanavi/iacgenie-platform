#!/usr/bin/env python3
"""
Ensure Keycloak client exists for a given configuration.
Usage: keycloak_client_setup.py --client-id <id> --secret <secret> --redirect <uri>
"""
import argparse, json, sys
import httpx


def ensure_client(kc_url, realm, admin_token, client_id, client_secret, redirect_uris):
    """Ensure a Keycloak client exists with the given config."""
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {admin_token}"}

    # Find existing client
    with httpx.Client(timeout=10) as c:
        resp = c.get(f"{kc_url}/admin/realms/{realm}/clients?search={client_id}", headers=headers)
        clients = resp.json()
        existing = None
        for cl in clients:
            if cl["clientId"] == client_id:
                existing = cl
                break

        if existing:
            # Update
            payload = {
                "clientId": client_id,
                "enabled": True,
                "clientAuthenticatorType": "client-secret",
                "redirectUris": redirect_uris,
                "secret": client_secret,
            }
            resp = c.put(f"{kc_url}/admin/realms/{realm}/clients/{existing['id']}", headers=headers, json=payload)
        else:
            # Create
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
    parser.add_argument("--admin-token", required=True)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--secret", required=True)
    parser.add_argument("--redirect-uris", nargs="+", required=True)
    args = parser.parse_args()

    code = ensure_client(
        kc_url=args.kc_url,
        realm=args.realm,
        admin_token=args.admin_token,
        client_id=args.client_id,
        client_secret=args.secret,
        redirect_uris=args.redirect_uris,
    )
    sys.exit(0 if code in (200, 201) else 1)


if __name__ == "__main__":
    main()
