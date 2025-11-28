# Terraform Module: Database
# PostgreSQL with multi-database setup

resource "docker_volume" "postgres_data" {
  name = "maestro_postgres_data_${var.environment}"
  
  labels {
    label = "maestro.volume"
    value = "postgres"
  }
  
  labels {
    label = "maestro.environment"
    value = var.environment
  }
}

resource "docker_image" "postgres" {
  name         = "postgres:15"
  keep_locally = true
}

resource "docker_container" "postgres" {
  name  = "maestro-postgres-${var.environment}"
  image = docker_image.postgres.image_id
  
  restart = "unless-stopped"
  
  env = [
    "POSTGRES_USER=${var.admin_user}",
    "POSTGRES_PASSWORD=${var.admin_password}",
    "POSTGRES_INITDB_ARGS=--encoding=UTF8 --lc-collate=en_US.utf8 --lc-ctype=en_US.utf8"
  ]
  
  ports {
    internal = 5432
    external = var.external_port
  }
  
  volumes {
    volume_name    = docker_volume.postgres_data.name
    container_path = "/var/lib/postgresql/data"
  }
  
  volumes {
    host_path      = var.init_scripts_path
    container_path = "/docker-entrypoint-initdb.d"
    read_only      = true
  }
  
  networks_advanced {
    name = var.network_name
  }
  
  healthcheck {
    test     = ["CMD-SHELL", "pg_isready -U ${var.admin_user}"]
    interval = "10s"
    timeout  = "5s"
    retries  = 5
  }
  
  labels {
    label = "maestro.service"
    value = "postgres"
  }
  
  labels {
    label = "maestro.layer"
    value = "infrastructure"
  }
  
  labels {
    label = "maestro.environment"
    value = var.environment
  }
}

# Redis
resource "docker_volume" "redis_data" {
  name = "maestro_redis_data_${var.environment}"
  
  labels {
    label = "maestro.volume"
    value = "redis"
  }
}

resource "docker_image" "redis" {
  name         = "redis:7-alpine"
  keep_locally = true
}

resource "docker_container" "redis" {
  name  = "maestro-redis-${var.environment}"
  image = docker_image.redis.image_id
  
  restart = "unless-stopped"
  
  command = [
    "redis-server",
    "--requirepass", var.redis_password,
    "--appendonly", "yes",
    "--appendfsync", "everysec",
    "--maxmemory", "2gb",
    "--maxmemory-policy", "allkeys-lru"
  ]
  
  ports {
    internal = 6379
    external = var.redis_external_port
  }
  
  volumes {
    volume_name    = docker_volume.redis_data.name
    container_path = "/data"
  }
  
  networks_advanced {
    name = var.network_name
  }
  
  healthcheck {
    test     = ["CMD", "redis-cli", "--raw", "incr", "ping"]
    interval = "10s"
    timeout  = "3s"
    retries  = 5
  }
  
  labels {
    label = "maestro.service"
    value = "redis"
  }
  
  labels {
    label = "maestro.layer"
    value = "infrastructure"
  }
}

output "postgres_container_name" {
  value = docker_container.postgres.name
}

output "redis_container_name" {
  value = docker_container.redis.name
}

output "postgres_port" {
  value = var.external_port
}

output "redis_port" {
  value = var.redis_external_port
}
