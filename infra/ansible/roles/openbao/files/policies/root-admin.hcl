# OpenBao policy for root/admin operations
# Scope: Full access to all paths (for bootstrap and admin tasks only)

path "*" {
  capabilities = ["create", "read", "update", "delete", "list", "sudo"]
}
