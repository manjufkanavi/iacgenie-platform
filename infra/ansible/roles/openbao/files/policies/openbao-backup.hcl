# OpenBao policy for backup operations
# Scope: Read-only access to snapshot and audit data

path "sys/storage/raft/snapshot" {
  capabilities = ["read"]
}

path "sys/storage/raft/restore" {
  capabilities = ["sudo"]
}

path "sys/storage/raft/snapshot/manual" {
  capabilities = ["read"]
}

path "iacgenie/data/*" {
  capabilities = ["read", "list"]
}

path "lightserp/data/*" {
  capabilities = ["read", "list"]
}

path "terraform/data/*" {
  capabilities = ["read", "list"]
}

path "iacgenie/data" {
  capabilities = ["read", "list"]
}

path "lightserp/data" {
  capabilities = ["read", "list"]
}

path "terraform/data" {
  capabilities = ["read", "list"]
}
