---
name: ansible-service-audit
description: >
  Full automated service audit: reads all Ansible files for a service,
  launches 4 parallel subagent audits (DevOps+Antares, DevOps+VibeThinker,
  SecOps+Antares, SecOps+VibeThinker), consolidates findings, fixes genuine
  issues, redeploy, verify, and commit.
version: 1.0.0
tags: [ansible, audit, service, devops, secops, multi-agent, redeploy]
---

# Ansible Service Audit

Automated, multi-agent audit of any deployed service from the iacgenie-platform
Ansible roles. Produces 4 independent audit reports, consolidates them, fixes
genuine issues, redeploy, and commits.

## When to Use

- Before major service changes or upgrades
- Periodic infrastructure health audits
- After reported service issues or outages
- Pre-deployment hardening checks
- When the user says "audit <service>" or "fix <service>"

## Prerequisites

- **Repo:** `/Users/manjunathkanavi/iacgenie-platform` (already pulled)
- **VM:** `mkanavi@192.168.0.118`
- **Docker path:** `/home/mkanavi/docker/iacgenie`
- **Roles:** `infra/ansible/roles/<service>/`
- **Models:** Antares (`antares-1b-mlx-8bit`) on `127.0.0.1:1234`,
  VibeThinker (`VibeThinker-3B-OptiQ-4bit`) on `127.0.0.1:1234`,
  Self (`Qwen3.6-35B-A3B-UD-MLX-8bit`) — this agent
- **Role SOULs:** `.agent/devops-engineer/SOUL.md`, `.agent/secops-engineer/SOUL.md`

## Phase 1: Gather Service Context

### 1.1 Locate All Related Ansible Files

```bash
cd /Users/manjunathkanavi/iacgenie-platform
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
  "service": "lightserp-api",
  "container_name": "iacgenie_lightserp_api",
  "ansible_files": ["infra/ansible/roles/lightserp-api/tasks/main.yml", ...],
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

## Phase 2: Launch 4 Parallel Audits

Use `delegate_task` to spawn 4 subagents in parallel. Each receives:
- The service context (from Phase 1)
- The role SOUL (devops-engineer or secops-engineer)
- The model to use (antares or vibethinker)
- Instruction to produce a JSON audit report

### 2.1 Build Role Prompt

Load the appropriate SOUL file and prepend the service context:

```
You are a <role> following this SOUL:
<contents of .agent/<role>/SOUL.md>

AUDIT TARGET: <service-name>

CONTEXT:
<contents of /tmp/<service>_audit_context.json>

TASK: Perform a thorough audit of this service. Identify ALL problems:
- Configuration issues
- Security vulnerabilities
- Resource misconfigurations
- Missing best practices
- Health check problems
- Network exposure issues
- Secret management problems
- Docker security issues

OUTPUT FORMAT — return ONLY valid JSON:
{
  "service": "<service-name>",
  "role": "<devops-engineer|secops-engineer>",
  "model": "<antares|vibethinker>",
  "findings": [
    {
      "severity": "CRITICAL|HIGH|MEDIUM|LOW|INFO",
      "category": "security|configuration|resource|network|healthcheck|secrets|best-practice",
      "title": "Brief title",
      "description": "Detailed description of the issue",
      "files_affected": ["path/to/file"],
      "current_value": "...",
      "recommended_value": "...",
      "fix_command": "ansible fix command or manual fix",
      "ansible_files_to_modify": ["infra/ansible/roles/<service>/..."],
      "docker_compose_to_modify": true|false,
      "risk_if_unfixed": "What happens if this is not fixed"
    }
  ],
  "summary": "Overall assessment",
  "priority_order": ["fix 1", "fix 2", ...]
}
```

### 2.2 Launch 4 Delegations

```python
# The 4 audit tasks — launch all 4 in parallel
audit_tasks = [
    {
        "goal": "Audit service <SERVICE> from a DevOps perspective",
        "context": "<role_prompt_devops_antares>",
        "toolsets": ["terminal", "file", "web"],
        "acp_command": "copilot"  # Use Antares model via delegation config
    },
    {
        "goal": "Audit service <SERVICE> from a DevOps perspective using VibeThinker reasoning",
        "context": "<role_prompt_devops_vibethinker>",
        "toolsets": ["terminal", "file", "web"],
    },
    {
        "goal": "Audit service <SERVICE> from a SecOps perspective",
        "context": "<role_prompt_secops_antares>",
        "toolsets": ["terminal", "file", "web"],
    },
    {
        "goal": "Audit service <SERVICE> from a SecOps perspective using VibeThinker reasoning",
        "context": "<role_prompt_secops_vibethinker>",
        "toolsets": ["terminal", "file", "web"],
    },
]
```

**Note:** The model selection for each subagent is controlled by the
`delegation.model` config in `config.yaml`. Override per-task if needed.

### 2.3 Save Audit Results

Each subagent writes its JSON report to:
- `/tmp/<service>_devops_antares_audit.json`
- `/tmp/<service>_devops_vibethinker_audit.json`
- `/tmp/<service>_secops_antares_audit.json`
- `/tmp/<service>_secops_vibethinker_audit.json`

Wait for all 4 to complete before proceeding.

## Phase 3: Consolidate Audit Findings

### 3.1 Merge All Findings

Read all 4 JSON files and merge:

```python
import json
from collections import defaultdict

audit_files = [
    f"/tmp/{SERVICE}_devops_antares_audit.json",
    f"/tmp/{SERVICE}_devops_vibethinker_audit.json",
    f"/tmp/{SERVICE}_secops_antares_audit.json",
    f"/tmp/{SERVICE}_secops_vibethinker_audit.json",
]

all_findings = []
for f in audit_files:
    with open(f) as fh:
        data = json.load(fh)
        for finding in data.get("findings", []):
            finding["source"] = f.split("/")[-1].replace("_audit.json", "")
            all_findings.append(finding)
```

### 3.2 Deduplicate

Group findings by `(category, title)` — if the same issue is found by
multiple auditors, keep it once and note which auditors flagged it:

```python
seen = {}
deduped = []
for f in all_findings:
    key = (f["category"], f["title"])
    if key not in seen:
        seen[key] = f
        f["found_by"] = [f["source"]]
        deduped.append(f)
    else:
        seen[key]["found_by"].append(f["source"])

# Sort: CRITICAL first, then HIGH, MEDIUM, LOW, INFO
severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
deduped.sort(key=lambda x: severity_order.get(x["severity"], 99))
```

### 3.3 Write Consolidated Report

Save to `/tmp/<service>_consolidated_audit.json` and
`infra/docs/<service>-audit-report.md`.

## Phase 4: Validate & Filter Findings

### 4.1 Review Each Finding

For each finding, verify it is genuine:

1. **Read the actual Ansible file** referenced in `files_affected`
2. **Read the live docker-compose entry** for the service
3. **SSH to VM** and check the live state if needed
4. **Cross-reference** — does the issue exist in BOTH the template AND live state?

### 4.2 Classify Findings

| Category | Action |
|----------|--------|
| **Genuine + Critical** | Fix immediately |
| **Genuine + High** | Fix in same batch |
| **Genuine + Medium** | Fix if quick/safe |
| **False positive** | Skip, note why |
| **Info only** | Skip |

### 4.3 Write Fix Plan

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

## Phase 5: Apply Fixes

### 5.1 Fix Ansible Role Files

For each fix, use the `patch` tool to modify the Ansible role files:

```bash
# Example: Fix a docker-compose template issue
patch(path="infra/ansible/roles/<service>/templates/docker-compose.service.yml.j2",
      old_string="old config line",
      new_string="new config line")
```

### 5.2 Fix Docker Compose Templates

If the issue requires docker-compose changes, update the template:

```bash
patch(path="infra/docker-compose/docker-compose-unified.yml.j2",
      old_string="old compose line",
      new_string="new compose line")
```

### 5.3 Fix Nginx/Cloudflare If Needed

```bash
patch(path="infra/ansible/roles/nginx/templates/nginx-unified.conf.j2", ...)
patch(path="infra/ansible/roles/cloudflare_tunnel/templates/config.yml.j2", ...)
```

### 5.4 Validate Ansible Syntax

Before deploying, validate:

```bash
cd /Users/manjunathkanavi/iacgenie-platform/infra/ansible
ansible-playbook -i inventory/hosts.yml site.yml --check -l <service> --tags validate
```

## Phase 6: Redeploy Service

### 6.1 Clean Up Existing Service

```bash
# SSH to VM and stop/remove the service container
ssh mkanavi@192.168.0.118 "docker stop iacgenie_<service> && docker rm iacgenie_<service>"
ssh mkanavi@192.168.0.118 "docker rmi -f <image>"  # if needed
```

### 6.2 Run Ansible Playbook

```bash
cd /Users/manjunathkanavi/iacgenie-platform/infra/ansible
ansible-playbook -i inventory/hosts.yml playbooks/services.yml -l <service> --tags deploy
```

### 6.3 Or Deploy Compose Changes Directly

If changes are only in docker-compose:

```bash
# Sync compose file to VM
scp infra/docker-compose/docker-compose-unified.yml mkanavi@192.168.0.118:/tmp/
ssh mkanavi@192.168.0.118 "cp /tmp/docker-compose-unified.yml /home/mkanavi/docker/iacgenie/docker-compose-unified.yml && cd /home/mkanavi/docker/iacgenie && docker compose up -d <service> --force-recreate"
```

## Phase 7: Verify Service

### 7.1 Container Health

```bash
ssh mkanavi@192.168.0.118 "docker ps --filter name=iacgenie_<service> --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
ssh mkanavi@192.168.0.118 "docker logs iacgenie_<service> --tail 20"
```

### 7.2 Service Reachability

```bash
# Internal check (from VM)
ssh mkanavi@192.168.0.118 "curl -sf http://127.0.0.1:<PORT>/health || echo 'UNREACHABLE'"

# External check (via Cloudflare)
curl -sI "https://<domain>.iacgenie.com/health" | head -5
```

### 7.3 Health Check Endpoints

```bash
# Check specific health endpoint
ssh mkanavi@192.168.0.118 "docker exec iacgenie_<service> curl -sf http://127.0.0.1:<PORT>/health"
```

### 7.4 Verification Checklist

| Check | Command | Expected |
|-------|---------|----------|
| Container running | `docker ps | grep <service>` | `Up` status |
| No errors in logs | `docker logs --tail 50` | No ERROR/FATAL |
| Health endpoint | `curl <health-url>` | 200 OK |
| Nginx proxying | `curl -H 'Host: <domain>' http://127.0.0.1` | 200/redirect |
| Cloudflare tunnel | `curl -sI https://<domain>` | 200 OK |
| Ansible idempotent | `ansible-playbook --check` | `changed=0` |

## Phase 8: Commit & Push

```bash
cd /Users/manjunathkanavi/iacgenie-platform

# Stage all changes
git add -A

# Commit with audit summary
git commit -m "audit: <service> multi-agent audit fixes

Automated audit with 4 parallel agents (DevOps+Antares, DevOps+VibeThinker,
SecOps+Antares, SecOps+VibeThinker). Consolidated <N> findings, fixed <M>
genuine issues.

Findings: <N> total, <M> fixed, <K> skipped (false positive/info)
Services redeployed: <service>
Verification: all health checks passing

Fixes applied:
- <fix 1>
- <fix 2>
- ..."

git push origin main
```

## Quick Reference

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
| `/tmp/<service>_devops_antares_audit.json` | DevOps + Antares audit |
| `/tmp/<service>_devops_vibethinker_audit.json` | DevOps + VibeThinker audit |
| `/tmp/<service>_secops_antares_audit.json` | SecOps + Antares audit |
| `/tmp/<service>_secops_vibethinker_audit.json` | SecOps + VibeThinker audit |
| `/tmp/<service>_consolidated_audit.json` | Merged/deduped findings |
| `/tmp/<service>_fix_plan.json` | Approved fix list |
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

### Related Skills

- `devops` — Infrastructure debugging, service teardown, deployment patterns
- `antares-security-audit` — Direct Antares model security audit
- `infra-drift-audit` — Ansible template vs live VM drift comparison
- `docker-compose-drift-remediation` — Docker compose drift detection
- `service-security-audit` — Service-level security audit workflow
