# CrowdSec Setup & Status

This document tracks the deployment status of CrowdSec across the infrastructure.

## Mac Studio (192.168.0.120)
**Status**: ✅ Installed and Enrolled

* **Deployment Method**: Docker Container
* **Port Mapping**: `8090:8080` (Port 8080 was conflicting with an existing service)
* **Volumes**: 
  * `/var/lib/crowdsec/data` (for local database persistence)
  * `/etc/crowdsec` (for configurations)
  * `/var/log` (Read-only, for log parsing)
* **Autostart Configuration**: 
  * The Docker container is configured with the `--restart unless-stopped` policy.
  * **Requirement:** "Start Docker Desktop when you log in" must be enabled in Docker Desktop settings for autostart to trigger on system boot.

## Linux VM (192.168.0.118)
**Status**: ⏸️ Installation Pending / Blocked

### Blockers Encountered:
1. **Network Instability**: The VM is currently experiencing severe packet loss (~33%) and high latency (>1500ms), causing all downloads from the CrowdSec package repository to time out.
2. **Sudo Password Restriction**: To comply with the strict "SSH Key Only" mandate and avoid piping plaintext passwords into `sudo` over SSH, **passwordless `sudo`** must be configured for the `mkanavi` user before automated installation can succeed.

### Resolved Issues:
* **HashiCorp Apt Repository Bug**: A syntax error in `/etc/apt/sources.list.d/hashicorp.list` (specifically `$(lsb_release Release`) was breaking `apt-get update`. This has been permanently patched.
* **IPv6 Package Hangs**: Configured `apt` to use `Acquire::ForceIPv4=true` to bypass IPv6 routing hangs when communicating with `packagecloud.io`.

### Next Steps / Manual Installation:
Once network stability is restored and/or passwordless sudo is configured, run the following commands directly on the VM:

1. **Install CrowdSec**:
   ```bash
   curl -s https://install.crowdsec.net | sudo os=ubuntu dist=noble bash
   sudo apt-get install crowdsec crowdsec-firewall-bouncer-iptables -y
   ```
2. **Enroll in Console**:
   ```bash
   sudo cscli console enroll <your_enroll_key>
   sudo systemctl restart crowdsec
   ```
