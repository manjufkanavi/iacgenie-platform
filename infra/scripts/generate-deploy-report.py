#!/usr/bin/env python3
"""Generate beautiful HTML report for deploy/destroy workflows."""

import json
import sys
import os
from datetime import datetime, timezone

def main():
    """Read job metadata from environment and render HTML report."""
    action = os.environ.get("CI_ACTION", "deploy").lower()
    status = os.environ.get("DEPLOY_STATUS", "success").lower()
    start_time = os.environ.get("DEPLOY_START", datetime.now(timezone.utc).isoformat())
    end_time = os.environ.get("DEPLOY_END", datetime.now(timezone.utc).isoformat())
    duration = os.environ.get("DEPLOY_DURATION", "0s")
    hostname = os.environ.get("DEPLOY_HOSTNAME", "192.168.0.118")
    commit_sha = os.environ.get("GITHUB_SHA", "unknown")
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    trigger = os.environ.get("GITHUB_EVENT_NAME", "push")
    services_json = os.environ.get("SERVICES_DATA", "[]")
    log_lines = os.environ.get("DEPLOY_LOG", "").split("\n")

    try:
        services = json.loads(services_json)
    except json.JSONDecodeError:
        services = []

    is_success = status in ("success", "healthy", "true", "1")
    status_color = "#22c55e" if is_success else "#ef4444"
    status_emoji = "✅" if is_success else "❌"
    status_label = "SUCCESS" if is_success else "FAILED"
    action_label = "DEPLOY" if action == "deploy" else "DESTROY"

    # Generate services table rows
    service_rows = ""
    for svc in services:
        name = svc.get("name", "unknown")
        state = svc.get("status", "unknown")
        health = svc.get("health", "n/a")
        ports = svc.get("ports", "n/a")
        uptime = svc.get("uptime", "n/a")
        state_badge = "healthy" if health == "healthy" else ("running" if state == "running" else "degraded")
        row_color = "#22c55e" if health == "healthy" else "#f59e0b" if health == "unhealthy" else "#3b82f6"
        service_rows += f"""<tr>
            <td><strong>{name}</strong></td>
            <td>{state}</td>
            <td><span class="badge" style="border-left: 3px solid {row_color};">{health}</span></td>
            <td><code>{ports}</code></td>
            <td>{uptime}</td>
        </tr>"""

    if not services:
        service_rows = '<tr><td colspan="5" style="text-align:center; color:#94a3b8;">No services data available</td></tr>'

    # Generate log timeline
    log_html = ""
    if log_lines:
        for line in log_lines[-50:]:  # Last 50 lines
            line = line.strip()
            if not line:
                continue
            if "ERROR" in line or "FAIL" in line:
                log_html += f'<div class="log-line error">[ERROR] {line}</div>\n'
            elif "WARN" in line:
                log_html += f'<div class="log-line warn">[WARN]  {line}</div>\n'
            elif "✅" in line or "SUCCESS" in line or "READY" in line or "ok" in line:
                log_html += f'<div class="log-line success">{line}</div>\n'
            else:
                log_html += f'<div class="log-line info">{line}</div>\n'

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{action_label} Report — {hostname}</title>
<style>
    :root {{
        --bg: #0f172a;
        --surface: #1e293b;
        --surface2: #334155;
        --text: #f1f5f9;
        --text-muted: #94a3b8;
        --accent: #6366f1;
        --border: #475569;
        --success: #22c55e;
        --danger: #ef4444;
        --warning: #f59e0b;
        --info: #3b82f6;
    }}
    @media (prefers-color-scheme: light) {{
        :root {{
            --bg: #f8fafc;
            --surface: #ffffff;
            --surface2: #f1f5f9;
            --text: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
        }}
        .log-line.info {{ color: #334155; }}
    }}
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: var(--bg);
        color: var(--text);
        line-height: 1.6;
        padding: 2rem 1rem;
    }}
    .container {{ max-width: 900px; margin: 0 auto; }}
    .header {{
        text-align: center;
        padding: 2rem 0;
        border-bottom: 1px solid var(--border);
        margin-bottom: 2rem;
    }}
    .header h1 {{ font-size: 2rem; margin-bottom: 0.5rem; }}
    .header .action {{ color: var(--accent); }}
    .status-banner {{
        display: inline-block;
        padding: 0.5rem 1.5rem;
        border-radius: 9999px;
        font-size: 1.1rem;
        font-weight: 700;
        background: {status_color}22;
        color: {status_color};
        border: 1px solid {status_color}44;
        margin: 1rem 0;
    }}
    .meta-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 1rem;
        margin-bottom: 2rem;
    }}
    .meta-card {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1rem 1.25rem;
    }}
    .meta-card .label {{
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-muted);
        margin-bottom: 0.25rem;
    }}
    .meta-card .value {{
        font-size: 1.1rem;
        font-weight: 600;
    }}
    .section {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }}
    .section h2 {{
        font-size: 1.25rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid var(--border);
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
    }}
    th {{
        text-align: left;
        padding: 0.75rem 1rem;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-muted);
        border-bottom: 2px solid var(--border);
    }}
    td {{
        padding: 0.75rem 1rem;
        border-bottom: 1px solid var(--border);
        font-size: 0.95rem;
    }}
    tr:last-child td {{ border-bottom: none; }}
    tr:hover {{ background: var(--surface2); }}
    .badge {{
        display: inline-block;
        padding: 0.15rem 0.6rem;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
    }}
    code {{
        background: var(--surface2);
        padding: 0.15rem 0.4rem;
        border-radius: 4px;
        font-size: 0.85rem;
        font-family: 'SF Mono', 'Fira Code', monospace;
    }}
    .log-section {{
        background: #000;
        border-radius: 8px;
        padding: 1rem;
        max-height: 300px;
        overflow-y: auto;
        font-family: 'SF Mono', 'Fira Code', monospace;
        font-size: 0.85rem;
        color: #e2e8f0;
    }}
    .log-line {{ padding: 0.1rem 0; }}
    .log-line.error {{ color: #ef4444; }}
    .log-line.warn {{ color: #f59e0b; }}
    .log-line.success {{ color: #22c55e; }}
    .footer {{
        text-align: center;
        padding: 2rem 0;
        color: var(--text-muted);
        font-size: 0.85rem;
        border-top: 1px solid var(--border);
        margin-top: 2rem;
    }}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🚀 <span class="action">{action_label}</span> Report</h1>
        <div class="status-banner">{status_emoji} {status_label}</div>
        <p style="color: var(--text-muted); margin-top: 0.5rem;">Infrastructure Automation — {hostname}</p>
    </div>

    <div class="meta-grid">
        <div class="meta-card">
            <div class="label">Status</div>
            <div class="value" style="color: {status_color};">{status_emoji} {status_label}</div>
        </div>
        <div class="meta-card">
            <div class="label">Duration</div>
            <div class="value">{duration}</div>
        </div>
        <div class="meta-card">
            <div class="label">Started</div>
            <div class="value">{start_time}</div>
        </div>
        <div class="meta-card">
            <div class="label">Completed</div>
            <div class="value">{end_time}</div>
        </div>
        <div class="meta-card">
            <div class="label">Branch</div>
            <div class="value">{branch}</div>
        </div>
        <div class="meta-card">
            <div class="label">Commit</div>
            <div class="value"><code>{commit_sha[:8]}</code></div>
        </div>
        <div class="meta-card">
            <div class="label">Trigger</div>
            <div class="value">{trigger}</div>
        </div>
        <div class="meta-card">
            <div class="label">Services</div>
            <div class="value">{len(services)} total</div>
        </div>
    </div>

    <div class="section">
        <h2>📋 Services</h2>
        <table>
            <thead>
                <tr>
                    <th>Service</th>
                    <th>Status</th>
                    <th>Health</th>
                    <th>Ports</th>
                    <th>Uptime</th>
                </tr>
            </thead>
            <tbody>
                {service_rows}
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>📜 Execution Log</h2>
        <div class="log-section">
            {log_html or '<div class="log-line info">No log output captured</div>'}
        </div>
    </div>

    <div class="footer">
        <p>Generated by IacGenie CI/CD Pipeline • {now}</p>
        <p>Repository: manjufkanavi/iacgenie-unified-infra</p>
    </div>
</div>
</body>
</html>"""

    output_path = os.environ.get("REPORT_OUTPUT", "/tmp/deploy-report.html")
    with open(output_path, "w") as f:
        f.write(html)

    print(f"HTML report written to: {output_path}")
    print(f"Status: {status_label} | Services: {len(services)} | Duration: {duration}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
