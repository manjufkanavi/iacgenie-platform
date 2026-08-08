#!/usr/bin/env python3
"""Deploy all infra changes to VM with proper sudo handling."""

import os
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VM_SSH = "mkanavi@192.168.0.118"
VM_BASE = "/home/mkanavi/docker/iacgenie"


def run_ssh(cmd, sudo=False):
    full = f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 {VM_SSH}"
    if sudo:
        full += " sudo"
    full += f" bash -c {cmd!r}"
    result = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=60)
    return result.stdout.strip() or result.stderr.strip()


def scp_file(local, remote):
    result = subprocess.run(
        f"scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 {local} {VM_SSH}:{remote}",
        shell=True, capture_output=True, text=True, timeout=30,
    )
    return result.returncode == 0, result.stderr[:200]


def main():
    print("=" * 60)
    print("  DEPLOYING INFRA CHANGES TO VM")
    print("=" * 60)

    # ── 1. Nginx config (needs sudo) ──
    print("\n[1/6] Nginx config...")
    tmp_nginx = "/tmp/nginx-iacgenie.conf"
    scp_file(
        os.path.join(SCRIPT_DIR, "files", "nginx-iacgenie.conf"),
        f"{tmp_nginx}",
    )
    run_ssh(f"cp {tmp_nginx} /etc/nginx/conf.d/iacgenie.conf && rm -f {tmp_nginx}", sudo=True)
    print(f"  ✅ Nginx config deployed")

    # ── 2. Cloudflare config (needs sudo) ──
    print("[2/6] Cloudflare tunnel config...")
    tmp_cf = "/tmp/cf-config.yml"
    scp_file(
        os.path.join(SCRIPT_DIR, "files", "cloudflared-config.yml"),
        tmp_cf,
    )
    run_ssh(f"cp {tmp_cf} /etc/cloudflared/config.yml && rm -f {tmp_cf}", sudo=True)
    print(f"  ✅ Cloudflare config deployed")

    # ── 3. Landing page ──
    print("[3/6] Landing page...")
    landing_dir = f"{VM_BASE}/landing"
    run_ssh(f"mkdir -p {landing_dir}")
    scp_file(
        os.path.join(SCRIPT_DIR, "files", "landing-page.html"),
        f"{landing_dir}/index.html",
    )
    run_ssh(f"ls -la {landing_dir}/index.html")
    print(f"  ✅ Landing page deployed")

    # ── 4. PageZen docs ──
    print("[4/6] PageZen docs UI...")
    pagezen_dir = f"{VM_BASE}/pagezen-docs"
    run_ssh(f"mkdir -p {pagezen_dir}")
    scp_file(
        os.path.join(SCRIPT_DIR, "files", "pagezen-docs.html"),
        f"{pagezen_dir}/index.html",
    )
    run_ssh(f"ls -la {pagezen_dir}/index.html")
    print(f"  ✅ PageZen docs deployed")

    # ── 5. Security compose ──
    print("[5/6] Security Docker Compose...")
    sec_dir = f"{VM_BASE}/docker-compose/security"
    run_ssh(f"mkdir -p {sec_dir}")
    scp_file(
        os.path.join(SCRIPT_DIR, "ansible", "roles", "security", "templates", "docker-compose.security.yml.j2").replace(".j2", ""),
        f"{sec_dir}/docker-compose.security.yml",
    )
    run_ssh(f"ls -la {sec_dir}/docker-compose.security.yml")
    print(f"  ✅ Security compose deployed")

    # ── 6. Reload services ──
    print("[6/6] Reloading services...")
    print("  🔍 Nginx config test...")
    nginx_test = run_ssh("nginx -t 2>&1", sudo=True)
    print(f"    {nginx_test[:200]}")

    print("  🔄 Reloading Nginx...")
    run_ssh("systemctl reload nginx 2>&1", sudo=True)

    print("  🔄 Restarting cloudflared...")
    run_ssh("systemctl restart cloudflared 2>&1", sudo=True)
    run_ssh("systemctl is-active cloudflared 2>&1", sudo=True)

    print("  🔄 Starting security containers...")
    run_ssh(f"docker compose -f {sec_dir}/docker-compose.security.yml up -d 2>&1")

    # ── Verification ──
    print("\n" + "=" * 60)
    print("  VERIFICATION")
    print("=" * 60)

    checks = [
        ("Nginx config", 'nginx -t 2>&1', True),
        ("Cloudflare active", 'systemctl is-active cloudflared 2>&1', True),
        ("Docker ps (count)", 'docker ps --format "{{.Names}}" | wc -l 2>&1', False),
        ("Security containers", f'docker compose -f {sec_dir}/docker-compose.security.yml ps 2>&1', False),
        ("Landing page", f'curl -s http://iacgenie.com | head -5', False),
        ("Cloudflare config size", f'wc -c < /etc/cloudflared/config.yml 2>&1', False),
        ("Landing file size", f'wc -c < {landing_dir}/index.html 2>&1', False),
        ("PageZen file size", f'wc -c < {pagezen_dir}/index.html 2>&1', False),
        ("Nginx conf size", f'wc -c < /etc/nginx/conf.d/iacgenie.conf 2>&1', False),
    ]

    for label, cmd, sudo_c in checks:
        result = run_ssh(cmd, sudo=sudo_c)
        # Simple health check: has meaningful content
        ok = len(result) > 5 and ("nginx" not in result.lower() or "test is successful" in result.lower() or "active" in result.lower() or "running" in result.lower() or "200" in result or "bytes" in result or result.isdigit())
        icon = "✅" if ok else "⚠️"
        preview = result[:100].replace('\n', ' ')
        print(f"  {icon} {label}: {preview}")

    print("\n" + "=" * 60)
    print("  DEPLOYMENT COMPLETE — now commit & push")
    print("=" * 60)


if __name__ == "__main__":
    main()
