# Hermes Agent — Complete Setup Guide

> A self-hosted AI agent platform with WhatsApp integration, sandboxed for security.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Step 1 — Install Required Tools](#step-1--install-required-tools)
- [Step 2 — Set Up Hermes Agent](#step-2--set-up-hermes-agent)
- [Step 3 — Configure Hermes](#step-3--configure-hermes)
- [Step 4 — Set Up WhatsApp Bridge](#step-4--set-up-whatsapp-bridge)
- [Step 5 — Set Up Safehouse Sandbox](#step-5--set-up-safehouse-sandbox)
- [Step 6 — Run Hermes in Sandbox](#step-6--run-hermes-in-sandbox)
- [Troubleshooting](#troubleshooting)

---

## Overview

Hermes is an AI agent platform that connects you to a local LLM (Qwen, Llama, etc.) through messaging apps like WhatsApp. It consists of three components:

| Component | Purpose |
|---|---|
| **Hermes Gateway** | Python process that orchestrates the LLM, MCP servers, and messaging platforms |
| **WhatsApp Bridge** | Node.js process that connects to WhatsApp via Baileys and exposes an HTTP API |
| **Safehouse Sandbox** | macOS sandbox profile that restricts the gateway's filesystem and network access |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   macOS Sandbox                      │
│                                                      │
│  ┌──────────────────────────────────────────────┐    │
│  │         Hermes Gateway (Python)              │    │
│  │   - Orchestrates LLM calls                   │    │
│  │   - Routes WhatsApp messages                 │    │
│  │   - Manages MCP servers (LightSerp)          │    │
│  └──────────────────────────────────────────────┘    │
│                      │                               │
│                      │ HTTP 127.0.0.1:3000           │
│                      ▼                               │
│  ┌──────────────────────────────────────────────┐    │
│  │      WhatsApp Bridge (Node.js)               │    │
│  │   - Connects to WhatsApp (Baileys)           │    │
│  │   - Exposes /send, /messages, /health        │    │
│  └──────────────────────────────────────────────┘    │
│                      │                               │
│                      │ WhatsApp API                  │
└──────────────────────┼───────────────────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │   WhatsApp      │
              │   Servers       │
              └─────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │   Your Phone    │
              └─────────────────┘

  Local LLM (llama.cpp/ooba) on http://127.0.0.1:1234/v1
  MCP Server (LightSerp) on http://127.0.0.1:3001
```

---

## Prerequisites

| Item | Version / Details |
|---|---|
| macOS 14+ (Sonoma or later) | Required for `sandbox-exec` |
| Python 3.11+ | For Hermes gateway |
| Node.js 20+ | For WhatsApp bridge |
| Homebrew | For installing packages |
| Local LLM server | llama.cpp, ooba, or compatible on port 1234 |

---

## Step 1 — Install Required Tools

### 1. Install Homebrew (if not already installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install Python and Node.js

```bash
brew install python node
```

### 3. Install Hermes CLI

```bash
pip install hermes-agent
```

Verify the installation:

```bash
hermes --version
```

### 4. Install WhatsApp Bridge Dependencies

The WhatsApp bridge is a Node.js application. Navigate to the bridge directory and install its dependencies:

```bash
cd ~/.hermes/hermes-agent/scripts/whatsapp-bridge
npm install
```

The bridge requires these packages:
- `@whiskeysockets/baileys` — WhatsApp protocol library
- `express` — HTTP server
- `pino` — Logging
- `qrcode-terminal` — QR code display in terminal
- `qrcode` — QR code PNG generation
- `@hapi/boom` — HTTP error handling

### 5. Install Safehouse Sandbox

Safehouse is the sandbox management tool. Create the following structure:

```bash
mkdir -p ~/.local/bin/safehouse/lib/bootstrap
mkdir -p ~/.local/profiles/60-agents
```

The `safehouse` script acts as a wrapper around macOS `sandbox-exec`. It translates high-level sandbox policy declarations into macOS-compatible profiles.

```bash
cat > ~/.local/bin/safehouse << 'EOF'
#!/usr/bin/env bash
# Safehouse — sandbox wrapper for agent processes
# Usage: safehouse <profile-name> [options] -- <command> [args...]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd -P)"

# Parse arguments
ARGS=("$@")
PROFILE=""
ADD_DIRS=()
ADD_DIRS_RO=()
ENV_PASS=()
CMD_ARGS=()
IN_CMD=false

for arg in "${ARGS[@]}"; do
  if [[ "$arg" == "--" ]]; then
    IN_CMD=true
  elif $IN_CMD; then
    CMD_ARGS+=("$arg")
  elif [[ "$arg" == --add-dirs ]]; then
    ADD_DIRS+=("${ARGS[i+1]}")
  elif [[ "$arg" == --add-dirs-ro ]]; then
    ADD_DIRS_RO+=("${ARGS[i+1]}")
  elif [[ "$arg" == --env-pass ]]; then
    ENV_PASS+=("${ARGS[i+1]}")
  else
    PROFILE="$arg"
  fi
done

# Build sandbox profile
PROFILE_PATH="${ROOT_DIR}/profiles/60-agents/${PROFILE}.provision"

if [[ ! -f "$PROFILE_PATH" ]]; then
  echo "Error: Sandbox profile not found: ${PROFILE_PATH}"
  echo "Available profiles:"
  ls "${ROOT_DIR}/profiles/"*/. 2>/dev/null | grep -o '[^/]*.provision' || true
  exit 1
fi

# Set up environment
export PATH="${HOME}/.hermes/hermes-agent/venv/bin:${HOME}/.local/bin:/opt/homebrew/bin:${PATH}"

# Launch sandbox-exec
exec sandbox-exec -f "$PROFILE_PATH" hermes "${CMD_ARGS[@]}"
EOF

chmod +x ~/.local/bin/safehouse
```

---

## Step 2 — Set Up Hermes Agent

### 1. Create the Hermes Data Directories

```bash
mkdir -p ~/.hermes/hermes-agent
mkdir -p ~/.hermes/whatsapp/session
mkdir -p ~/.hermes/logs
mkdir -p ~/.hermes/sessions
mkdir -p ~/.hermes/image_cache
mkdir -p ~/.hermes/audio_cache
mkdir -p ~/.hermes/document_cache
mkdir -p ~/.local/state/hermes
```

### 2. Create the Virtual Environment

```bash
python3 -m venv ~/.hermes/hermes-agent/venv
source ~/.hermes/hermes-agent/venv/bin/activate
pip install hermes-agent
deactivate
```

### 3. Verify the Installation

```bash
~/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main --version
```

---

## Step 3 — Configure Hermes

### 1. Create the Main Configuration File

```bash
cat > ~/.hermes/config.yaml << 'EOF'
model:
  default: local/Qwen3.6-35B-A3B-UD-MLX-4bit
  context_length: 260000
  provider: custom
  api_key: not-needed
  base_url: http://127.0.0.1:1234/v1

providers: {}
fallback_providers: []

toolsets:
  - hermes-cli

mcp_servers:
  lightserp:
    command: node
    args:
      - /path/to/your/LightSerp/dist/server.js
    env:
      SEARXNG_URL: http://localhost:8080/search?format=json
      REDIS_URL: redis://localhost:6379
      PAGEZEN_URL: http://localhost:8082
      HTTP_PORT: '3001'
      LIGHTSERP_PORT: '3001'
    connect_timeout: 30
    timeout: 120

agent:
  max_turns: 60
  gateway_timeout: 1800
  reasoning_effort: medium

terminal:
  backend: local

whatsapp: {}

telegram: {}

display:
  personality: ''
  streaming: true
  timestamps: false

logging:
  level: INFO
  max_size_mb: 5
  backup_count: 3

platform_toolsets:
  whatsapp:
    - hermes-whatsapp
  cli:
    - hermes-cli
EOF
```

**Key configuration points:**
- `model.context_length`: Set this to at least `64000` (or higher, e.g. `260000`). The default minimum Hermes enforces is 64K. If your model's actual context is smaller, increase this value or Hermes will reject the model.
- `model.base_url`: Points to your local LLM server (llama.cpp, ooba, text-generation-webui, etc.) on port `1234`.
- `mcp_servers.lightserp`: Points to your LightSerp MCP server. Update the path.

### 2. Create the `.env` File

```bash
cat > ~/.hermes/.env << 'EOF'
# WhatsApp
WHATSAPP_ENABLED=true
WHATSAPP_ALLOWED_USERS=
WHATSAPP_MODE=self-chat
WHATSAPP_REPLY_PREFIX='⚕ *Hermes Agent*\n────────────\n'

# Gateway
GATEWAY_ALLOW_ALL_USERS=true

# Model
HERMES_MAX_ITERATIONS=60
EOF
```

---

## Step 4 — Set Up WhatsApp Bridge

### 1. Install Bridge Dependencies

```bash
mkdir -p ~/.hermes/hermes-agent/scripts/whatsapp-bridge
cd ~/.hermes/hermes-agent/scripts/whatsapp-bridge
cat > package.json << 'EOF'
{
  "name": "whatsapp-bridge",
  "version": "1.0.0",
  "type": "module",
  "dependencies": {
    "@whiskeysockets/baileys": "^6.7.0",
    "express": "^4.18.0",
    "pino": "^8.17.0",
    "qrcode-terminal": "^0.12.0",
    "qrcode": "^1.5.3",
    "@hapi/boom": "^10.0.0"
  }
}
EOF
npm install
```

### 2. Start the Bridge Manually (First-Time Setup)

```bash
cd ~/.hermes/hermes-agent/scripts/whatsapp-bridge
node bridge.js --port 3000 --session ~/.hermes/whatsapp/session --mode self-chat
```

You will see a QR code in the terminal. **Open WhatsApp on your phone, go to Linked Devices, and scan the QR code.**

The QR code will also be saved as a PNG file at `~/.hermes/whatsapp/session/qr-code.png` so you can open it from your file manager.

### 3. Verify the Bridge

After scanning the QR code, you should see:
```
✅ WhatsApp connected!
🌉 WhatsApp bridge listening on port 3000 (mode: self-chat)
🔒 Self-chat mode — only your own messages to yourself are processed.
```

Test it:

```bash
curl -s -X POST http://localhost:3000/health | python3 -m json.tool
```

Expected output:
```json
{
  "status": "connected",
  "queueLength": 0,
  "uptime": 12.5,
  "scriptHash": "abc123..."
}
```

### Understanding WhatsApp Bridge Modes

| Mode | Behavior |
|---|---|
| `self-chat` | Only processes messages you send to yourself in WhatsApp. This is the recommended mode for personal agents. |
| `bot` | Processes messages from any number. Use with `WHATSAPP_ALLOWED_USERS` to restrict who can interact with the agent. |

---

## Step 5 — Set Up Safehouse Sandbox

The sandbox isolates the Hermes gateway using macOS's `sandbox-exec` system call. It restricts what files the gateway can access and what network connections it can make.

### 1. Create the Sandbox Profile

Create the file at `~/.local/profiles/60-agents/hermes-agent.provision`:

```
(version 1)
(allow default)
(allow network-outbound)

;; Allow file access to Hermes directories
(allow file-read* file-write*
  (subpath "/Users/manjunathkanavi/.hermes"))

;; Allow file access to local state
(allow file-read* file-write*
  (subpath "/Users/manjunathkanavi/.local"))

;; Read-only access to workspace
(allow file-read*
  (subpath "/Users/manjunathkanavi/workspace/hermes_workspace"))
(allow file-read*
  (subpath "/Users/manjunathkanavi/workspace/git_workspace"))
(allow file-read*
  (subpath "/Users/manjunathkanavi/workspace"))
```

**Important syntax rules:**
- Use `(allow network-outbound)` — do NOT use `(allow network)`. The generic keyword is not recognized on macOS 15+.
- Use `(subpath "/path")` for recursive directory access.
- Use `(literal "/exact/path")` for single file access.
- Each `(allow ...)` block is a separate rule. The gateway needs ALL of them to function.

### 2. Create the `hermes-safe` Wrapper

This script launches Hermes inside the sandbox:

```bash
cat > ~/.local/bin/hermes-safe << 'WRAPPER'
#!/usr/bin/env bash
set -euo pipefail

PROFILE=~/.local/profiles/60-agents/hermes-agent.provision

export PATH="/Users/manjunathkanavi/.hermes/hermes-agent/venv/bin:/Users/manjunathkanavi/.local/bin:/opt/homebrew/bin:$PATH"
export HOME="$HOME"

exec sandbox-exec -f "$PROFILE" hermes "$@"
WRAPPER

chmod +x ~/.local/bin/hermes-safe
```

### 3. Test the Sandbox

```bash
hermes-safe gateway run --help
```

If this returns without errors, the sandbox is configured correctly.

---

## Step 6 — Run Hermes in Sandbox

### 1. Start the Local LLM

Before starting Hermes, your local LLM server must be running on port 1234:

```bash
# Example with llama.cpp
./server -m ./models/your-model.gguf -c 8192

# Or with text-generation-webui
python server.py
```

Verify it is responding:

```bash
curl -s http://127.0.0.1:1234/v1/models | python3 -m json.tool | head -5
```

### 2. Start the WhatsApp Bridge

Open a separate terminal and run:

```bash
cd ~/.hermes/hermes-agent/scripts/whatsapp-bridge
node bridge.js --port 3000 --session ~/.hermes/whatsapp/session --mode self-chat
```

Wait for `✅ WhatsApp connected!` before proceeding.

### 3. Start Hermes Gateway in Sandbox

Open a third terminal and run:

```bash
hermes-safe gateway run --replace
```

You should see:

```
╔══════════════════════════════════════════╗
║      Hermes Gateway Starting...         ║
╚══════════════════════════════════════════╝

[Whatsapp] Bridge found at ~/.hermes/hermes-agent/scripts/whatsapp-bridge/bridge.js
✓ whatsapp connected
Gateway running with 1 platform(s)
Channel directory built: 2 target(s)
Cron ticker started (interval=60s)
```

### 4. Test the Full Stack

Send a message to your own WhatsApp number (in the self-chat with yourself):

> "Hello, this is a test."

You should receive a reply from Hermes within a few seconds.

---

## Troubleshooting

### "Context length exceeded" Error

```
Model local/Qwen... has a context window of 60,000 tokens,
which is below the minimum 64,000 required by Hermes Agent.
```

**Fix:** In `~/.hermes/config.yaml`, set the `context_length` explicitly:

```yaml
model:
  default: local/YourModel
  context_length: 260000
```

### WhatsApp Bridge Not Connecting

**Symptom:** Gateway log shows `[Whatsapp] Bridge exited during shutdown (code -15)`

**Fix:**
1. Ensure the bridge is running: `curl http://localhost:3000/health`
2. Ensure the sandbox profile allows loopback networking. The `(allow network-outbound)` rule is required.
3. Check the bridge port matches the gateway config (default: 3000).

### Sandbox Profile Errors

**Symptom:** `sandbox-exec: unbound variable: network`

**Fix:** On macOS 15+, the sandbox profile syntax requires `(allow network-outbound)` instead of `(allow network)`. Also ensure the profile file has a `.provision` extension, not `.sb`.

### "No such file or directory" in Sandbox

**Fix:** The sandbox restricts file access. Add the missing path to the sandbox profile:

```
(allow file-read* file-write*
  (subpath "/path/to/missing/directory"))
```

### Gateway Won't Start

**Fix:** Check the gateway log:

```bash
tail -f ~/.hermes/logs/gateway.log
```

Common causes:
- LLM server not running on port 1234
- WhatsApp bridge not running on port 3000
- Incorrect `base_url` in config.yaml
- Missing `context_length` in config

### Bridge QR Code Not Appearing

**Fix:** The QR code is saved as PNG at `~/.hermes/whatsapp/session/qr-code.png`. Open it manually:

```bash
open ~/.hermes/whatsapp/session/qr-code.png
```

To re-scan, delete the session and restart:

```bash
rm -rf ~/.hermes/whatsapp/session/*
node bridge.js --port 3000 --session ~/.hermes/whatsapp/session --mode self-chat
```

### LightSerp MCP Errors

**Symptom:** `JSONRPCResponse.jsonrpc Field required`

**Fix:** This is a known issue with the MCP server protocol. Update LightSerp to the latest version:

```bash
cd /path/to/LightSerp
npm install
npm run build
```

### Memory / OOM Errors

If you see memory guard errors when using large context lengths (260K+), try:
- Reducing `context_length` to 120000 or 64000
- Freeing system memory
- Running the model with fewer context tokens

### WhatsApp Messages Not Getting Through

1. Ensure you are sending messages to **your own number** (self-chat mode).
2. Ensure `WHATSAPP_MODE=self-chat` in `~/.hermes/.env`.
3. Ensure the WhatsApp bridge is connected: check `curl http://localhost:3000/health` returns `"status": "connected"`.
4. Check the gateway log for inbound message entries.

### Service Management

Hermes uses `launchd` for auto-start. To manage the gateway service:

```bash
# Stop the service
launchctl unload ~/Library/LaunchAgents/ai.hermes.gateway.plist

# Start the service
launchctl load ~/Library/LaunchAgents/ai.hermes.gateway.plist

# Check service status
launchctl list | grep hermes
```

To run manually instead:

```bash
hermes-safe gateway run --replace
```

---

## Quick Reference

| Command | Purpose |
|---|---|
| `hermes-safe gateway run` | Start gateway in sandbox |
| `hermes-safe gateway status` | Check gateway status |
| `curl localhost:3000/health` | Check WhatsApp bridge health |
| `tail -f ~/.hermes/logs/gateway.log` | View gateway logs |
| `open ~/.hermes/whatsapp/session/qr-code.png` | View QR code |
| `launchctl list \| grep hermes` | Check launchd service |
| `ps aux \| grep hermes` | Check running processes |

## File Locations

| Path | Purpose |
|---|---|
| `~/.hermes/config.yaml` | Main configuration |
| `~/.hermes/.env` | Environment variables |
| `~/.hermes/logs/` | Gateway and agent logs |
| `~/.hermes/whatsapp/session/` | WhatsApp session data and QR code |
| `~/.hermes/sessions/` | Conversation sessions |
| `~/.hermes/hermes-agent/scripts/whatsapp-bridge/` | WhatsApp bridge code |
| `~/.hermes/image_cache/` | Cached images from WhatsApp |
| `~/.hermes/audio_cache/` | Cached audio from WhatsApp |
| `~/.hermes/document_cache/` | Cached documents from WhatsApp |
| `~/.local/bin/hermes-safe` | Sandbox wrapper script |
| `~/.local/profiles/60-agents/hermes-agent.provision` | Sandbox profile |
