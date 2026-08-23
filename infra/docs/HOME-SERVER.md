# Home Server — Infrastructure Runbook

**Last Updated:** 2026-08-23  
**Host Alias:** `homeserver`  
**IP:** `192.168.0.116`  
**User:** `mkanavi`  
**SSH Key:** `~/.ssh/home-server` (ed25519)  
**Auth:** Public key only (password auth disabled)

---

## 1. VM Details

| Property | Value |
|----------|-------|
| Hostname alias | `homeserver` |
| IP Address | `192.168.0.116` |
| SSH User | `mkanavi` |
| SSH Port | `22` (default) |
| SSH Key | `~/.ssh/home-server` (ed25519) |
| Key Comment | `home-server-mkanavi` |
| Auth method | Public key only |

---

## 2. SSH Key Setup (One-Time, Already Done)

> **Note:** This has already been completed. Steps below are for reference / disaster recovery.

### 2.1 Generate the SSH Key Pair

```bash
ssh-keygen -t ed25519 -f ~/.ssh/home-server -C "home-server-mkanavi" -N ""
```

This creates:
- `~/.ssh/home-server` — **private key** (stays on your Mac, never committed)
- `~/.ssh/home-server.pub` — **public key** (deployed to the VM)

### 2.2 Deploy the Public Key to the VM

Use `ssh-copy-id` with the initial password for the first and only time:

```bash
ssh-copy-id -i ~/.ssh/home-server.pub mkanavi@192.168.0.116
# Enter password when prompted: (use the server's current password)
```

Alternatively, manually append the key:

```bash
cat ~/.ssh/home-server.pub | ssh mkanavi@192.168.0.116 \
  "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

---

## 3. SSH Config Alias

The `~/.ssh/config` on your Mac has been updated with the following block.
This enables `ssh homeserver` to connect directly with the correct key.

```ssh-config
Host homeserver
    HostName 192.168.0.116
    User mkanavi
    IdentityFile ~/.ssh/home-server
    UserKnownHostsFile /dev/null
    StrictHostKeyChecking no
    ConnectTimeout 10
    ServerAliveInterval 30
    ServerAliveCountMax 3
    TCPKeepAlive yes
    IdentitiesOnly yes
    PreferredAuthentications publickey
    AddressFamily inet
    # Key-only auth — password auth disabled on server after initial setup
    AddKeysToAgent yes
    UseKeychain yes
```

### Usage

```bash
ssh homeserver                             # Connect to home server
scp file homeserver:~/                     # Copy file to home server
rsync -av . homeserver:~/project/          # Sync files
```

---

## 4. Server Hardening — Disable Password Auth

> **WARNING:** Verify key-based login works first before running these commands.
> If you get locked out, you will need physical/console access to the machine.

### 4.1 Verify Key Login Works

```bash
ssh homeserver
# Should connect WITHOUT any password prompt
```

### 4.2 Harden SSH on the Server

Once connected, run the following to disable password authentication:

```bash
# Disable password auth
sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config

# Ensure public key auth is explicitly enabled
sudo sed -i 's/^#\?PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config

# Disable root login
sudo sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config

# Verify config before restarting
sudo sshd -t && echo "Config OK"

# Restart SSH daemon
sudo systemctl restart sshd
```

### 4.3 Verify Hardening

```bash
# Check sshd effective config
ssh homeserver "sudo sshd -T | grep -E 'passwordauthentication|pubkeyauthentication|permitrootlogin'"
```

Expected output:
```
passwordauthentication no
pubkeyauthentication yes
permitrootlogin no
```

### 4.4 Confirm Password Login is Rejected

From your Mac (in a new terminal — keep your existing session open as a safety net):

```bash
ssh -o IdentitiesOnly=no -o PreferredAuthentications=password mkanavi@192.168.0.116
# Expected: Permission denied (publickey)
```

---

## 5. Day-to-Day Operations

### Connect

```bash
ssh homeserver
```

### Load Key Into Agent (if not auto-loaded)

```bash
ssh-add ~/.ssh/home-server
```

### Copy Files

```bash
# Local → Server
scp /local/path/file.txt homeserver:~/destination/

# Server → Local
scp homeserver:~/remote/file.txt /local/path/
```

### Port Forwarding

```bash
# Forward remote port 8080 to local 8080
ssh -L 8080:localhost:8080 homeserver

# SOCKS proxy
ssh -D 1080 homeserver
```

---

## 6. Key Management

| File | Location | Purpose |
|------|----------|---------|
| Private key | `~/.ssh/home-server` | **Never share or commit** |
| Public key | `~/.ssh/home-server.pub` | Deploy to servers |
| SSH config | `~/.ssh/config` | Alias definition |

### Rotate the SSH Key

If the key is compromised or needs rotation:

```bash
# 1. Generate a new key
ssh-keygen -t ed25519 -f ~/.ssh/home-server-new -C "home-server-mkanavi-rotated" -N ""

# 2. Deploy new key (while old key still works)
ssh-copy-id -i ~/.ssh/home-server-new.pub homeserver

# 3. Test new key works
ssh -i ~/.ssh/home-server-new mkanavi@192.168.0.116

# 4. Update ~/.ssh/config IdentityFile to point to home-server-new

# 5. Remove old key from server's authorized_keys
ssh homeserver "sed -i '/home-server-mkanavi$/d' ~/.ssh/authorized_keys"

# 6. Replace key files
mv ~/.ssh/home-server-new ~/.ssh/home-server
mv ~/.ssh/home-server-new.pub ~/.ssh/home-server.pub
```

---

## 7. Troubleshooting

### `Permission denied (publickey)`

```bash
# Check the key is loaded in the agent
ssh-add -l

# If not listed, add it
ssh-add ~/.ssh/home-server

# Test with verbose output
ssh -vvv homeserver 2>&1 | grep -E "Offering|Authenticated|denied"
```

### `Connection refused`

```bash
# Check if VM is reachable
ping 192.168.0.116

# If reachable, SSH may be down — requires console access:
# sudo systemctl start sshd
```

### `Connection timed out`

- Verify the VM is powered on
- Check the IP hasn't changed (DHCP): `arp -a | grep 192.168.0.116`
- Consider setting a static IP or DHCP reservation on your router for `192.168.0.116`

### Locked Out (Password Auth Disabled, Key Lost)

Requires physical access to the machine:
1. Boot into recovery mode or use a live USB
2. Mount the filesystem
3. Edit `/etc/ssh/sshd_config` — set `PasswordAuthentication yes` temporarily
4. Add your new public key to `/home/mkanavi/.ssh/authorized_keys`
5. Reboot and reconnect

---

## 8. Related Infrastructure

| Host | IP | Key | Alias | Purpose |
|------|----|-----|-------|---------|
| iacgenie-server | `192.168.0.118` | `~/.ssh/newvm_key` | `newvm` | Platform VM (iacgenie-platform) |
| Raspberry Pi | `192.168.0.101` | `~/.ssh/raspberry_key` | `rpi` | Raspberry Pi |
| **Home Server** | **`192.168.0.116`** | **`~/.ssh/home-server`** | **`homeserver`** | Home server |
| Gitea (via newvm) | `127.0.0.1:2222` | via `newvm` | `gitea` | Git/CI proxy |

---

## 9. Security Notes

| Control | Status | Detail |
|---------|--------|--------|
| Key type | ✅ ed25519 | Modern, compact, fast elliptic curve |
| IdentitiesOnly | ✅ yes | Prevents SSH agent from offering other keys |
| PreferredAuthentications | ✅ publickey only | No password fallback attempted |
| PasswordAuthentication | ✅ disabled on server | After hardening step |
| PermitRootLogin | ✅ no | Root SSH login blocked |
| StrictHostKeyChecking | ⚠️ no | Acceptable for LAN — no MITM risk on local network |
| AddKeysToAgent + UseKeychain | ✅ yes | macOS Keychain integration |
| Private key location | ✅ `~/.ssh/home-server` | Ensure FileVault (Mac disk encryption) is enabled |
