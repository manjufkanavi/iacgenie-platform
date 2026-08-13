# OpenBao policy for iacgenie-backend service
# Scope: Read access to iacgenie backend secrets only
# Prevents access to lightserp, terraform, or system paths

path "iacgenie/data/config/platform/*" {
  capabilities = ["read"]
}

path "iacgenie/data/config/keycloak/*" {
  capabilities = ["read"]
}

path "iacgenie/data/config/minio/*" {
  capabilities = ["read"]
}

path "iacgenie/data/config/platform" {
  capabilities = ["read"]
}

path "iacgenie/data/config/keycloak" {
  capabilities = ["read"]
}

path "iacgenie/data/config/minio" {
  capabilities = ["read"]
}
