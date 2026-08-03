#!/usr/bin/env python3
"""
OpenBao Backup - Raft snapshot + raft data copy + SHA256 checksum + rotation.

Usage:
    ./backup_openbao.py                  # Take backup
    ./backup_openbao.py --status         # Show backup inventory
    ./backup_openbao.py --restore <file> # Restore from snapshot

Environment:
    OPENBAO_ROOT_TOKEN   - Optional, overrides .env lookup
    OPENBAO_BACKUP_DIR   - Optional, overrides default backup dir
"""
import json, os, sys, time, datetime, hashlib, glob, argparse, ssl, subprocess, urllib.request, urllib.error

# ── Configuration ──────────────────────────────────────────────────────────
COMPOSE_DIR = os.getenv("COMPOSE_DIR", "/home/mkanavi/docker/iacgenie")
ENV_FILE = os.path.join(COMPOSE_DIR, ".env")
RAFT_DIR = os.path.join(COMPOSE_DIR, "openbao_raft")
BACKUP_DIR = os.getenv("OPENBAO_BACKUP_DIR", os.path.join(RAFT_DIR, "backups"))
VAULT_DB = os.path.join(RAFT_DIR, "vault.db")
CONFIG_FILE = os.path.join(RAFT_DIR, "..", "openbao-prod.hcl")
CONFIG_ALT = os.path.join(COMPOSE_DIR, "openbao_data", "openbao-prod.hcl")
BAO_ADDR = "https://127.0.0.1:8200"
KEEP_DAYS = 30
CONTEXT = ssl._create_unverified_context()

# ── Helpers ────────────────────────────────────────────────────────────────

def log(msg=""):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")

def load_token():
    """Load root token from .env or environment."""
    token = os.getenv("OPENBAO_ROOT_TOKEN")
    if token:
        return token.strip()

    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line.startswith("OPENBAO_ROOT_TOKEN="):
                    token = line.split("=", 1)[1].strip().strip("'\"")
                    if token:
                        log(f"  Loaded token from {ENV_FILE}")
                        return token

    token_file = os.path.join(RAFT_DIR, "init_keys.json")
    if os.path.exists(token_file):
        try:
            with open(token_file) as f:
                keys = json.load(f)
                token = keys.get("root_token", keys.get("root_token_id", ""))
                if token:
                    log(f"  Loaded token from {token_file}")
                    return token
        except Exception:
            pass

    log("ERROR: Cannot find OpenBao root token. Set OPENBAO_ROOT_TOKEN env var or ensure .env exists.")
    sys.exit(1)

def bao_request(path, method="GET", data=None):
    """Make an authenticated request to OpenBao."""
    token = load_token()
    url = f"{BAO_ADDR}{path}"
    headers = {"X-Vault-Token": token, "Content-Type": "application/json"}
    req = urllib.request.Request(url, headers=headers, method=method)
    if data:
        req.data = json.dumps(data).encode()
    try:
        resp = urllib.request.urlopen(req, context=CONTEXT, timeout=30)
        content = resp.read()
        if not content:
            return {}
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return content.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        log(f"  ERROR: OpenBao request failed: HTTP {e.code} - {e.read().decode()[:200]}")
        raise
    except urllib.error.URLError as e:
        log(f"  ERROR: OpenBao request failed: {e}")
        raise

def sha256_file(filepath):
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

# ── Backup operations ──────────────────────────────────────────────────────

def take_snapshot_via_api():
    """Take raft snapshot via the streaming HTTP API."""
    log("  Attempting API snapshot...")

    token = load_token()
    url = f"{BAO_ADDR}/v1/sys/storage/raft/snapshot"
    headers = {"X-Vault-Token": token, "Accept": "application/octet-stream"}
    req = urllib.request.Request(url, headers=headers)

    timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%SZ")
    snap_path = os.path.join(BACKUP_DIR, f"openbao-snapshot-{timestamp}.snap")

    try:
        with open(snap_path, "wb") as f:
            with urllib.request.urlopen(req, context=CONTEXT, timeout=120) as resp:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
        checksum = sha256_file(snap_path)
        with open(f"{snap_path}.sha256", "w") as f:
            f.write(f"{checksum}  {snap_path}\n")
        size = os.path.getsize(snap_path)
        log(f"  OK API Snapshot: {os.path.basename(snap_path)} ({size:,} bytes)")
        log(f"    SHA256: {checksum}")
        return snap_path
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        log(f"  WARN API snapshot failed ({e}) -- falling back to raw copy")
        return None

def copy_vault_db():
    """Copy the raw raft database (host bind mount)."""
    if not os.path.exists(VAULT_DB):
        log("  WARN vault.db not found -- skipping raw copy")
        return None

    timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%SZ")
    dest = os.path.join(BACKUP_DIR, f"vault.db-{timestamp}")

    import shutil
    shutil.copy2(VAULT_DB, dest)

    checksum = sha256_file(dest)
    with open(f"{dest}.sha256", "w") as f:
        f.write(f"{checksum}  {dest}\n")

    log(f"  OK Raft DB: {os.path.basename(dest)} ({os.path.getsize(dest):,} bytes)")
    log(f"    SHA256: {checksum}")
    return dest

def copy_config():
    """Copy the OpenBao HCL config for reference."""
    config_src = CONFIG_FILE
    if not os.path.exists(config_src):
        config_src = CONFIG_ALT
    if not os.path.exists(config_src):
        log("  WARN Config file not found -- skipping")
        return None

    timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%SZ")
    dest = os.path.join(BACKUP_DIR, f"openbao-config-{timestamp}.hcl")

    import shutil
    shutil.copy2(config_src, dest)
    log(f"  OK Config backup: {os.path.basename(dest)} ({os.path.getsize(dest):,} bytes)")
    return dest

def rotate_backups():
    """Remove backups older than KEEP_DAYS."""
    now = time.time()
    cutoff = now - (KEEP_DAYS * 86400)

    removed = 0
    for pattern in ["vault.db-*", "openbao-config-*.hcl", "openbao-snapshot-*.snap*"]:
        for f in glob.glob(os.path.join(BACKUP_DIR, pattern)):
            if os.path.isfile(f) and os.path.getmtime(f) < cutoff:
                os.remove(f)
                removed += 1

    if removed:
        log(f"  Rotated {removed} old backup(s)")
    else:
        log("  No old backups to rotate")

def restore_snapshot(snapshot_path):
    """Restore from a snapshot file."""
    log(f"  Restoring from: {snapshot_path}")

    if not os.path.exists(snapshot_path):
        log(f"  ERROR: Snapshot file not found: {snapshot_path}")
        sys.exit(1)

    # Verify checksum
    sha_file = f"{snapshot_path}.sha256"
    if os.path.exists(sha_file):
        with open(sha_file) as f:
            expected_hash = f.read().split()[0]
        actual_hash = sha256_file(snapshot_path)
        if actual_hash != expected_hash:
            log(f"  ERROR: Checksum mismatch! Expected {expected_hash}, got {actual_hash}")
            sys.exit(1)
        log("  OK Checksum verified")

    # Upload snapshot to OpenBao
    token = load_token()
    with open(snapshot_path, "rb") as f:
        data = f.read()

    url = f"{BAO_ADDR}/v1/sys/storage/raft/snapshot"
    headers = {"X-Vault-Token": token}
    req = urllib.request.Request(url, headers=headers, data=data, method="PUT")

    log("  Uploading snapshot to OpenBao...")
    resp = urllib.request.urlopen(req, context=CONTEXT, timeout=300)
    log(f"  OK Restore complete. Response: {resp.status}")
    log("  NOTE: OpenBao may need to be restarted to apply the restored state.")

def show_status():
    """Show current backup inventory."""
    log(f"=== OpenBao Backup Inventory ===")
    log(f"Backup dir: {BACKUP_DIR}")
    log(f"Retention: {KEEP_DAYS} days")
    log()

    snaps = sorted(glob.glob(os.path.join(BACKUP_DIR, "openbao-snapshot-*.snap")))
    db_copies = sorted(glob.glob(os.path.join(BACKUP_DIR, "vault.db-*")))
    configs = sorted(glob.glob(os.path.join(BACKUP_DIR, "openbao-config-*.hcl")))

    log(f"Snapshots: {len(snaps)}")
    for s in snaps:
        age_h = (time.time() - os.path.getmtime(s)) / 3600
        log(f"  {os.path.basename(s)}  ({os.path.getsize(s):>10,} bytes, {age_h:5.1f}h ago)")

    log(f"Raft DB copies: {len(db_copies)}")
    for r in db_copies:
        age_h = (time.time() - os.path.getmtime(r)) / 3600
        log(f"  {os.path.basename(r)}  ({os.path.getsize(r):>10,} bytes, {age_h:5.1f}h ago)")

    log(f"Config backups: {len(configs)}")
    for c in configs:
        age_h = (time.time() - os.path.getmtime(c)) / 3600
        log(f"  {os.path.basename(c)}  ({os.path.getsize(c):>10,} bytes, {age_h:5.1f}h ago)")

    total = sum(os.path.getsize(f) for f in snaps + db_copies + configs if os.path.isfile(f))
    log(f"\nTotal: {total:,} bytes ({total / 1024 / 1024:.1f} MB)")

# ── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="OpenBao Backup Tool")
    parser.add_argument("action", nargs="?", default="backup",
                        choices=["backup", "status", "restore"],
                        help="Action to perform")
    parser.add_argument("snapshot", nargs="?", help="Snapshot file for restore")
    args = parser.parse_args()

    os.makedirs(BACKUP_DIR, exist_ok=True)

    if args.action == "status":
        show_status()
        return

    if args.action == "restore":
        if not args.snapshot:
            log("ERROR: --restore requires a snapshot file path")
            sys.exit(1)
        restore_snapshot(args.snapshot)
        return

    # ── Default: take backup ─────────────────────────────────────────────
    log("=" * 55)
    log(" OpenBao Backup - Raft Snapshot + Data Copy")
    log("=" * 55)

    # 1. Verify OpenBao is reachable and unsealed
    log("[1/5] Checking OpenBao health...")
    status = bao_request("/v1/sys/seal-status")
    if status.get("sealed"):
        log("  FAIL OpenBao is sealed! Aborting.")
        sys.exit(1)
    log(f"  OK OpenBao unsealed (v{status.get('version', '?')}, raft storage)")

    # 2. Take API snapshot (best effort)
    log("[2/5] Attempting API snapshot...")
    snap_file = take_snapshot_via_api()

    # 3. Copy raw raft DB (always available via host bind mount)
    log("[3/5] Copying raw raft database...")
    copy_vault_db()

    # 4. Copy config
    log("[4/5] Backing up OpenBao config...")
    copy_config()

    # 5. Rotate old backups
    log("[5/5] Rotating old backups...")
    rotate_backups()

    # Summary
    log()
    show_status()
    log()
    log("Backup completed successfully.")

if __name__ == "__main__":
    main()
