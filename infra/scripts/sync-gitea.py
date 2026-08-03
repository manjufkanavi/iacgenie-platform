#!/usr/bin/env python3
"""
GitHub -> Gitea Sync Script with Daily Email Report

Synchronizes repositories from GitHub to Gitea via internal HTTP port 3000.
Sends HTML email report on sync status via SMTP2GO REST API.

Usage:
    python3 sync-gitea.py              # Sync all repos
    python3 sync-gitea.py --test-email # Test SMTP email delivery

Environment Variables:
    GITHUB_PAT     - GitHub Personal Access Token
    GITEA_PASS     - Gitea admin password
    GITEA_BASE_URL - Gitea API base URL (internal: http://localhost:3000)
    SMTP2GO_API_KEY- SMTP2GO API key for email reports
    SMTP2GO_FROM   - Sender email (default: admin@zencloudsec.com)
    SMTP2GO_TO     - Recipient email (default: manjufkanavi@gmail.com)
"""

import subprocess
import sys
import os
import json
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError

# Configuration

GITHUB_TOKEN   = os.environ.get("GITHUB_PAT", "")
GITEA_PASS     = os.environ.get("GITEA_PASS", "")
GITHUB_ORG     = "manjufkanavi"
GITEA_BASE_URL = os.environ.get("GITEA_BASE_URL", "127.0.0.1:3000")
REPO_DIR       = "/tmp/gitea-sync-work"
LOG_FILE       = "/home/mkanavi/bin/sync-gitea.log"

# SMTP2GO REST API Config
SMTP2GO_API_KEY = os.environ.get("SMTP2GO_API_KEY", "")
SMTP2GO_FROM    = os.environ.get("SMTP2GO_FROM", "admin@zencloudsec.com")
SMTP2GO_TO      = os.environ.get("SMTP2GO_TO", "manjufkanavi@gmail.com")
SMTP2GO_URL     = "https://api.smtp2go.com/v3/email/send"

REPOS = [
    {"name": "iacgenie", "gitea_name": "iacgenie"},
    {"name": "LightSerp", "gitea_name": "lightserp"},
    {"name": "iacgenie-unified-infra", "gitea_name": "iacgenie-unified-infra"},
]


# Helpers

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = "[{}] {}".format(ts, msg)
    print(line)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def git_cmd(*args, cwd=None):
    cmd = ["git"] + list(args)
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=300)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


# Sync Logic

def sync_repo(repo):
    """Sync a single repo from GitHub to Gitea."""
    name   = repo["name"]
    gname  = repo["gitea_name"]
    log("=== Syncing: {} ===".format(name))

    gh_url   = "https://x-access-token:{}@github.com/{}/{}.git".format(
        GITHUB_TOKEN, GITHUB_ORG, name)
    gitea_url = "http://{}:{}@{}/{}/{}.git".format(
        GITHUB_ORG, GITEA_PASS, GITEA_BASE_URL, GITHUB_ORG, gname)

    work_dir = os.path.join(REPO_DIR, name)
    os.makedirs(REPO_DIR, exist_ok=True)

    if os.path.isdir(os.path.join(work_dir, ".git")):
        git_cmd("remote", "set-url", "origin", gh_url, cwd=work_dir)
        git_cmd("fetch", "origin", cwd=work_dir)
        git_cmd("remote", "set-url", "gitea", gitea_url, cwd=work_dir)
        p = git_cmd("pull", "--rebase", "gitea", "main", cwd=work_dir)
        if p[0] != 0:
            log("  Remote has divergent content, forcing sync from GitHub")
            git_cmd("fetch", "origin", "main", cwd=work_dir)
            git_cmd("reset", "--hard", "origin/main", cwd=work_dir)
        git_cmd("push", "gitea", "--all", "--force", cwd=work_dir)
        git_cmd("push", "gitea", "--tags", "--force", cwd=work_dir)
    else:
        git_cmd("clone", gh_url, work_dir)
        git_cmd("remote", "add", "gitea", gitea_url, cwd=work_dir)
        p2 = git_cmd("push", "gitea", "--all", cwd=work_dir)
        if p2[0] != 0:
            git_cmd("push", "gitea", "--all", "--force", cwd=work_dir)
            git_cmd("push", "gitea", "--tags", "--force", cwd=work_dir)
        else:
            git_cmd("push", "gitea", "--tags", cwd=work_dir)

    ret, out, _ = git_cmd("rev-parse", "--short", "HEAD", cwd=work_dir)
    commit = out.strip() if ret == 0 else "unknown"
    log("=== Done: {} ({}) ===".format(name, commit))
    return {"name": name, "status": "ok", "commit": commit, "branch": "main", "message": "Synced"}


# Email Report (SMTP2GO REST API)

def build_html_report(results):
    """Build a beautiful HTML email report for sync results."""
    total   = len(results)
    success = sum(1 for r in results if r["status"] == "ok")
    failed  = total - success
    failed_color = "#dc2626" if failed > 0 else "#16a34a"

    rows = []
    for r in results:
        if r["status"] == "ok":
            badge = '<span style="background:#dcfce7;color:#166534;padding:2px 10px;border-radius:4px;font-size:12px;font-weight:bold;">OK</span>'
        else:
            badge = '<span style="background:#fef2f2;color:#991b1b;padding:2px 10px;border-radius:4px;font-size:12px;font-weight:bold;">FAIL</span>'
        row = '<tr style="border-bottom:1px solid #f0f0f0;">'
        row += '<td style="padding:12px 16px;font-weight:600;color:#1e293b;">{}</td>'.format(r["name"])
        row += '<td style="padding:12px 16px;">{}</td>'.format(badge)
        row += '<td style="padding:12px 16px;font-family:monospace;color:#6366f1;">{}/{}  </td>'.format(
            r.get("branch", "main"), r.get("commit", "?"))
        row += '<td style="padding:12px 16px;color:#64748b;">{}</td>'.format(r.get("message", ""))
        row += "</tr>"
        rows.append(row)

    now = datetime.now()
    rows_html = "\n".join(rows)
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Gitea Sync Report</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8fafc; margin: 0; padding: 20px; color: #334155; }}
.container {{ max-width: 680px; margin: 0 auto; background: #fff; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 4px 12px rgba(0,0,0,0.04); overflow: hidden; }}
.header {{ background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; padding: 28px 32px; text-align: center; }}
.header h1 {{ margin: 0; font-size: 22px; font-weight: 700; }}
.header p {{ margin: 6px 0 0; font-size: 14px; opacity: 0.9; }}
.summary {{ display: flex; justify-content: space-around; padding: 20px 32px; background: #f8fafc; border-bottom: 1px solid #f1f5f9; }}
.summary-item {{ text-align: center; }}
.summary-value {{ font-size: 28px; font-weight: 700; color: #6366f1; }}
.summary-value.fail {{ color: {failed_color}; }}
.summary-label {{ font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }}
.content {{ padding: 24px 32px; }}
table {{ width: 100%; border-collapse: collapse; }}
thead th {{ text-align: left; padding: 10px 16px; font-size: 11px; text-transform: uppercase; color: #94a3b8; border-bottom: 2px solid #f1f5f9; }}
.footer {{ padding: 20px 32px; background: #f8fafc; border-top: 1px solid #f1f5f9; text-align: center; font-size: 12px; color: #94a3b8; }}
.footer a {{ color: #6366f1; text-decoration: none; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>Gitea Sync Report</h1>
    <p>GitHub &gt; Gitea Repository Synchronization</p>
  </div>
  <div class="summary">
    <div class="summary-item"><div class="summary-value">{total}</div><div class="summary-label">Repos</div></div>
    <div class="summary-item"><div class="summary-value">{success}</div><div class="summary-label">Success</div></div>
    <div class="summary-item"><div class="summary-value fail">{failed}</div><div class="summary-label">Failed</div></div>
    <div class="summary-item"><div class="summary-value" style="font-size:20px;">{time}</div><div class="summary-label">UTC</div></div>
  </div>
  <div class="content">
    <table>
      <thead><tr><th>Repository</th><th>Status</th><th>Commit</th><th>Message</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
  <div class="footer">
    <p>Synced via <a href="https://gitea.iacgenie.com">gitea.iacgenie.com</a> &middot; Every 6 hours</p>
    <p>{org} GitHub &middot; {gitea_url}</p>
  </div>
</div>
</body></html>""".format(
        total=total, success=success, failed=failed,
        time=now.strftime("%H:%M"), rows=rows_html,
        failed_color=failed_color, org=GITHUB_ORG, gitea_url=GITEA_BASE_URL)
    return html


def send_email_report(results):
    """Send HTML email report via SMTP2GO REST API."""
    if not SMTP2GO_API_KEY:
        log("WARNING: SMTP2GO_API_KEY not set, skipping email report")
        return False

    now   = datetime.now()
    date  = now.strftime("%A, %d %B %Y")
    total   = len(results)
    success = sum(1 for r in results if r["status"] == "ok")
    failed  = total - success

    subject = "[Gitea Sync] {} - {} repos synced".format(date, total)

    payload = {
        "to": [SMTP2GO_TO],
        "sender": SMTP2GO_FROM,
        "subject": subject,
        "html_body": build_html_report(results),
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = Request(SMTP2GO_URL, data=data,
                      headers={"Content-Type": "application/json", "X-Smtp2go-Api-Key": SMTP2GO_API_KEY})
        resp = urlopen(req, timeout=30)
        result = json.loads(resp.read().decode("utf-8"))
        if result.get("data", {}).get("succeeded", 0) > 0:
            log("Email report sent to {} (email_id={})".format(SMTP2GO_TO, result["data"]["email_id"]))
            return True
        else:
            log("Email send failed: {}".format(result.get("data", {}).get("failures", [])))
            return False
    except Exception as e:
        log("Failed to send email: {}".format(e))
        return False


# Main

def run_sync():
    """Run sync for all repos and return results."""
    results = []
    for repo in REPOS:
        try:
            result = sync_repo(repo)
            results.append(result)
        except Exception as e:
            log("Sync error for {}: {}".format(repo["name"], str(e)))
            results.append({"name": repo["name"], "status": "error", "commit": "?", "branch": "main", "message": str(e)})
    return results


if __name__ == "__main__":
    if "--test-email" in sys.argv:
        log("Testing SMTP2GO email delivery...")
        test_results = [
            {"name": "iacgenie", "status": "ok", "commit": "abc1234", "branch": "main", "message": "Email test"},
            {"name": "LightSerp", "status": "ok", "commit": "def5678", "branch": "main", "message": "Email test"},
            {"name": "iacgenie-unified-infra", "status": "ok", "commit": "ghi9012", "branch": "main", "message": "Email test"},
        ]
        if send_email_report(test_results):
            log("Email test successful!")
        else:
            log("Email test failed")
        sys.exit(0)

    log("Starting GitHub -> Gitea sync...")
    results = run_sync()
    send_email_report(results)

    success = sum(1 for r in results if r["status"] == "ok")
    log("Sync complete: {}/{} repos synced successfully".format(success, len(results)))
    sys.exit(0 if success == len(results) else 1)
