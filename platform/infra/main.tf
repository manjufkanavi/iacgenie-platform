provider "google" {
  project = var.project_id
  region  = var.region
}

module "networking" {
  source     = "./modules/networking"
  vpc_cidr   = "10.0.0.0/16"
  project_id = var.project_id
}

module "gke-cluster" {
  source       = "./modules/gke-cluster"
  cluster_name = "iacgenie-${var.environment}"
  node_count   = var.environment == "production" ? 3 : 1
  network      = module.networking.vpc_name
  subnetwork   = module.networking.subnet_name
}

module "cloud-sql" {
  source        = "./modules/cloud-sql"
  database_name = "iacgenie"
  project_id    = var.project_id
}

module "cloud-memory-store" {
  source        = "./modules/cloud-memory-store"
  instance_name = "iacgenie-redis"
  project_id    = var.project_id
}

module "artifact-registry" {
  source        = "./modules/artifact-registry"
  repository_id = "iacgenie-docker"
  project_id    = var.project_id
}
