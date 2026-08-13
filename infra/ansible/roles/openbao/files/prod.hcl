# =============================================================================
# OpenBao Production Configuration
# Managed by Ansible — DO NOT EDIT MANUALLY
# =============================================================================
# OpenBao 2.6.0 production config
# - TLS via Nginx reverse proxy (termination at edge)
# - Raft storage with integrated snapshot
# - Prometheus telemetry
# =============================================================================

# === UI ===
ui = true

# === Telemetry ===
telemetry {
  prometheus_retention_time = "30s"
  disable_hostname          = true
}

# === Listener (TLS via Nginx — bind to localhost for Docker) ===
# OpenBao listens on 127.0.0.1 only. Nginx handles external TLS termination.
listener "tcp" {
  address     = "127.0.0.1:8200"
  tls_disable = 0

  tls_cert_file = "/etc/letsencrypt/live/vault.iacgenie.com/fullchain.pem"
  tls_key_file  = "/etc/letsencrypt/live/vault.iacgenie.com/privkey.pem"
}

# === Cluster address (TLS for single-node) ===
cluster_addr = "https://127.0.0.1:8201"

# === Storage (Raft) ===
storage "raft" {
  path    = "/openbao/raft"
  node_id = "node1"
}

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

# === API Addr (for cluster discovery — TLS) ===
api_addr = "https://127.0.0.1:8200"

# === Log level ===
# NOTE: Log level is controlled via OPENBAO_LOG_LEVEL env var
log_level = "info"

# === Audit ===
# NOTE: Audit is enabled at runtime via `bao audit enable file`
# File-based audit configured at runtime for security:
# audit "file" {
#   file_path = "/openbao/audit/audit.log"
#   mode      = "0640"
# }

# === Disable memory lock (allowed in Docker) ===
disable_mlock = true
