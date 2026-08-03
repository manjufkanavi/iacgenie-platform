resource "google_container_cluster" "primary" {
  name     = var.cluster_name
  location = var.zone

  node_pool {
    name               = "default-node-pool"
    initial_node_count = var.node_count

    autoscaling {
      min_node_count = 1
      max_node_count = 15
    }
  }

  network    = var.network
  subnetwork = var.subnetwork
}

output "endpoint" {
  value = google_container_cluster.primary.endpoint
}

output "ca_certificate" {
  value = google_container_cluster.primary.master_auth[0].cluster_ca_certificate
}
