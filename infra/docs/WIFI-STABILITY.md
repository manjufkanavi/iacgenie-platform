# WiFi Stability — Infrastructure Runbook

**Last Updated:** 2026-08-23  
**Applies To:** homeserver (192.168.0.116), newvm (192.168.0.118)  
**OS:** elementary OS 8 (Ubuntu 24.04 Noble base)  
**Author:** Senior Network Engineer (20yr) — automated via Antigravity

---

## Problem Statement

Both VMs use **USB WiFi dongles** (`wlx`-prefixed interfaces). WiFi connection
frequently goes stale or drops silently, causing SSH timeouts and service
interruptions. The physical RF signal is stable — this is a Linux OS / driver
power management problem.

---

## Root Cause Analysis

### 1. USB WiFi Adapters (Structural Risk)

| VM | Interface | Type |
|----|-----------|------|
| homeserver | `wlxe0ad4752659c` | USB WiFi dongle |
| newvm | `wlx90de8031384d` | USB WiFi dongle |

The `wlx` prefix (MAC-derived) confirms USB-attached adapters. USB WiFi on
Linux is inherently less stable than PCIe/M.2 due to:
- USB bus power management suspending the device
- Driver interaction with `wpa_supplicant` keepalive
- Silent de-authentication without NM reconnect trigger

### 2. WiFi Power Management (homeserver was ON)

```
homeserver → Power Management: on   ← PROBLEM (was causing drops)
newvm      → Power Management: off  ← was already correct
```

With power management on, the WiFi chip reduces polling frequency when idle,
misses AP beacons, and silently loses association.

### 3. USB Autosuspend Enabled (Both VMs)

```bash
cat /sys/class/net/wlx.../power/control  # was: "auto" → now: "on"
```

Kernel USB autosuspend (default: 2s) powers down the USB WiFi chip after
inactivity. The driver loses its firmware context, causing a full
re-association cycle (10–30s outage each time).

### 4. NetworkManager Not Tuned for Stability

- No `wifi.powersave = 2` in global NM config
- Default DHCP timeout of 45s (causes 45s blackout per reconnect)
- IPv6 DHCP transactions causing duplicate reconnect events in logs
- No dispatcher hook to re-enforce power-off after NM reconnect

### 5. TCP Keepalive Too Slow

```
Before: keepalive_time=7200s (2 hours) — SSH goes zombie for hours
After:  keepalive_time=60s             — dead connection detected in ~2 min
```

---

## Applied Fixes

All fixes applied 2026-08-23 to both VMs via SSH. **No reboots required.**

### Fix 1 — Disable USB Autosuspend

**File:** `/etc/udev/rules.d/70-wifi-usb-powersave.rules`

```udev
ACTION=="add", SUBSYSTEM=="usb", TEST=="power/control", ATTR{power/control}="on"
ACTION=="add", SUBSYSTEM=="usb", TEST=="power/autosuspend_delay_ms", ATTR{power/autosuspend_delay_ms}="-1"
```

Activated immediately via `udevadm control --reload-rules && udevadm trigger`.
Persists across reboots.

---

### Fix 2 — Disable WiFi Power Management Globally (NM)

**File:** `/etc/NetworkManager/conf.d/wifi-stable.conf`

```ini
[connection]
wifi.powersave = 2

[device]
wifi.scan-rand-mac-address=no
```

`wifi.powersave = 2` = **disabled** (1=default, 2=disabled, 3=enabled).

---

### Fix 3 — NM Dispatcher Hook (Enforce on Every Reconnect)

**File:** `/etc/NetworkManager/dispatcher.d/99-wifi-powersave`

```bash
#!/bin/bash
IFACE=$1; EVENT=$2
if [[ "$EVENT" == "up" ]] && [[ "$IFACE" == wl* ]]; then
  /sbin/iwconfig "$IFACE" power off 2>/dev/null || true
  echo "on" > /sys/class/net/$IFACE/power/control 2>/dev/null || true
  logger -t wifi-dispatcher "Power management disabled on $IFACE"
fi
```

Called by NM every time a WiFi interface comes up. Ensures power management
is disabled even after NM-triggered reconnects (which reset iwconfig state).

---

### Fix 4 — NM Connection Profile Tuning

Applied via `nmcli con mod "SilenceYourEgo_2.4g"` on both VMs:

| Setting | Before | After | Reason |
|---------|--------|-------|--------|
| `wifi.powersave` | default (1) | 2 (disabled) | Stop adapter power saving |
| `ipv4.dhcp-timeout` | 45s | 15s | Faster reconnect on DHCP loss |
| `connection.autoconnect` | yes | yes | Ensure auto-reconnect |
| `connection.autoconnect-priority` | 0 | 100 | Highest priority reconnect |
| `connection.autoconnect-retries` | 3 | 0 (forever) | Never give up reconnecting |
| `ipv6.method` | auto | disabled | Eliminate duplicate DHCP cycles |

---

### Fix 5 — TCP Keepalive Tuning

**File:** `/etc/sysctl.d/99-wifi-keepalive.conf`

```ini
# Detect dead TCP connections within ~2 minutes instead of 2+ hours
net.ipv4.tcp_keepalive_time = 60
net.ipv4.tcp_keepalive_intvl = 10
net.ipv4.tcp_keepalive_probes = 6
```

Applied immediately with `sysctl -p`. Dead SSH sessions now detected and
cleaned up within ~2 minutes of a WiFi drop (previously could take 2+ hours).

---

### Fix 6 — WiFi Watchdog (30s Auto-Recovery)

**Script:** `/usr/local/bin/wifi-watchdog.sh`  
**Service:** `/etc/systemd/system/wifi-watchdog.service`  
**Timer:** `/etc/systemd/system/wifi-watchdog.timer`

The watchdog runs every 30 seconds:
1. Identifies the active WiFi interface via `nmcli`
2. Pings the default gateway with 2 probes, 3s timeout
3. If gateway is unreachable → triggers NM `con down` + `con up`
4. Re-enforces `iwconfig power off` after reconnect
5. Logs all events to `/var/log/wifi-watchdog.log`

```bash
# Check watchdog status
systemctl status wifi-watchdog.timer

# Watch live log
tail -f /var/log/wifi-watchdog.log
```

---

## File Inventory

| File | VM | Purpose |
|------|----|---------|
| `/etc/udev/rules.d/70-wifi-usb-powersave.rules` | Both | Disable USB autosuspend |
| `/etc/NetworkManager/conf.d/wifi-stable.conf` | Both | Global NM wifi.powersave=2 |
| `/etc/NetworkManager/dispatcher.d/99-wifi-powersave` | Both | Re-enforce power-off on reconnect |
| `/etc/sysctl.d/99-wifi-keepalive.conf` | Both | Faster TCP keepalive |
| `/usr/local/bin/wifi-watchdog.sh` | Both | Gateway ping watchdog |
| `/etc/systemd/system/wifi-watchdog.service` | Both | Watchdog oneshot service |
| `/etc/systemd/system/wifi-watchdog.timer` | Both | 30s watchdog timer |

---

## Verification Commands

```bash
# 1. Confirm power management is OFF
iwconfig wlx* | grep -i power
# Expected: Power Management:off

# 2. Confirm USB autosuspend is disabled
cat /sys/bus/usb/devices/*/power/control 2>/dev/null | sort -u
# Expected: all "on"

# 3. Confirm TCP keepalive
sysctl net.ipv4.tcp_keepalive_time
# Expected: net.ipv4.tcp_keepalive_time = 60

# 4. Confirm watchdog is running
systemctl status wifi-watchdog.timer --no-pager
# Expected: Active: active (waiting)

# 5. Check watchdog log
tail -20 /var/log/wifi-watchdog.log
# Expected: "OK: wlx... → gateway ... reachable" every 30s

# 6. Confirm NM profile settings
nmcli con show "SilenceYourEgo_2.4g" | grep -E 'powersave|dhcp-timeout|autoconnect|ipv6.method'
```

---

## Monitoring

### Check Both VMs at Once (from Mac)

```bash
# Quick health check
for vm in homeserver newvm; do
  echo "=== $vm ==="
  ssh $vm "iwconfig \$(ip link | grep -oP 'wl\S+' | head -1) | grep Power; \
           systemctl is-active wifi-watchdog.timer; \
           tail -1 /var/log/wifi-watchdog.log 2>/dev/null"
done
```

### Watchdog Log Location

```
/var/log/wifi-watchdog.log
```

Sample healthy output:
```
2026-08-23 16:20:01 OK: wlxe0ad4752659c → gateway 192.168.0.1 reachable
2026-08-23 16:20:31 OK: wlxe0ad4752659c → gateway 192.168.0.1 reachable
```

Sample recovery event:
```
2026-08-23 16:25:01 WARN: Gateway 192.168.0.1 unreachable via wlxe0ad4752659c — triggering reconnect
2026-08-23 16:25:06 INFO: Reconnected 'SilenceYourEgo_2.4g' on wlxe0ad4752659c
```

---

## Long-Term Recommendation

> **USB WiFi dongles are not production-grade for always-on servers.**
>
> Even with all fixes applied, a USB adapter can still be reset by the OS or
> lose firmware context on kernel events. For permanent stability, consider:
>
> - **Option A:** USB-to-Ethernet adapter + wired connection (most reliable)
> - **Option B:** PCIe/M.2 WiFi card (if mini-PC has M.2 slot)
> - **Option C:** Powerline ethernet adapter (no cable runs needed)
>
> The watchdog ensures **auto-recovery within 30 seconds** of any WiFi drop,
> which is acceptable for a home lab / dev server use case.

---

## Related Docs

- [HOME-SERVER.md](./HOME-SERVER.md) — homeserver SSH setup
- [INFRA-DESIGN.md](./INFRA-DESIGN.md) — full infrastructure overview
- [DEPLOY.md](./DEPLOY.md) — deployment procedures
