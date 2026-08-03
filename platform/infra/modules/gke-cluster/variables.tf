variable "cluster_name" {
  type = string
}

variable "zone" {
  type    = string
  default = "us-central1-a"
}

variable "network" {
  type = string
}

variable "subnetwork" {
  type = string
}

variable "node_count" {
  type    = number
  default = 1
}
