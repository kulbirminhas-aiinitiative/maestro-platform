# Terraform Module: Monitoring
# Prometheus + Grafana

resource "docker_volume" "prometheus_data" {
  name = "maestro_prometheus_data_${var.environment}"
}

resource "docker_volume" "grafana_data" {
  name = "maestro_grafana_data_${var.environment}"
}

resource "docker_image" "prometheus" {
  name         = "prom/prometheus:latest"
  keep_locally = true
}

resource "docker_image" "grafana" {
  name         = "grafana/grafana:latest"
  keep_locally = true
}

resource "docker_container" "prometheus" {
  name  = "maestro-prometheus-${var.environment}"
  image = docker_image.prometheus.image_id
  
  restart = "unless-stopped"
  
  command = [
    "--config.file=/etc/prometheus/prometheus.yml",
    "--storage.tsdb.path=/prometheus",
    "--storage.tsdb.retention.time=30d",
    "--web.console.libraries=/usr/share/prometheus/console_libraries",
    "--web.console.templates=/usr/share/prometheus/consoles",
    "--web.enable-lifecycle",
    "--web.enable-admin-api"
  ]
  
  ports {
    internal = 9090
    external = var.prometheus_port
  }
  
  volumes {
    volume_name    = docker_volume.prometheus_data.name
    container_path = "/prometheus"
  }
  
  volumes {
    host_path      = var.prometheus_config_path
    container_path = "/etc/prometheus"
    read_only      = true
  }
  
  networks_advanced {
    name = var.network_name
  }
  
  healthcheck {
    test     = ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:9090/-/healthy"]
    interval = "15s"
    timeout  = "5s"
    retries  = 3
  }
  
  labels {
    label = "maestro.service"
    value = "prometheus"
  }
}

resource "docker_container" "grafana" {
  name  = "maestro-grafana-${var.environment}"
  image = docker_image.grafana.image_id
  
  restart = "unless-stopped"
  
  env = [
    "GF_SECURITY_ADMIN_USER=${var.grafana_admin_user}",
    "GF_SECURITY_ADMIN_PASSWORD=${var.grafana_admin_password}",
    "GF_SERVER_ROOT_URL=http://localhost:${var.grafana_port}",
    "GF_DATABASE_TYPE=postgres",
    "GF_DATABASE_HOST=${var.postgres_host}:5432",
    "GF_DATABASE_NAME=grafana",
    "GF_DATABASE_USER=${var.postgres_admin_user}",
    "GF_DATABASE_PASSWORD=${var.postgres_admin_password}",
    "GF_USERS_ALLOW_ORG_CREATE=false",
    "GF_AUTH_ANONYMOUS_ENABLED=false",
    "GF_PATHS_PROVISIONING=/etc/grafana/provisioning"
  ]
  
  ports {
    internal = 3000
    external = var.grafana_port
  }
  
  volumes {
    volume_name    = docker_volume.grafana_data.name
    container_path = "/var/lib/grafana"
  }
  
  volumes {
    host_path      = var.grafana_provisioning_path
    container_path = "/etc/grafana/provisioning"
    read_only      = true
  }
  
  volumes {
    host_path      = var.grafana_dashboards_path
    container_path = "/var/lib/grafana/dashboards"
    read_only      = true
  }
  
  networks_advanced {
    name = var.network_name
  }
  
  healthcheck {
    test     = ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:3000/api/health"]
    interval = "15s"
    timeout  = "5s"
    retries  = 5
  }
  
  depends_on = [var.postgres_container_name]
  
  labels {
    label = "maestro.service"
    value = "grafana"
  }
}

output "prometheus_url" {
  value = "http://localhost:${var.prometheus_port}"
}

output "grafana_url" {
  value = "http://localhost:${var.grafana_port}"
}
