# Terraform Module: Network
# Creates Docker networks for Maestro Platform

terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

# Maestro shared network
resource "docker_network" "maestro_network" {
  name   = var.network_name
  driver = "bridge"
  
  labels {
    label = "maestro.network"
    value = "shared"
  }
  
  labels {
    label = "maestro.environment"
    value = var.environment
  }
  
  ipam_config {
    subnet  = var.subnet_cidr
    gateway = var.gateway
  }
}

output "network_name" {
  value = docker_network.maestro_network.name
}

output "network_id" {
  value = docker_network.maestro_network.id
}
