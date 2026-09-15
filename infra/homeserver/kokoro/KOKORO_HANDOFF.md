# Kokoro-82M TTS — Offline Deployment Handoff

**Target:** homeserver `192.168.0.116` · **Role:** `infra/homeserver/kokoro/roles/kokoro`
**Status:** DEPLOYED & VERIFIED OFFLINE (2026-08-31)

This doc captures everything the README deliberately omits (secrets, exact byte
counts, and — most importantly — the offline-resolution bug that was blocking this).

---

## 1. What "offline" actually means here

Kokoro loads its weights via HuggingFace Hub's `snapshot_download("hexgrad/Kokoro-82M",
local_files_only=True)` (no revision). For that to resolve **without any network call**,
the host cache must be a *complete, standard* HF Hub layout under the path the container's
`HF_HUB_CACHE=/var/lib/kokoro/hub` expects:

```
<cache>/models--hexgrad--Kokoro-82M/
├── blobs/
│   ├── 14a726edd3718279eac426630879ff743955b16a   # config.json (2,351 B)
│   └── 496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4  # weights (327,212,226 B)
├── refs/main          # 40-hex commit hash, NO trailing newline   ← the gotcha
└── snapshots/f3ff3571791e39611d31c381e3a41a3af07b4987/
    ├── config.json -> ../../blobs/14a726edd3718279eac426630879ff743955b16a
    └── kokoro-v1_0.pth -> ../../blobs/496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4
```

The role bind-mounts the host dir `kokoro_model_cache_host_path` to container path
`kokoro_model_cache_container_path`:

| Var | Value |
|-----|-------|
| `kokoro_model_cache_host_path` | `/home/mkanavi/kokoro_hub/hub/models--hexgrad--Kokoro-82M` |
| `kokoro_model_cache_container_path` | `/var/lib/kokoro/hub/models--hexgrad--Kokoro-82M` |

> ⚠️ **Do NOT** point `kokoro_model_cache_host_path` at `/home/mkanavi/kokoro_hub/hub/Kokoro-82M`.
> That was an early, *incomplete* download (only the config blob). hfdl names its repo
> directory `models--hexgrad--Kokoro-82M` — that is the one to bind-mount.

---

## 2. THE BUG: trailing newline in `refs/main` (root cause of every offline failure)

HuggingFace Hub's `hf_file_download.py` resolves a branch name via:

```python
ref_path = os.path.join(storage_folder, "refs", revision)   # revision == "main"
with open(ref_path) as f:
    commit_hash = f.read()   # <-- .read() KEEPS the trailing newline
```

If `refs/main` is `<hash>\n`, then `commit_hash = "<hash>\n"`. The code then looks for
`snapshots/<hash>/…`, but the folder is `snapshots/<hash>` (no newline) → **miss** →
`LocalEntryNotFoundError`.

**Empirically proven on the host (HF 1.29.0, `snapshot_download`):**
- `refs/main = b"…f3ff3571…\n"` (with newline) → `SNAP_NO_REV_FAIL`
- `refs/main = b"…f3ff3571…"   ` (no newline) → `SNAP_NO_REV_OK`

**Fix:** strip the trailing newline so `refs/main` is exactly 40 bytes:

```bash
printf "%s" "$(cat refs/main)" > refs/main     # removes trailing \n
python3 -c "print(repr(open('refs/main','rb').read()))"   # -> b'f3ff3571...4987'  (len 40)
```

This is why the earlier handoff's "strip the newline" instruction was correct — and
why a naive `echo "$hash" > refs/main` (which appends `\n`) re-breaks it.

---

## 3. Authoritative hashes (do not trust the old `ed38dc2e…`)

| Artifact | sha256 (authoritative) | size |
|----------|------------------------|------|
| weights `.pth` blob | `496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4` | 327,212,226 B |
| `config.json` blob  | `14a726edd3718279eac426630879ff743955b16a` | 2,351 B |
| commit hash (refs/main) | `f3ff3571791e39611d31c381e3a41a3af07b4987` | 40 hex, no newline |

The old handoff's `ed38dc2e…` was a stale blob hash from an interrupted download — ignore it.

---

## 4. How to verify offline resolution yourself

Run inside a Python that has `huggingface_hub` (the host uses `/opt/hfdl-venv/bin/python`;
system `python3` does **not** have it):

```bash
/opt/hfdl-venv/bin/python - <<'PYEOF'
import os
os.environ["HF_HUB_OFFLINE"] = "1"
from huggingface_hub import snapshot_download, hf_hub_download

# This is the call Kokoro's loader makes (no revision):
d = snapshot_download("hexgrad/Kokoro-82M", allow_patterns=["kokoro-v1_0.pth","config.json"],
                      local_files_only=True)
print("SNAPSHOT_OK:", d)

# And a direct file resolve:
p = hf_hub_download("hexgrad/Kokoro-82M", "kokoro-v1_0.pth", repo_type="model",
                    revision="main")   # commit_hash shortcut requires the file to exist
print("HFD_OK:", p)
PYEOF
```

Expected: both print `*_OK` with paths under
`snapshots/f3ff3571…/`. If you get `LocalEntryNotFoundError`, re-check #2 (newline) and
#3 (blobs present + hashes match).

---

## 5. Docker design decisions (why it looks "worse" than a volume)

- **Host bind-mount, NOT a Docker named volume.** The weights must live on the host so
  they survive `docker compose down` and redeploys. A named volume (`kokoro-data`) would
  be wiped by `down` and re-created empty — defeating the offline cache. (A *previous*
  manual stack at `/home/mkanavi/docker/kokoro` used a volume; it predates the offline
  fix and is **not** what this role deploys.)
|- **Bridge mode** publishes only on `127.0.0.1:<port>` so the API is never exposed
  publicly (network_mode: host would bind `0.0.0.0`, defeating the loopback-only design).
  Cloudflare Tunnel routes `*.iacgenie.com → http://127.0.0.1:80` (this nginx).
- **No OpenBao dependency.** The role stores the generated API key at
  `/home/mkanavi/docker/kokoro/.api_key` (mode `0600`) and reuses it. OpenBao is not
  reachable from the homeserver, so auto-managing keys there would break offline deploys.

---

## 6. Deploying / tearing down (from the repo)

```bash
cd ~/.hermes/git_clone_dir/iacgenie-platform/infra/homeserver/kokoro
# Ensure the model cache is complete FIRST (see §2–3), then:
ansible-playbook -i inventory.ini playbooks/deploy.yml        # idempotent; fails fast if cache missing
ansible-playbook -i inventory.ini playbooks/teardown.yml      # removes containers + compose file
```

The role `tasks/main.yml` checks that `kokoro_model_cache_host_path` exists and fails
before pulling images if it does not — so a missing/incomplete cache is caught early.

---

## 7. Secrets (do NOT paste into chat or commit)

- HF token: `hf_xxx` — 37-char read-access key, injected via container env at deploy.
- API key: auto-generated random 32-char string, stored in `/home/mkanavi/docker/kokoro/.api_key`
  (mode `0600`). Pin your own with `-e kokoro_api_key=...` if you prefer a fixed key.
- sudo password: `[REDACTED]` — used only for the one-time `chown` of the download dir.

---

## 8. Watch items for the next person

1. **`refs/main` trailing newline** — the single most important thing (see §2).
   `echo "$hash" > refs/main` will re-break it; use `printf "%s"` instead.
2. **Container cache path** must be `/var/lib/kokoro/hub/models--hexgrad--Kokoro-82M`
   (the image sets `HF_HUB_CACHE=/var/lib/kokoro/hub`). A bare `/var/lib/kokoro` is wrong.
3. **No Docker volume** in the role's design — host bind-mount only, `KOKORO_LOCAL_ONLY=true`.
4. **Host cache path** is `/home/mkanavi/kokoro_hub/hub/models--hexgrad--Kokoro-82M`,
   *not* `.../hub/Kokoro-82M`.
5. **Authoritative blob hash** is `496dba118d…e4` (327,212,226 B). Ignore `ed38dc2e…`.
6. **`huggingface_hub` is in `/opt/hfdl-venv/bin/python`, not system `python3`.**
