# 5 GHz Wi-Fi Migration & Troubleshooting Guide

**Document Version:** 1.0.0  
**Target Environments:** `homeserver` (\`192.168.0.116\`), `newvm` (\`192.168.0.118\`)  
**Network Hardware:** Realtek RTL8821CU USB 802.11ac NIC (\`0bda:c820\`)  
**OS:** Ubuntu 24.04 LTS / elementary OS 8 (Linux Kernel 6.17+)  
**Author:** Senior Network Engineering  

---

## 1. Executive Summary

This guide details the architectural migration of Linux infrastructure VMs from legacy single-band 2.4 GHz Wi-Fi (\`SilenceYourEgo_2.4g\`) to high-throughput 5 GHz Wi-Fi (\`SilenceYourEgo_5G\`). It documents root causes behind 5 GHz connection failures, the multi-band priority configuration deployed, safe headless cutover procedures, and a diagnostic runbook for VM users.

---

## 2. Infrastructure & Network Specifications

| Parameter | 2.4 GHz Network (Backup) | 5 GHz Network (Primary) |
| :--- | :--- | :--- |
| **SSID** | \`SilenceYourEgo_2.4g\` | \`SilenceYourEgo_5G\` |
| **BSSID (AP MAC)** | \`54:AF:97:2C:FB:22\` | \`54:AF:97:2C:FB:24\` |
| **Channel / Freq** | Channel 5 (2432 MHz) | Channel 36 (5180 MHz / UNII-1) |
| **Bandwidth** | 20/40 MHz | 80 MHz |
| **Security** | WPA2-PSK (AES-CCMP) | WPA2-PSK (AES-CCMP) |
| **Autoconnect Priority** | \`50\` (Failover) | \`100\` (Preferred) |
| **Pre-Shared Key** | \`AndYourPowerWillRise\` | \`AndYourPowerWillRise\` |

### Target Hosts Matrix

| Hostname | SSH Alias | Default IP | Wireless Interface | Dongle MAC |
| :--- | :--- | :--- | :--- | :--- |
| \`home-server\` | \`ssh homeserver\` | \`192.168.0.116\` | \`wlxe0ad4752659c\` | \`e0:ad:47:52:65:9c\` |
| \`vm.iacgenie.com\` | \`ssh newvm\` | \`192.168.0.118\` | \`wlx90de8031384d\` | \`90:de:80:31:38:4d\` |

---

## 3. Root Cause Analysis (RCA)

When attempting to connect headless VMs to 5 GHz APs, several systemic issues were diagnosed:

### 3.1. SSID Typo & Beacon Matching Failure
- **Issue:** Attempting to associate with \`SileneceYourEgo_5G\` (extra \`e\`).
- **Mechanism:** In 802.11 probe requests, SSID matching is strictly byte-for-byte. A mismatch results in \`wpa_supplicant\` timing out during probe scan with \`The Wi-Fi network could not be found\`.
- **Resolution:** Corrected SSID to broadcast beacon \`SilenceYourEgo_5G\`.

### 3.2. Missing NetworkManager Connection Profiles
- **Issue:** VMs provisioned via initial netplan installers had static profiles bound only to the 2.4 GHz SSID in \`/etc/netplan/\` and \`/etc/NetworkManager/system-connections/\`.
- **Mechanism:** NetworkManager will not auto-roam or attempt association with 5 GHz without an explicit \`802-11-wireless\` profile and stored credentials.

### 3.3. RF Propagation & Signal-to-Noise Ratio (SNR) Boundary
- **Issue:** Higher free-space path loss and wall absorption on 5.18 GHz:
  - 2.4 GHz RSSI: \`-66 dBm\` (~54% signal)
  - 5 GHz RSSI: \`-75 dBm\` to \`-81 dBm\` (~35–43% signal)
- **Mechanism:** 5 GHz signals attenuate rapidly through obstacles. If the signal drops below \`-82 dBm\`, 802.11ac MCS data rates downshift and frame retransmissions increase.
- **Resolution:** Retained 2.4 GHz profile with lower priority (\`50\`) to enable automatic failover if 5 GHz is momentarily obstructed.

### 3.4. Single-Uplink Headless Cutover Risk
- **Issue:** Changing Wi-Fi networks on headless servers over SSH risks complete loss of management access if association fails or DHCP times out.
- **Resolution:** Implemented an asynchronous **watchdog rollback pattern** that automatically falls back to 2.4 GHz if gateway reachability (\`192.168.0.1\`) is not confirmed within 60 seconds.

---

## 4. Applied Changes & Configuration

### 4.1. NetworkManager Dual-Band Priority Model

Both VMs are configured with multi-tier connection priorities:

\`\`\`bash
# 1. Primary 5 GHz Connection (Priority 100)
sudo nmcli con mod "SilenceYourEgo_5G" \
  connection.autoconnect yes \
  connection.autoconnect-priority 100 \
  802-11-wireless-security.key-mgmt wpa-psk \
  802-11-wireless-security.psk "AndYourPowerWillRise" \
  ipv4.method auto

# 2. Backup 2.4 GHz Connection (Priority 50)
sudo nmcli con mod "SilenceYourEgo_2.4g" \
  connection.autoconnect yes \
  connection.autoconnect-priority 50
\`\`\`

### 4.2. Headless Safe Cutover Script Pattern

When switching Wi-Fi on any headless VM, execute the following fail-safe wrapper:

\`\`\`bash
#!/usr/bin/env bash
set -euo pipefail

GATEWAY="192.168.0.1"
BACKUP_CON="SilenceYourEgo_2.4g"
TARGET_CON="SilenceYourEgo_5G"

# Launch background watchdog (60 second timeout)
(
  sleep 60
  if ! ping -c 2 -W 2 "${GATEWAY}" >/dev/null 2>&1; then
    logger -t wifi-watchdog "5G gateway unreachable! Reverting to ${BACKUP_CON}"
    sudo nmcli con up "${BACKUP_CON}"
  else
    logger -t wifi-watchdog "5G connection healthy and verified."
  fi
) &

# Activate 5 GHz profile
sudo nmcli con up "${TARGET_CON}"
\`\`\`

---

## 5. VM User Troubleshooting & Diagnostics Runbook

Follow these sequential steps if Wi-Fi connection drops or fails to connect:

\`\`\`
                  +--------------------------------+
                  |  WiFi Connectivity Issue       |
                  +---------------+----------------+
                                  |
                                  v
                  +--------------------------------+
                  | Step 1: Check Physical/USB NIC |
                  | lsusb | grep -i realtek        |
                  +---------------+----------------+
                                  |
                                  v
                  +--------------------------------+
                  | Step 2: Verify RF Frequencies  |
                  | sudo nmcli dev wifi list       |
                  +---------------+----------------+
                                  |
                                  v
                  +--------------------------------+
                  | Step 3: Check WPA Handshake    |
                  | journalctl -u wpa_supplicant   |
                  +---------------+----------------+
                                  |
                                  v
                  +--------------------------------+
                  | Step 4: Validate IP & Gateway  |
                  | ip addr; ping 192.168.0.1      |
                  +---------------+----------------+
\`\`\`

### Step 1: Verify USB Hardware & Kernel Module
\`\`\`bash
# Check USB device enumeration
lsusb | grep -i "0bda:c820"

# Verify driver state
lsmod | grep rtw88

# Check rfkill state
rfkill list all
\`\`\`
*Expected: \`phy: Wireless LAN\` Soft blocked: no, Hard blocked: no.*

---

### Step 2: Scan for Available Access Points
\`\`\`bash
# Rescan airwaves
sudo nmcli dev wifi rescan

# Check 2.4G and 5G signals
nmcli -f BSSID,SSID,CHAN,FREQ,SIGNAL,BARS dev wifi list | grep -E "Silence|SSID"
\`\`\`
*Expected Output:*
\`\`\`text
BSSID              SSID                 CHAN  FREQ      SIGNAL  BARS 
54:AF:97:2C:FB:24  SilenceYourEgo_5G    36    5180 MHz  35-45   ▂▄__ 
54:AF:97:2C:FB:22  SilenceYourEgo_2.4g  5     2432 MHz  45-55   ▂▄__ 
\`\`\`

---

### Step 3: Check Association & Supplicant Logs
\`\`\`bash
# Monitor real-time authentication events
sudo journalctl -u wpa_supplicant -n 40 --no-pager
\`\`\`
*Key Events to Look For:*
- \`Associated with 54:af:97:2c:fb:24\` → L2 Association successful.
- \`WPA: Key negotiation completed [PTK=CCMP GTK=CCMP]\` → 4-Way Handshake OK.
- \`CTRL-EVENT-BEACON-LOSS\` or \`signal=-9999\` → RF signal too weak / physical obstruction.

---

### Step 4: Verify IP & Routing
\`\`\`bash
# Check assigned IPv4
ip -4 addr show dev $(nmcli -t -f DEVICE,TYPE dev | grep wifi | cut -d: -f1)

# Check default gateway
ip route show default

# Ping Gateway and Internet
ping -c 3 192.168.0.1
ping -c 3 1.1.1.1
\`\`\`

---

### Step 5: Manual Recovery Commands

If 5 GHz is unstable due to temporary RF interference:

\`\`\`bash
# Switch back to 2.4 GHz immediately
sudo nmcli con up "SilenceYourEgo_2.4g"

# Force switch to 5 GHz
sudo nmcli con up "SilenceYourEgo_5G"

# Restart NetworkManager stack if unresponsive
sudo systemctl restart NetworkManager
\`\`\`

---

## 6. Verification Checklist

- [x] Both \`homeserver\` and \`newvm\` associated to \`SilenceYourEgo_5G\` (5.18 GHz / Channel 36).
- [x] DHCP IPv4 lease bound (\`192.168.0.116\` on homeserver, \`192.168.0.118\` on newvm).
- [x] Priority 100 (5G) / Priority 50 (2.4G) established on all NetworkManager profiles.
- [x] Sub-20ms latency to gateway \`192.168.0.1\` and 0% packet loss to \`1.1.1.1\`.
- [x] Headless SSH connectivity confirmed via \`ssh homeserver\` and \`ssh newvm\`.
