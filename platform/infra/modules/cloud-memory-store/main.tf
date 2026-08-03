resource "google_redis_instance" "primary" {
  name           = var.instance_name
  tier           = "BASIC"
  memory_size_gb = 1

  location_id   = var.zone
  redis_version = "REDIS_7_0"
}

output "host" {
  value = google_redis_instance.primary.host
}
