---
name: ansible-service-audit
description: >
  Full automated service audit: reads all Ansible files for a service,
  launches 6 parallel audits (Self+DevOps, Self+SecOps, Antares+DevOps,
  Antares+SecOps, VibeThinker+DevOps, VibeThinker+SecOps), consolidates
  findings, fixes genuine issues, redeploy, verify, and commit.
version: 3.0.0
tags: [ansible, audit, service, devops, secops, multi-agent, redeploy]
---

# Ansible Service Audit

Automated, multi-agent audit of any deployed service from the iacgenie-platform
Ansible roles. Produces 6 independent audit reports from 3 models × 2 roles,
consolidates them, fixes genuine issues, redeploy, and commits.

## When to Use

- Before major service changes or upgrades
- Periodic infrastructure health audits
- After reported service issues or outages
- Pre-deployment hardening checks
- When the user says "audit <service>" or "fix <service>"

## Environment Variables (configurable)

| Variable | Default | Purpose |
|----------|---------|---------|
| `REPO_ROOT` | `/Users/manjunathkanavi/iacgenie-platform` | Git repo root |
| `VM_HOST` | `mkanavi@192.168.0.118` | SSH target |
| `DOCKER_PATH` | `/home/mkanavi/docker/iacgenie` | Docker compose dir |
| `MODEL_API_URL` | `http://127.0.0.1:1234/v1/chat/completions` | Remote model API |
| `MODEL_TIMEOUT` | `300` | Per-request timeout (seconds) |
| `MODEL_RETRIES` | `2` | Retry attempts on failure |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ansible-service-audit (parent)            │
│                    whatever model this agent runs on         │
└──────────┬─────────────────────────────────┬────────────────┘
           │                                 │
    ┌──────▼───────┐              ┌──────────▼──────────┐
    │ delegate_task│              │ ThreadPoolExecutor   │
    │ (Self+DevOps)│              │ (4 parallel curl     │
    │ (full tools) │              │  calls: Antares×2,   │
    └──────┬───────┘              │  VibeThinker×2)      │
    │                    ┌────────┴──────────────────┐
    │                    │                           │
    │              ┌─────▼──────┐            ┌──────▼─────┐
    │              │ Antares    │            │ VibeThinker│
    │              │ + DevOps   │            │ + DevOps   │
    │              └─────┬──────┘            └──────┬─────┘
    │                    │                           │
    │              ┌─────▼──────┐            ┌──────▼─────┐
    │              │ Antares    │            │ VibeThinker│
    │              │ + SecOps   │            │ + SecOps   │
    │              └────────────┘            └────────────┘
    │
    └──────────────┬──────────────────────────┘
                   │
            ┌──────▼──────┐
            │ Self + SecOps│
            │ (full tools) │
            └─────────────┘
```

**Key design decisions:**
- Self (this agent) uses `delegate_task` with full tool access (file, terminal, search)
- Antares and VibeThinker do NOT support tool/function calling — they are pure text-in/text-out
- All 4 remote calls run in parallel via `ThreadPoolExecutor`
- The parent orchestrates; no model spawns sub-agents

## Prerequisites

- **Repo:** `$REPO_ROOT` (already pulled)
- **VM:** `$VM_HOST`
- **Docker path:** `$DOCKER_PATH`
- **Roles:** `infra/ansible/roles/<service>/`
- **Remote models:** Antares (`antares-1b-mlx-8bit`) and
  VibeThinker (`VibeThinker-3B-OptiQ-4bit`) on `$MODEL_API_URL`
  (no tool calling, text-only)
- **Self model:** Whatever this agent runs on (no hardcoded model names)
- **Role SOULs:** `REPO_ROOT/.agent/devops-engineer/SOUL.md`,
  `REPO_ROOT/.agent/secops-engineer/SOUL.md`
- **Remote model wrapper:** `~/.hermes/skills/ansible-service-audit/scripts/remote_model_caller.py`

## Phase 1: Gather Service Context

### 1.1 Locate All Related Ansible Files

```bash
cd $REPO_ROOT
SERVICE="<service-name>"

# Find all ansible role files for this service
find infra/ansible/roles -path "*${SERVICE}*" -type f \( -name "*.yml" -o -name "*.yaml" -o -name "*.j2" -o -name "*.py" \) | sort

# Also check docker-compose templates
find infra/docker-compose -name "*${SERVICE}*" -type f 2>/dev/null | sort

# Check if service has its own role directory
ls -d infra/ansible/roles/${SERVICE}/ 2>/dev/null
```

### 1.2 Collect Service Context

Read and compress the following into a context package:

1. **Ansible role files** — all `.yml`, `.yaml`, `.j2` in `infra/ansible/roles/<service>/`
2. **Docker compose entry** — the service definition in `infra/docker-compose/docker-compose-unified.yml`
3. **Nginx vHost** — if the service has a public URL, extract the nginx server block
4. **Cloudflare tunnel rule** — if applicable, extract the ingress rule
5. **Keycloak client** — if applicable, extract the OIDC client config
6. **Live VM state** — `docker inspect <container>`, `docker logs --tail 50`, `docker ps --filter name=<container>`

### 1.3 Build Context Package

Write a JSON context file at `/tmp/<service>_audit_context.json`:

```json
{
  "service": "openbao",
  "container_name": "iacgenie_openbao",
  "ansible_files": ["infra/ansible/roles/openbao/tasks/main.yml", ...],
  "compose_entry": "...",
  "nginx_vhost": "...",
  "cloudflare_rule": "...",
  "live_state": {
    "docker_inspect": "...",
    "docker_logs": "...",
    "docker_ps": "..."
  }
}
```

### 1.4 Validate Prerequisites

Before launching audits, verify required files exist:

```bash
# Check SOUL files
test -f "$REPO_ROOT/.agent/devops-engineer/SOUL.md" || echo "MISSING: devops-engineer SOUL"
test -f "$REPO_ROOT/.agent/secops-engineer/SOUL.md" || echo "MISSING: secops-engineer SOUL"

# Check wrapper script
test -f ~/.hermes/skills/ansible-service-audit/scripts/remote_model_caller.py || echo "MISSING: remote_model_caller.py"

# Check context file
test -f /tmp/${SERVICE}_audit_context.json || echo "MISSING: audit context"
```

If any prerequisite is missing, abort or skip the affected audits.

## Phase 2: Launch 6 Parallel Audits

### 2.1 Self Audits (delegate_task — full tool access)

Launch 2 subagents using `delegate_task`. These run with full tool access
(file, terminal, search) and can read files and SSH to VM.

**Self + DevOps:**
```python
# Specify exact files to read (not "all" — be explicit)
ansible_files = $(find "$REPO_ROOT/infra/ansible/roles/${SERVICE}" -type f \( -name "*.yml" -o -name "*.yaml" -o -name "*.j2" -o -name "*.py" \) | sort | tr '\n' ',')

delegate_task(
    goal=f"Audit service {SERVICE} from a DevOps perspective",
    context=f"You are a DevOps Engineer following this SOUL:\n{read_file('$REPO_ROOT/.agent/devops-engineer/SOUL.md')}\n\nAUDIT TARGET: {SERVICE}\n\nCONTEXT:\n{read_file('/tmp/{SERVICE}_audit_context.json')}\n\nFILES TO READ:\n{ansible_files}\n\nTASK: Read the files above and perform a thorough DevOps audit. Identify ALL configuration, resource, health, backup, automation, and operational issues.\n\nOUTPUT — return ONLY valid JSON:\n{{\"service\": \"{SERVICE}\", \"role\": \"devops-engineer\", \"model\": \"self\", \"findings\": [...], \"summary\": \"...\", \"priority_order\": [...]}}",
    toolsets=["file", "terminal", "search"]
)
```

**Self + SecOps:**
```python
delegate_task(
    goal=f"Audit service {SERVICE} from a SecOps perspective",
    context=f"You are a SecOps Engineer following this SOUL:\n{read_file('$REPO_ROOT/.agent/secops-engineer/SOUL.md')}\n\nAUDIT TARGET: {SERVICE}\n\nCONTEXT:\n{read_file('/tmp/{SERVICE}_audit_context.json')}\n\nFILES TO READ:\n{ansible_files}\n\nTASK: Read the files above and perform a thorough security audit. Identify ALL security problems.\n\nOUTPUT — return ONLY valid JSON:\n{{\"service\": \"{SERVICE}\", \"role\": \"secops-engineer\", \"model\": \"self\", \"findings\": [...], \"summary\": \"...\", \"priority_order\": [...]}}",
    toolsets=["file", "terminal", "search"]
)
```

### 2.2 Remote Model Audits (curl — text only, no tool calling)

Antares and VibeThinker do NOT support tool calling. Use the wrapper script
with parallel execution.

**The clean approach** — build a JSON prompt file and call all 4 in parallel:

```python
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

WRAPPER = Path.home() / ".hermes" / "skills" / "ansible-service-audit" / "scripts" / "remote_model_caller.py"
SERVICE = "openbao"
CONTEXT = json.loads(Path("/tmp/${SERVICE}_audit_context.json").read_text())

# Build the prompt — embed file paths, not full contents
def build_prompt(role: str, model_name: str) -> str:
    return json.dumps({
        "service": SERVICE,
        "role": role,
        "model": model_name,
        "context": CONTEXT,
        "ansible_files": CONTEXT.get("ansible_files", []),
        "task": f"Perform a thorough {role.lower()} audit of {SERVICE}. Read the context and file paths above. Identify ALL issues. Return JSON: {{'service','role','model','findings':[{{'severity','category','title','description','files_affected','current_value','recommended_value','fix_command','risk_if_unfixed'}}],'summary','priority_order'}}"
    })

# Define the 4 remote audits
remote_tasks = [
    ("antares-1b-mlx-8bit", "devops-engineer", f"/tmp/{SERVICE}_devops_antares_audit.json"),
    ("antares-1b-mlx-8bit", "secops-engineer", f"/tmp/{SERVICE}_secops_antares_audit.json"),
    ("VibeThinker-3B-OptiQ-4bit", "devops-engineer", f"/tmp/{SERVICE}_devops_vibethinker_audit.json"),
    ("VibeThinker-3B-OptiQ-4bit", "secops-engineer", f"/tmp/{SERVICE}_secops_vibethinker_audit.json"),
]

# Run in parallel
results = {}
with ThreadPoolExecutor(max_workers=4) as pool:
    futures = {}
    for model, role, output_file in remote_tasks:
        prompt = build_prompt(role, model)
        futures[output_file] = pool.submit(
            subprocess.run,
            ["python3", str(WRAPPER), model,
             f"You are a senior {role.replace('-',' ')} auditing infrastructure.",
             prompt],
            capture_output=True, text=True
        )
    for output_file, future in futures.items():
        try:
            r = future.result(timeout=360)
            results[output_file] = r.stdout.strip()
        except Exception as e:
            results[output_file] = json.dumps({"error": str(e), "success": False})

# Write results
for output_file, content in results.items():
    Path(output_file).write_text(content)
```

### 2.3 Save Audit Results

Each audit writes its JSON report to:

| # | Role | Model | Output File |
|---|------|-------|-------------|
| 1 | DevOps | Self | `/tmp/<service>_devops_self_audit.json` |
| 2 | SecOps | Self | `/tmp/<service>_secops_self_audit.json` |
| 3 | DevOps | Antares | `/tmp/<service>_devops_antares_audit.json` |
| 4 | SecOps | Antares | `/tmp/<service>_secops_antares_audit.json` |
| 5 | DevOps | VibeThinker | `/tmp/<service>_devops_vibethinker_audit.json` |
| 6 | SecOps | VibeThinker | `/tmp/<service>_secops_vibethinker_audit.json` |

Wait for all 6 to complete before proceeding.

## Phase 3: Quality Gates

### 3.1 Validate All 6 Reports Exist and Are Valid JSON

```python
import json
from pathlib import Path

audit_files = [
    f"/tmp/{SERVICE}_devops_self_audit.json",
    f"/tmp/{SERVICE}_secops_self_audit.json",
    f"/tmp/{SERVICE}_devops_antares_audit.json",
    f"/tmp/{SERVICE}_secops_antares_audit.json",
    f"/tmp/{SERVICE}_devops_vibethinker_audit.json",
    f"/tmp/{SERVICE}_secops_vibethinker_audit.json",
]

missing = []
invalid = []
for f in audit_files:
    if not Path(f).exists():
        missing.append(f)
    else:
        try:
            data = json.loads(Path(f).read_text())
            if "findings" not in data:
                invalid.append(f)
        except json.JSONDecodeError:
            invalid.append(f)

if missing:
    print(f"MISSING reports: {missing}")
if invalid:
    print(f"INVALID reports: {invalid}")

if missing or invalid:
    print("ABORTING — not all 6 reports are valid. Fix before proceeding.")
    # Optionally retry the failed ones
```

### 3.2 Record Audit Trail

```python
import time, hashlib

trail = {
    "audit_date": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "service": SERVICE,
    "repo_root": "$REPO_ROOT",
    "vm_host": "$VM_HOST",
    "models_used": {
        "self": "auto-detect",
        "antares": "antares-1b-mlx-8bit",
        "vibethinker": "VibeThinker-3B-OptiQ-4bit",
    },
    "report_hashes": {},
    "reports": audit_files,
}

for f in audit_files:
    if Path(f).exists():
        trail["report_hashes"][f] = hashlib.sha256(Path(f).read_bytes()).hexdigest()

Path(f"/tmp/{SERVICE}_audit_trail.json").write_text(json.dumps(trail, indent=2))
```

## Phase 4: Consolidate Audit Findings

### 4.1 Merge All Findings

```python
import json
from pathlib import Path

audit_files = [
    f"/tmp/{SERVICE}_devops_self_audit.json",
    f"/tmp/{SERVICE}_secops_self_audit.json",
    f"/tmp/{SERVICE}_devops_antares_audit.json",
    f"/tmp/{SERVICE}_secops_antares_audit.json",
    f"/tmp/{SERVICE}_devops_vibethinker_audit.json",
    f"/tmp/{SERVICE}_secops_vibethinker_audit.json",
]

all_findings = []
for f in audit_files:
    with open(f) as fh:
        data = json.load(fh)
        for finding in data.get("findings", []):
            finding["source"] = Path(f).stem.replace("_audit", "")
            all_findings.append(finding)
```

### 4.2 Deduplicate with Fuzzy Matching

Group findings by normalized title similarity. If two findings have the same
category and titles that are 80%+ similar, merge them:

```python
import re

def normalize(s: str) -> str:
    """Normalize a string for comparison: lowercase, strip punctuation, collapse whitespace."""
    return re.sub(r'[^a-z0-9\s]', '', s.lower()).strip()

def similarity(a: str, b: str) -> float:
    """Simple Jaccard similarity on word sets."""
    wa, wb = set(normalize(a).split()), set(normalize(b).split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)

seen = {}
deduped = []
for f in all_findings:
    key = (f["category"], f["title"])
    merged = False
    for existing in deduped:
        if existing["category"] == f["category"] and similarity(existing["title"], f["title"]) >= 0.8:
            existing["found_by"].append(f["source"])
            existing["description"] = f"{existing['description']} | {f['description']}"
            merged = True
            break
    if not merged:
        f["found_by"] = [f["source"]]
        deduped.append(f)

# Sort: CRITICAL first, then HIGH, MEDIUM, LOW, INFO
severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
deduped.sort(key=lambda x: severity_order.get(x["severity"], 99))
```

### 4.3 Write Consolidated Report

Save to `/tmp/<service>_consolidated_audit.json` and
`infra/docs/<service>-audit-report.md`.

## Phase 5: Validate & Filter Findings

### 5.1 Review Each Finding

For each finding, verify it is genuine:

1. **Read the actual Ansible file** referenced in `files_affected`
2. **Read the live docker-compose entry** for the service
3. **SSH to VM** and check the live state if needed
4. **Cross-reference** — does the issue exist in BOTH the template AND live state?

### 5.2 Classify Findings

| Category | Action |
|----------|--------|
| **Genuine + Critical** | Fix immediately |
| **Genuine + High** | Fix in same batch |
| **Genuine + Medium** | Fix if quick/safe |
| **False positive** | Skip, note why |
| **Info only** | Skip |

### 5.3 Write Fix Plan

Save to `/tmp/<service>_fix_plan.json`:

```json
{
  "service": "<service>",
  "fixes": [
    {
      "finding_id": 1,
      "title": "...",
      "severity": "HIGH",
      "files_to_modify": ["infra/ansible/roles/<service>/tasks/main.yml"],
      "fix_description": "...",
      "risk": "low"
    }
  ],
  "skip": [
    {
      "finding_id": 3,
      "reason": "False positive — current value is correct"
    }
  ]
}
```

## Phase 5.5: Dry-Run Mode

Before applying any fixes, run a dry-run to preview changes:

```bash
# Dry-run: show what would be changed without modifying files
cd $REPO_ROOT
for file in $(python3 -c "import json; import sys; print('\\n'.join(json.load(open('/tmp/${SERVICE}_fix_plan.json'))['fixes']))" | grep -o '"files_to_modify": \[[^]]*\]' | grep -o '"[^"]*\.yml"'); do
    echo "Would modify: $file"
done

# Or use ansible --check
cd $REPO_ROOT/infra/ansible
ansible-playbook -i inventory/hosts.yml site.yml --check -l <service>
```

If the dry-run reveals issues, adjust the fix plan before proceeding.

## Phase 6: Apply Fixes

### 6.1 Snapshot Current State (for rollback)

```bash
# Create a rollback snapshot before any changes
BACKUP_DIR="/tmp/${SERVICE}_rollback_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Snapshot Ansible role files that will be modified
for f in $(python3 -c "import json; print('\\n'.join(json.load(open('/tmp/${SERVICE}_fix_plan.json'))['fixes']))" | grep -o '"files_to_modify": \[[^]]*\]' | grep -o '"[^"]*"' | tr -d '"'); do
    cp "$REPO_ROOT/$f" "$BACKUP_DIR/" 2>/dev/null
done

# Snapshot docker-compose
cp "$DOCKER_PATH/docker-compose-unified.yml" "$BACKUP_DIR/" 2>/dev/null

echo "Rollback snapshot: $BACKUP_DIR"
```

### 6.2 Fix Ansible Role Files

For each fix, use the `patch` tool to modify the Ansible role files:

```bash
patch(path="infra/ansible/roles/<service>/templates/docker-compose.service.yml.j2",
      old_string="old config line",
      new_string="new config line")
```

### 6.3 Fix Docker Compose Templates

If the issue requires docker-compose changes, update the template:

```bash
patch(path="infra/docker-compose/docker-compose-unified.yml.j2",
      old_string="old compose line",
      new_string="new compose line")
```

### 6.4 Fix Nginx/Cloudflare If Needed

```bash
patch(path="infra/ansible/roles/nginx/templates/nginx-unified.conf.j2", ...)
patch(path="infra/ansible/roles/cloudflare_tunnel/templates/config.yml.j2", ...)
```

### 6.5 Validate Ansible Syntax

Before deploying, validate:

```bash
cd $REPO_ROOT/infra/ansible
ansible-playbook -i inventory/hosts.yml site.yml --check -l <service> --tags validate
```

## Phase 7: Redeploy Service

### 7.1 Clean Up Existing Service

```bash
ssh $VM_HOST "docker stop iacgenie_<service> && docker rm iacgenie_<service>"
ssh $VM_HOST "docker rmi -f <image>"  # if needed
```

### 7.2 Run Ansible Playbook

```bash
cd $REPO_ROOT/infra/ansible
ansible-playbook -i inventory/hosts.yml playbooks/services.yml -l <service> --tags deploy
```

### 7.3 Or Deploy Compose Changes Directly

If changes are only in docker-compose:

```bash
scp infra/docker-compose/docker-compose-unified.yml $VM_HOST:/tmp/
ssh $VM_HOST "cp /tmp/docker-compose-unified.yml $DOCKER_PATH/docker-compose-unified.yml && cd $DOCKER_PATH && docker compose up -d <service> --force-recreate"
```

## Phase 8: Verify Service

### 8.1 Container Health

```bash
ssh $VM_HOST "docker ps --filter name=iacgenie_<service> --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
ssh $VM_HOST "docker logs iacgenie_<service> --tail 20"
```

### 8.2 Service Reachability

```bash
ssh $VM_HOST "curl -sf http://127.0.0.1:<PORT>/health || echo 'UNREACHABLE'"
curl -sI "https://<domain>.iacgenie.com/health" | head -5
```

### 8.3 Health Check Endpoints

```bash
ssh $VM_HOST "docker exec iacgenie_<service> curl -sf http://127.0.0.1:<PORT>/health"
```

### 8.4 Verification Checklist

| Check | Command | Expected |
|-------|---------|----------|
| Container running | `docker ps | grep <service>` | `Up` status |
| No errors in logs | `docker logs --tail 50` | No ERROR/FATAL |
| Health endpoint | `curl <health-url>` | 200 OK |
| Nginx proxying | `curl -H 'Host: <domain>' http://127.0.0.1` | 200/redirect |
| Cloudflare tunnel | `curl -sI https://<domain>` | 200 OK |
| Ansible idempotent | `ansible-playbook --check` | `changed=0` |

## Phase 9: Commit & Push

```bash
cd $REPO_ROOT

# Stage all changes
git add -A

# Commit with audit summary
git commit -m "audit: <service> 6-model multi-agent audit fixes

Automated audit with 6 parallel audits (Self+DevOps, Self+SecOps,
Antares+DevOps, Antares+SecOps, VibeThinker+DevOps, VibeThinker+SecOps).
Consolidated <N> findings, fixed <M> genuine issues.

Findings: <N> total, <M> fixed, <K> skipped (false positive/info)
Services redeployed: <service>
Verification: all health checks passing

Fixes applied:
- <fix 1>
- <fix 2>
- ..."

git push origin main
```

## Rollback

If fixes break the service, rollback to the snapshot:

```bash
# List latest rollback snapshot
ls -td /tmp/${SERVICE}_rollback_* | head -1

# Restore files
cp /tmp/${SERVICE}_rollback_*/<filename> $REPO_ROOT/<filename>

# Redeploy
ansible-playbook -i $REPO_ROOT/infra/ansible/inventory/hosts.yml playbooks/services.yml -l <service> --tags deploy
```

## Quick Reference

### Model Architecture

| Model | Access Type | Tool Calling | Use |
|-------|-------------|--------------|-----|
| Self (this agent) | `delegate_task` | ✅ Full tools | DevOps + SecOps audits |
| Antares | `curl` (text-only) | ❌ No | DevOps + SecOps audits |
| VibeThinker | `curl` (text-only) | ❌ No | DevOps + SecOps audits |

### 6 Audit Matrix

| # | Role | Model | Output File |
|---|------|-------|-------------|
| 1 | DevOps | Self | `_devops_self_audit.json` |
| 2 | SecOps | Self | `_secops_self_audit.json` |
| 3 | DevOps | Antares | `_devops_antares_audit.json` |
| 4 | SecOps | Antares | `_secops_antares_audit.json` |
| 5 | DevOps | VibeThinker | `_devops_vibethinker_audit.json` |
| 6 | SecOps | VibeThinker | `_secops_vibethinker_audit.json` |

### Service Name Mapping

| User Input | Service Name | Container | Ansible Role |
|------------|-------------|-----------|-------------|
| postgres | postgresql | iacgenie_postgres | `infra/ansible/roles/postgresql/` |
| redis | redis | iacgenie_redis | `infra/ansible/roles/redis/` |
| minio | minio | iacgenie_minio | `infra/ansible/roles/minio/` |
| openbao | openbao | iacgenie_openbao | `infra/ansible/roles/openbao/` |
| keycloak | keycloak | iacgenie_keycloak | `infra/ansible/roles/keycloak/` |
| gitea | gitea | iacgenie_gitea | `infra/ansible/roles/gitea/` |
| lightserp-api | lightserp-api | iacgenie_lightserp_api | `infra/ansible/roles/lightserp-api/` |
| lightserp-webui | lightserp-webui | iacgenie_lightserp_webui | `infra/ansible/roles/lightserp/` |
| searxng | searxng | iacgenie_searxng | `infra/ansible/roles/searxng/` |
| pagezen | pagezen | iacgenie_pagezen | `infra/ansible/roles/pagezen/` |
| nginx | nginx | (systemd) | `infra/ansible/roles/nginx/` |
| cloudflared | cloudflared | (systemd) | `infra/ansible/roles/cloudflared/` |

### Audit File Locations

| File | Purpose |
|------|---------|
| `/tmp/<service>_audit_context.json` | Service context package |
| `/tmp/<service>_devops_self_audit.json` | Self + DevOps audit |
| `/tmp/<service>_secops_self_audit.json` | Self + SecOps audit |
| `/tmp/<service>_devops_antares_audit.json` | Antares + DevOps audit |
| `/tmp/<service>_secops_antares_audit.json` | Antares + SecOps audit |
| `/tmp/<service>_devops_vibethinker_audit.json` | VibeThinker + DevOps audit |
| `/tmp/<service>_secops_vibethinker_audit.json` | VibeThinker + SecOps audit |
| `/tmp/<service>_consolidated_audit.json` | Merged/deduped findings |
| `/tmp/<service>_fix_plan.json` | Approved fix list |
| `/tmp/<service>_audit_trail.json` | Audit trail (timestamps, hashes) |
| `/tmp/<service>_rollback_*` | Rollback snapshots |
| `infra/docs/<service>-audit-report.md` | Human-readable report |

### Pitfalls

1. **Don't mix Jinja2 and shell syntax** — docker-compose files use `${VAR}`, NOT `{{ }}`
2. **Service names in docker-compose are kebab-case** (`iacgenie_lightserp_api`) but role dirs may differ
3. **Always validate ansible syntax before deploy** — `--check` mode catches template errors
4. **Force-recreate containers** after env var changes — `docker restart` won't pick up new vars
5. **Nginx reload ≠ restart** — use `reload` to avoid dropping connections
6. **Cloudflared needs restart, not reload** — it has no SIGHUP handler
7. **SSH to VM for live verification** — templates may differ from deployed state
8. **Remember to update both template AND live** — Ansible SOT pattern
9. **Remote models don't support tool calling** — pass all context as text in curl
10. **Self model is not hardcoded** — whatever this agent runs on is "self"
11. **Always validate prerequisites** (SOULs, wrapper, context) before launching audits
12. **Use dry-run before applying fixes** — prevents breaking changes
13. **Snapshot before fixing** — enables rollback if fixes break things

### Related Skills

- `multi-model-service-audit` — Reference alias (load `ansible-service-audit` instead)
- `infra-drift-audit` — Ansible template vs live VM drift comparison
- `docker-compose-drift-remediation` — Docker compose drift detection
- `service-security-audit` — Service-level security audit workflow
