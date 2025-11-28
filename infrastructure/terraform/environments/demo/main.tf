# Maestro Platform - Demo Environment Infrastructure
# Single command deployment: terraform apply -auto-approve

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
  
  backend "local" {
    path = "terraform.tfstate"
  }
}

provider "docker" {
  host = "unix:///var/run/docker.sock"
}

# Network Module
module "network" {
  source = "../../modules/network"
  
  network_name = "maestro-network"
  environment  = "demo"
  subnet_cidr  = "172.28.0.0/16"
  gateway      = "172.28.0.1"
}

# Database Module
module "database" {
  source = "../../modules/database"
  
  environment         = "demo"
  network_name        = module.network.network_name
  admin_user          = var.postgres_admin_user
  admin_password      = var.postgres_admin_password
  redis_password      = var.redis_password
  external_port       = var.postgres_port
  redis_external_port = var.redis_port
  init_scripts_path   = abspath("${path.module}/../../databases/postgres/init-scripts")
  
  depends_on = [module.network]
}

# Monitoring Module
module "monitoring" {
  source = "../../modules/monitoring"
  
  environment               = "demo"
  network_name              = module.network.network_name
  prometheus_port           = var.prometheus_port
  grafana_port              = var.grafana_port
  grafana_admin_user        = var.grafana_admin_user
  grafana_admin_password    = var.grafana_admin_password
  postgres_host             = "maestro-postgres-demo"
  postgres_admin_user       = var.postgres_admin_user
  postgres_admin_password   = var.postgres_admin_password
  postgres_container_name   = module.database.postgres_container_name
  prometheus_config_path    = abspath("${path.module}/../../monitoring/prometheus")
  grafana_provisioning_path = abspath("${path.module}/../../monitoring/grafana/provisioning")
  grafana_dashboards_path   = abspath("${path.module}/../../monitoring/grafana/dashboards")
  
  depends_on = [module.database]
}

# Outputs
output "infrastructure_urls" {
  value = {
    postgres   = "postgresql://${var.postgres_admin_user}:***@localhost:${var.postgres_port}"
    redis      = "redis://:***@localhost:${var.redis_port}"
    prometheus = module.monitoring.prometheus_url
    grafana    = module.monitoring.grafana_url
  }
}

output "service_connection_strings" {
  value = {
    quality_fabric = {
      postgres = "postgresql://quality_fabric:***@maestro-postgres-demo:5432/quality_fabric"
      redis    = "redis://:***@maestro-redis-demo:6379/0"
    }
    maestro_v2 = {
      postgres = "postgresql://maestro_v2:***@maestro-postgres-demo:5432/maestro_v2"
      redis    = "redis://:***@maestro-redis-demo:6379/1"
    }
  }
  description = "Connection strings for services (internal Docker network)"
}

output "network_name" {
  value = module.network.network_name
}
