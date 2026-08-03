resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = var.repository_id
  format        = "DOCKER"
}

output "url" {
  value = google_artifact_registry_repository.docker.uri
}
