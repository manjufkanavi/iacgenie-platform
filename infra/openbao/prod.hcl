# =============================================================================
# OpenBao Production Configuration
# Managed by Ansible — DO NOT EDIT MANUALLY
# =============================================================================
# Version: 3.0
# Date: 2026-08-13
#
# Production-hardened OpenBao 2.6.0 configuration
# - TLS via Nginx reverse proxy (termination at edge)
# - Raft storage with integrated snapshot
# - Audit logging (enabled at runtime via `bao audit enable file`)
# - Prometheus telemetry
# =============================================================================

# === UI ===
ui = true

# === Telemetry ===
telemetry {
  prometheus_retention_time = "30s"
  disable_hostname          = true
}

# === Listener (HTTP for Nginx proxy termination) ===
listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1
}

# === Cluster address ===
cluster_addr = "https://127.0.0.1:8201"

# === Storage (Raft) ===
storage "raft" {
  path    = "/openbao/raft"
  node_id = "node1"

  # Raft performance tuning
  snapshot_interval = "30s"
  publish_leader_change = true
}

# === Audit logging ===
# NOTE: Audit is enabled at runtime via `bao audit enable file`
# The config file can specify the default audit directory.

# === Seal ===
# NOTE: Re-key management is configured at runtime via `bao operator migrate-key`
# For KMS sealing, add:
#   seal "transit" {
#     address = "https://openbao-transit:8200"
#     token   = "..."
#     secret_name = "openbao-unseal"
#   }

# === Default/Max Lease TTL ===
default_lease_ttl = "768h"
max_lease_ttl     = "768h"

# === API Addr (for cluster discovery) ===
api_addr = "https://127.0.0.1:8200"
