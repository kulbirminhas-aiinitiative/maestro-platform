variable "postgres_admin_user" {
  description = "PostgreSQL admin username"
  type        = string
  default     = "maestro_admin"
}

variable "postgres_admin_password" {
  description = "PostgreSQL admin password"
  type        = string
  sensitive   = true
}

variable "redis_password" {
  description = "Redis password"
  type        = string
  sensitive   = true
}

variable "grafana_admin_user" {
  description = "Grafana admin username"
  type        = string
  default     = "admin"
}

variable "grafana_admin_password" {
  description = "Grafana admin password"
  type        = string
  sensitive   = true
}

variable "postgres_port" {
  description = "External port for PostgreSQL"
  type        = number
  default     = 25432
}

variable "redis_port" {
  description = "External port for Redis"
  type        = number
  default     = 27379
}

variable "prometheus_port" {
  description = "External port for Prometheus"
  type        = number
  default     = 29090
}

variable "grafana_port" {
  description = "External port for Grafana"
  type        = number
  default     = 23000
}
