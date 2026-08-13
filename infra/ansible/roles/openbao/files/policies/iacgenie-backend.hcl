path "iacgenie/data/" {
  capabilities = ["read"]
}

path "iacgenie/data/*" {
  capabilities = ["read"]
}

path "iacgenie/metadata/*" {
  capabilities = ["read", "list"]
}

path "lightserp/data/" {
  capabilities = ["read"]
}

path "lightserp/data/*" {
  capabilities = ["read"]
}

path "lightserp/metadata/*" {
  capabilities = ["read", "list"]
}
