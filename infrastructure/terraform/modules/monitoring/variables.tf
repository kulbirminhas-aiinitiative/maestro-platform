variable "environment" {
  type = string
}

variable "network_name" {
  type = string
}

variable "prometheus_port" {
  type = number
}

variable "grafana_port" {
  type = number
}

variable "grafana_admin_user" {
  type    = string
  default = "admin"
}

variable "grafana_admin_password" {
  type      = string
  sensitive = true
}

variable "postgres_host" {
  type = string
}

variable "postgres_admin_user" {
  type = string
}

variable "postgres_admin_password" {
  type      = string
  sensitive = true
}

variable "postgres_container_name" {
  type = string
}

variable "prometheus_config_path" {
  type = string
}

variable "grafana_provisioning_path" {
  type = string
}

variable "grafana_dashboards_path" {
  type = string
}
