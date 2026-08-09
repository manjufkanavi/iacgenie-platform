#!/usr/bin/env python3
"""Extract CF_API_KEY from bash_profile and run cloudflared tunnel login."""
import re, os, subprocess, sys, time

# Read bash_profile
with open('/Users/manjunathkanavi/.bash_profile') as f:
    content = f.read()

# Extract the key value
lines = content.split('\n')
api_key = None
for line in lines:
    if 'CLOUDFLARE_API_KEY=' in line:
        # Get everything after the first =
        parts = line.split('=', 1)
        if len(parts) == 2:
            val = parts[1].strip()
            # Remove quotes
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            api_key = val
            break

if not api_key:
    print("ERROR: CLOUDFLARE_API_KEY not found in ~/.bash_profile")
    sys.exit(1)

print(f"API_KEY: {api_key[:10]}...{api_key[-6:]}")

env = os.environ.copy()
env['CF_API_KEY'] = api_key

print("\nStarting cloudflared tunnel login...")
print("Waiting for URL to be generated...\n")

proc = subprocess.Popen(
    ['cloudflared', 'tunnel', 'login'],
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

# Read first few lines (the URL)
url = ""
for i in range(30):
    line = proc.stdout.readline()
    if line:
        print(line, end='')
        if 'https://' in line:
            url = line.strip()
            break
    time.sleep(0.5)

if not url:
    print("ERROR: Could not extract URL from output")
    proc.kill()
    sys.exit(1)

print(f"\n{'='*70}")
print(f"COPY THIS URL AND OPEN IN BROWSER:")
print(f"{url}")
print(f"{'='*70}")
print(f"\nAfter approving in browser, the cert.pem will be saved to:")
print(f"~/.cloudflared/cert.pem")
print(f"\nWaiting for process to complete (you have ~30 seconds to approve)...")

try:
    proc.wait(timeout=30)
    if proc.returncode == 0:
        print("\n✅ Login successful! cert.pem created.")
        import glob
        files = glob.glob('/Users/manjunathkanavi/.cloudflared/*')
        for f in files:
            stat = os.stat(f)
            print(f"  {f} ({stat.st_size} bytes)")
    else:
        print(f"\n❌ Login failed with exit code {proc.returncode}")
except subprocess.TimeoutExpired:
    print("\n⏱️  Timeout - process still waiting for browser approval.")
    print("If you already approved, the cert.pem may have been created.")
    proc.kill()
