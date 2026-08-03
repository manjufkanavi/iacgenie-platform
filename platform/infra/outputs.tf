output "gke_cluster_endpoint" {
  value = module.gke-cluster.endpoint
}

output "gke_cluster_ca_certificate" {
  value = module.gke-cluster.ca_certificate
}

output "cloud_sql_connection_name" {
  value = module.cloud-sql.connection_name
}

output "memorystore_host" {
  value = module.cloud-memory-store.host
}

output "artifact_registry_url" {
  value = module.artifact-registry.url
}
