# OpenBao policy for lightserp-api service
# Scope: Read access to lightserp secrets only
# Prevents access to iacgenie, terraform, or system paths

path "lightserp/data/config/lightserp/*" {
  capabilities = ["read"]
}

path "lightserp/data/config/minio/*" {
  capabilities = ["read"]
}

path "lightserp/data/config/redis/*" {
  capabilities = ["read"]
}

path "lightserp/data/config/lightserp" {
  capabilities = ["read"]
}

path "lightserp/data/config/minio" {
  capabilities = ["read"]
}

path "lightserp/data/config/redis" {
  capabilities = ["read"]
}
