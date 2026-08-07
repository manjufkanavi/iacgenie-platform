#!/bin/bash
# ==============================================================================
# IacGenie Platform — Asymmetric Encryption & Google Drive Backup Script
# ==============================================================================
set -euo pipefail

BACKUP_DIR="${1:-/home/mkanavi/backups}"
ENCRYPTED_DIR="${BACKUP_DIR}/encrypted"
VAULT_URL="${VAULT_URL:-https://vault.iacgenie.com}"
GDRIVE_FOLDER_NAME="${GDRIVE_FOLDER_NAME:-IacGenie-Backups}"

mkdir -p "$ENCRYPTED_DIR"

echo "=== Starting Backup Encryption & Google Drive Sync ==="
echo "Backup Directory: $BACKUP_DIR"
echo "Vault URL: $VAULT_URL"
echo "Target Google Drive Folder: $GDRIVE_FOLDER_NAME"

# ------------------------------------------------------------------------------
# STEP 1: Fetch Public Key from OpenBao (vault.iacgenie.com) for Asymmetric Encryption
# ------------------------------------------------------------------------------
echo "[1/4] Fetching GPG Asymmetric Public Key from OpenBao..."

PUB_KEY_FILE="/tmp/backup_pubkey.asc"

if [ -n "${VAULT_TOKEN:-}" ]; then
  # Fetch public key from OpenBao KV secret engine
  curl -s --fail --header "X-Vault-Token: $VAULT_TOKEN" \
    "${VAULT_URL}/v1/secret/data/backup/keys" | jq -r '.data.data.public_key' > "$PUB_KEY_FILE" || true
fi

if [ ! -s "$PUB_KEY_FILE" ]; then
  echo "⚠️ Could not retrieve public key from OpenBao. Generating standard asymmetric GPG key pair locally..."
  gpg --batch --passphrase '' --quick-generate-key "backup@iacgenie.com" rsa2048 default 0 2>/dev/null || true
  gpg --armor --export "backup@iacgenie.com" > "$PUB_KEY_FILE"
fi

# Import public key into GPG keyring
gpg --import "$PUB_KEY_FILE" 2>/dev/null || true
echo "  ✅ Public key ready for encryption"

# ------------------------------------------------------------------------------
# STEP 2: Asymmetric Encryption of Latest Backup Archives
# ------------------------------------------------------------------------------
echo "[2/4] Encrypting latest backup archives with GPG Asymmetric Key..."

LATEST_FILES=$(find "$BACKUP_DIR" -maxdepth 1 -type f \( -name "*.sql" -o -name "*.tar.gz" -o -name "*.snap" \))

for file in $LATEST_FILES; do
  BASENAME=$(basename "$file")
  ENC_OUTPUT="${ENCRYPTED_DIR}/${BASENAME}.gpg"
  
  if [ ! -f "$ENC_OUTPUT" ]; then
    echo "  🔒 Encrypting $BASENAME -> ${BASENAME}.gpg"
    gpg --batch --yes --trust-model always --encrypt --recipient "backup@iacgenie.com" \
      --output "$ENC_OUTPUT" "$file"
  fi
done

echo "  ✅ Asymmetric encryption complete"

# ------------------------------------------------------------------------------
# STEP 3: Sync Encrypted Backups to Google Drive via rclone
# ------------------------------------------------------------------------------
echo "[3/4] Syncing encrypted backups to Google Drive..."

if command -v rclone &>/dev/null; then
  if rclone listremotes | grep -q "^gdrive:"; then
    rclone copy "$ENCRYPTED_DIR" "gdrive:${GDRIVE_FOLDER_NAME}" \
      --transfers 4 \
      --retries 3 \
      --stats 5s
    echo "  ✅ Google Drive sync complete!"
  else
    echo "⚠️ rclone remote 'gdrive:' is not configured yet."
    echo "   Run 'rclone config' to connect your Google Account, or set RCLONE_CONFIG_GDRIVE credentials."
  fi
else
  echo "⚠️ rclone is not installed on target host. Install via: 'sudo apt-get install -y rclone'"
fi

# ------------------------------------------------------------------------------
# STEP 4: Tiered Retention Cleanup (Local encrypted backups: keep 7 days)
# ------------------------------------------------------------------------------
echo "[4/4] Cleaning up local encrypted backups older than 7 days..."
find "$ENCRYPTED_DIR" -name "*.gpg" -mtime +7 -delete 2>/dev/null || true
rm -f "$PUB_KEY_FILE"

echo "=== Backup Processing Complete ==="
