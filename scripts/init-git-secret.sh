#!/usr/bin/env bash
# =============================================================================
# Git-Secret Initialization Script
# =============================================================================
# Sets up git-secret for the iacgenie-platform repository.
# Encrypts bootstrap secrets (Ansible vault key, OpenBao unseal keys).
#
# Prerequisites:
#   - git-secret installed: brew install git-secret (macOS)
#   - GPG key available for the admin user
#
# Usage:
#   ./scripts/init-git-secret.sh <gpg-email>
#
# Example:
#   ./scripts/init-git-secret.sh manjufkanavi@gmail.com
# =============================================================================

set -euo pipefail

GPG_EMAIL="${1:?Usage: $0 <gpg-email>}"

echo "==> Initializing git-secret for iacgenie-platform"
echo "    Admin GPG email: ${GPG_EMAIL}"

# Check prerequisites
command -v git-secret >/dev/null 2>&1 || {
    echo "❌ git-secret not found. Install: brew install git-secret"
    exit 1
}

command -v gpg >/dev/null 2>&1 || {
    echo "❌ gpg not found. Install: brew install gnupg"
    exit 1
}

# Verify GPG key exists
if ! gpg --list-keys "${GPG_EMAIL}" >/dev/null 2>&1; then
    echo "❌ No GPG key found for ${GPG_EMAIL}"
    echo "   Generate one: gpg --gen-key"
    exit 1
fi

# Navigate to repo root
cd "$(git rev-parse --show-toplevel)"

# Initialize git-secret (idempotent)
if [ ! -d ".gitsecret" ]; then
    git secret init
    echo "  ✅ git-secret initialized"
else
    echo "  ℹ️  git-secret already initialized"
fi

# Add admin GPG key
git secret tell "${GPG_EMAIL}" 2>/dev/null || true
echo "  ✅ Added GPG key for ${GPG_EMAIL}"

# Register files to encrypt
FILES_TO_ENCRYPT=(
    "infra/ansible/.vault_key"
)

for f in "${FILES_TO_ENCRYPT[@]}"; do
    if [ -f "$f" ]; then
        git secret add "$f" 2>/dev/null || echo "  ℹ️  $f already tracked"
        echo "  ✅ Registered: $f"
    else
        echo "  ⚠️  Skipped (not found): $f"
    fi
done

# Encrypt all registered files
echo "==> Encrypting secrets..."
git secret hide
echo "  ✅ All secrets encrypted"

# Verify
echo ""
echo "==> Registered secret files:"
git secret list

echo ""
echo "==> Next steps:"
echo "  1. Commit the .gitsecret/ directory and .secret files:"
echo "     git add .gitsecret/ *.secret infra/ansible/.vault_key.secret"
echo "     git commit -m 'feat: add git-secret for bootstrap credentials'"
echo ""
echo "  2. Add these repository secrets to Gitea/GitHub:"
echo "     - GPG_PRIVATE_KEY: gpg --armor --export-secret-keys ${GPG_EMAIL}"
echo "     - ANSIBLE_VAULT_PASSWORD: (contents of infra/ansible/.vault_key)"
echo "     - OPENBAO_ROOT_TOKEN: (from OpenBao init_keys.json)"
echo "     - OPENBAO_UNSEAL_KEY_1..3: (from OpenBao init_keys.json)"
echo ""
echo "  3. To decrypt in CI/CD:"
echo "     echo \"\$GPG_PRIVATE_KEY\" | gpg --import"
echo "     git secret reveal"
