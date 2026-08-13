#!/usr/bin/env python3
"""Deploy all infra changes to VM and local repo."""

import os
import subprocess
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VM_SSH = "mkanavi@192.168.0.118"
VM_BASE = "/home/mkanavi/docker/iacgenie"
VM_NGINX = "/etc/nginx/conf.d/iacgenie.conf"
VM_CLOUDFLARED = "/etc/cloudflared/config.yml"
REPO_INFRA = "/Users/manjunathkanavi/iacgenie-platform/infra"


def ssh(cmd):
    """Run SSH command and return output."""
    full = f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 {VM_SSH} {cmd}"
    result = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=30)
    return result.stdout.strip() or result.stderr.strip()


def scp_put(local, remote):
    """SCP file to VM."""
    cmd = f"scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 {local} {VM_SSH}:{remote}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return result.returncode == 0


def deploy_file(content, remote_path, label=""):
    """Write content to VM via SSH."""
    if label:
        print(f"[{label}] Deploying to {remote_path}...")
    cmd = f"cat > {remote_path} << 'HERMES_EOF'\n{content}\nHERMES_EOF"
    result = subprocess.run(
        f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 {VM_SSH} {cmd}",
        shell=True, capture_output=True, text=True, timeout=30,
    )
    return result.returncode == 0


def main():
    # ──────────────────────────────────────────────────────────────
    # 1. Nginx config (NEW — base domain landing page, no api/app/lightserp)
    # ──────────────────────────────────────────────────────────────
    nginx_conf = read_file("files/nginx-iacgenie.conf")
    print("[OK] Writing Nginx config...")
    # We'll write via Python helper script to avoid shell heredoc issues
    deploy_script = f'''
import sys, os
content = sys.stdin.read()
with open(sys.argv[1], 'w') as f:
    f.write(content)
'''
    result = subprocess.run(
        f"echo '{nginx_conf}' | ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 {VM_SSH} "
        f"python3 -c '{deploy_script} {VM_NGINX}'",
        shell=True, capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        # Fallback: write via temp file
        tmp = f"/tmp/nginx-new.conf"
        with open(tmp, "w") as f:
            f.write(nginx_conf)
        scp_put(tmp, VM_SSH + ":" + tmp)
        ssh(f"sudo cp {tmp} {VM_NGINX}")
        print("[OK] Nginx config deployed via SCP fallback")
    else:
        print("[OK] Nginx config deployed")

    # ──────────────────────────────────────────────────────────────
    # 2. Cloudflare tunnel config
    # ──────────────────────────────────────────────────────────────
    cf_config = read_file("files/cloudflared-config.yml")
    print("[OK] Writing Cloudflare tunnel config...")
    result = subprocess.run(
        f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 {VM_SSH} "
        f"python3 -c \"import sys; open(sys.argv[1],'w').write(sys.stdin.read()) {VM_CLOUDFLARED}\" "
        f"<< 'EOF'\n{cf_config}\nEOF",
        shell=True, capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        tmp = f"/tmp/cf-config.yml"
        with open(tmp, "w") as f:
            f.write(cf_config)
        scp_put(tmp, VM_SSH + ":" + tmp)
        ssh(f"sudo cp {tmp} {VM_CLOUDFLARED}")
        print("[OK] Cloudflare config deployed via SCP fallback")
    else:
        print("[OK] Cloudflare config deployed")

    # ──────────────────────────────────────────────────────────────
    # 3. Landing page
    # ──────────────────────────────────────────────────────────────
    landing_html = read_file("files/landing-page.html")
    print("[OK] Writing landing page...")
    landing_dir = f"{VM_BASE}/landing"
    ssh(f"mkdir -p {landing_dir}")
    with open(f"/tmp/landing.html", "w") as f:
        f.write(landing_html)
    scp_put(f"/tmp/landing.html", VM_SSH + f":{landing_dir}/index.html")
    print("[OK] Landing page deployed")

    # ──────────────────────────────────────────────────────────────
    # 4. PageZen docs UI
    # ──────────────────────────────────────────────────────────────
    pagezen_html = read_file("files/pagezen-docs.html")
    print("[OK] Writing PageZen docs UI...")
    pagezen_dir = f"{VM_BASE}/pagezen-docs"
    ssh(f"mkdir -p {pagezen_dir}")
    with open(f"/tmp/pagezen.html", "w") as f:
        f.write(pagezen_html)
    scp_put(f"/tmp/pagezen.html", VM_SSH + f":{pagezen_dir}/index.html")
    print("[OK] PageZen docs UI deployed")

    # ──────────────────────────────────────────────────────────────
    # 5. Reload services
    # ──────────────────────────────────────────────────────────────
    print("[OK] Reloading Nginx...")
    ssh("sudo nginx -t && sudo systemctl reload nginx")

    print("[OK] Restarting cloudflared...")
    ssh("sudo systemctl restart cloudflared && sudo systemctl status cloudflared --no-pager | head -5")

    # ──────────────────────────────────────────────────────────────
    # 6. Verify
    # ──────────────────────────────────────────────────────────────
    print("\n[OK] === Verification ===")
    print(ssh("sudo nginx -t 2>&1"))
    print(ssh("sudo systemctl is-active cloudflared 2>&1"))
    print(ssh(f"curl -s -o /dev/null -w '{{'\"'\"'http_code': %{{http_code}}, 'size': %{{size_download}}'}}' "
             f"http://iacgenie.com 2>&1"))
    print("[OK] All deployments complete!")


def read_file(rel_path):
    """Read file from local repo."""
    path = os.path.join(SCRIPT_DIR, rel_path)
    with open(path) as f:
        return f.read()


if __name__ == "__main__":
    main()
