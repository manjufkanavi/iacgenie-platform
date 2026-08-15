# =============================================================================
# OpenBao Production Configuration
# Managed by Ansible — DO NOT EDIT MANUALLY
# =============================================================================
# OpenBao 2.6.0 production config
# - TLS terminated at Cloudflare edge / Nginx reverse proxy
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

# === Listener (TLS — mutual auth for internal services) ===
listener "tcp" {
  address     = "127.0.0.1:8200"
  tls_disable = 0

  tls_cert_file   = "/openbao/raft/server.crt"
  tls_key_file    = "/openbao/raft/server.key"
  tls_client_ca_file = "/openbao/raft/ca.crt"
}

# === Cluster address (HTTPS for single-node) ===
cluster_addr = "https://127.0.0.1:8201"

# === Storage (Raft) ===
storage "raft" {
  path    = "/openbao/raft"
  node_id = "node1"
}

# === Default/Max Lease TTL ===
default_lease_ttl = "768h"
max_lease_ttl     = "768h"

# === API Addr (for cluster discovery — HTTP) ===
api_addr = "http://127.0.0.1:8200"

# === Log level ===
log_level = "info"
