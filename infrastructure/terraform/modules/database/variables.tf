variable "environment" {
  description = "Environment name"
  type        = string
}

variable "network_name" {
  description = "Docker network name"
  type        = string
}

variable "admin_user" {
  description = "PostgreSQL admin username"
  type        = string
  default     = "maestro_admin"
}

variable "admin_password" {
  description = "PostgreSQL admin password"
  type        = string
  sensitive   = true
}

variable "redis_password" {
  description = "Redis password"
  type        = string
  sensitive   = true
}

variable "external_port" {
  description = "External port for PostgreSQL"
  type        = number
}

variable "redis_external_port" {
  description = "External port for Redis"
  type        = number
}

variable "init_scripts_path" {
  description = "Path to PostgreSQL init scripts"
  type        = string
}
