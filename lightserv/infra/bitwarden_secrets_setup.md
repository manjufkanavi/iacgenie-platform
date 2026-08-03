# Bitwarden Secrets Manager (BWS) Setup Guide

This guide details how to securely migrate the `iacgenie` project away from hardcoded secrets and `.env` files by implementing the **Bitwarden Secrets Manager (BWS)**.

## 1. Installation

The `bws` CLI needs to be installed on any machine (Mac Studio, Linux VM) that needs to fetch secrets programmatically.

**For Mac Studio (Homebrew):**
```bash
brew install bitwarden/tap/bws
```

**For Linux VM / Debian-based servers:**
```bash
curl -LO "https://github.com/bitwarden/sdk-sm/releases/download/bws-v0.4.0/bws-x86_64-unknown-linux-gnu-0.4.0.zip"
unzip bws-*-linux-gnu-*.zip
sudo mv bws /usr/local/bin/
```
*(Check the [official BWS releases page](https://github.com/bitwarden/sdk-sm/releases) for the latest version).*

---

## 2. Generate a Machine Account Token

You do not use your master password to authenticate servers. Instead, you create a scoped Machine Account token.

1. Log into your **Bitwarden Web Vault**.
2. Navigate to the **Secrets Manager** application (usually available via the app switcher in the top right).
3. Create a new **Project** called `iacgenie`.
4. Go to **Machine Accounts** and click **New Machine Account**.
   - Name it `iacgenie-prod-server` (or similar).
   - Grant it **Read** access strictly to the `iacgenie` project.
5. Once created, generate an **Access Token** for this machine account.
   - **IMPORTANT:** Copy this token immediately. It starts with `bws_at_...` and will never be shown again.

---

## 3. Server Configuration

To authenticate the CLI on your server or Mac, you simply inject the token into the environment. 

For the Linux VM, you can add it to the user's profile, or inject it directly into the systemd service files/cron jobs that need it:

```bash
# Add to ~/.bashrc or ~/.zshrc for interactive sessions
export BWS_ACCESS_TOKEN="bws_at_YOUR_TOKEN_HERE"
```

If running inside a Docker container, pass it as an environment variable:
```bash
docker run -e BWS_ACCESS_TOKEN="bws_at_YOUR_TOKEN_HERE" ...
```

---

## 4. Fetching Secrets Programmatically

Once the `BWS_ACCESS_TOKEN` is exported in the environment, the CLI works completely headless. 

### Fetching a single secret
First, get the unique UUID of the secret from your Bitwarden dashboard, then use it in your bash scripts:

```bash
# Fetch the secret as a raw string
DB_PASSWORD=$(bws secret get "00000000-0000-0000-0000-000000000000" --output tsv | cut -f 2)

echo "Connecting to database..."
# Use $DB_PASSWORD in your connection strings
```

### Fetching all secrets as JSON
If your application can parse JSON (like Python, Node.js, or Go), you can fetch the entire project's secrets at once:

```bash
bws project get "YOUR_PROJECT_ID"
```

---

## 5. Security Best Practices

> [!CAUTION]
> **Never commit your `bws_at_...` token to Git.** Treat the Access Token just like a production database password.

* **Minimize Scope:** Create separate Machine Accounts for `dev` and `prod`. The `dev` token should not be able to read `prod` secrets.
* **Instant Revocation:** If you suspect a server has been compromised, immediately delete the Machine Account or revoke its Access Token from the Bitwarden Web Vault to instantly cut off access.
* **MFA Isolation:** Because `bws` uses dedicated access tokens, your human-interactive Bitwarden account remains heavily protected by MFA without breaking your automated pipelines.
