resource "google_sql_database_instance" "primary" {
  name             = var.database_name
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier = "db-f1-micro"
  }

  deletion_protection = true
}

resource "google_sql_database" "database" {
  name     = var.database_name
  instance = google_sql_database_instance.primary.name
}

output "connection_name" {
  value = google_sql_database_instance.primary.connection_name
}
